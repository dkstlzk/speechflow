"""Upload transcription worker.

Executes: preprocess -> transcribe -> persist -> completion.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..config.logging import get_logger
from ..config.settings import Settings
from ..models.enums import SessionStatus
from ..services.audio import AudioPreprocessorService
from ..services.diarization import DiarizationService
from ..services.persistence.session_repository import update_session_status
from ..services.persistence.speaker_repository import get_or_create_speaker
from ..services.persistence.transcript_repository import replace_session_chunks
from ..services.transcription import WhisperTranscriptionService
from ..services.transcription.transcript_service import align_transcript_with_speakers
from ..utils.file_manager import cleanup_file
from ..db.session import SessionLocal

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
    settings = Settings()
    owns_session = db_session is None
    db = db_session or SessionLocal()

    preprocessor = preprocessor or AudioPreprocessorService(settings.TEMP_DIR)
    transcriber = transcriber or WhisperTranscriptionService()
    diarizer = diarizer or DiarizationService()

    wav_path: Optional[str] = None

    try:
        update_session_status(db, session_id, SessionStatus.PREPROCESSING)
        wav_path = preprocessor.preprocess(file_path)

        update_session_status(db, session_id, SessionStatus.TRANSCRIBING)
        result = transcriber.transcribe(wav_path)

        update_session_status(db, session_id, SessionStatus.DIARIZING)
        speaker_segments = diarizer.diarize(wav_path)
        aligned_segments = align_transcript_with_speakers(
            result.segments, speaker_segments
        )

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
                }
            )

        replace_session_chunks(db, session_id, payloads)

        update_session_status(db, session_id, SessionStatus.COMPLETED)
        logger.info("Upload processing completed", extra={"session_id": session_id})
    except Exception as exc:
        update_session_status(db, session_id, SessionStatus.FAILED, error=str(exc))
        logger.exception("Upload processing failed", extra={"session_id": session_id})
    finally:
        cleanup_file(file_path)
        if wav_path:
            cleanup_file(wav_path)
        if owns_session:
            db.close()
