import time
from flask_socketio import SocketIO
from ...config.logging import get_logger
from ...services.transcription.streaming import session_manager, SpeechSegment
from .caption_engine import emit_caption_update
from .segmentation_engine import check_segment_boundary
from .transcript_engine import transcribe_and_persist_segment

logger = get_logger(__name__)

WORKER_SLEEP_SECONDS = 0.2

def handle_session_end(socketio: SocketIO, sid: str, session) -> None:
    segment = None
    with session.lock:
        current_buf_len = len(session.audio_buffer)
        segment_bytes = current_buf_len - session.segment_start_offset
        bytes_per_sec = session.sample_rate * 2

        if segment_bytes > bytes_per_sec * 0.3:
            segment_duration = segment_bytes / bytes_per_sec
            segment = SpeechSegment(
                start_offset=session.segment_start_offset,
                end_offset=current_buf_len,
                start_time=session.segment_start_time,
                end_time=session.segment_start_time + segment_duration,
            )

    if segment:
        transcribe_and_persist_segment(socketio, sid, session, segment)

    logger.info(f"[RealtimeWorker] Session {session.session_id} finalized")

    socketio.emit(
        "stream_finalized",
        {"session_id": session.session_id},
        to=sid,
    )

    session_manager.destroy_session(sid)


def handle_pause(socketio: SocketIO, sid: str, session) -> None:
    with session.lock:
        session.pause_pending = True
        session.is_paused = True
        session.last_activity_time = time.time()
    logger.info(f"[RealtimeWorker] Session {session.session_id} pause requested")


def handle_resume(sid: str, session) -> None:
    with session.lock:
        session.is_paused = False
        session.segment_start_offset = len(session.audio_buffer)
        session.last_speech_time = time.time()
        session.last_activity_time = time.time()
    logger.info(f"[RealtimeWorker] Session {session.session_id} resumed")


def realtime_worker_loop(socketio: SocketIO):
    logger.info("[RealtimeWorker] Background loop started. AI is ready.")

    while True:
        for sid, session in list(session_manager.active_sessions.items()):
            now = time.time()
            timeout = 3600 if session.is_paused else 60
            if now - getattr(session, 'last_activity_time', now) > timeout:
                if not session.is_ending:
                    logger.warning(f"[Watchdog] Session {session.session_id} idle timeout. Finalizing.")
                    session.is_ending = True

            if session.is_paused and not session.pause_pending and not session.is_ending:
                continue

            if session.pause_pending:
                segment = None
                with session.lock:
                    current_buf_len = len(session.audio_buffer)
                    segment_bytes = current_buf_len - session.segment_start_offset
                    bytes_per_sec = session.sample_rate * 2

                    if segment_bytes > bytes_per_sec * 0.3:
                        segment_duration = segment_bytes / bytes_per_sec
                        segment = SpeechSegment(
                            start_offset=session.segment_start_offset,
                            end_offset=current_buf_len,
                            start_time=session.segment_start_time,
                            end_time=session.segment_start_time + segment_duration,
                        )
                    session.pause_pending = False

                if segment:
                    transcribe_and_persist_segment(socketio, sid, session, segment)
                continue

            bytes_per_second = session.sample_rate * 2
            has_audio = session_manager.has_new_audio(
                sid, min_bytes=int(bytes_per_second * 0.3)
            )

            if not has_audio and not session.is_ending:
                continue

            emit_caption_update(socketio, sid, session)

            with session.lock:
                closed_segment = check_segment_boundary(sid, session)

            if closed_segment:
                transcribe_and_persist_segment(
                    socketio, sid, session, closed_segment
                )

            if session.is_ending:
                handle_session_end(socketio, sid, session)
                continue

        time.sleep(WORKER_SLEEP_SECONDS)
