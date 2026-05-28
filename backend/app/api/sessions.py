from flask import Blueprint, jsonify

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.get("/")
def list_sessions():
    # TODO: return recent sessions for history view.
    return jsonify({"status": "not_implemented"}), 501


@sessions_bp.get("/<session_id>")
def get_session(session_id: str):
    # TODO: load session, transcript, and summaries from persistence layer.
    return jsonify({"status": "not_implemented", "session_id": session_id}), 501
