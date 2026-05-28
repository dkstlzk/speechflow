"""Session repository for ORM access."""

from typing import Optional

from sqlalchemy.orm import Session

from ...models.enums import SessionStatus
from ...models.session import Session as SessionModel


def create_session(
    db: Session,
    session_type: str,
    original_filename: Optional[str] = None,
    status: SessionStatus = SessionStatus.PENDING,
) -> SessionModel:
    """Persist a new session row."""
    session = SessionModel(
        session_type=session_type,
        status=status,
        original_filename=original_filename,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session_status(
    db: Session, session_id: int, status: SessionStatus, error: Optional[str] = None
) -> SessionModel:
    """Update session status and optional error message."""
    session = db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")

    session.status = status
    session.processing_error = error
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_id(db: Session, session_id: int) -> Optional[SessionModel]:
    """Fetch a session by id."""
    return db.get(SessionModel, session_id)
