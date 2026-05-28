"""Session lifecycle task helpers."""

from typing import Optional

from ..models.enums import SessionStatus
from ..services.session.session_service import update_session_status


def mark_status(session_id: int, status: SessionStatus) -> None:
    update_session_status(session_id, status)


def mark_failed(session_id: int, error: Optional[str] = None) -> None:
    update_session_status(session_id, SessionStatus.FAILED, error=error)
