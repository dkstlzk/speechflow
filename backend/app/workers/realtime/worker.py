import time

from flask_socketio import SocketIO

from ...config.logging import get_logger
from ...services.transcription.streaming import SpeechSegment, session_manager
from .caption_engine import emit_caption_update
from .segmentation_engine import check_segment_boundary
from .transcript_engine import transcribe_and_persist_segment

logger = get_logger(__name__)

WORKER_SLEEP_SECONDS = 0.2


def handle_session_end(socketio: SocketIO, sid: str, session) -> None:
    # Synchronous teardown only. Final chunks are already submitted by the worker loop.
    pass

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
            try:
                now = time.time()
                timeout = 3600 if session.is_paused else 60
                if now - getattr(session, "last_activity_time", now) > timeout:
                    if not session.is_ending:
                        logger.warning(
                            f"[Watchdog] Session {session.session_id} idle timeout. Finalizing."
                        )
                        session.is_ending = True

                if (
                    session.is_paused
                    and not session.pause_pending
                    and not session.is_ending
                ):
                    continue

                if session.pause_pending:
                    if session.is_transcribing:
                        continue  # wait until current transcription finishes

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
                        with session.lock:
                            session.is_transcribing = True
                        transcribe_and_persist_segment(socketio, sid, session, segment)
                    continue

                bytes_per_second = session.sample_rate * 2
                has_audio = session_manager.has_new_audio(
                    sid, min_bytes=int(bytes_per_second * 0.3)
                )

                if session.is_ending:
                    if session.is_transcribing:
                        continue  # wait for it to finish

                    if getattr(session, "final_chunk_submitted", False) is False:
                        session.final_chunk_submitted = True
                        segment = None
                        with session.lock:
                            current_buf_len = len(session.audio_buffer)
                            segment_bytes = (
                                current_buf_len - session.segment_start_offset
                            )
                            bytes_per_sec = session.sample_rate * 2

                            if segment_bytes > bytes_per_sec * 0.3:
                                segment_duration = segment_bytes / bytes_per_sec
                                segment = SpeechSegment(
                                    start_offset=session.segment_start_offset,
                                    end_offset=current_buf_len,
                                    start_time=session.segment_start_time,
                                    end_time=session.segment_start_time
                                    + segment_duration,
                                )

                        if segment:
                            with session.lock:
                                session.is_transcribing = True
                            transcribe_and_persist_segment(
                                socketio, sid, session, segment
                            )
                            continue  # let it run in background

                    handle_session_end(socketio, sid, session)
                    continue

                if not has_audio:
                    continue

                emit_caption_update(socketio, sid, session)

                if not session.is_transcribing:
                    with session.lock:
                        closed_segment = check_segment_boundary(sid, session)

                    if closed_segment:
                        with session.lock:
                            session.is_transcribing = True
                        transcribe_and_persist_segment(
                            socketio, sid, session, closed_segment
                        )
            except Exception as e:
                logger.error(
                    f"[RealtimeWorker] Error processing session {session.session_id}: {e}",
                    exc_info=True,
                )

        time.sleep(WORKER_SLEEP_SECONDS)
