from flask import Blueprint, jsonify

from ..schemas.response import ApiResponse

actions_bp = Blueprint("actions", __name__)


@actions_bp.get("/<session_id>")
def get_actions(session_id: str):
    # TODO: load action items for session.
    return jsonify(ApiResponse.fail("not implemented").to_dict()), 501
