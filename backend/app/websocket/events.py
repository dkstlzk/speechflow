import time

from flask import request, session
from flask_socketio import SocketIO, emit, join_room

from ..config.logging import get_logger
from ..services.transcription.streaming import session_manager
from ..workers.realtime.worker import handle_pause, handle_resume

logger = get_logger(__name__)


def register_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect():
        if not session.get("authenticated"):
            logger.warning(
                f"[Socket.IO] Unauthorized connection attempt: {request.sid}"
            )
            return False  # Reject connection

        join_room("admin")
        logger.info(f"[Socket.IO] Connected: {request.sid} (joined admin room)")
        emit("server_status", {"status": "connected"})

    @socketio.on("disconnect")
    def handle_disconnect():
        session = session_manager.get_session_by_sid(request.sid)
        if session:
            with session.lock:
                session.is_ending = True
        logger.info(f"[Socket.IO] Disconnect requested: {request.sid}")

    @socketio.on("ping_test")
    def handle_ping_test(data):
        # Ping test log is intentionally removed as an obvious debug artifact
        emit(
            "pong_test",
            {
                "message": "backend_alive",
                "sid": request.sid,
                "server_time": time.time(),
                "echo_client_time": data.get("client_time"),
            },
        )

    @socketio.on("stream_start")
    def handle_stream_start(payload):
        # Extract the session_id sent by the frontend's startRecording()
        session_id = (
            payload.get("session_id", "unknown_session")
            if payload
            else "unknown_session"
        )
        
        # Validate session in DB
        from ..db.session import SessionLocal
        from ..models.enums import SessionStatus
        from ..models.session import Session
        
        db = SessionLocal()
        try:
            try:
                sid_int = int(session_id)
            except ValueError:
                logger.error(f"[Socket.IO] Invalid session_id format: {session_id}")
                return
            
            db_session = db.query(Session).filter(Session.id == sid_int).first()
            if not db_session or db_session.status != SessionStatus.RECORDING:
                logger.error(f"[Socket.IO] Cannot start stream for session {session_id} - not found or not RECORDING")
                return
                
            # Extract dynamic sample rate, fallback to 16000
            sample_rate = payload.get("sample_rate", 16000) if payload else 16000
            
            try:
                # Create a dedicated memory buffer for this connection
                session_manager.create_session(request.sid, session_id, sample_rate)
                
                db_session.sample_rate = sample_rate
                db.commit()
            except Exception:
                db.rollback()
                session_manager.destroy_session(request.sid)
                raise
            
        finally:
            db.close()

        emit(
            "stream_ack",
            {
                "status": "started",
                "session_id": session_id,
                "sample_rate": sample_rate,
            },
        )

    @socketio.on("audio_chunk")
    def handle_audio_chunk(payload):
        logger.debug(
            f"[Socket.IO] audio_chunk received for {request.sid} at {time.time():.3f}"
        )
        try:
            # Append incoming raw bytes directly to this user's stateful audio buffer
            session_manager.append_audio(request.sid, payload)
        except RuntimeError as e:
            logger.error(f"[Socket.IO] Stream aborted for {request.sid}: {e}")
            session = session_manager.get_session_by_sid(request.sid)
            if session:
                emit(
                    "stream_error",
                    {
                        "status": "error",
                        "error": str(e),
                        "session_id": session.session_id,
                    },
                )
                # The worker loop will see session.is_ending == True (set inside append_audio) 
                # and clean up the session organically.

    @socketio.on("stream_end")
    def handle_stream_end(_payload):
        session = session_manager.get_session_by_sid(request.sid)
        if session:
            with session.lock:
                session.is_ending = True
            emit(
                "stream_complete",
                {"status": "finalizing", "session_id": session.session_id},
            )

    @socketio.on("stream_pause")
    def handle_stream_pause(_payload):
        session = session_manager.get_session_by_sid(request.sid)
        if session:
            with session.lock:
                if not session.is_paused:
                    handle_pause(socketio, request.sid, session)
            
            emit(
                "stream_paused", {"status": "paused", "session_id": session.session_id}
            )

    @socketio.on("stream_resume")
    def handle_stream_resume(_payload):
        session = session_manager.get_session_by_sid(request.sid)
        if session:
            with session.lock:
                if session.is_paused:
                    handle_resume(request.sid, session)
            
            emit(
                "stream_resumed",
                {"status": "recording", "session_id": session.session_id},
            )
