from flask import Blueprint, jsonify

from ..schemas.response import ApiResponse
from ..services.session.session_service import get_session_transcript

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.get("/")
def list_sessions():
    # TODO: return recent sessions for history view.
    return jsonify(ApiResponse.fail("not implemented").to_dict()), 501


@sessions_bp.get("/<session_id>")
def get_session(session_id: str):
    # TODO: load session, transcript, and summaries from persistence layer.
    return (
        jsonify(ApiResponse.fail("not implemented").to_dict()),
        501,
    )


@sessions_bp.get("/<session_id>/transcript")
def get_session_transcript_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    payload = get_session_transcript(session_id_int)
    if payload is None:
        return jsonify(ApiResponse.fail("session not found").to_dict()), 404

    return jsonify(ApiResponse.ok(payload).to_dict()), 200
