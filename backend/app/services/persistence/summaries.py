"""Persistence operations for session summaries."""

from typing import Dict, Optional

from ...config.logging import get_logger
from ...db.session import SessionLocal
from ...models.summary import SessionSummary

logger = get_logger("persistence")


def save_summary(session_id: int, summary: str, mom: Optional[str] = None) -> None:
    """Insert a new summary row for the given session with incremented iteration."""
    db = SessionLocal()
    from sqlalchemy import func

    try:
        max_iter = (
            db.query(func.max(SessionSummary.iteration))
            .filter(SessionSummary.session_id == session_id)
            .scalar()
            or 0
        )
        row = SessionSummary(
            session_id=session_id,
            summary=summary,
            mom=mom,
            iteration=max_iter + 1,
        )
        db.add(row)
        db.commit()
        logger.info(
            "Summary saved", extra={"session_id": session_id, "iteration": max_iter + 1}
        )
    finally:
        db.close()


def get_summary(session_id: int) -> Optional[Dict]:
    """Load summary and MoM history for a session. Returns a dict containing history."""
    db = SessionLocal()
    try:
        rows = (
            db.query(SessionSummary)
            .filter(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.iteration.asc())
            .all()
        )
        if not rows:
            return None

        history = [
            {
                "iteration": row.iteration,
                "summary": row.summary,
                "mom": row.mom,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

        return {
            "session_id": session_id,
            "history": history,
            "summary": rows[-1].summary,  # Legacy fallback to newest
            "mom": rows[-1].mom,  # Legacy fallback to newest
        }
    finally:
        db.close()
