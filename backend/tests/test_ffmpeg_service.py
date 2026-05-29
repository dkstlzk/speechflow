import shutil
import wave
from pathlib import Path

import pytest

from backend.app.services.audio import AudioPreprocessorService


def _write_silence(path: Path, sample_rate: int = 8000, duration_seconds: int = 1) -> None:
    frames = sample_rate * duration_seconds
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frames)


def test_ffmpeg_preprocess(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")

    input_path = tmp_path / "input.wav"
    _write_silence(input_path)

    service = AudioPreprocessorService(str(tmp_path))
    output_path = Path(service.preprocess(str(input_path)))

    assert output_path.exists()
    assert output_path.suffix == ".wav"

    with wave.open(str(output_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
