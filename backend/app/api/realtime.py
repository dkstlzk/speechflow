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
from ..models.session import Session as SessionModel


from ..config.logging import get_logger
logger = get_logger("realtime_api")

realtime_bp = Blueprint("realtime", __name__)


@realtime_bp.post("/session")
def create_realtime_session():
    """Create a new realtime recording session.

    Called when the user presses Start Recording.
    Returns the session_id for use throughout the recording lifecycle.
    """
    db = SessionLocal()

    body = flask_request.get_json(silent=True) or {}
    title = body.get("title")
    host_name = body.get("host_name")
    participants = body.get("participants")

    try:
        session = create_session(
            db,
            session_type="realtime",
            original_filename=None,
            status=SessionStatus.RECORDING,
            title=title,
            host_name=host_name,
            participants=participants,
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
    finalized = True
    if target_session:
        finalized = target_session.finalized_event.wait(timeout=5.0)
        if not finalized:
            logger.warning(f"Session {session_id_int} finalization timed out after 5.0s. Marking FINALIZING.")

    db = SessionLocal()

    try:
        # Use row-level locking to prevent race with destroy_session
        session = db.query(SessionModel).with_for_update().filter(SessionModel.id == session_id_int).first()
        if session:
            if not session.title:
                session.title = f"Recording_{session_id_int:03d}"
            
            # If target_session is None, destroy_session already popped it and is likely committing COMPLETED.
            # Only update status if it's still RECORDING.
            if session.status == SessionStatus.RECORDING:
                if target_session is None:
                    # destroy_session is in flight but hasn't committed yet, mark FINALIZING
                    session.status = SessionStatus.FINALIZING
                elif not finalized:
                    session.status = SessionStatus.FINALIZING
                # If finalized is True, destroy_session is literally committing COMPLETED right now,
                # but since we hold the lock, it might be waiting for us. So we just let it be,
                # or set it to FINALIZING and let destroy_session overwrite it.
                else:
                    session.status = SessionStatus.FINALIZING
                
            db.add(session)
            db.commit()
            db.refresh(session)

        return jsonify(
            ApiResponse.ok(
                {
                    "session_id": session_id_int,
                    "status": session.status.value,
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
