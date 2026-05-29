from dataclasses import dataclass
from typing import Optional

from ...config.logging import get_logger
from ...db.session import SessionLocal
from ...models.enums import SessionStatus
from ...services.persistence.session_repository import create_session
from ...services.persistence.session_repository import update_session_status as update_record

logger = get_logger("session")


@dataclass
class SessionContext:
    session_id: int
    status: SessionStatus
    session_type: str
    original_filename: str


def create_upload_session(original_filename: str) -> SessionContext:
    """Create a new upload session and return its context."""
    db = SessionLocal()
    try:
        record = create_session(
            db,
            session_type="upload",
            original_filename=original_filename,
            status=SessionStatus.PENDING,
        )
        logger.info("Created upload session", extra={"session_id": record.id})
        return SessionContext(
            session_id=record.id,
            status=record.status,
            session_type=record.session_type,
            original_filename=record.original_filename or "",
        )
    finally:
        db.close()


def update_session_status(
    session_id: int, status: SessionStatus, error: Optional[str] = None
) -> None:
    """Update session lifecycle status in persistence layer."""
    db = SessionLocal()
    try:
        update_record(db, session_id, status, error=error)
        logger.info(
            "Session status updated",
            extra={"session_id": session_id, "status": status},
        )
    finally:
        db.close()
