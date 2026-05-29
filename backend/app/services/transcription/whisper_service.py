"""Whisper transcription service.

Defines interfaces for file-based and streaming transcription.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from faster_whisper import WhisperModel

from ...config.logging import get_logger
from ...config.settings import Settings

logger = get_logger("transcription")


@dataclass
class TranscriptionResult:
    text: str
    segments: List[Dict]


class WhisperTranscriptionService:
    """CPU-only Whisper transcription service."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        model: Optional[WhisperModel] = None,
    ) -> None:
        settings = Settings()
        self.model_name = model_name or settings.WHISPER_MODEL
        self.device = device or settings.WHISPER_DEVICE
        self.compute_type = compute_type or settings.WHISPER_COMPUTE_TYPE
        self._model = model

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            logger.info(
                "Loading Whisper model",
                extra={
                    "model": self.model_name,
                    "device": self.device,
                    "compute_type": self.compute_type,
                },
            )
            self._model = WhisperModel(
                self.model_name, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        model = self._get_model()
        segments, _info = model.transcribe(audio_path)

        ordered_segments: List[Dict] = []
        for index, segment in enumerate(segments):
            ordered_segments.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text.strip(),
                    "order": index,
                }
            )

        full_text = " ".join(item["text"] for item in ordered_segments).strip()
        return TranscriptionResult(text=full_text, segments=ordered_segments)


def transcribe_audio_file(audio_path: str) -> List[Dict]:
    """Return Whisper segments for a normalized audio file."""
    service = WhisperTranscriptionService()
    return service.transcribe(audio_path).segments


def transcribe_stream_window(chunks: Iterable[bytes]) -> List[Dict]:
    """Return partial segments from a rolling audio window."""
    # TODO: support streaming chunk stabilization.
    return []
