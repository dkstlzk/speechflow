"""Realtime worker — four-layer architecture.

Layer 1: Audio Ingestion (handled by WebSocket events + SessionManager)
Layer 2: Live Caption Engine (emit_caption_update)
Layer 3: Speech Segmentation Engine (check_segment_boundary)
Layer 4: Transcript Engine (transcribe_and_persist_segment)
+ Buffer Trim after persistence
"""

import time
from dataclasses import dataclass
from typing import Optional

import torch
import numpy as np
from flask_socketio import SocketIO

from ..services.transcription.streaming import (
    SpeechSegment,
    session_manager,
)
from ..services.transcription.whisper_service import WhisperTranscriptionService
from ..services.persistence.transcripts import save_transcript_chunks

# ── Configuration Constants ────────────────────────────────────────────

CAPTION_WINDOW_SECONDS = 5.0     # How much audio to feed caption Whisper
CAPTION_INTERVAL_SECONDS = 1.0   # Min time between caption passes
SILENCE_THRESHOLD_SECONDS = 1.5  # Silence duration to close a segment
MAX_SEGMENT_SECONDS = 25.0       # Hard cap on segment length
CONTEXT_OVERLAP_SECONDS = 0.5    # Context prepended to segment for Whisper
TRIM_KEEP_SECONDS = 3.0          # Audio retained after segment persist
VAD_SPEECH_THRESHOLD = 0.5       # Silero VAD probability threshold
WORKER_SLEEP_SECONDS = 0.2       # Main loop tick interval

# ── Load Models Once ───────────────────────────────────────────────────

transcriber = WhisperTranscriptionService()

try:
    from silero_vad import load_silero_vad
    vad_model = load_silero_vad(onnx=True)
    print("[VAD] Silero VAD loaded successfully (ONNX CPU Mode).")
except Exception as e:
    print(f"[VAD] Error loading Silero VAD. Running without VAD. Error: {e}")
    vad_model = None


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2 — LIVE CAPTION ENGINE
# ═══════════════════════════════════════════════════════════════════════

def emit_caption_update(socketio: SocketIO, sid: str, session) -> None:
    """Run a fast Whisper pass on the trailing audio window and emit
    a disposable caption to the frontend.

    Throttled to run at most once per CAPTION_INTERVAL_SECONDS.
    Output is NEVER persisted. NEVER used for transcripts.
    """
    now = time.time()
    if (now - session.last_caption_time) < CAPTION_INTERVAL_SECONDS:
        return

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
        result = transcriber.transcribe(audio_np)
        text = result.text.strip() if result.text else ""

        if text:
            socketio.emit(
                "caption_update",
                {"text": text, "timestamp": now},
                to=sid,
            )
    except Exception as e:
        print(f"[CaptionEngine] Inference error for {sid}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# LAYER 3 — SPEECH SEGMENTATION ENGINE
# ═══════════════════════════════════════════════════════════════════════

def _check_vad_speaking(audio_np: np.ndarray, sample_rate: int) -> bool:
    """Run Silero VAD on the last 1 second of audio.
    Returns True if speech is detected."""
    if vad_model is None:
        return True  # Fallback: assume speech

    if len(audio_np) < sample_rate:
        return True  # Not enough audio for VAD

    try:
        last_second = audio_np[-sample_rate:]
        chunk_size = 512 if sample_rate == 16000 else 256

        for i in range(0, len(last_second), chunk_size):
            vad_chunk = last_second[i : i + chunk_size]
            if len(vad_chunk) != chunk_size:
                continue

            vad_tensor = torch.from_numpy(vad_chunk)
            speech_prob = vad_model(vad_tensor, sample_rate).item()

            if speech_prob > VAD_SPEECH_THRESHOLD:
                return True

        return False

    except Exception as e:
        print(f"[VAD Warning] {e}")
        return True  # Fail open — assume speech


def check_segment_boundary(
    sid: str, session
) -> Optional[SpeechSegment]:
    """Check if the current speech segment should close.

    A segment closes when:
      A. Silence > SILENCE_THRESHOLD_SECONDS
      B. Segment duration > MAX_SEGMENT_SECONDS
      C. session.is_ending is True

    Returns a SpeechSegment if closed, None otherwise.
    """
    current_buf_len = len(session.audio_buffer)
    segment_bytes = current_buf_len - session.segment_start_offset
    bytes_per_sec = session.sample_rate * 2

    # Need at least 0.5 seconds in the segment to consider closing
    if segment_bytes < bytes_per_sec * 0.5 and not session.is_ending:
        return None

    segment_duration = segment_bytes / bytes_per_sec
    now = time.time()

    # Run VAD on the tail of the current segment
    segment_audio = session.audio_buffer[session.segment_start_offset:]
    audio_np = (
        np.frombuffer(bytes(segment_audio), dtype=np.int16).astype(np.float32)
        / 32768.0
    )

    is_speaking = _check_vad_speaking(audio_np, session.sample_rate)

    if is_speaking:
        session.last_speech_time = now

    silence_duration = now - session.last_speech_time

    # Determine if segment should close
    reason = None
    if session.is_ending:
        reason = "END"
    elif silence_duration >= SILENCE_THRESHOLD_SECONDS:
        reason = "SILENCE"
    elif segment_duration >= MAX_SEGMENT_SECONDS:
        reason = "MAX_LENGTH"

    if reason is None:
        return None

    # Calculate end time
    end_time = session.segment_start_time + segment_duration

    segment = SpeechSegment(
        start_offset=session.segment_start_offset,
        end_offset=current_buf_len,
        start_time=session.segment_start_time,
        end_time=end_time,
    )

    print(
        f"[Segmenter] Segment closed | Reason: {reason} "
        f"| Duration: {segment_duration:.1f}s "
        f"| Chunk #{session.chunk_index}"
    )

    return segment


# ═══════════════════════════════════════════════════════════════════════
# LAYER 4 — TRANSCRIPT ENGINE
# ═══════════════════════════════════════════════════════════════════════

def transcribe_and_persist_segment(
    socketio: SocketIO,
    sid: str,
    session,
    segment: SpeechSegment,
) -> None:
    """Final Whisper pass on a closed segment → persist to DB → emit."""
    audio_bytes = session_manager.get_segment_audio(
        sid, segment, context_seconds=CONTEXT_OVERLAP_SECONDS
    )
    if not audio_bytes:
        return

    # Task 1: Duplicate chunk protection
    if session.chunk_index in session.persisted_chunk_indices:
        return

    try:
        audio_np = (
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            / 32768.0
        )

        result = transcriber.transcribe(audio_np)
        text = result.text.strip() if result.text else ""

        # Task 2: Skip empty/silent segments purely based on text
        if not text.strip():
            print(
                f"[TranscriptEngine] Empty transcription for "
                f"chunk #{session.chunk_index} — skipping"
            )
            # Still advance segment so we don't re-process
            session_manager.advance_segment(sid, segment.end_time)
            return

        # Persist to database immediately
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

        print(
            f"[TranscriptEngine] Persisted chunk #{session.chunk_index} "
            f"({segment.start_time:.2f}s → {segment.end_time:.2f}s): "
            f"{text[:80]}..."
        )

        # Emit committed transcript to frontend
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

        # Advance segment cursor
        session_manager.advance_segment(sid, segment.end_time)

        # Trim old audio to prevent unbounded memory growth
        session_manager.trim_buffer_after_persist(
            sid, keep_seconds=TRIM_KEEP_SECONDS
        )

    except Exception as e:
        print(
            f"[TranscriptEngine] Error for {sid} "
            f"chunk #{session.chunk_index}: {e}"
        )


# ═══════════════════════════════════════════════════════════════════════
# SESSION END + PAUSE HANDLING
# ═══════════════════════════════════════════════════════════════════════

def handle_session_end(
    socketio: SocketIO, sid: str, session
) -> None:
    """Handle final segment when recording stops."""
    # Force-close whatever segment is open
    current_buf_len = len(session.audio_buffer)
    segment_bytes = current_buf_len - session.segment_start_offset
    bytes_per_sec = session.sample_rate * 2

    if segment_bytes > bytes_per_sec * 0.3:  # At least 0.3s
        segment_duration = segment_bytes / bytes_per_sec
        segment = SpeechSegment(
            start_offset=session.segment_start_offset,
            end_offset=current_buf_len,
            start_time=session.segment_start_time,
            end_time=session.segment_start_time + segment_duration,
        )
        transcribe_and_persist_segment(socketio, sid, session, segment)

    print(f"[RealtimeWorker] Session {session.session_id} finalized")

    socketio.emit(
        "stream_finalized",
        {"session_id": session.session_id},
        to=sid,
    )

    session_manager.destroy_session(sid)


def handle_pause(
    socketio: SocketIO, sid: str, session
) -> None:
    """Force-close the current segment and pause the session."""
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
        transcribe_and_persist_segment(socketio, sid, session, segment)

    session.is_paused = True
    print(f"[RealtimeWorker] Session {session.session_id} paused")


def handle_resume(sid: str, session) -> None:
    """Resume a paused session — start a new segment from current position."""
    session.is_paused = False
    session.segment_start_offset = len(session.audio_buffer)
    session.last_speech_time = time.time()
    print(f"[RealtimeWorker] Session {session.session_id} resumed")


# ═══════════════════════════════════════════════════════════════════════
# MAIN WORKER LOOP
# ═══════════════════════════════════════════════════════════════════════

def realtime_worker_loop(socketio: SocketIO):
    """Background loop orchestrating captions, segmentation, and persistence.

    Runs continuously in a daemon thread. Processes all active sessions
    each tick (~200ms).
    """
    print("[RealtimeWorker] Background loop started. AI is ready.")

    while True:
        for sid, session in list(session_manager.active_sessions.items()):
            # Skip paused sessions
            if session.is_paused:
                continue

            bytes_per_second = session.sample_rate * 2

            # Only process if we have at least 1 second of new audio
            # (or session is ending)
            has_audio = session_manager.has_new_audio(
                sid, min_bytes=bytes_per_second
            )

            if not has_audio and not session.is_ending:
                continue

            # --- LAYER 2: LIVE CAPTIONS (throttled to ~1s) ---
            emit_caption_update(socketio, sid, session)

            # --- LAYER 3: SPEECH SEGMENTATION ---
            closed_segment = check_segment_boundary(sid, session)

            # --- LAYER 4: TRANSCRIPT ENGINE ---
            if closed_segment:
                transcribe_and_persist_segment(
                    socketio, sid, session, closed_segment
                )

            # Handle session ending
            if session.is_ending:
                handle_session_end(socketio, sid, session)
                continue  # Session destroyed, move on

        time.sleep(WORKER_SLEEP_SECONDS)