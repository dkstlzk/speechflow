"""Upload pipeline worker.

Stages: preprocess -> transcription -> persistence -> completion.
"""

from typing import List

from ..models.enums import SessionStatus
from .transcription_worker import process_upload_session
import multiprocessing
import logging

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
    p = multiprocessing.Process(
        target=process_upload_session,
        args=(session_id, temp_path)
    )
    p.start()
    logger.info(f"[UploadWorker] Spawned process PID={p.pid} session={session_id}")
