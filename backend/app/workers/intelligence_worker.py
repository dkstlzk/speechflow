import logging
from ..services.summarization.transcript_processor import TranscriptProcessor, TranscriptNotFoundError, EmptyTranscriptError, OllamaClientError, TranscriptProcessorError
from ..services.persistence.session_repository import update_session_status, update_transcript_type
from ..services.persistence.summaries import save_summary
from ..services.persistence.actions import save_action_items
from ..api.sessions import _parse_action_items_text
from ..models.enums import SessionStatus
from ..db.session import SessionLocal

logger = logging.getLogger("workers.intelligence")

def run_intelligence_pipeline(session_id: int):
    """Background worker to generate and persist intelligence."""
    logger.info(f"[IntelligenceWorker] Started for session={session_id}")
    
    db = SessionLocal()
    try:
        processor = TranscriptProcessor()
        try:
            result = processor.process_session(session_id)
        except TranscriptNotFoundError:
            logger.warning(f"Transcript not found for session {session_id}")
            update_session_status(db, session_id, SessionStatus.COMPLETED)
            return
        except EmptyTranscriptError:
            logger.warning(f"Empty transcript for session {session_id}")
            update_session_status(db, session_id, SessionStatus.COMPLETED)
            return
        except OllamaClientError as e:
            logger.error(f"Ollama unavailable for session {session_id}: {e}")
            update_session_status(db, session_id, SessionStatus.FAILED, error="Ollama unavailable")
            return
        except TranscriptProcessorError as e:
            logger.exception(f"Transcript processing failed for session {session_id}")
            update_session_status(db, session_id, SessionStatus.FAILED, error=str(e))
            return
        except Exception as e:
            logger.exception(f"Unexpected error in intelligence pipeline for session {session_id}")
            update_session_status(db, session_id, SessionStatus.FAILED, error=str(e))
            return

        # Update transcript type
        try:
            update_transcript_type(
                db,
                session_id,
                result["transcript_type"],
            )
        except Exception as e:
            logger.error(f"Failed to update transcript type for session {session_id}: {e}")

        # Persist outputs
        try:
            save_summary(session_id, result["summary"], result.get("mom"))
            raw_actions = result.get("action_items") or ""
            parsed_items = _parse_action_items_text(raw_actions)
            save_action_items(session_id, parsed_items)
        except Exception as e:
            logger.exception(f"Failed to persist generated outputs for session {session_id}")
            update_session_status(db, session_id, SessionStatus.FAILED, error="Failed to persist outputs")
            return

        update_session_status(db, session_id, SessionStatus.COMPLETED)
        logger.info(f"[IntelligenceWorker] Completed successfully for session={session_id}")
    finally:
        db.close()
