from dataclasses import dataclass
from typing import Optional

from ...config.logging import get_logger
from ...models.enums import SessionStatus

logger = get_logger("session")


@dataclass
class SessionContext:
    session_id: int
    status: SessionStatus
    session_type: str
    original_filename: str


def create_upload_session(original_filename: str) -> SessionContext:
    """Create a session placeholder until DB persistence is wired."""
    # TODO: persist session row via repository and return real id.
    session_id = 0
    status = SessionStatus.UPLOADED
    logger.info("Created upload session placeholder", extra={"session_id": session_id})
    return SessionContext(
        session_id=session_id,
        status=status,
        session_type="upload",
        original_filename=original_filename,
    )


def update_session_status(
    session_id: int, status: SessionStatus, error: Optional[str] = None
) -> None:
    """Update session lifecycle status (placeholder)."""
    # TODO: update status in repository and persist errors.
    if error:
        logger.error(
            "Session failed",
            extra={"session_id": session_id, "status": status, "error": error},
        )
        return

    logger.info(
        "Session status updated",
        extra={"session_id": session_id, "status": status},
    )
