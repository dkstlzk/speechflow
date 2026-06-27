"""Persistence operations for action items."""

from typing import Dict, List

from ...config.logging import get_logger
from ...db.session import SessionLocal
from ...models.action_item import ActionItem

logger = get_logger("persistence")


def save_action_items(session_id: int, items: List[str]) -> None:
    """Insert new action items for a session with an incremented iteration."""
    db = SessionLocal()
    from sqlalchemy import func

    try:
        max_iter = (
            db.query(func.max(ActionItem.iteration))
            .filter(ActionItem.session_id == session_id)
            .scalar()
            or 0
        )
        new_iter = max_iter + 1
        for text in items:
            text = text.strip()
            if not text:
                continue
            db.add(ActionItem(session_id=session_id, text=text, iteration=new_iter))
        db.commit()
        logger.info(
            "Action items saved",
            extra={
                "session_id": session_id,
                "count": len(items),
                "iteration": new_iter,
            },
        )
    finally:
        db.close()


def list_action_items(session_id: int) -> List[Dict]:
    """Load action items for a session."""
    db = SessionLocal()
    try:
        rows = (
            db.query(ActionItem)
            .filter(ActionItem.session_id == session_id)
            .order_by(ActionItem.id)
            .all()
        )
        return [
            {
                "id": row.id,
                "text": row.text,
                "status": row.status,
                "iteration": row.iteration,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()
