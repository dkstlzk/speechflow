import os

import pytest

from backend.app.config.settings import Settings


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_HEAVY_TESTS"),
    reason="Set RUN_HEAVY_TESTS=1 to run model smoke tests.",
)


def test_pyannote_pipeline_loads():
    token = os.getenv("HF_TOKEN")
    if not token:
        pytest.skip("Missing HF_TOKEN for pyannote")

    from pyannote.audio import Pipeline

    settings = Settings()
    pipeline = Pipeline.from_pretrained(
        settings.DIARIZATION_MODEL,
        token=token,
    )

    assert pipeline is not None