import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Dict, Optional

class RollingBuffer:
    def __init__(self, max_chunks: int = 30) -> None:
        self.max_chunks = max_chunks
        self._chunks: Deque[bytes] = deque(maxlen=max_chunks)

    def append(self, audio_chunk: bytes) -> None:
        self._chunks.append(audio_chunk)

    def get_window(self) -> List[bytes]:
        # TODO: convert buffered chunks into a contiguous window for inference.
        return list(self._chunks)

@dataclass
class StreamingSession:
    sid: str
    session_id: str
    sample_rate: int = 16000  # Dynamic sample rate tracking
    # bytearray is perfect for accumulating raw PCM data continuously
    audio_buffer: bytearray = field(default_factory=bytearray)
    transcript_buffer: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    # Track where the worker last left off
    processed_offset: int = 0
    last_emitted_text: str = ""

class StreamingSessionManager:
    def __init__(self) -> None:
        # Maps Socket.IO sid to the active StreamingSession
        self.active_sessions: Dict[str, StreamingSession] = {}

    def create_session(self, sid: str, session_id: str, sample_rate: int = 16000) -> StreamingSession:
        session = StreamingSession(sid=sid, session_id=session_id, sample_rate=sample_rate)
        self.active_sessions[sid] = session
        print(f"[SessionManager] Created Session | SID: {sid} | DB Session ID: {session_id} | Rate: {sample_rate}Hz")
        return session

    def append_audio(self, sid: str, chunk: bytes) -> None:
        session = self.active_sessions.get(sid)
        if session:
            session.audio_buffer.extend(chunk)
            # We are removing the print here so it doesn't spam the terminal,
            # allowing us to clearly see the worker extracting the bytes!
        else:
            print(f"[SessionManager] WARNING: Audio chunk received for untracked SID: {sid}")

    # Extract only new bytes and move the cursor
    def get_unprocessed_audio(self, sid: str) -> Optional[bytes]:
        session = self.active_sessions.get(sid)
        if not session:
            return None

        # Slice from the last offset to the end
        new_audio = session.audio_buffer[session.processed_offset:]
        
        # Update offset to the new end of the buffer
        session.processed_offset = len(session.audio_buffer)

        return bytes(new_audio)
        
    # Check if enough new bytes arrived, and move the cursor
    def has_new_audio(self, sid: str, min_bytes: int) -> bool:
        session = self.active_sessions.get(sid)
        if not session:
            return False
            
        unread_bytes = len(session.audio_buffer) - session.processed_offset
        if unread_bytes >= min_bytes:
            session.processed_offset = len(session.audio_buffer)
            return True
        return False

    # Grab the trailing acoustic context for Whisper
    def get_context_window(self, sid: str, window_seconds: float = 5.0) -> Optional[bytes]:
        session = self.active_sessions.get(sid)
        if not session:
            return None
            
        # Dynamically calculate window size based on this session's true sample rate
        # 1 sample = 2 bytes (Int16)
        bytes_per_sec = session.sample_rate * 2
        window_size = int(bytes_per_sec * window_seconds)
        
        return bytes(session.audio_buffer[-window_size:])

    def destroy_session(self, sid: str) -> None:
        if sid in self.active_sessions:
            session = self.active_sessions.pop(sid)
            print(f"[SessionManager] Destroyed Session | SID: {sid} | Final Buffer Size: {len(session.audio_buffer)} bytes")

# Global singleton to be imported by the websocket events
session_manager = StreamingSessionManager()