
import numpy as np
from flask_socketio import SocketIO

from ...config.logging import get_logger
from ...services.persistence.transcripts import save_transcript_chunks
from ...services.transcription.streaming import SpeechSegment, session_manager

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
        current_chunk_index = session.chunk_index
        if current_chunk_index in session.persisted_chunk_indices:
            session.is_transcribing = False
            return

    if not audio_bytes:
        with session.lock:
            session.is_transcribing = False
        return

    def _do_transcribe():
        try:
            audio_np = (
                np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )

            logger.debug(
                f"[TranscriptEngine] Whisper inference starting for {sid} chunk #{current_chunk_index}"
            )
            # pyrefly: ignore [missing-import]
            import eventlet.tpool

            from .worker_state import transcriber

            # Provide fast_mode=False for persisted chunks and DO NOT lock language
            # so Whisper can dynamically detect code-switching per segment.
            result = eventlet.tpool.execute(
                transcriber.transcribe, audio_np, getattr(session, 'detected_language', None), False
            )

            # Keep the initially detected language locked in for future fast-mode live captions
            # but allow the final chunk to be whatever Whisper detected.
            if result.language and not session.detected_language:
                session.detected_language = result.language
            logger.info(
                f"[TranscriptEngine] Whisper inference finished for {sid} chunk #{current_chunk_index}"
            )

            text = result.text.strip() if result.text else ""

            if not text.strip():
                logger.info(
                    f"[TranscriptEngine] Empty transcription for "
                    f"chunk #{current_chunk_index} — skipping"
                )
                with session.lock:
                    session_manager.advance_segment(
                        sid, segment.end_time, segment.end_offset
                    )
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
                            "language": result.language,
                        }
                    ],
                )
            except IntegrityError as e:
                logger.warning(
                    f"[TranscriptEngine] Integrity error saving chunk #{current_chunk_index} "
                    f"for session {session.session_id}. Session was likely deleted mid-transaction. Error: {e}"
                )
                return
            except Exception as db_e:
                logger.error(f"[TranscriptEngine] DB Error saving chunk: {db_e}")
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
                session_manager.advance_segment(
                    sid, segment.end_time, segment.end_offset
                )
                session_manager.trim_buffer_after_persist(
                    sid, keep_seconds=TRIM_KEEP_SECONDS
                )

        except Exception:
            logger.exception(
                f"[TranscriptEngine] Error for {sid} chunk #{current_chunk_index}"
            )
        finally:
            with session.lock:
                session.is_transcribing = False

    # pyrefly: ignore [missing-import]
    import eventlet

    eventlet.spawn(_do_transcribe)
