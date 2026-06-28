"""Upload transcription worker.

Executes: preprocess -> transcribe -> persist -> completion.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config.logging import get_logger
from ..config.settings import settings
from ..db.session import SessionLocal, engine
from ..models.enums import SessionStatus
from ..services.audio import AudioPreprocessorService
from ..services.diarization import DiarizationService
from ..services.persistence.session_repository import update_session_status
from ..services.persistence.speaker_repository import get_or_create_speaker
from ..services.persistence.transcript_repository import replace_session_chunks
from ..services.transcription import WhisperTranscriptionService
from ..services.transcription.transcript_service import align_transcript_with_speakers
from ..utils.file_manager import cleanup_file
from .job_manager import unregister_job

logger = get_logger("workers.transcription")


def process_upload_session(
    session_id: int,
    file_path: str,
    preprocessor: Optional[AudioPreprocessorService] = None,
    transcriber: Optional[WhisperTranscriptionService] = None,
    diarizer: Optional[DiarizationService] = None,
    db_session: Optional[Session] = None,
) -> None:
    """Process an upload session with FFmpeg and Whisper."""
    engine.dispose()
    logger.info(f"[UploadWorker] Child process started session={session_id}")

    owns_session = db_session is None
    db = db_session or SessionLocal()

    preprocessor = preprocessor or AudioPreprocessorService(settings.TEMP_DIR)
    transcriber = transcriber or WhisperTranscriptionService()
    diarizer = diarizer or DiarizationService()

    wav_path: Optional[str] = None

    try:
        timings = {}
        t_start = time.time()

        update_session_status(db, session_id, SessionStatus.PREPROCESSING)
        wav_path = preprocessor.preprocess(file_path)
        timings["preprocess"] = time.time() - t_start

        t0 = time.time()
        update_session_status(db, session_id, SessionStatus.TRANSCRIBING)
        result = transcriber.transcribe(wav_path)
        timings["transcribe"] = time.time() - t0

        # Persist detected language
        if result.language:
            from ..models.session import Session as SessionModel

            session_model = (
                db.query(SessionModel).filter(SessionModel.id == session_id).first()
            )
            if session_model:
                session_model.detected_language = result.language
                db.commit()

        # [Progressive Rendering] Save raw un-diarized transcript immediately
        logger.info("[TranscriptionWorker] Saving raw transcript before diarization")
        raw_speaker = get_or_create_speaker(db, session_id, "Unknown Speaker")
        raw_payloads = []
        for i, segment in enumerate(result.segments):
            raw_payloads.append(
                {
                    "session_id": session_id,
                    "speaker_id": raw_speaker.id,
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "text": segment["text"],
                    "chunk_index": i,
                    "is_partial": False,
                    "language": result.language,
                }
            )
        replace_session_chunks(db, session_id, raw_payloads)

        update_session_status(db, session_id, SessionStatus.DIARIZING)

        logger.info("[Diarization] Starting pyannote inference")
        t0 = time.time()
        speaker_segments = diarizer.diarize(wav_path)
        timings["diarize"] = time.time() - t0
        logger.info("[Diarization] Finished pyannote inference")

        logger.info("[Diarization] Starting transcript alignment")
        t0 = time.time()
        aligned_segments = align_transcript_with_speakers(
            result.segments, speaker_segments
        )
        timings["align"] = time.time() - t0
        logger.info("[Diarization] Finished transcript alignment")

        update_session_status(db, session_id, SessionStatus.PROCESSING)

        payloads = []
        speaker_cache = {}
        for segment in aligned_segments:
            speaker_label = segment["speaker"]
            speaker = speaker_cache.get(speaker_label)
            if speaker is None:
                speaker = get_or_create_speaker(db, session_id, speaker_label)
                speaker_cache[speaker_label] = speaker

            payloads.append(
                {
                    "session_id": session_id,
                    "speaker_id": speaker.id,
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "text": segment["text"],
                    "chunk_index": segment["order"],
                    "is_partial": False,
                    "language": result.language,
                }
            )

        replace_session_chunks(db, session_id, payloads)

        # Save canonical WAV
        try:
            if wav_path and os.path.exists(wav_path):
                storage_dir = Path(settings.EXPORT_DIR).resolve() / "audio"
                storage_dir.mkdir(parents=True, exist_ok=True)
                final_wav_path = storage_dir / f"session_{session_id}.wav"
                tmp_wav_path = final_wav_path.with_suffix(".wav.tmp")
                shutil.copy2(wav_path, str(tmp_wav_path))

                with open(tmp_wav_path, "rb") as f:
                    os.fsync(f.fileno())
                os.replace(str(tmp_wav_path), str(final_wav_path))

                if final_wav_path.exists() and final_wav_path.stat().st_size > 0:
                    from ..models.session import Session as SessionModel

                    session_model = (
                        db.query(SessionModel)
                        .filter(SessionModel.id == session_id)
                        .first()
                    )
                    if session_model:
                        session_model.audio_path = final_wav_path.name
                        db.commit()
                        logger.info(
                            f"[Playback] Upload audio_path updated: {final_wav_path}"
                        )
                else:
                    logger.error(
                        f"[Playback] Upload WAV missing or size 0: {final_wav_path}"
                    )
        except Exception as copy_err:
            logger.error(f"[Playback] Failed to copy canonical WAV: {copy_err}")

        update_session_status(db, session_id, SessionStatus.COMPLETED)

        timings["total"] = time.time() - t_start
        logger.info(
            "Upload processing completed",
            extra={
                "session_id": session_id,
                "timings": timings,
            },
        )
    except Exception as exc:
        update_session_status(db, session_id, SessionStatus.FAILED, error=str(exc))
        logger.exception("Upload processing failed", extra={"session_id": session_id})
    finally:
        unregister_job(session_id, "upload")
        
        cleanup_file(file_path)
        if wav_path:
            cleanup_file(wav_path)
        if owns_session:
            db.close()
