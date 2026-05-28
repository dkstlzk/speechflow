"""Speaker diarization service."""

from typing import Dict, List

from .pyannote import diarize_audio


def run_diarization(audio_path: str) -> List[Dict]:
    """Return speaker segments for the audio file."""
    # TODO: handle diarization retries and fallback behavior.
    return diarize_audio(audio_path)
