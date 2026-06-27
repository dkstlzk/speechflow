"""FFmpeg preprocessing service.

Responsible for converting uploads into normalized 16kHz mono WAV files.
"""

from pathlib import Path
from typing import Optional

from ...config.logging import get_logger
from ...utils.file_manager import cleanup_file, create_temp_path
from .ffmpeg import preprocess_to_wav

logger = get_logger("ffmpeg")


class AudioPreprocessorService:
    """Preprocess audio files using FFmpeg."""

    def __init__(self, temp_dir: str) -> None:
        self.temp_dir = temp_dir

    def preprocess(self, input_path: str) -> str:
        """Convert input audio into 16kHz mono WAV and return output path."""
        output_path = create_temp_path(self.temp_dir, f"{Path(input_path).stem}.wav")

        try:
            logger.info(
                "Starting FFmpeg preprocessing",
                extra={"input": input_path, "output": str(output_path)},
            )
            return preprocess_to_wav(input_path, str(output_path))
        except Exception as exc:
            cleanup_file(str(output_path))
            logger.exception("FFmpeg preprocessing failed", extra={"input": input_path})
            raise exc

    def cleanup(self, path: Optional[str]) -> None:
        if path:
            cleanup_file(path)


def normalize_audio(input_path: str, output_path: str) -> str:
    """Normalize audio to 16kHz mono WAV."""
    return preprocess_to_wav(input_path, output_path)
