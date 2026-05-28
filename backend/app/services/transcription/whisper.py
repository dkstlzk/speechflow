from typing import Dict, Iterable, List


def transcribe_file(audio_path: str) -> List[Dict]:
    # TODO: run faster-whisper on normalized WAV and return segments.
    return []


def transcribe_stream(chunks: Iterable[bytes]) -> List[Dict]:
    # TODO: run rolling Whisper inference on buffered audio chunks.
    return []
