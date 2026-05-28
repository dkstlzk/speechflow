"""Upload pipeline worker.

Stages: upload -> preprocess -> transcription -> diarization -> persistence
-> post-processing -> completion.
"""

from typing import List

from ..config.logging import get_logger
from ..models.enums import SessionStatus
from ..services.session.session_service import SessionContext, update_session_status
from .background import run_in_thread

logger = get_logger("workers.upload")


def get_pipeline_stages() -> List[str]:
    return [
        SessionStatus.UPLOADED.value,
        SessionStatus.PREPROCESSING.value,
        SessionStatus.TRANSCRIBING.value,
        SessionStatus.DIARIZING.value,
        SessionStatus.PROCESSING.value,
        SessionStatus.COMPLETED.value,
    ]


def start_upload_pipeline(session: SessionContext, temp_path: str) -> None:
    """Launch the upload pipeline in a background thread."""
    run_in_thread(run_upload_pipeline, session, temp_path)


def run_upload_pipeline(session: SessionContext, temp_path: str) -> None:
    """Execute the upload pipeline stages without heavy inference yet."""
    logger.info("Upload pipeline started", extra={"session_id": session.session_id})
    try:
        update_session_status(session.session_id, SessionStatus.PREPROCESSING)
        # TODO: run FFmpeg preprocessing

        update_session_status(session.session_id, SessionStatus.TRANSCRIBING)
        # TODO: run Whisper transcription

        update_session_status(session.session_id, SessionStatus.DIARIZING)
        # TODO: run diarization and alignment

        update_session_status(session.session_id, SessionStatus.PROCESSING)
        # TODO: persist transcript + run summarization

        update_session_status(session.session_id, SessionStatus.COMPLETED)
        logger.info(
            "Upload pipeline completed", extra={"session_id": session.session_id}
        )
    except Exception as exc:
        update_session_status(session.session_id, SessionStatus.FAILED, error=str(exc))
        logger.exception(
            "Upload pipeline failed", extra={"session_id": session.session_id}
        )
        # TODO: cleanup temp files and partial data
