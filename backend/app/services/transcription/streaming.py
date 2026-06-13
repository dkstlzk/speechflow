import time
from dataclasses import dataclass, field
from typing import Dict, Optional, BinaryIO
import threading
from ...config.logging import get_logger
from ...models.enums import SessionStatus
from ...models.session import Session as SessionModel
from ...db.session import SessionLocal

logger = get_logger(__name__)

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
    last_activity_time: float = field(default_factory=time.time)  # wall clock
    has_speech: bool = False  # Track if current segment has had speech

    # Caption throttle
    last_caption_time: float = 0.0

    # Counters
    chunk_index: int = 0
    persisted_chunk_indices: set = field(default_factory=set)

    # Lifecycle
    is_ending: bool = False
    is_paused: bool = False
    pause_pending: bool = False

    # Persistence
    raw_audio_path: Optional[str] = None
    raw_file_handle: Optional[BinaryIO] = None

    lock: threading.Lock = field(default_factory=threading.Lock)
    finalized_event: threading.Event = field(default_factory=threading.Event)


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

        # Open raw file for canonical audio saving
        from ...config.settings import settings
        import os
        realtime_dir = os.path.abspath(os.path.join(settings.EXPORT_DIR, "audio"))
        os.makedirs(realtime_dir, exist_ok=True)
        session.raw_audio_path = os.path.join(realtime_dir, f"session_{session_id}.raw")
        session.raw_file_handle = open(session.raw_audio_path, "wb")
        logger.info(f"[Playback] Raw file created: {session.raw_audio_path}")

        logger.info(
            f"[SessionManager] Created Session | SID: {sid} "
            f"| DB Session ID: {session_id} | Rate: {sample_rate}Hz"
        )
        return session

    def destroy_session(self, sid: str) -> None:
        session = self.active_sessions.get(sid)
        if not session:
            logger.warning(f"[SessionManager] destroy_session called but sid={sid} not found")
            return

        try:
            if session.raw_file_handle:
                session.raw_file_handle.close()

            # Convert raw to wav and update DB
            if session.raw_audio_path:
                db = None
                recovery_db = None
                persisted_successfully = False
                try:
                    import wave
                    import os
                    logger.info("[Playback] Converting raw to wav")
                    wav_path = session.raw_audio_path.replace(".raw", ".wav")

                    with wave.open(wav_path, "wb") as f_wav:
                        f_wav.setnchannels(1)
                        f_wav.setsampwidth(2)
                        f_wav.setframerate(session.sample_rate)

                        with open(session.raw_audio_path, "rb") as f_raw:
                            while True:
                                chunk = f_raw.read(1024 * 1024) # 1MB chunks
                                if not chunk:
                                    break
                                f_wav.writeframes(chunk)

                    logger.info(f"[Playback] WAV created: {wav_path}")

                    # Calculate duration
                    wav_size = os.path.getsize(wav_path)
                    # 44 bytes header, 2 bytes per sample, sample_rate samples per second
                    duration = (wav_size - 44) / (2 * session.sample_rate)
                    logger.info(f"WAV duration: {duration:.2f} seconds")

                    # Safe Persistence
                    if os.path.exists(wav_path) and wav_size > 0:
                        db = SessionLocal()
                        try:
                            db_session = db.query(SessionModel).filter(SessionModel.id == int(session.session_id)).first()
                            if db_session:
                                db_session.audio_path = os.path.basename(wav_path)
                                db_session.status = SessionStatus.COMPLETED
                                db_session.duration_seconds = duration
                                db.commit()
                                persisted_successfully = True
                                logger.info(f"[Playback] audio_path, status, and duration updated for session {session.session_id}")

                                # SAFELY remove raw file only after successful DB commit
                                if os.path.exists(session.raw_audio_path):
                                    os.remove(session.raw_audio_path)
                        finally:
                            db.close()
                    else:
                        raise RuntimeError("WAV creation failed or size is 0 bytes")

                except Exception as e:
                    logger.error(f"[Playback] Error saving realtime audio: {e}")
                    import os
                    import time
                    if session.raw_audio_path and os.path.exists(session.raw_audio_path):
                        try:
                            orphan_path = session.raw_audio_path + f".orphan.{int(time.time())}"
                            os.rename(session.raw_audio_path, orphan_path)
                            logger.info(f"[Playback] Archived corrupted raw stream to {orphan_path}")
                        except Exception as rename_err:
                            logger.error(f"[Playback] Failed to archive raw stream: {rename_err}")
                    # Isolated recovery transaction
                    try:
                        if db is not None:
                            try:
                                db.rollback()
                            except Exception:
                                pass
                                
                        recovery_db = SessionLocal()
                        
                        db_session = (
                            recovery_db.query(SessionModel)
                            .filter(SessionModel.id == int(session.session_id))
                            .first()
                        )
                        
                        if db_session and not persisted_successfully:
                            db_session.status = SessionStatus.FAILED
                            recovery_db.commit()
                            logger.info(f"[Playback] Marked session {session.session_id} as FAILED after error")
                    except Exception as recovery_err:
                        if recovery_db is not None:
                            try:
                                recovery_db.rollback()
                            except Exception:
                                pass
                        logger.error(f"[Playback] Failed to mark session as FAILED: {recovery_err}")
                    finally:
                        if recovery_db is not None:
                            recovery_db.close()

            logger.info(
                f"[Playback] Session finalized | SID: {sid} "
                f"| Final Buffer Size: {len(session.audio_buffer)} bytes"
            )

        finally:
            popped_session = self.active_sessions.pop(sid, None)
            if popped_session:
                popped_session.finalized_event.set()
            else:
                logger.warning(f"[SessionManager] Could not set finalized_event, sid={sid} not found in active_sessions during pop")

    # ── Audio Ingestion ────────────────────────────────────────────────

    def append_audio(self, sid: str, chunk: bytes) -> None:
        session = self.active_sessions.get(sid)
        if session:
            with session.lock:
                session.last_activity_time = time.time()
                session.audio_buffer.extend(chunk)
                if session.raw_file_handle:
                    session.raw_file_handle.write(chunk)
        else:
            logger.warning(
                f"[SessionManager] WARNING: Audio chunk received "
                f"for untracked SID: {sid}"
            )

    def has_new_audio(self, sid: str, min_bytes: int) -> bool:
        """Check if enough new bytes arrived since last check."""
        session = self.active_sessions.get(sid)
        if not session:
            return False
        with session.lock:
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

    def advance_segment(self, sid: str, end_time: float, end_offset: int) -> None:
        """Move the segment cursor forward after a segment closes."""
        session = self.active_sessions.get(sid)
        if not session:
            return

        session.segment_start_offset = end_offset
        session.segment_start_time = end_time
        session.chunk_index += 1
        session.last_speech_time = time.time()
        session.has_speech = False


# Global singleton — imported by websocket events and workers
session_manager = StreamingSessionManager()