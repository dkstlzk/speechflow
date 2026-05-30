from typing import Dict, List, Optional

from pyannote.audio import Pipeline

from ...config.logging import get_logger
from ...config.settings import Settings

logger = get_logger("diarization")
_PIPELINE: Optional[Pipeline] = None


def _get_pipeline() -> Pipeline:
    global _PIPELINE
    if _PIPELINE is None:
        settings = Settings()
        if not settings.HF_TOKEN:
            raise RuntimeError("HF_TOKEN is required for pyannote diarization")

        _PIPELINE = Pipeline.from_pretrained(
            settings.DIARIZATION_MODEL,
            token=settings.HF_TOKEN,
        )
        try:
            _PIPELINE.to("cpu")
        except Exception:
            logger.info("pyannote pipeline device defaulted")
    return _PIPELINE


def diarize_audio(audio_path: str) -> List[Dict]:
    pipeline = _get_pipeline()
    diarization = pipeline(audio_path)

    segments: List[Dict] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            {
                "speaker": str(speaker),
                "start": float(turn.start),
                "end": float(turn.end),
            }
        )

    segments.sort(key=lambda item: (item["start"], item["end"], item["speaker"]))
    return segments
