import time

# pyrefly: ignore [missing-import]
import eventlet

# pyrefly: ignore [missing-import]
import eventlet.tpool
import numpy as np
from flask_socketio import SocketIO

from ...config.logging import get_logger
from ...services.transcription.streaming import session_manager
from .worker_state import transcriber

logger = get_logger(__name__)

# Window size of 5.0s to capture full sentences, update every 0.5s for lower latency
CAPTION_WINDOW_SECONDS = 5.0
CAPTION_INTERVAL_SECONDS = 0.5


def emit_caption_update(socketio: SocketIO, sid: str, session) -> None:
    now = time.time()
    if (now - session.last_caption_time) < CAPTION_INTERVAL_SECONDS:
        return

    with session.lock:
        if session.is_captioning:
            return
        session.is_captioning = True

        audio_window = session_manager.get_caption_window(
            sid, window_seconds=CAPTION_WINDOW_SECONDS
        )
        if audio_window:
            session.last_caption_time = now

    if not audio_window:
        session.is_captioning = False
        return

    def _do_caption_inference(audio_np, session_id, now):
        try:
            # tpool.execute runs the blocking C++ inference in a true OS thread,
            # preventing it from freezing the Eventlet websocket loop.
            # We enforce fast_mode=True to skip languge detection and get sub-second latency.
            # We pass the previously detected language to maintain consistency, 
            # because fast_mode skips detection and defaults to English.
            result = eventlet.tpool.execute(
                transcriber.transcribe, audio_np, getattr(session, 'detected_language', None), True
            )
            text = result.text.strip() if result.text else ""

            if text:
                socketio.emit(
                    "caption_update",
                    {"text": text, "timestamp": now, "session_id": session_id},
                    to=sid,
                )
        except Exception as e:
            logger.error(f"[CaptionEngine] Inference error for {sid}: {e}")
        finally:
            with session.lock:
                session.is_captioning = False

    try:
        audio_np = (
            np.frombuffer(audio_window, dtype=np.int16).astype(np.float32) / 32768.0
        )
        # Spawn a background greenthread so we don't block the caller
        eventlet.spawn(_do_caption_inference, audio_np, session.session_id, now)
    except Exception as e:
        with session.lock:
            session.is_captioning = False
        logger.error(f"[CaptionEngine] Setup error for {sid}: {e}")
