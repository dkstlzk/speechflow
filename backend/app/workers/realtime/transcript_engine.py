import time
import numpy as np
from flask_socketio import SocketIO
from ...config.logging import get_logger
from ...services.transcription.streaming import session_manager, SpeechSegment
from ...services.persistence.transcripts import save_transcript_chunks
from .worker_state import transcriber

logger = get_logger(__name__)

CONTEXT_OVERLAP_SECONDS = 0.5
TRIM_KEEP_SECONDS = 3.0

def transcribe_and_persist_segment(
    socketio: SocketIO,
    sid: str,
    session,
    segment: SpeechSegment,
) -> None:
    with session.lock:
        audio_bytes = session_manager.get_segment_audio(
            sid, segment, context_seconds=CONTEXT_OVERLAP_SECONDS
        )
    if not audio_bytes:
        return

    # We capture chunk_index upfront outside the lock
    # (Safe because this is the only thread modifying it)
    current_chunk_index = session.chunk_index
    if current_chunk_index in session.persisted_chunk_indices:
        return

    try:
        audio_np = (
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            / 32768.0
        )

        t0 = time.time()
        logger.debug(f"[TranscriptEngine] Whisper inference starting for {sid} chunk #{current_chunk_index} at {t0:.3f}")
        # pyrefly: ignore [missing-import]
        import eventlet
        result = eventlet.tpool.execute(transcriber.transcribe, audio_np)
        t1 = time.time()
        logger.debug(f"[TranscriptEngine] Whisper inference finished for {sid} chunk #{current_chunk_index} at {t1:.3f} (Duration: {t1-t0:.3f}s)")
        
        text = result.text.strip() if result.text else ""

        if not text.strip():
            logger.info(
                f"[TranscriptEngine] Empty transcription for "
                f"chunk #{current_chunk_index} — skipping"
            )
            with session.lock:
                session_manager.advance_segment(sid, segment.end_time, segment.end_offset)
            return

        from sqlalchemy.exc import IntegrityError
        try:
            save_transcript_chunks(
                int(session.session_id),
                [
                    {
                        "session_id": int(session.session_id),
                        "speaker_id": None,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "text": text,
                        "chunk_index": current_chunk_index,
                        "is_partial": False,
                    }
                ],
            )
        except IntegrityError as e:
            logger.warning(
                f"[TranscriptEngine] Integrity error saving chunk #{current_chunk_index} "
                f"for session {session.session_id}. Session was likely deleted mid-transaction. Error: {e}"
            )
            return

        with session.lock:
            session.persisted_chunk_indices.add(current_chunk_index)

        logger.info(
            f"[TranscriptEngine] Persisted chunk #{current_chunk_index} "
            f"({segment.start_time:.2f}s → {segment.end_time:.2f}s): "
            f"{text[:80]}..."
        )

        socketio.emit(
            "transcript_committed",
            {
                "speaker": "UNKNOWN",
                "text": text,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "chunk_index": current_chunk_index,
                "session_id": session.session_id,
            },
            to=sid,
        )

        with session.lock:
            session_manager.advance_segment(sid, segment.end_time, segment.end_offset)
            session_manager.trim_buffer_after_persist(
                sid, keep_seconds=TRIM_KEEP_SECONDS
            )

    except Exception:
        logger.exception(
            f"[TranscriptEngine] Error for {sid} "
            f"chunk #{current_chunk_index}"
        )
