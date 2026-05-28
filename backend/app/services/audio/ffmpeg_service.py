"""FFmpeg preprocessing service.

Responsible for converting uploads into normalized 16kHz mono WAV files.
"""

from .ffmpeg import preprocess_to_wav


def normalize_audio(input_path: str, output_path: str) -> str:
    """Normalize audio to 16kHz mono WAV."""
    # TODO: validate input/output paths and handle FFmpeg failures.
    return preprocess_to_wav(input_path, output_path)
