import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class StreamingSession:
    """In-memory state for one active realtime recording connection.

    Responsibilities:
      - Accumulate raw PCM audio bytes
      - Track segment boundaries (byte offsets + timestamps)
      - Track caption throttle
      - Track lifecycle flags (ending, paused)

    Does NOT hold any transcript text or Whisper output.
    """

    sid: str
    session_id: str
    sample_rate: int = 16000

    # Continuous audio buffer (raw PCM Int16 mono)
    audio_buffer: bytearray = field(default_factory=bytearray)
    created_at: float = field(default_factory=time.time)
    recording_started_at: float = field(default_factory=time.time)

    # Cursor for detecting new audio arrival
    processed_offset: int = 0

    # Segment tracking — byte offsets into audio_buffer
    segment_start_offset: int = 0
    segment_start_time: float = 0.0  # recording-relative seconds
    last_speech_time: float = field(default_factory=time.time)  # wall clock

    # Caption throttle
    last_caption_time: float = 0.0

    # Counters
    chunk_index: int = 0
    persisted_chunk_indices: set = field(default_factory=set)

    # Lifecycle
    is_ending: bool = False
    is_paused: bool = False


@dataclass
class SpeechSegment:
    """A closed speech segment ready for final transcription."""

    start_offset: int  # byte offset in audio_buffer
    end_offset: int    # byte offset in audio_buffer
    start_time: float  # recording-relative seconds
    end_time: float    # recording-relative seconds


class StreamingSessionManager:
    """Manages in-memory streaming sessions keyed by Socket.IO sid."""

    def __init__(self) -> None:
        self.active_sessions: Dict[str, StreamingSession] = {}

    # ── Session Lifecycle ──────────────────────────────────────────────

    def create_session(
        self, sid: str, session_id: str, sample_rate: int = 16000
    ) -> StreamingSession:
        session = StreamingSession(
            sid=sid, session_id=session_id, sample_rate=sample_rate
        )
        self.active_sessions[sid] = session
        print(
            f"[SessionManager] Created Session | SID: {sid} "
            f"| DB Session ID: {session_id} | Rate: {sample_rate}Hz"
        )
        return session

    def destroy_session(self, sid: str) -> None:
        if sid in self.active_sessions:
            session = self.active_sessions.pop(sid)
            print(
                f"[SessionManager] Destroyed Session | SID: {sid} "
                f"| Final Buffer Size: {len(session.audio_buffer)} bytes"
            )

    # ── Audio Ingestion ────────────────────────────────────────────────

    def append_audio(self, sid: str, chunk: bytes) -> None:
        session = self.active_sessions.get(sid)
        if session:
            session.audio_buffer.extend(chunk)
        else:
            print(
                f"[SessionManager] WARNING: Audio chunk received "
                f"for untracked SID: {sid}"
            )

    def has_new_audio(self, sid: str, min_bytes: int) -> bool:
        """Check if enough new bytes arrived since last check."""
        session = self.active_sessions.get(sid)
        if not session:
            return False
        unread = len(session.audio_buffer) - session.processed_offset
        if unread >= min_bytes:
            session.processed_offset = len(session.audio_buffer)
            return True
        return False

    # ── Caption Window ─────────────────────────────────────────────────

    def get_caption_window(
        self, sid: str, window_seconds: float = 5.0
    ) -> Optional[bytes]:
        """Return the last N seconds of audio for caption inference.

        This is a trailing window — always the most recent audio.
        Used by the caption engine (Layer 2) only.
        """
        session = self.active_sessions.get(sid)
        if not session:
            return None

        bytes_per_sec = session.sample_rate * 2  # PCM Int16 = 2 bytes/sample
        window_size = int(bytes_per_sec * window_seconds)

        if len(session.audio_buffer) < bytes_per_sec:
            return None  # Need at least 1 second

        return bytes(session.audio_buffer[-window_size:])

    # ── Segment Audio Extraction ───────────────────────────────────────

    def get_segment_audio(
        self,
        sid: str,
        segment: "SpeechSegment",
        context_seconds: float = 0.5,
    ) -> Optional[bytes]:
        """Extract audio for a closed segment with context overlap.

        Returns the segment audio prepended with `context_seconds` of
        audio from before the segment start for Whisper context.
        The caller should only use timestamps from the current segment.
        """
        session = self.active_sessions.get(sid)
        if not session:
            return None

        bytes_per_sec = session.sample_rate * 2
        context_bytes = int(bytes_per_sec * context_seconds)

        # Context starts before the segment (clamped to buffer start)
        context_start = max(0, segment.start_offset - context_bytes)
        audio_slice = session.audio_buffer[context_start : segment.end_offset]

        return bytes(audio_slice)

    def get_current_segment_duration(self, sid: str) -> float:
        """How many seconds of audio are in the current open segment."""
        session = self.active_sessions.get(sid)
        if not session:
            return 0.0

        segment_bytes = len(session.audio_buffer) - session.segment_start_offset
        bytes_per_sec = session.sample_rate * 2
        return segment_bytes / bytes_per_sec

    # ── Buffer Trimming ────────────────────────────────────────────────

    def trim_buffer_after_persist(
        self, sid: str, keep_seconds: float = 3.0
    ) -> None:
        """Trim old audio after a segment has been persisted.

        Keeps `keep_seconds` of overlap audio for context, removes
        everything before that. Adjusts all byte offsets.

        This prevents unbounded memory growth during long recordings.
        """
        session = self.active_sessions.get(sid)
        if not session:
            return

        bytes_per_sec = session.sample_rate * 2
        keep_bytes = int(bytes_per_sec * keep_seconds)

        # How much can we trim? Everything before (segment_start_offset - keep_bytes)
        trim_up_to = max(0, session.segment_start_offset - keep_bytes)

        if trim_up_to <= 0:
            return

        # Perform the trim
        session.audio_buffer = session.audio_buffer[trim_up_to:]

        # Adjust all byte offsets
        session.segment_start_offset -= trim_up_to
        session.processed_offset = max(
            0, session.processed_offset - trim_up_to
        )

    # ── Segment Advancement ────────────────────────────────────────────

    def advance_segment(self, sid: str, end_time: float) -> None:
        """Move the segment cursor forward after a segment closes."""
        session = self.active_sessions.get(sid)
        if not session:
            return

        session.segment_start_offset = len(session.audio_buffer)
        session.segment_start_time = end_time
        session.chunk_index += 1
        session.last_speech_time = time.time()


# Global singleton — imported by websocket events and workers
session_manager = StreamingSessionManager()