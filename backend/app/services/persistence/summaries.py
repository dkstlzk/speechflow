"""Persistence operations for session summaries."""

from typing import Dict, Optional

from ...config.logging import get_logger
from ...db.session import SessionLocal
from ...models.summary import SessionSummary

logger = get_logger("persistence")


def save_summary(session_id: int, summary: str, mom: Optional[str] = None) -> None:
    """Upsert a summary row for the given session."""
    db = SessionLocal()
    try:
        existing = (
            db.query(SessionSummary)
            .filter(SessionSummary.session_id == session_id)
            .first()
        )
        if existing:
            existing.summary = summary
            existing.mom = mom
        else:
            row = SessionSummary(
                session_id=session_id,
                summary=summary,
                mom=mom,
            )
            db.add(row)
        db.commit()
        logger.info("Summary saved", extra={"session_id": session_id})
    finally:
        db.close()


def get_summary(session_id: int) -> Optional[Dict]:
    """Load summary and MoM for a session. Returns None if not found."""
    db = SessionLocal()
    try:
        row = (
            db.query(SessionSummary)
            .filter(SessionSummary.session_id == session_id)
            .first()
        )
        if row is None:
            return None
        return {
            "session_id": row.session_id,
            "summary": row.summary,
            "mom": row.mom,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        db.close()
