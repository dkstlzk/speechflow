import os
from pathlib import Path

import pytest

from backend.app.services.diarization import DiarizationService


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_HEAVY_TESTS"),
    reason="Set RUN_HEAVY_TESTS=1 to run model smoke tests.",
)


def test_diarization_smoke():
    if not os.getenv("HF_TOKEN"):
        pytest.skip("Missing HF_TOKEN for pyannote")

    audio_path = Path("temp/meeting.wav")
    if not audio_path.exists():
        pytest.skip("Missing temp/meeting.wav")

    service = DiarizationService()
    segments = service.diarize(str(audio_path))
    assert segments is not None