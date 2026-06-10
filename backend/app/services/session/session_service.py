from dataclasses import dataclass
from typing import Optional

from ...config.logging import get_logger
from ...db.session import SessionLocal
from ...models.enums import SessionStatus
from ...services.persistence.session_repository import create_session
from ...services.persistence.session_repository import get_session_by_id
from ...services.persistence.session_repository import update_session_status as update_record
from ...services.persistence.transcript_repository import list_transcript_chunks

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


def get_session_transcript(session_id: int) -> Optional[dict]:
    """Return ordered transcript data for a session."""
    db = SessionLocal()
    try:
        session = get_session_by_id(db, session_id)
        if session is None:
            return None

        chunks = sorted(
            list_transcript_chunks(db, session_id),
            key=lambda chunk: (
                chunk.chunk_index,
                chunk.start_time,
                chunk.end_time,
                chunk.id,
            ),
        )
        from ...services.persistence.speaker_repository import get_or_create_speaker
        unknown_speaker = get_or_create_speaker(db, session_id, "UNKNOWN")
        unknown_display_name = unknown_speaker.display_name

        transcript = [
            {
                "speaker": chunk.speaker.speaker_label
                if chunk.speaker is not None
                else "UNKNOWN",
                "display_name": chunk.speaker.display_name
                if chunk.speaker is not None
                else unknown_display_name,
                "startSec": float(chunk.start_time),
                "endSec": float(chunk.end_time),
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            for chunk in chunks
        ]

        status = session.status.value if hasattr(session.status, "value") else session.status
        return {
            "session_id": str(session.id),
            "status": status,
            "transcript": transcript,
        }
    finally:
        db.close()
