import time
import numpy as np
from flask_socketio import SocketIO
from ...config.logging import get_logger
from ...services.transcription.streaming import session_manager
from .worker_state import transcriber

logger = get_logger(__name__)

CAPTION_WINDOW_SECONDS = 5.0
CAPTION_INTERVAL_SECONDS = 0.3

def emit_caption_update(socketio: SocketIO, sid: str, session) -> None:
    now = time.time()
    if (now - session.last_caption_time) < CAPTION_INTERVAL_SECONDS:
        return

    with session.lock:
        audio_window = session_manager.get_caption_window(
            sid, window_seconds=CAPTION_WINDOW_SECONDS
        )
    if not audio_window:
        return

    session.last_caption_time = now

    try:
        audio_np = (
            np.frombuffer(audio_window, dtype=np.int16).astype(np.float32)
            / 32768.0
        )
        t0 = time.time()
        logger.debug(f"[CaptionEngine] Whisper inference starting for {sid} at {t0:.3f}")
        import eventlet
        result = eventlet.tpool.execute(transcriber.transcribe, audio_np)
        t1 = time.time()
        logger.debug(f"[CaptionEngine] Whisper inference finished for {sid} at {t1:.3f} (Duration: {t1-t0:.3f}s)")
        text = result.text.strip() if result.text else ""

        if text:
            socketio.emit(
                "caption_update",
                {"text": text, "timestamp": now, "session_id": session.session_id},
                to=sid,
            )
    except Exception as e:
        logger.error(f"[CaptionEngine] Inference error for {sid}: {e}")
