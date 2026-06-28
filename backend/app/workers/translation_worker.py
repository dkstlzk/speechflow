from ..config.logging import get_logger
from ..config.settings import settings
from ..db.session import SessionLocal
from ..models.translation import SessionTranslation
from ..services.persistence.summaries import get_summary
from ..services.translation import TranslationService
from .job_manager import unregister_job

logger = get_logger("translation_worker")


def process_translation(session_id: int, target_language: str) -> None:
    """Background worker to translate a session's transcript and summary.

    This function performs an end-to-end translation of a completed session:
    1. Translates all individual transcript chunks in batches to prevent LLM hallucination.
    2. Translates the generated Summary and Minutes of Meeting (MOM).
    3. Persists the translated artifacts to the database.

    Args:
        session_id: The ID of the session to translate.
        target_language: The target language key (e.g., 'hi', 'es').
    """
    import time
    from ..db.session import engine

    start_time = time.monotonic()
    
    # Dispose of any inherited connection pools before opening a new session
    engine.dispose()
    db = SessionLocal()
    try:
        # Check if the translation row exists
        translation_row = (
            db.query(SessionTranslation)
            .filter(
                SessionTranslation.session_id == session_id,
                SessionTranslation.target_language == target_language,
            )
            .first()
        )

        if not translation_row:
            logger.error(
                f"No SessionTranslation row found for session {session_id} and language {target_language}"
            )
            return
            
        # Get transcript_type from Session
        from ..models.session import Session
        session_row = db.query(Session).filter(Session.id == session_id).first()
        transcript_type = session_row.transcript_type if session_row and session_row.transcript_type else "conversation"

        # Get chunks
        from ..models.transcript_chunk import TranscriptChunk
        from ..models.translation import TranslatedChunk

        chunks_query = (
            db.query(TranscriptChunk)
            .filter(TranscriptChunk.session_id == session_id)
            .order_by(TranscriptChunk.chunk_index)
            .all()
        )

        if not chunks_query:
            translation_row.status = "failed"
            translation_row.error_message = "No transcript chunks to translate"
            db.commit()
            return

        chunk_dicts = [
            {"id": c.id, "text": c.text} for c in chunks_query if c.text.strip()
        ]

        if not chunk_dicts:
            translation_row.status = "failed"
            translation_row.error_message = "Transcript has no translatable text"
            db.commit()
            return

        # Fetch summary data
        summary_data = get_summary(session_id)
        summary_text = None
        mom_text = None

        service = TranslationService()

        # Translate chunks
        logger.info(
            f"Translating transcript chunks for session {session_id} to {target_language}"
        )
        try:
            # We translate them in batches to prevent LLM output truncation and JSON malformation
            BATCH_SIZE = settings.TRANSLATION_BATCH_SIZE
            translated_dicts = []
            failed_batches = 0
            total_batches = (len(chunk_dicts) + BATCH_SIZE - 1) // BATCH_SIZE
            for i in range(0, len(chunk_dicts), BATCH_SIZE):
                batch = chunk_dicts[i : i + BATCH_SIZE]
                logger.info(
                    f"Translating batch {i // BATCH_SIZE + 1} of {total_batches}"
                )
                batch_res = service.translate_chunks(batch, target_language, transcript_type=transcript_type)
                if batch_res:
                    translated_dicts.extend(batch_res)
                else:
                    failed_batches += 1

            # Delete existing translation chunks to avoid duplicates
            db.query(TranslatedChunk).filter(
                TranslatedChunk.translation_id == translation_row.id
            ).delete(synchronize_session=False)

            # Save translated chunks in bulk
            new_chunks = []
            seen_chunk_ids = set()
            for t_dict in translated_dicts:
                if not isinstance(t_dict, dict):
                    continue
                c_id = t_dict.get("id")
                t_text = t_dict.get("text")
                if t_text is not None:
                    t_text = str(t_text).strip()
                else:
                    t_text = ""
                if c_id and t_text and c_id not in seen_chunk_ids:
                    seen_chunk_ids.add(c_id)
                    new_chunks.append(
                        TranslatedChunk(
                            translation_id=translation_row.id,
                            chunk_id=c_id,
                            translated_text=t_text,
                        )
                    )
            db.add_all(new_chunks)
            db.flush()

            # Build flattened translated transcript for legacy clients/exports
            # We fetch speaker names from the original chunks and format them nicely
            id_to_speaker = {}
            speaker_idx = 0
            speaker_map = {}
            
            for c in chunks_query:
                display_name = None
                if c.speaker:
                    if c.speaker.display_name:
                        display_name = c.speaker.display_name
                    elif c.speaker.speaker_label:
                        label = c.speaker.speaker_label
                        if label.startswith("SPEAKER_"):
                            if label not in speaker_map:
                                speaker_map[label] = f"Speaker {chr(65 + speaker_idx)}"
                                speaker_idx += 1
                            display_name = speaker_map[label]
                        else:
                            display_name = label
                
                if not display_name or display_name == "UNKNOWN":
                    display_name = "Speaker"
                    
                id_to_speaker[c.id] = display_name

            translated_lines = []
            for chunk in new_chunks:
                speaker = id_to_speaker.get(chunk.chunk_id, 'Speaker')
                translated_lines.append(
                    f"{speaker}: {chunk.translated_text}"
                )

            translated_transcript = "\n".join(translated_lines)

        except Exception as e:
            logger.error(f"Chunk translation failed: {e}")
            raise

        # Translate summary
        if summary_data and summary_data.get("summary"):
            try:
                logger.info(
                    f"Translating summary for session {session_id} to {target_language}"
                )
                summary_text = service.translate_text(
                    summary_data["summary"], target_language, transcript_type=transcript_type, is_summary=True
                )
            except Exception as e:
                logger.warning(f"Summary translation failed: {e}")

        # Translate MoM
        if summary_data and summary_data.get("mom"):
            try:
                logger.info(
                    f"Translating MoM for session {session_id} to {target_language}"
                )
                mom_text = service.translate_text(
                    summary_data["mom"], target_language, transcript_type=transcript_type, is_summary=True
                )
            except Exception as e:
                logger.warning(f"MoM translation failed: {e}")

        # Save to DB
        translation_row.translated_transcript = translated_transcript
        translation_row.translated_summary = summary_text
        translation_row.translated_mom = mom_text
        translation_row.status = "completed"
        if failed_batches > 0:
            warning = f"Warning: {failed_batches}/{total_batches} translation batches failed. Some transcript chunks remain untranslated."
            translation_row.error_message = (
                (translation_row.error_message or "") + "\n" + warning
            ).strip()
        db.commit()
        elapsed = time.monotonic() - start_time
        logger.info(
            f"[TranslationWorker] Session={session_id} Stage=Translation "
            f"Elapsed={elapsed:.1f} Chunks={len(new_chunks)} Batches={total_batches} FailedBatches={failed_batches} Language={target_language} Status=Completed"
        )

    except Exception as e:
        logger.exception(
            f"Translation failed for session {session_id} ({target_language})"
        )
        if "translation_row" in locals() and translation_row:
            try:
                translation_row.status = "failed"
                translation_row.error_message = str(e)
                db.commit()
            except Exception:
                db.rollback()
                # Open a new session to ensure the failure state is persisted
                try:
                    with SessionLocal() as new_db:
                        new_row = (
                            new_db.query(SessionTranslation)
                            .filter(SessionTranslation.id == translation_row.id)
                            .first()
                        )
                        if new_row:
                            new_row.status = "failed"
                            new_row.error_message = str(e)
                            new_db.commit()
                except Exception as inner_err:
                    logger.error(
                        f"Failed to persist translation failure state: {inner_err}"
                    )
    finally:
        unregister_job(session_id, f"translation_{target_language}")
        db.close()
