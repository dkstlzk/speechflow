"""Optional post-session speaker diarization worker.

Executes: Pyannote diarization -> alignment with existing chunks -> DB update.
"""

import os
import threading
from pathlib import Path
from typing import Optional

from ..config.logging import get_logger
from ..config.settings import settings
from ..models.enums import SessionStatus
from ..services.diarization import DiarizationService
from ..services.persistence.session_repository import update_session_status, get_session_by_id
from ..services.persistence.speaker_repository import get_or_create_speaker
from ..services.persistence.transcript_repository import list_transcript_chunks, update_chunk_speakers
from ..services.transcription.transcript_service import align_transcript_with_speakers
from ..db.session import SessionLocal

logger = get_logger("workers.diarization")


from ..services.transcription import WhisperTranscriptionService
from ..services.persistence.transcript_repository import replace_session_chunks

import torchaudio
import numpy as np
from sklearn.cluster import AgglomerativeClustering

_EMBEDDING_MODEL = None
_EMBEDDING_INFERENCE = None
_EMBEDDING_LOCK = threading.Lock()

def _get_embedding_inference():
    global _EMBEDDING_MODEL, _EMBEDDING_INFERENCE
    if _EMBEDDING_INFERENCE is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_INFERENCE is None:
                from pyannote.audio import Model, Inference
                logger.info("[DiarizationWorker] Downloading or loading embedding model pyannote/wespeaker-voxceleb-resnet34-LM from Hugging Face. This may take a moment on first run.")
                _EMBEDDING_MODEL = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM")
                _EMBEDDING_INFERENCE = Inference(_EMBEDDING_MODEL, window="whole")
    return _EMBEDDING_INFERENCE

def process_quick_diarization(session_id: int) -> None:
    """Extract embeddings per chunk and cluster them to assign speakers."""
    logger.info(f"[DiarizationWorker] Started QUICK diarization for session={session_id}")

    db = SessionLocal()
    try:
        import time
        for _ in range(10):
            session = get_session_by_id(db, session_id)
            if not session:
                logger.error(f"[DiarizationWorker] Session {session_id} not found")
                return
            if session.audio_path:
                break
            logger.info(f"[DiarizationWorker] Waiting for audio_path for session={session_id}...")
            time.sleep(1)
            db.expire_all() # Clear SQLAlchemy identity map cache
            
        if not session.audio_path:
            logger.error(f"[DiarizationWorker] Session {session_id} missing audio_path after timeout")
            return

        storage_dir = Path(settings.EXPORT_DIR).resolve() / "audio"
        wav_path = storage_dir / session.audio_path

        if not wav_path.exists():
            logger.error(f"[DiarizationWorker] WAV file missing at {wav_path}")
            update_session_status(db, session_id, SessionStatus.FAILED, error="WAV file missing")
            return

        update_session_status(db, session_id, SessionStatus.DIARIZING)

        existing_chunks = list_transcript_chunks(db, session_id)
        if not existing_chunks:
            update_session_status(db, session_id, SessionStatus.COMPLETED)
            return

        logger.info("Before _get_embedding_inference")
        inference = _get_embedding_inference()
        logger.info("After _get_embedding_inference")
        
        logger.info("Before torchaudio.load")
        waveform, sample_rate = torchaudio.load(str(wav_path))
        logger.info("After torchaudio.load")
        
        embeddings = []
        valid_chunks = []
        MIN_EMBEDDING_DURATION = 1.0

        for chunk in existing_chunks:
            start_frame = int(chunk.start_time * sample_rate)
            end_frame = int(chunk.end_time * sample_rate)
            if start_frame >= end_frame:
                continue
                
            duration = chunk.end_time - chunk.start_time
            if duration < MIN_EMBEDDING_DURATION:
                continue

            chunk_waveform = waveform[:, start_frame:end_frame]
            try:
                emb = inference({"waveform": chunk_waveform, "sample_rate": sample_rate})
                embeddings.append(emb)
                valid_chunks.append(chunk)
            except Exception as e:
                logger.warning(f"Failed to generate embedding for chunk {chunk.id}: {e}")

        speaker_cache = {}
        
        if valid_chunks:
            embeddings_np = np.array(embeddings)
            if len(embeddings_np.shape) > 2:
                embeddings_np = embeddings_np.squeeze()
            if len(embeddings_np.shape) == 1:
                embeddings_np = embeddings_np.reshape(1, -1)
                
            if len(valid_chunks) == 1:
                labels = [0]
            else:
                clustering = AgglomerativeClustering(
                    n_clusters=None,
                    metric="cosine",
                    linkage="average",
                    distance_threshold=settings.QUICK_DIARIZATION_THRESHOLD
                )
                labels = clustering.fit_predict(embeddings_np)
            
            for chunk, label in zip(valid_chunks, labels):
                speaker_label = f"Speaker {label + 1}"
                speaker = speaker_cache.setdefault(speaker_label, get_or_create_speaker(db, session_id, speaker_label))
                chunk._temp_speaker_id = speaker.id

        updates = []
        default_speaker = speaker_cache.setdefault("Speaker 1", get_or_create_speaker(db, session_id, "Speaker 1"))
        current_speaker_id = default_speaker.id
        
        for chunk in existing_chunks:
            if hasattr(chunk, "_temp_speaker_id"):
                current_speaker_id = chunk._temp_speaker_id
            updates.append({
                "id": chunk.id,
                "speaker_id": current_speaker_id,
                "speaker_source": "quick"
            })

        update_chunk_speakers(db, session_id, updates)

        from sqlalchemy.sql import func
        session.diarization_mode = "quick"
        session.diarized_at = func.now()
        db.add(session)
        db.commit()

        update_session_status(db, session_id, SessionStatus.COMPLETED)
        logger.info(f"[DiarizationWorker] Completed QUICK diarization for session={session_id}")

    except Exception as exc:
        update_session_status(db, session_id, SessionStatus.FAILED, error=str(exc))
        logger.exception(f"[DiarizationWorker] Quick Diarization failed for session={session_id}")
    finally:
        db.close()


def process_accurate_diarization(session_id: int) -> None:
    """Run Whisper + Pyannote on existing WAV and rebuild transcript chunks."""
    logger.info(f"[DiarizationWorker] Started ACCURATE diarization for session={session_id}")

    db = SessionLocal()
    try:
        import time
        for _ in range(10):
            session = get_session_by_id(db, session_id)
            if not session:
                logger.error(f"[DiarizationWorker] Session {session_id} not found")
                return
            if session.audio_path:
                break
            logger.info(f"[DiarizationWorker] Waiting for audio_path for session={session_id}...")
            time.sleep(1)
            db.expire_all() # Clear SQLAlchemy identity map cache
            
        if not session.audio_path:
            logger.error(f"[DiarizationWorker] Session {session_id} missing audio_path after timeout")
            return

        storage_dir = Path(settings.EXPORT_DIR).resolve() / "audio"
        wav_path = storage_dir / session.audio_path

        if not wav_path.exists():
            logger.error(f"[DiarizationWorker] WAV file missing at {wav_path}")
            update_session_status(db, session_id, SessionStatus.FAILED, error="WAV file missing")
            return

        update_session_status(db, session_id, SessionStatus.DIARIZING)

        transcriber = WhisperTranscriptionService()
        diarizer = DiarizationService()
        
        # 1. Run Whisper on full WAV
        result = transcriber.transcribe(str(wav_path))

        # 2. Run Pyannote on full WAV
        speaker_segments = diarizer.diarize(str(wav_path))

        # 3. Align (assigns one speaker per Whisper segment with hysteresis)
        aligned_segments = align_transcript_with_speakers(
            result.segments, speaker_segments
        )

        # 4. Map to new DB chunks and REPLACE
        payloads = []
        speaker_cache = {}
        for idx, segment in enumerate(aligned_segments):
            speaker_label = segment["speaker"]
            speaker = speaker_cache.get(speaker_label)
            if speaker is None:
                speaker = get_or_create_speaker(db, session_id, speaker_label)
                speaker_cache[speaker_label] = speaker

            payloads.append({
                "session_id": session_id,
                "speaker_id": speaker.id,
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"],
                "chunk_index": segment.get("order", idx),
                "is_partial": False,
                "speaker_source": "accurate"
            })

        replace_session_chunks(db, session_id, payloads)

        from sqlalchemy.sql import func
        session.diarization_mode = "accurate"
        session.diarized_at = func.now()
        db.add(session)
        db.commit()

        update_session_status(db, session_id, SessionStatus.COMPLETED)
        logger.info(f"[DiarizationWorker] Completed ACCURATE diarization for session={session_id}")

    except Exception as exc:
        update_session_status(db, session_id, SessionStatus.FAILED, error=str(exc))
        logger.exception(f"[DiarizationWorker] Accurate Diarization failed for session={session_id}")
    finally:
        db.close()
