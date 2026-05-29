"""Upload transcription worker.

Executes: preprocess -> transcribe -> persist -> completion.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..config.logging import get_logger
from ..config.settings import Settings
from ..models.enums import SessionStatus
from ..services.audio import AudioPreprocessorService
from ..services.persistence.session_repository import update_session_status
from ..services.persistence.transcript_repository import bulk_insert_chunks
from ..services.transcription import WhisperTranscriptionService
from ..services.utils import cleanup_file
from ..db.session import SessionLocal

logger = get_logger("workers.transcription")


def process_upload_session(
    session_id: int,
    file_path: str,
    preprocessor: Optional[AudioPreprocessorService] = None,
    transcriber: Optional[WhisperTranscriptionService] = None,
    db_session: Optional[Session] = None,
) -> None:
    """Process an upload session with FFmpeg and Whisper."""
    settings = Settings()
    owns_session = db_session is None
    db = db_session or SessionLocal()

    preprocessor = preprocessor or AudioPreprocessorService(settings.TEMP_DIR)
    transcriber = transcriber or WhisperTranscriptionService()

    wav_path: Optional[str] = None

    try:
        update_session_status(db, session_id, SessionStatus.PREPROCESSING)
        wav_path = preprocessor.preprocess(file_path)

        update_session_status(db, session_id, SessionStatus.TRANSCRIBING)
        result = transcriber.transcribe(wav_path)

        payloads = [
            {
                "session_id": session_id,
                "speaker_id": None,
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"],
                "chunk_index": segment["order"],
                "is_partial": False,
            }
            for segment in result.segments
        ]

        if payloads:
            bulk_insert_chunks(db, payloads)

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
