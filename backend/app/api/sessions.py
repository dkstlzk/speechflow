import os
import multiprocessing

# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, send_file

# pyrefly: ignore [missing-import]
from flask import request as flask_request

from ..config.constants import MAX_FIELD_LENGTH
from ..config.extensions import limiter
from ..config.logging import get_logger
from ..config.settings import settings
from ..db.session import SessionLocal
from ..schemas.response import ApiResponse
from ..services.persistence.session_repository import (
    delete_session,
    get_session_by_id,
    list_recent_sessions,
)
from ..services.persistence.speaker_repository import update_speaker_display_name
from ..services.persistence.summaries import get_summary
from ..services.session.session_service import get_session_transcript
from ..workers.worker_state import get_processing_stage
from ..workers.job_manager import get_active_job_type

logger = get_logger("sessions_api")

sessions_bp = Blueprint("sessions", __name__)


def _serialize_session(row) -> dict:
    """Serialize a Session ORM row to the API shape."""
    status = row.status.value if hasattr(row.status, "value") else row.status
    data = {
        "id": row.id,
        "status": status,
        "transcript_type": row.transcript_type,
        "session_type": row.session_type,
        "original_filename": row.original_filename,
        "duration_seconds": row.duration_seconds,
        "title": row.title,
        "host_name": getattr(row, "host_name", None),
        "participants": getattr(row, "participants", None),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "has_audio": bool(getattr(row, "audio_path", None)),
        "audio_url": f"/api/sessions/{row.id}/audio"
        if getattr(row, "audio_path", None)
        else None,
        "diarization_mode": getattr(row, "diarization_mode", None),
        "diarized_at": row.diarized_at.isoformat()
        if getattr(row, "diarized_at", None)
        else None,
        "detected_language": getattr(row, "detected_language", None),
        "detected_languages": getattr(row, "detected_languages", None),
        "active_job_type": get_active_job_type(row.id),
    }

    if status == "processing":
        data["processing_stage"] = get_processing_stage(row.id) or "Processing..."

    return data


@sessions_bp.get("/")
def list_sessions():
    # pyrefly: ignore [missing-import]
    from flask import request

    query = request.args.get("q")
    db = SessionLocal()
    try:
        rows = list_recent_sessions(db, limit=50, query=query)
        data = [_serialize_session(r) for r in rows]
    except Exception:
        logger.exception("Failed to list sessions")
        return jsonify(ApiResponse.fail("Failed to list sessions").to_dict()), 500
    finally:
        db.close()
    return jsonify(ApiResponse.ok(data).to_dict()), 200


@sessions_bp.get("/<session_id>")
def get_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    db = SessionLocal()
    try:
        row = get_session_by_id(db, session_id_int)
        if row is None:
            return jsonify(ApiResponse.fail("session not found").to_dict()), 404
        data = _serialize_session(row)
    except Exception:
        logger.exception("Failed to load session")
        return jsonify(ApiResponse.fail("Failed to load session").to_dict()), 500
    finally:
        db.close()
    return jsonify(ApiResponse.ok(data).to_dict()), 200


@sessions_bp.get("/<session_id>/audio")
def get_session_audio(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    db = SessionLocal()
    try:
        session = get_session_by_id(db, session_id_int)
        if not session or not getattr(session, "audio_path", None):
            return jsonify(ApiResponse.fail("audio not found").to_dict()), 404

        from ..config.settings import settings

        filename = os.path.basename(session.audio_path)
        # Both upload and realtime audio are stored in EXPORT_DIR/audio/
        safe_path = os.path.join(settings.EXPORT_DIR, "audio", filename)

        if not os.path.exists(safe_path):
            return jsonify(ApiResponse.fail("audio not found").to_dict()), 404

        import mimetypes
        mimetype = mimetypes.guess_type(safe_path)[0] or "audio/wav"
        return send_file(safe_path, mimetype=mimetype)
    except Exception:
        logger.exception("Failed to load audio")
        return jsonify(ApiResponse.fail("Failed to load audio").to_dict()), 500
    finally:
        db.close()


@sessions_bp.delete("/<session_id>")
def delete_session_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    db = SessionLocal()

    try:
        deleted = delete_session(db, session_id_int)

        if not deleted:
            return jsonify(ApiResponse.fail("session not found").to_dict()), 404

    except Exception:
        logger.exception("Failed to delete session")
        return jsonify(ApiResponse.fail("Failed to delete session").to_dict()), 500

    finally:
        db.close()

    return jsonify(ApiResponse.ok({"session_id": session_id_int}).to_dict()), 200


@sessions_bp.post("/<session_id>/cancel")
def cancel_session_job_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    body = flask_request.get_json(silent=True) or {}
    job_type = body.get("job_type", "").strip()

    if not job_type:
        return jsonify(ApiResponse.fail("job_type is required").to_dict()), 400

    from ..workers.job_manager import cancel_job
    was_killed = cancel_job(session_id_int, job_type)

    return jsonify(ApiResponse.ok({
        "message": f"Job {job_type} cancellation processed",
        "was_killed": was_killed
    }).to_dict()), 200


@sessions_bp.patch("/<session_id>/title")
def update_session_title_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    body = flask_request.get_json(silent=True) or {}
    title = body.get("title", "").strip()

    if not title:
        return jsonify(ApiResponse.fail("title is required").to_dict()), 400

    if len(title) > MAX_FIELD_LENGTH:
        return jsonify(
            ApiResponse.fail(
                f"Title cannot exceed {MAX_FIELD_LENGTH} characters"
            ).to_dict()
        ), 400

    db = SessionLocal()
    try:
        session = get_session_by_id(db, session_id_int)
        if not session:
            return jsonify(ApiResponse.fail("session not found").to_dict()), 404

        session.title = title
        db.add(session)
        db.commit()
        db.refresh(session)

        return jsonify(
            ApiResponse.ok(
                {"session_id": session_id_int, "title": session.title}
            ).to_dict()
        ), 200
    except Exception:
        logger.exception("Failed to update session title")
        return jsonify(
            ApiResponse.fail("Failed to update session title").to_dict()
        ), 500
    finally:
        db.close()


@sessions_bp.patch("/<session_id>/speakers/<speaker_label>")
def update_speaker_endpoint(session_id: str, speaker_label: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    body = flask_request.get_json(silent=True) or {}
    display_name = body.get("display_name", "").strip()

    if len(display_name) > MAX_FIELD_LENGTH:
        return jsonify(
            ApiResponse.fail(
                f"Speaker name cannot exceed {MAX_FIELD_LENGTH} characters"
            ).to_dict()
        ), 400

    db = SessionLocal()
    try:
        session = get_session_by_id(db, session_id_int)
        if not session:
            return jsonify(ApiResponse.fail("session not found").to_dict()), 404

        speaker = update_speaker_display_name(
            db, session_id_int, speaker_label, display_name
        )

        from ..services.persistence import invalidate_translations
        invalidate_translations(db, session_id_int)
        db.commit()

        return jsonify(
            ApiResponse.ok(
                {
                    "speaker_label": speaker.speaker_label,
                    "display_name": speaker.display_name,
                }
            ).to_dict()
        ), 200
    except Exception:
        logger.exception("Failed to update speaker")
        return jsonify(ApiResponse.fail("Failed to update speaker").to_dict()), 500
    finally:
        db.close()


@sessions_bp.get("/<session_id>/transcript")
def get_session_transcript_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    payload = get_session_transcript(session_id_int)
    if payload is None:
        return jsonify(ApiResponse.ok({"exists": False}).to_dict()), 200

    return jsonify(ApiResponse.ok(payload).to_dict()), 200


@sessions_bp.post("/<session_id>/process")
@limiter.limit("5 per minute")
def process_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    from ..workers.job_manager import get_active_job_count

    if get_active_job_count() >= settings.MAX_BACKGROUND_WORKERS:
        return jsonify(
            ApiResponse.fail("Server overloaded. Too many active jobs.").to_dict()
        ), 503

    from ..db.session import SessionLocal
    from ..models.enums import SessionStatus
    from ..models.session import Session

    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id_int).first()
        if not session:
            return jsonify(ApiResponse.fail("Session not found").to_dict()), 404
        if session.status not in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            return jsonify(
                ApiResponse.fail(
                    "Session must be COMPLETED or FAILED to process"
                ).to_dict()
            ), 400

        updated_rows = (
            db.query(Session)
            .filter(Session.id == session_id_int, Session.status == session.status)
            .update({"status": SessionStatus.PROCESSING})
        )

        if updated_rows == 0:
            db.rollback()
            return jsonify(
                ApiResponse.fail("Session is already being processed").to_dict()
            ), 409

        db.commit()
    finally:
        db.close()

    try:
        import multiprocessing

        from ..workers.intelligence_worker import run_intelligence_pipeline
        from ..workers.job_manager import register_job

        p = multiprocessing.get_context("spawn").Process(
            target=run_intelligence_pipeline, args=(session_id_int,)
        )
        p.start()
        register_job(session_id_int, "intelligence", p.pid)
        return jsonify(ApiResponse.ok({"message": "Processing started"}).to_dict()), 202
    except Exception as e:
        logger.exception(f"Failed to spawn process for session {session_id_int}: {e}")
        rollback_db = SessionLocal()
        try:
            rollback_session = (
                rollback_db.query(Session).filter(Session.id == session_id_int).first()
            )
            if rollback_session:
                rollback_session.status = SessionStatus.FAILED
                rollback_session.processing_error = (
                    "Server overloaded. Failed to start process."
                )
                rollback_db.commit()
        finally:
            rollback_db.close()
        return jsonify(
            ApiResponse.fail("Server overloaded. Failed to start process.").to_dict()
        ), 500


@sessions_bp.post("/<session_id>/retry")
def retry_session_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    from ..db.session import SessionLocal
    from ..models.enums import SessionStatus
    from ..models.session import Session

    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id_int).first()
        if not session:
            return jsonify(ApiResponse.fail("Session not found").to_dict()), 404
        # Guard against active sessions (PROCESSING, TRANSCRIBING, DIARIZING, RECORDING) being accidentally updated
        if session.status != SessionStatus.FAILED:
            return jsonify(
                ApiResponse.fail("Only failed sessions can be retried").to_dict()
            ), 400

        from ..services.session.session_service import get_session_transcript

        transcript_data = get_session_transcript(session_id_int)
        has_transcript = (
            transcript_data is not None
            and len(transcript_data.get("transcript", [])) > 0
        )

        if not has_transcript:
            return jsonify(
                ApiResponse.fail(
                    "Cannot retry session: audio transcription failed. Please re-upload the file."
                ).to_dict()
            ), 400

        updated_rows = (
            db.query(Session)
            .filter(
                Session.id == session_id_int, Session.status == SessionStatus.FAILED
            )
            .update({"status": SessionStatus.PROCESSING, "processing_error": None})
        )

        if updated_rows == 0:
            db.rollback()
            return jsonify(
                ApiResponse.fail("Session is already being processed").to_dict()
            ), 409

        db.commit()

    finally:
        db.close()

    try:
        import multiprocessing

        from ..workers.intelligence_worker import run_intelligence_pipeline
        from ..workers.job_manager import register_job

        p = multiprocessing.get_context("spawn").Process(
            target=run_intelligence_pipeline, args=(session_id_int,)
        )
        p.start()
        register_job(session_id_int, "intelligence", p.pid)

        return jsonify(ApiResponse.ok({"message": "Retry started"}).to_dict()), 202
    except Exception as e:
        logger.exception(f"Failed to spawn retry process for session {session_id_int}")
        rollback_db = SessionLocal()
        try:
            rollback_session = (
                rollback_db.query(Session).filter(Session.id == session_id_int).first()
            )
            if rollback_session:
                rollback_session.status = SessionStatus.FAILED
                rollback_session.processing_error = f"Failed to start process: {str(e)}"
                rollback_db.commit()
        finally:
            rollback_db.close()
        return jsonify(
            ApiResponse.fail("Server overloaded. Failed to start process.").to_dict()
        ), 500


@sessions_bp.post("/<session_id>/quick-diarization")
@limiter.limit("5 per minute")
def trigger_quick_diarization(session_id: str):
    from ..workers.diarization_worker import process_quick_diarization

    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    from ..config.settings import settings
    from ..workers.job_manager import get_active_job_count

    if get_active_job_count() >= settings.MAX_BACKGROUND_WORKERS:
        return jsonify(
            ApiResponse.fail("Server overloaded. Too many active jobs.").to_dict()
        ), 503

    from ..db.session import SessionLocal
    from ..models.enums import SessionStatus
    from ..models.session import Session

    db = SessionLocal()
    try:
        # Optimistic update prevents TOCTOU race on concurrent requests
        session = db.query(Session).filter(Session.id == session_id_int).first()
        if not session:
            return jsonify(ApiResponse.fail("Session not found").to_dict()), 404
        if session.status not in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            return jsonify(
                ApiResponse.fail(
                    "Session must be COMPLETED or FAILED to run diarization"
                ).to_dict()
            ), 400

        updated_rows = (
            db.query(Session)
            .filter(Session.id == session_id_int, Session.status == session.status)
            .update({"status": SessionStatus.DIARIZING})
        )

        if updated_rows == 0:
            db.rollback()
            return jsonify(
                ApiResponse.fail("Session is already being processed").to_dict()
            ), 409

        db.commit()
    finally:
        db.close()

    # TODO(TechDebt): Fire-and-forget threads risk job loss if the process restarts.
    # Acceptable for MVP, but should be migrated to Celery/Redis in production.
    try:
        import multiprocessing

        from ..workers.job_manager import register_job
        p = multiprocessing.get_context("spawn").Process(
            target=process_quick_diarization, args=(session_id_int,)
        )
        p.start()
        register_job(session_id_int, "quick_diarization", p.pid)
        return jsonify(
            ApiResponse.ok({"message": "Quick diarization started"}).to_dict()
        ), 202
    except Exception:
        logger.exception(
            f"Failed to spawn quick diarization process for session {session_id_int}"
        )
        rollback_db = SessionLocal()
        try:
            rollback_session = (
                rollback_db.query(Session).filter(Session.id == session_id_int).first()
            )
            if rollback_session:
                rollback_session.status = SessionStatus.FAILED
                rollback_session.processing_error = (
                    "Server overloaded. Failed to start quick diarization."
                )
                rollback_db.commit()
        finally:
            rollback_db.close()
        return jsonify(
            ApiResponse.fail("Server overloaded. Failed to start process.").to_dict()
        ), 500


@sessions_bp.post("/<session_id>/accurate-diarization")
@limiter.limit("5 per minute")
def trigger_accurate_diarization(session_id: str):
    from ..workers.diarization_worker import process_accurate_diarization

    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    from ..workers.job_manager import get_active_job_count

    if get_active_job_count() >= settings.MAX_BACKGROUND_WORKERS:
        return jsonify(
            ApiResponse.fail("Server overloaded. Too many active jobs.").to_dict()
        ), 503

    from ..db.session import SessionLocal
    from ..models.enums import SessionStatus
    from ..models.session import Session

    db = SessionLocal()
    try:
        # Optimistic update prevents TOCTOU race on concurrent requests
        session = db.query(Session).filter(Session.id == session_id_int).first()
        if not session:
            return jsonify(ApiResponse.fail("Session not found").to_dict()), 404
        if session.status not in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            return jsonify(
                ApiResponse.fail(
                    "Session must be COMPLETED or FAILED to run diarization"
                ).to_dict()
            ), 400

        updated_rows = (
            db.query(Session)
            .filter(Session.id == session_id_int, Session.status == session.status)
            .update({"status": SessionStatus.DIARIZING})
        )

        if updated_rows == 0:
            db.rollback()
            return jsonify(
                ApiResponse.fail("Session is already being processed").to_dict()
            ), 409

        db.commit()
    finally:
        db.close()

    # TODO(TechDebt): Fire-and-forget threads risk job loss if the process restarts.
    # Acceptable for MVP, but should be migrated to Celery/Redis in production.

    try:
        from ..workers.job_manager import register_job
        p = multiprocessing.get_context("spawn").Process(
            target=process_accurate_diarization, args=(session_id_int,)
        )
        p.start()
        register_job(session_id_int, "accurate_diarization", p.pid)
        return jsonify(
            ApiResponse.ok({"message": "Accurate diarization started"}).to_dict()
        ), 202
    except Exception:
        logger.exception(
            f"Failed to spawn accurate diarization process for session {session_id_int}"
        )
        rollback_db = SessionLocal()
        try:
            rollback_session = (
                rollback_db.query(Session).filter(Session.id == session_id_int).first()
            )
            if rollback_session:
                rollback_session.status = SessionStatus.FAILED
                rollback_session.processing_error = (
                    "Server overloaded. Failed to start accurate diarization."
                )
                rollback_db.commit()
        finally:
            rollback_db.close()
        return jsonify(
            ApiResponse.fail("Server overloaded. Failed to start process.").to_dict()
        ), 500


@sessions_bp.get("/<session_id>/summary")
def get_session_summary(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    data = get_summary(session_id_int)
    if data is None:
        return jsonify(ApiResponse.ok({"exists": False}).to_dict()), 200

    return jsonify(ApiResponse.ok(data).to_dict()), 200


@sessions_bp.get("/languages")
def list_supported_languages():
    from ..services.translation import TranslationService

    languages = TranslationService.get_supported_languages()
    return jsonify(ApiResponse.ok(languages).to_dict()), 200


@sessions_bp.post("/<session_id>/translate")
@limiter.limit("5 per minute")
def translate_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    import multiprocessing

    body = flask_request.get_json(silent=True) or {}
    target_language = body.get("target_language", "").strip().lower()

    if not target_language:
        return jsonify(ApiResponse.fail("target_language is required").to_dict()), 400

    from ..services.translation import SUPPORTED_LANGUAGES

    if target_language not in SUPPORTED_LANGUAGES:
        return jsonify(
            ApiResponse.fail(
                f"Unsupported language: {target_language}. "
                f"Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            ).to_dict()
        ), 400

    # DB interaction

    from ..db.session import SessionLocal
    from ..models.translation import SessionTranslation
    from ..workers.translation_worker import process_translation

    db = SessionLocal()
    try:
        # Check if already translating or completed
        translation = (
            db.query(SessionTranslation)
            .filter(
                SessionTranslation.session_id == session_id_int,
                SessionTranslation.target_language == target_language,
            )
            .first()
        )

        if translation:
            if translation.status == "translating":
                return jsonify(
                    ApiResponse.ok(
                        {"message": "Translation already in progress"}
                    ).to_dict()
                ), 202
            # If completed or failed, we'll reset it to translating and re-run
            translation.status = "translating"
            translation.error_message = None
        else:
            translation = SessionTranslation(
                session_id=session_id_int,
                target_language=target_language,
                status="translating",
            )
            db.add(translation)

        db.commit()

        # Spawn background process
        try:
            from ..workers.job_manager import register_job
            p = multiprocessing.get_context("spawn").Process(
                target=process_translation, args=(session_id_int, target_language)
            )
            p.start()
            register_job(session_id_int, f"translation_{target_language}", p.pid)
        except Exception as e:
            logger.exception(
                f"Failed to start translation for session {session_id_int}"
            )
            rollback_db = SessionLocal()
            try:
                rollback_translation = (
                    rollback_db.query(SessionTranslation)
                    .filter(
                        SessionTranslation.session_id == session_id_int,
                        SessionTranslation.target_language == target_language,
                    )
                    .first()
                )
                if rollback_translation:
                    rollback_translation.status = "failed"
                    rollback_translation.error_message = (
                        "Server overloaded. Failed to start translation."
                    )
                    rollback_db.commit()
            finally:
                rollback_db.close()
            return jsonify(
                ApiResponse.fail(f"Failed to start translation: {str(e)}").to_dict()
            ), 500

    except Exception as e:
        logger.exception(
            f"Database error while starting translation for session {session_id_int}"
        )
        return jsonify(
            ApiResponse.fail(f"Failed to setup translation: {str(e)}").to_dict()
        ), 500
    finally:
        db.close()

    return jsonify(ApiResponse.ok({"message": "Translation started"}).to_dict()), 202


@sessions_bp.get("/<session_id>/translations")
def get_session_translations(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    from ..db.session import SessionLocal
    from ..models.translation import SessionTranslation

    db = SessionLocal()
    try:
        translations = (
            db.query(SessionTranslation)
            .filter(SessionTranslation.session_id == session_id_int)
            .all()
        )

        data = []
        for t in translations:
            data.append(
                {
                    "id": t.id,
                    "session_id": t.session_id,
                    "target_language": t.target_language,
                    "translated_transcript": t.translated_transcript,
                    "translated_summary": t.translated_summary,
                    "translated_mom": t.translated_mom,
                    "status": t.status,
                    "error_message": t.error_message,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                    "translated_chunks": [
                        {"chunk_id": c.chunk_id, "text": c.translated_text}
                        for c in t.chunks
                    ]
                    if getattr(t, "chunks", None)
                    else [],
                }
            )

    except Exception:
        logger.exception(f"Failed to get translations for session {session_id_int}")
        return jsonify(ApiResponse.fail("Failed to get translations").to_dict()), 500
    finally:
        db.close()

    return jsonify(ApiResponse.ok(data).to_dict()), 200
