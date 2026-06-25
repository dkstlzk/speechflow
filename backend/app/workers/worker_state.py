import json
import os
import logging
from ..config.settings import settings

logger = logging.getLogger("worker_state")

def _get_state_file_path(session_id: int) -> str:
    state_dir = os.path.join(settings.EXPORT_DIR, "states")
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f"session_{session_id}_state.json")

def set_processing_stage(session_id: int, stage: str) -> None:
    """Write the current processing stage to a file."""
    path = _get_state_file_path(session_id)
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump({"stage": stage}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception as e:
        logger.warning(f"Failed to write state file for session {session_id}: {e}")

def get_processing_stage(session_id: int) -> str | None:
    """Read the current processing stage from the file."""
    path = _get_state_file_path(session_id)
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("stage")
    except Exception as e:
        logger.warning(f"Failed to read state file for session {session_id}: {e}")
    return None

def clear_processing_stage(session_id: int) -> None:
    """Remove the state file when processing is complete."""
    path = _get_state_file_path(session_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to clear state file for session {session_id}: {e}")
