from flask import Blueprint, jsonify, send_file
import os

from ..db.session import SessionLocal
from ..schemas.response import ApiResponse
from ..services.session.session_service import get_session_transcript
from ..services.summarization.transcript_processor import (
    TranscriptProcessor,
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptProcessorError,
)
from ..services.summarization.ollama import OllamaClientError
from ..services.persistence.summaries import save_summary, get_summary
from ..services.persistence.actions import save_action_items
from ..services.persistence.session_repository import (
    get_session_by_id,
    list_recent_sessions,
    delete_session,
    update_transcript_type,
)
from ..services.persistence.speaker_repository import update_speaker_display_name
from flask import request as flask_request
from ..config.logging import get_logger

logger = get_logger("sessions_api")

sessions_bp = Blueprint("sessions", __name__)


def _serialize_session(row) -> dict:
    """Serialize a Session ORM row to the API shape."""
    status = row.status.value if hasattr(row.status, "value") else row.status
    return {
        "id": row.id,
        "status": status,
        "transcript_type": row.transcript_type,
        "session_type": row.session_type,
        "original_filename": row.original_filename,
        "duration_seconds": row.duration_seconds,
        "title": row.title,
        "created_at": row.created_at.isoformat()
            if row.created_at
            else None,
        "has_audio": bool(getattr(row, "audio_path", None)),
        "audio_url": f"/api/sessions/{row.id}/audio" if getattr(row, "audio_path", None) else None,
    }


def _parse_action_items_text(raw: str) -> list[str]:
    """Parse the raw action items text into a list of individual items."""
    if not raw or raw.strip().lower() == "no action items identified.":
        return []
    items = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            line = line[2:].strip()
        elif line.startswith("* "):
            line = line[2:].strip()
        if line.lower() == "no action items identified.":
            continue
        if line and line.lower() not in ("action items", "action items:"):
            items.append(line)
    return items


@sessions_bp.get("/")
def list_sessions():
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
        safe_path = os.path.join(settings.EXPORT_DIR, "audio", filename)

        if not os.path.exists(safe_path):
            return jsonify(ApiResponse.fail("audio not found").to_dict()), 404
        
        return send_file(safe_path, mimetype="audio/wav")
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
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    db = SessionLocal()

    try:
        deleted = delete_session(db, session_id_int)

        if not deleted:
            return jsonify(
                ApiResponse.fail("session not found").to_dict()
            ), 404

    except Exception:
        logger.exception("Failed to delete session")
        return jsonify(
            ApiResponse.fail(
                "Failed to delete session"
            ).to_dict()
        ), 500

    finally:
        db.close()

    return jsonify(
        ApiResponse.ok(
            {"session_id": session_id_int}
        ).to_dict()
    ), 200


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
            ApiResponse.ok({"session_id": session_id_int, "title": session.title}).to_dict()
        ), 200
    except Exception:
        logger.exception("Failed to update session title")
        return jsonify(ApiResponse.fail("Failed to update session title").to_dict()), 500
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

    db = SessionLocal()
    try:
        session = get_session_by_id(db, session_id_int)
        if not session:
            return jsonify(ApiResponse.fail("session not found").to_dict()), 404

        speaker = update_speaker_display_name(
            db, session_id_int, speaker_label, display_name
        )

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
def process_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    processor = TranscriptProcessor()

    try:
        result = processor.process_session(session_id_int)
        
        db = SessionLocal()

        try:
            update_transcript_type(
                db,
                session_id_int,
                result["transcript_type"],
            )
        finally:
            db.close()
        
    except TranscriptNotFoundError:
        logger.warning("Transcript not found")
        return jsonify(ApiResponse.fail("Transcript not found").to_dict()), 404
    except EmptyTranscriptError:
        logger.warning("Empty transcript error")
        return jsonify(ApiResponse.fail("Transcript is empty").to_dict()), 400
    except OllamaClientError:
        logger.warning("Ollama unavailable")
        return jsonify(ApiResponse.fail("Ollama is unavailable or timed out. Ensure Ollama is running and try again.").to_dict()), 503
    except TranscriptProcessorError:
        logger.exception("Transcript processing failed")
        return jsonify(ApiResponse.fail("Transcript processing failed").to_dict()), 500

    # Persist outputs
    try:
        save_summary(session_id_int, result["summary"], result.get("mom"))
        raw_actions = result.get("action_items") or ""
        parsed_items = _parse_action_items_text(raw_actions)
        save_action_items(session_id_int, parsed_items)
    except Exception:
        logger.exception("Failed to persist generated outputs")
        return jsonify(
            ApiResponse.fail(
                "Failed to persist generated outputs"
            ).to_dict()
        ), 500
    return jsonify(ApiResponse.ok(result).to_dict()), 200


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
