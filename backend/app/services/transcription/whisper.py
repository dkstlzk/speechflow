from typing import Dict, Iterable, List

from .whisper_service import WhisperTranscriptionService


def transcribe_file(audio_path: str) -> List[Dict]:
    service = WhisperTranscriptionService()
    return service.transcribe(audio_path).segments


def transcribe_stream(chunks: Iterable[bytes]) -> List[Dict]:
    # TODO: run rolling Whisper inference on buffered audio chunks.
    return []
