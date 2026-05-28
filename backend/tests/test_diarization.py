import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_HEAVY_TESTS"),
    reason="Set RUN_HEAVY_TESTS=1 to run model smoke tests.",
)


def test_diarization_smoke():
    token = os.getenv("HF_TOKEN")
    if not token:
        pytest.skip("Missing HF_TOKEN for pyannote")

    audio_path = Path("temp/meeting.wav")
    if not audio_path.exists():
        pytest.skip("Missing temp/meeting.wav")

    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=token,
    )

    diarization = pipeline(str(audio_path))
    assert diarization is not None