"""Speaker diarization service."""

from typing import Dict, List

from ...config.logging import get_logger
from .pyannote import diarize_audio

logger = get_logger("diarization")


class DiarizationService:
    """Run pyannote diarization on a WAV file."""

    def diarize(self, audio_path: str) -> List[Dict]:
        logger.info("Starting diarization", extra={"audio_path": audio_path})
        try:
            return diarize_audio(audio_path)
        except Exception:
            logger.exception("Diarization failed", extra={"audio_path": audio_path})
            raise


def run_diarization(audio_path: str) -> List[Dict]:
    """Return speaker segments for the audio file."""
    return DiarizationService().diarize(audio_path)
