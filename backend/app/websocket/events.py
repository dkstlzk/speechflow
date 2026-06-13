import time
from flask import request
from flask_socketio import SocketIO, emit

from ..config.logging import get_logger
from ..services.transcription.streaming import session_manager
from ..workers.realtime.worker import handle_pause, handle_resume

logger = get_logger(__name__)


def register_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect():
        logger.info(f"[Socket.IO] Connected: {request.sid}")
        emit("server_status", {"status": "connected"})

    @socketio.on("disconnect")
    def handle_disconnect():
        session = session_manager.active_sessions.get(request.sid)
        if session:
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
        # Extract dynamic sample rate, fallback to 16000
        sample_rate = (
            payload.get("sample_rate", 16000)
            if payload
            else 16000
        )

        # Create a dedicated memory buffer for this connection
        session_manager.create_session(request.sid, session_id, sample_rate)

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
        logger.debug(f"[Socket.IO] audio_chunk received for {request.sid} at {time.time():.3f}")
        # Append incoming raw bytes directly to this user's stateful audio buffer
        session_manager.append_audio(request.sid, payload)

    @socketio.on("stream_end")
    def handle_stream_end(_payload):
        session = session_manager.active_sessions.get(request.sid)
        if session:
            session.is_ending = True
            emit(
                "stream_complete",
                {"status": "finalizing", "session_id": session.session_id},
            )

    @socketio.on("stream_pause")
    def handle_stream_pause(_payload):
        session = session_manager.active_sessions.get(request.sid)
        if session and not session.is_paused:
            handle_pause(socketio, request.sid, session)
        if session:
            emit("stream_paused", {"status": "paused", "session_id": session.session_id})

    @socketio.on("stream_resume")
    def handle_stream_resume(_payload):
        session = session_manager.active_sessions.get(request.sid)
        if session and session.is_paused:
            handle_resume(request.sid, session)
        if session:
            emit("stream_resumed", {"status": "recording", "session_id": session.session_id})