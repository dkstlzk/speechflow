import logging
import time

from ..db.session import SessionLocal
from ..models.enums import SessionStatus
from ..services.persistence.actions import save_action_items
from ..services.persistence.session_repository import (
    update_session_status,
    update_transcript_type,
)
from ..services.persistence.summaries import save_summary
from ..services.summarization.intelligence_formatter import (
    format_action_items,
    format_mom,
)
from ..services.summarization.transcript_processor import (
    EmptyTranscriptError,
    OllamaClientError,
    TranscriptNotFoundError,
    TranscriptProcessor,
    TranscriptProcessorError,
)
from .job_manager import unregister_job

logger = logging.getLogger("workers.intelligence")


def run_intelligence_pipeline(session_id: int):
    """Background worker to generate and persist intelligence.

    This function orchestration the intelligence generation workflow:
    1. Loads the session transcript.
    2. Runs the TranscriptProcessor to generate JSON intelligence data.
    3. Formats the JSON into readable Markdown (MOM) and Action Item lists.
    4. Persists the outputs and tracks elapsed stage timings.

    Args:
        session_id: The ID of the session to process.
    """

    pipeline_start = time.time()
    logger.info(f"[IntelligenceWorker] Started for session={session_id}")

    from ..db.session import engine

    engine.dispose()

    db = SessionLocal()
    try:
        from ..services.persistence.session_repository import get_session_by_id

        session = get_session_by_id(db, session_id)
        if not session:
            logger.error(f"[IntelligenceWorker] Session {session_id} not found")
            return

        if session.status != SessionStatus.PROCESSING:
            logger.info(
                f"[IntelligenceWorker] Session {session_id} status is {session.status.value}, not PROCESSING. Exiting."
            )
            return

        from .worker_state import clear_processing_stage, set_processing_stage

        set_processing_stage(session_id, "Transcript Loaded")
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
            update_session_status(
                db, session_id, SessionStatus.FAILED, error="Ollama unavailable"
            )
            return
        except TranscriptProcessorError as e:
            logger.exception(f"Transcript processing failed for session {session_id}")
            update_session_status(db, session_id, SessionStatus.FAILED, error=str(e))
            return
        except Exception as e:
            logger.exception(
                f"Unexpected error in intelligence pipeline for session {session_id}"
            )
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
            logger.error(
                f"Failed to update transcript type for session {session_id}: {e}"
            )

        # Persist outputs
        timings = result.get("timings", {})
        try:
            set_processing_stage(session_id, "Saving Outputs...")
            save_start = time.time()

            intel = result.get("intelligence_data", {})

            # Format Summary
            # Format Summary
            summary_text = intel.get("overview", "")

            # Format MoM
            mom_text = format_mom(intel)
            save_summary(session_id, summary_text if summary_text else None, mom_text)

            # Format Action Items
            raw_actions = intel.get("action_items", [])
            parsed_items = format_action_items(raw_actions)
            save_action_items(session_id, parsed_items)
            timings["Save"] = time.time() - save_start

            # P1: Tally Session Languages
            try:
                from ..models.transcript_chunk import TranscriptChunk

                chunks = (
                    db.query(TranscriptChunk)
                    .filter(TranscriptChunk.session_id == session_id)
                    .all()
                )
                lang_counts = {}
                total_lang_chunks = 0
                for c in chunks:
                    if c.language:
                        lang_counts[c.language] = lang_counts.get(c.language, 0) + 1
                        total_lang_chunks += 1

                if total_lang_chunks > 0:
                    detected_langs = []
                    for lang, count in lang_counts.items():
                        detected_langs.append(
                            {
                                "code": lang,
                                "percentage": int(
                                    round((count / total_lang_chunks) * 100)
                                ),
                            }
                        )
                    detected_langs.sort(key=lambda x: x["percentage"], reverse=True)

                    from ..models.session import Session

                    session_row = (
                        db.query(Session).filter(Session.id == session_id).first()
                    )
                    if session_row:
                        session_row.detected_languages = detected_langs
                        db.commit()
                else:
                    from ..models.session import Session

                    session_row = (
                        db.query(Session).filter(Session.id == session_id).first()
                    )
                    if session_row:
                        session_row.detected_languages = None
                        db.commit()
            except Exception as e:
                logger.error(f"Failed to tally session languages: {e}")

        except Exception:
            logger.exception(
                f"Failed to persist generated outputs for session {session_id}"
            )
            update_session_status(
                db, session_id, SessionStatus.FAILED, error="Failed to persist outputs"
            )
            return

        update_session_status(db, session_id, SessionStatus.COMPLETED)

        total_time = time.time() - pipeline_start
        total_chars = result.get("total_chars", 0)

        log_msg = f"Session {session_id} Profiling:\n"
        log_msg += f"Total Transcript Chars: {total_chars / 1000:.1f}k\n"
        for k, v in timings.items():
            if isinstance(v, dict):
                log_msg += f"{k}:\n"
                if "num_chunks" in v:
                    log_msg += f"  chunks={v['num_chunks']}\n"
                if "chars" in v:
                    log_msg += f"  chars={v['chars']}\n"
                log_msg += "\n"
                for i, c in enumerate(v.get("chunks", [])):
                    log_msg += f"  chunk{i + 1}: {c:.1f}s\n"
                if v.get("merge") is not None:
                    log_msg += f"\n  merge: {v['merge']:.1f}s\n"
            else:
                log_msg += f"{k}: {v:.1f}s\n"
        log_msg += f"Total: {total_time:.1f}s"
        logger.info(log_msg)
        logger.info(
            f"[IntelligenceWorker] Session={session_id} Stage=Intelligence "
            f"Elapsed={total_time:.1f} Chars={total_chars} Status=Completed"
        )
    finally:
        clear_processing_stage(session_id)
        unregister_job(session_id, "intelligence")
        db.close()
