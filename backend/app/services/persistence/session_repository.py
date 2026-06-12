"""Session repository for ORM access."""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ...models.action_item import ActionItem
from ...models.summary import SessionSummary
from ...models.transcript_chunk import TranscriptChunk
from ...models.enums import SessionStatus
from ...models.speaker import Speaker
from ...models.session import Session as SessionModel

from ...config.logging import get_logger

logger = get_logger(__name__)
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


def list_recent_sessions(db: Session, limit: int = 50, query: Optional[str] = None) -> List[SessionModel]:
    """Return the most recent sessions ordered by created_at desc, optionally filtered by a search query."""
    from sqlalchemy import or_
    from ...models.transcript_chunk import TranscriptChunk

    q = db.query(SessionModel)
    if query:
        q = q.outerjoin(TranscriptChunk, SessionModel.id == TranscriptChunk.session_id)
        if db.bind.dialect.name == "postgresql":
            try:
                from sqlalchemy import func, literal_column
                search_query = func.plainto_tsquery('english', query)
                q_fts = q.filter(
                    or_(
                        literal_column("sessions.search_vector").op("@@")(search_query),
                        literal_column("transcript_chunks.search_vector").op("@@")(search_query),
                    )
                ).distinct()
                return q_fts.order_by(SessionModel.created_at.desc()).limit(limit).all()
            except Exception as e:
                import logging
                logging.getLogger("session_repository").warning(f"FTS search failed: {e}. Falling back to ILIKE.")
                db.rollback()
                # Fall through to ILIKE

        # ILIKE Fallback
        search_pattern = f"%{query}%"
        q = q.filter(
            or_(
                SessionModel.title.ilike(search_pattern),
                SessionModel.original_filename.ilike(search_pattern),
                TranscriptChunk.text.ilike(search_pattern),
            )
        ).distinct()

    return q.order_by(SessionModel.created_at.desc()).limit(limit).all()


def delete_session(db: Session, session_id: int) -> bool:
    """Delete a session and all dependent records."""
    session = db.get(SessionModel, session_id)

    if session is None:
        return False

    # Children are automatically deleted via SQLAlchemy cascade

    audio_path = getattr(session, 'audio_path', None)

    db.delete(session)
    db.commit()

    if audio_path:
        import os
        from ...config.settings import settings
        filename = os.path.basename(audio_path)
        safe_path = os.path.join(settings.EXPORT_DIR, "audio", filename)
        if os.path.exists(safe_path):
            try:
                os.remove(safe_path)
                logger.info(f"[Playback] Playback file deleted: {safe_path}")
            except Exception as e:
                logger.error(f"[Playback] Failed to delete playback file: {e}")

    return True

def update_transcript_type(
    db: Session,
    session_id: int,
    transcript_type: str,
) -> SessionModel:
    session = db.get(SessionModel, session_id)

    if session is None:
        raise ValueError(
            f"Session not found: {session_id}"
        )

    session.transcript_type = transcript_type

    db.add(session)
    db.commit()
    db.refresh(session)

    return session

def recover_stale_sessions(db: Session, max_hours: int = 2) -> int:
    """
    Find processing sessions that are stuck and mark them as failed.
    Cleans up orphaned audio files for RECORDING sessions.
    Returns the number of recovered sessions.
    """
    import os
    from ...config.settings import settings
    cutoff_time = datetime.now() - timedelta(hours=max_hours)

    stale_states = [
        SessionStatus.PREPROCESSING,
        SessionStatus.TRANSCRIBING,
        SessionStatus.DIARIZING,
        SessionStatus.PROCESSING,
        SessionStatus.FINALIZING,
        SessionStatus.RECORDING,
    ]

    stuck_sessions = db.query(SessionModel).filter(
        SessionModel.status.in_(stale_states),
        SessionModel.updated_at < cutoff_time
    ).all()

    for session in stuck_sessions:
        logger.warning(f"[Recovery] Session {session.id} stuck in {session.status.value}. Marking as FAILED.")

        # Cleanup orphaned files for realtime sessions that crashed
        if session.status == SessionStatus.RECORDING:
            audio_dir = os.path.abspath(os.path.join(settings.EXPORT_DIR, "audio"))
            raw_path = os.path.join(audio_dir, f"session_{session.id}.raw")
            wav_path = os.path.join(audio_dir, f"session_{session.id}.wav")
            import time
            for path in [raw_path, wav_path]:
                if os.path.exists(path):
                    try:
                        orphan_path = path + f".orphan.{int(time.time())}"
                        os.rename(path, orphan_path)
                        logger.info(f"[Recovery] Archived stranded file to: {orphan_path}")
                    except Exception as e:
                        logger.error(f"[Recovery] Failed to archive stranded file: {e}")

        session.status = SessionStatus.FAILED
        session.processing_error = "Session failed due to unexpected worker interruption (stale state recovery)."

    if stuck_sessions:
        db.commit()

    # Clean up old orphan files (older than 7 days)
    audio_dir = os.path.abspath(os.path.join(settings.EXPORT_DIR, "audio"))
    if os.path.exists(audio_dir):
        import time
        now = time.time()
        seven_days = 7 * 24 * 3600
        for fname in os.listdir(audio_dir):
            if ".orphan." in fname:
                fpath = os.path.join(audio_dir, fname)
                try:
                    if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > seven_days:
                        os.remove(fpath)
                        logger.info(f"[Recovery] Deleted old orphan file: {fname}")
                except Exception as e:
                    logger.error(f"[Recovery] Failed to delete old orphan file {fname}: {e}")

    return len(stuck_sessions)
