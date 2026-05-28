import os

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_HEAVY_TESTS"),
    reason="Set RUN_HEAVY_TESTS=1 to run model smoke tests.",
)


def test_pyannote_pipeline_loads():
    token = os.getenv("HF_TOKEN")
    if not token:
        pytest.skip("Missing HF_TOKEN for pyannote")

    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=token,
    )

    assert pipeline is not None