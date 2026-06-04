"""Session repository for ORM access."""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

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
    if status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
        session.completed_at = func.now()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_id(db: Session, session_id: int) -> Optional[SessionModel]:
    """Fetch a session by id."""
    return db.get(SessionModel, session_id)


def list_recent_sessions(db: Session, limit: int = 50) -> List[SessionModel]:
    """Return the most recent sessions ordered by created_at desc."""
    return (
        db.query(SessionModel)
        .order_by(SessionModel.created_at.desc())
        .limit(limit)
        .all()
    )
