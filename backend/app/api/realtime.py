from flask import Blueprint, jsonify

from ..db.session import SessionLocal
from ..schemas.response import ApiResponse
from ..models.enums import SessionStatus
from ..services.persistence.session_repository import (
    create_session,
    update_session_status,
)

realtime_bp = Blueprint("realtime", __name__)


@realtime_bp.post("/session")
def create_realtime_session():
    db = SessionLocal()

    try:
        session = create_session(
            db,
            session_type="realtime",
            original_filename=None,
            status=SessionStatus.PENDING,
        )

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session.id,
                    "status": session.status.value,
                }
            ).to_dict()
        ), 200

    finally:
        db.close()


@realtime_bp.post("/session/<session_id>/finalize")
def finalize_realtime_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    db = SessionLocal()

    try:
        update_session_status(
            db,
            session_id_int,
            SessionStatus.COMPLETED,
        )

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session_id_int,
                    "status": "completed",
                }
            ).to_dict()
        ), 200

    finally:
        db.close()