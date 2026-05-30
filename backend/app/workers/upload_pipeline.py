"""Upload pipeline worker.

Stages: preprocess -> transcription -> persistence -> completion.
"""

from typing import List

from ..models.enums import SessionStatus
from .background import run_in_thread
from .transcription_worker import process_upload_session


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
    """Launch the upload pipeline in a background thread."""
    run_in_thread(process_upload_session, session_id, temp_path)
