import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_HEAVY_TESTS"),
    reason="Set RUN_HEAVY_TESTS=1 to run model smoke tests.",
)


def test_whisper_smoke():
    audio_path = Path("test_audio/meeting.mp4")
    if not audio_path.exists():
        pytest.skip("Missing test_audio/meeting.mp4")

    from faster_whisper import WhisperModel

    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio_path))

    assert segments is not None