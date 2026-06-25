from ..config.logging import get_logger
from ..db.session import SessionLocal
from ..models.translation import SessionTranslation
from ..services.session.session_service import get_session_transcript
from ..services.persistence.summaries import get_summary
from ..services.translation import TranslationService

logger = get_logger("translation_worker")

def process_translation(session_id: int, target_language: str) -> None:
    """Background worker to translate a session's transcript and summary."""
    db = SessionLocal()
    try:
        # Check if the translation row exists
        translation_row = db.query(SessionTranslation).filter(
            SessionTranslation.session_id == session_id,
            SessionTranslation.target_language == target_language
        ).first()

        if not translation_row:
            logger.error(f"No SessionTranslation row found for session {session_id} and language {target_language}")
            return
        
        # Get transcript
        payload = get_session_transcript(session_id)
        if payload is None or not payload.get("transcript"):
            translation_row.status = "failed"
            translation_row.error_message = "No transcript to translate"
            db.commit()
            return

        entries = payload.get("transcript", [])
        
        # Build transcript text for translation
        lines = []
        for entry in entries:
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            speaker = entry.get("display_name") or entry.get("speaker") or "Speaker"
            if speaker in ("UNKNOWN", ""):
                speaker = "Speaker"
            lines.append(f"{speaker}: {text}")

        combined_text = "\n".join(lines)

        if not combined_text.strip():
            translation_row.status = "failed"
            translation_row.error_message = "Transcript has no translatable text"
            db.commit()
            return

        # Fetch summary data
        summary_data = get_summary(session_id)
        summary_text = None
        mom_text = None

        service = TranslationService()

        # Translate transcript
        logger.info(f"Translating transcript for session {session_id} to {target_language}")
        translated_transcript = service.translate_text(combined_text, target_language)

        # Translate summary
        if summary_data and summary_data.get("summary"):
            try:
                logger.info(f"Translating summary for session {session_id} to {target_language}")
                summary_text = service.translate_text(
                    summary_data["summary"], target_language, is_summary=True
                )
            except Exception as e:
                logger.warning(f"Summary translation failed: {e}")

        # Translate MoM
        if summary_data and summary_data.get("mom"):
            try:
                logger.info(f"Translating MoM for session {session_id} to {target_language}")
                mom_text = service.translate_text(
                    summary_data["mom"], target_language, is_summary=True
                )
            except Exception as e:
                logger.warning(f"MoM translation failed: {e}")

        # Save to DB
        translation_row.translated_transcript = translated_transcript
        translation_row.translated_summary = summary_text
        translation_row.translated_mom = mom_text
        translation_row.status = "completed"
        db.commit()
        logger.info(f"Translation completed successfully for session {session_id} ({target_language})")

    except Exception as e:
        logger.exception(f"Translation failed for session {session_id} ({target_language})")
        if 'translation_row' in locals() and translation_row:
            translation_row.status = "failed"
            translation_row.error_message = str(e)
            try:
                db.commit()
            except:
                db.rollback()
    finally:
        db.close()
