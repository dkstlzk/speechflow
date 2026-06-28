"""Upload pipeline worker.

Stages: preprocess -> transcription -> persistence -> completion.
"""

import logging
import multiprocessing
from typing import List

from ..models.enums import SessionStatus
from .transcription_worker import process_upload_session

logger = logging.getLogger("upload_worker")


def get_pipeline_stages() -> List[str]:
    return [
        SessionStatus.PENDING.value,
        SessionStatus.PREPROCESSING.value,
        SessionStatus.TRANSCRIBING.value,
        SessionStatus.DIARIZING.value,
        SessionStatus.PROCESSING.value,
        SessionStatus.COMPLETED.value,
        SessionStatus.FAILED.value,
    ]


def start_upload_pipeline(session_id: int, temp_path: str) -> None:
    """Launch the upload pipeline in a background process."""
    ctx = multiprocessing.get_context("spawn")
    try:
        p = ctx.Process(target=process_upload_session, args=(session_id, temp_path))
        p.start()
        
        from .job_manager import register_job
        register_job(session_id, "upload", p.pid)
        
        logger.info(f"[UploadWorker] Spawned process PID={p.pid} session={session_id}")
    except Exception:
        logger.exception(
            f"[UploadWorker] Failed to spawn process for session {session_id}"
        )
        from ..db.session import SessionLocal

        db = SessionLocal()
        try:
            from ..services.persistence.session_repository import update_session_status

            update_session_status(
                db,
                session_id,
                SessionStatus.FAILED,
                error="Server overloaded. Failed to start process.",
            )
        finally:
            db.close()
