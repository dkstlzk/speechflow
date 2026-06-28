from flask import Blueprint, jsonify

from ..config.logging import get_logger
from ..schemas.response import ApiResponse
from ..services.persistence.actions import list_action_items

logger = get_logger(__name__)

actions_bp = Blueprint("actions", __name__)


@actions_bp.get("/<session_id>")
def get_actions(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    try:
        items = list_action_items(session_id_int)
    except Exception:
        logger.exception(
            "Failed to load action items",
            extra={"session_id": session_id_int},
        )
        return jsonify(
            ApiResponse.fail("Failed to load action items").to_dict()
        ), 500
    return jsonify(
        ApiResponse.ok(
            {"session_id": session_id_int, "action_items": items}
        ).to_dict()
    ), 200

