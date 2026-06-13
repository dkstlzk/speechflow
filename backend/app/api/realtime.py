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
    """Move session from RECORDING → COMPLETED.

    Called when the user presses Stop and the backend has finished
    persisting the final segment.
    """
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(
            ApiResponse.fail("invalid session id").to_dict()
        ), 400

    from ..services.transcription.streaming import session_manager
    
    target_session = next(
        (
            s
            for s in list(session_manager.active_sessions.values())
            if str(s.session_id) == str(session_id_int)
        ),
        None,
    )
            
    # Wait up to 5 seconds for background audio processing to finish destroying
    if target_session:
        finalized = target_session.finalized_event.wait(timeout=5.0)
        if not finalized:
            from ..config.logging import get_logger
            logger = get_logger("realtime_api")
            logger.warning(f"Session {session_id_int} finalization timed out after 5.0s")

    db = SessionLocal()

    try:
        session = get_session_by_id(db, session_id_int)
        if session:
            if not session.title:
                session.title = f"Recording_{session_id_int:03d}"
            
            if target_session is None and session.status == SessionStatus.RECORDING:
                session.status = SessionStatus.FAILED
                logger.warning(f"Session {session_id_int} finalized but no active session found. Marking FAILED.")
            elif session.status != SessionStatus.FAILED:
                session.status = SessionStatus.COMPLETED
                
            db.add(session)
            db.commit()
            db.refresh(session)

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
