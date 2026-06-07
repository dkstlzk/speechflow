import time
from flask import request
from flask_socketio import SocketIO, emit

# Import the new session manager (adjust import path if your IDE prefers relative imports)
from ..services.transcription.streaming import session_manager

def register_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect():
        print(f"[Socket.IO] Connected: {request.sid}")
        emit("server_status", {"status": "connected"})

    @socketio.on("disconnect")
    def handle_disconnect():
        print(f"[Socket.IO] Disconnected: {request.sid}")
        # Failsafe: Destroy session and free memory if the user closes the tab unexpectedly
        session_manager.destroy_session(request.sid)

    @socketio.on("ping_test")
    def handle_ping_test(data):
        print(f"[Socket.IO] Ping from {request.sid}", data)
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
        session_id = payload.get("session_id", "unknown_session") if payload else "unknown_session"
        # Extract dynamic sample rate, fallback to 16000
        sample_rate = payload.get("sample_rate", 16000) if payload else 16000
        
        # Create a dedicated memory buffer for this connection
        session_manager.create_session(request.sid, session_id, sample_rate)
        
        emit("stream_ack", {"status": "started"})

    @socketio.on("audio_chunk")
    def handle_audio_chunk(payload):
        # Append incoming raw bytes directly to this user's stateful audio buffer
        session_manager.append_audio(request.sid, payload)

    @socketio.on("stream_end")
    def handle_stream_end(_payload):
        # The user clicked stop. Clean up the memory tracker.
        session_manager.destroy_session(request.sid)
        
        # TODO: Here is where we will eventually trigger diarization and summarization
        emit("stream_complete", {"status": "finalizing"})
        