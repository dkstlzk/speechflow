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
    audio_bytes = session_manager.get_segment_audio(
        sid, segment, context_seconds=CONTEXT_OVERLAP_SECONDS
    )
    if not audio_bytes:
        return

    if session.chunk_index in session.persisted_chunk_indices:
        return

    try:
        audio_np = (
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            / 32768.0
        )

        result = transcriber.transcribe(audio_np)
        text = result.text.strip() if result.text else ""

        if not text.strip():
            logger.info(
                f"[TranscriptEngine] Empty transcription for "
                f"chunk #{session.chunk_index} — skipping"
            )
            session_manager.advance_segment(sid, segment.end_time, segment.end_offset)
            return

        save_transcript_chunks(
            int(session.session_id),
            [
                {
                    "session_id": int(session.session_id),
                    "speaker_id": None,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": text,
                    "chunk_index": session.chunk_index,
                    "is_partial": False,
                }
            ],
        )

        session.persisted_chunk_indices.add(session.chunk_index)

        logger.info(
            f"[TranscriptEngine] Persisted chunk #{session.chunk_index} "
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
                "chunk_index": session.chunk_index,
            },
            to=sid,
        )

        session_manager.advance_segment(sid, segment.end_time, segment.end_offset)

        session_manager.trim_buffer_after_persist(
            sid, keep_seconds=TRIM_KEEP_SECONDS
        )

    except Exception:
        logger.exception(
            f"[TranscriptEngine] Error for {sid} "
            f"chunk #{session.chunk_index}"
        )
