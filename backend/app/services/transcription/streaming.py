from collections import deque
from typing import Deque, List


class RollingBuffer:
    def __init__(self, max_chunks: int = 30) -> None:
        self.max_chunks = max_chunks
        self._chunks: Deque[bytes] = deque(maxlen=max_chunks)

    def append(self, audio_chunk: bytes) -> None:
        self._chunks.append(audio_chunk)

    def get_window(self) -> List[bytes]:
        # TODO: convert buffered chunks into a contiguous window for inference.
        return list(self._chunks)
