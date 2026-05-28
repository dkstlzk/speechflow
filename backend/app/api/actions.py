from flask import Blueprint, jsonify

actions_bp = Blueprint("actions", __name__)


@actions_bp.get("/<session_id>")
def get_actions(session_id: str):
    # TODO: load action items for session.
    return jsonify({"status": "not_implemented", "session_id": session_id}), 501
