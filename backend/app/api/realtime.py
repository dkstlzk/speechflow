from flask import Blueprint, jsonify, request as flask_request

from ..db.session import SessionLocal
from ..schemas.response import ApiResponse
from ..models.enums import SessionStatus
from ..services.persistence.session_repository import (
    create_session,
    delete_session,
    get_session_by_id,
    update_session_status,
)


realtime_bp = Blueprint("realtime", __name__)


@realtime_bp.post("/session")
def create_realtime_session():
    """Create a new realtime recording session.

    Called when the user presses Start Recording.
    Returns the session_id for use throughout the recording lifecycle.
    """
    db = SessionLocal()

    try:
        session = create_session(
            db,
            session_type="realtime",
            original_filename=None,
            status=SessionStatus.RECORDING,
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
    """Move session from RECORDING → REVIEW.

    Called when the user presses Stop and the backend has finished
    persisting the final segment.
    """
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    import time
    from ..services.transcription.streaming import session_manager
    
    # Wait up to 5 seconds for background audio processing to finish destroying
    for _ in range(50):
        is_active = False
        for active_sid, s in session_manager.active_sessions.items():
            if str(s.session_id) == str(session_id_int):
                is_active = True
                break
        if not is_active:
            break
        time.sleep(0.1)

    db = SessionLocal()

    try:
        update_session_status(
            db,
            session_id_int,
            SessionStatus.REVIEW,
        )

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session_id_int,
                    "status": "review",
                }
            ).to_dict()
        ), 200

    finally:
        db.close()


@realtime_bp.post("/session/<session_id>/save")
def save_realtime_session(session_id: str):
    """Save a reviewed recording.

    Moves session from REVIEW → SAVED and assigns a default title
    if none is provided.
    """
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    db = SessionLocal()

    try:
        session = get_session_by_id(db, session_id_int)
        if session is None:
            return jsonify(
                ApiResponse.fail("session not found").to_dict()
            ), 404

        # Assign default title: Recording_001, Recording_002, etc.
        if not session.title:
            session.title = f"Recording_{session_id_int:03d}"

        session.status = SessionStatus.SAVED
        db.add(session)
        db.commit()
        db.refresh(session)

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session_id_int,
                    "status": "saved",
                    "title": session.title,
                }
            ).to_dict()
        ), 200

    finally:
        db.close()


@realtime_bp.delete("/session/<session_id>")
def delete_realtime_session(session_id: str):
    """Hard delete a recording and all associated data.

    Removes session row, transcript chunks, speakers, summaries,
    and action items permanently.
    """
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

        return jsonify(
            ApiResponse.ok(
                {"session_id": session_id_int, "deleted": True}
            ).to_dict()
        ), 200

    finally:
        db.close()


@realtime_bp.patch("/session/<session_id>/title")
def update_realtime_title(session_id: str):
    """Update the title of a saved recording."""
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    body = flask_request.get_json(silent=True) or {}
    title = body.get("title", "").strip()

    if not title:
        return jsonify(
            ApiResponse.fail("title is required").to_dict()
        ), 400

    db = SessionLocal()

    try:
        session = get_session_by_id(db, session_id_int)
        if session is None:
            return jsonify(
                ApiResponse.fail("session not found").to_dict()
            ), 404

        session.title = title
        db.add(session)
        db.commit()
        db.refresh(session)

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session_id_int,
                    "title": session.title,
                }
            ).to_dict()
        ), 200

    finally:
        db.close()