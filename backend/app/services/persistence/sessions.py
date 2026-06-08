from typing import Optional, Union

from ...db.session import SessionLocal
from ...models.enums import SessionStatus
from .session_repository import create_session as create_session_record
from .session_repository import update_session_status as update_session_record

def create_session(session_type: str, original_filename: Optional[str] = None) -> int:
    """Create session using repository and return id."""
    db = SessionLocal()
    try:
        session = create_session_record(
            db,
            session_type=session_type,
            original_filename=original_filename,
            status=SessionStatus.PENDING,
        )
        return session.id
    finally:
        db.close()


def update_session_status(
    session_id: int, status: Union[str, SessionStatus], error: Optional[str] = None
) -> None:
    """Update session status using repository."""
    db = SessionLocal()
    try:
        resolved_status = (
            status if isinstance(status, SessionStatus) else SessionStatus(status)
        )
        update_session_record(db, session_id, resolved_status, error=error)
    finally:
        db.close()
