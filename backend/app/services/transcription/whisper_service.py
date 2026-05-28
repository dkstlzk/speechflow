"""Whisper transcription service.

Defines interfaces for file-based and streaming transcription.
"""

from typing import Dict, Iterable, List

from .whisper import transcribe_file, transcribe_stream


def transcribe_audio_file(audio_path: str) -> List[Dict]:
    """Return Whisper segments for a normalized audio file."""
    # TODO: wire model loading, batching, and error handling.
    return transcribe_file(audio_path)


def transcribe_stream_window(chunks: Iterable[bytes]) -> List[Dict]:
    """Return partial segments from a rolling audio window."""
    # TODO: support streaming chunk stabilization.
    return transcribe_stream(chunks)
