import time
from flask import request
from flask_socketio import SocketIO, emit

def register_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect():
        print(f"[Socket.IO] Connected: {request.sid}")
        emit("server_status", {"status": "connected"})

    @socketio.on("disconnect")
    def handle_disconnect():
        print(f"[Socket.IO] Disconnected: {request.sid}")

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
    def handle_stream_start(_payload):
        # TODO: create streaming session and initialize rolling buffer.
        emit("stream_ack", {"status": "started"})

    @socketio.on("audio_chunk")
    def handle_audio_chunk(_payload):
        # TODO: append chunk to rolling buffer.
        # TODO: run VAD gating and rolling Whisper inference window.
        # TODO: emit partial transcript chunks with chunk_index.
        emit("partial_transcript", {"status": "not_implemented"})

    @socketio.on("stream_end")
    def handle_stream_end(_payload):
        # TODO: finalize session, run diarization and summarization.
        # TODO: persist final transcript and session status.
        emit("stream_complete", {"status": "finalizing"})
