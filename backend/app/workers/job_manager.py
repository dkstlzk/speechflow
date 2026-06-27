import os
import signal
from typing import Dict, Tuple

from ..config.logging import get_logger
from ..db.session import SessionLocal
from ..models.enums import SessionStatus
from ..models.session import Session
from ..models.translation import SessionTranslation

logger = get_logger(__name__)

# Key: (session_id, job_type) -> Value: pid
# job_type: "intelligence", "quick_diarization", "accurate_diarization", "translation_<lang>"
ACTIVE_JOBS: Dict[Tuple[int, str], int] = {}

def register_job(session_id: int, job_type: str, pid: int):
    logger.info(f"[JobManager] Registering job {job_type} for session {session_id} with PID {pid}")
    ACTIVE_JOBS[(session_id, job_type)] = pid

def unregister_job(session_id: int, job_type: str):
    pid = ACTIVE_JOBS.pop((session_id, job_type), None)
    if pid:
        logger.info(f"[JobManager] Unregistered job {job_type} for session {session_id} (PID {pid})")

def cancel_job(session_id: int, job_type: str) -> bool:
    """
    Attempts to cancel the job by killing its OS process, and safely restores the database state.
    Returns True if a process was actively killed.
    """
    pid = ACTIVE_JOBS.pop((session_id, job_type), None)
    process_killed = False

    if pid:
        try:
            logger.info(f"[JobManager] Attempting to kill PID {pid} for session {session_id}, job {job_type}")
            os.kill(pid, signal.SIGTERM)
            process_killed = True
            logger.info(f"[JobManager] Successfully killed PID {pid}")
        except ProcessLookupError:
            logger.info(f"[JobManager] PID {pid} already finished/dead")
            pass

    # Roll back the database state regardless of whether the PID was still alive, 
    # to ensure the UI can recover from any stuck states.
    rollback_db_state(session_id, job_type)
    
    return process_killed

def rollback_db_state(session_id: int, job_type: str):
    db = SessionLocal()
    try:
        if job_type.startswith("translation_"):
            # job_type is translation_<language>
            lang = job_type.split("_", 1)[1]
            translation = db.query(SessionTranslation).filter(
                SessionTranslation.session_id == session_id,
                SessionTranslation.target_language == lang
            ).first()
            if translation and translation.status == "translating":
                logger.info(f"[JobManager] Rolling back translation {lang} to failed/canceled")
                # We can either delete it or mark it as invalidated
                db.delete(translation)
                db.commit()
        else:
            # It's a session-level job (intelligence, diarization)
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                if session.status in (SessionStatus.PROCESSING, SessionStatus.DIARIZING):
                    logger.info(f"[JobManager] Rolling back session {session_id} status to COMPLETED")
                    session.status = SessionStatus.COMPLETED
                    session.processing_error = "Process canceled by user"
                    db.commit()
    except Exception as e:
        logger.exception(f"[JobManager] Error rolling back state for session {session_id}, job {job_type}: {e}")
        db.rollback()
    finally:
        db.close()
