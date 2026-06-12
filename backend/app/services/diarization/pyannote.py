import time
import threading
from typing import Dict, List, Optional

from pyannote.audio import Pipeline

from ...config.logging import get_logger
from ...config.settings import settings

logger = get_logger("diarization")
_PIPELINE: Optional[Pipeline] = None
_PIPELINE_MODEL: Optional[str] = None
_PIPELINE_LOCK = threading.Lock()
_PIPELINE_FAILED = False

def _get_pipeline() -> Pipeline:
    global _PIPELINE, _PIPELINE_MODEL, _PIPELINE_FAILED
    if _PIPELINE_FAILED:
        raise RuntimeError("Diarization unavailable due to previous initialization failure")
        
    if _PIPELINE is None:
        with _PIPELINE_LOCK:
            if _PIPELINE_FAILED:
                raise RuntimeError("Diarization unavailable due to previous initialization failure")
            if _PIPELINE is None:
                try:
                    if not settings.HF_TOKEN:
                        raise RuntimeError("HF_TOKEN is required for pyannote diarization")

                    _PIPELINE_MODEL = settings.DIARIZATION_MODEL
                    _PIPELINE = Pipeline.from_pretrained(
                        settings.DIARIZATION_MODEL,
                        token=settings.HF_TOKEN,
                    )
                    try:
                        _PIPELINE.to("cpu")
                    except Exception:
                        logger.info("pyannote pipeline device defaulted")
                except Exception as e:
                    error_str = str(e)
                    if "HF_TOKEN" in error_str or "401" in error_str or "403" in error_str or "404" in error_str:
                        _PIPELINE_FAILED = True
                    raise RuntimeError("Diarization initialization failed") from e
    return _PIPELINE


def diarize_audio(audio_path: str) -> List[Dict]:
    pipeline = _get_pipeline()
    start_time = time.perf_counter()
    diarization = pipeline(audio_path)

    annotation = getattr(diarization, "speaker_diarization", diarization)

    segments: List[Dict] = []
    speaker_labels = set()

    for turn, _, speaker in annotation.itertracks(yield_label=True):
        speaker_label = str(speaker)
        speaker_labels.add(speaker_label)
        segments.append(
            {
                "speaker": speaker_label,
                "start": float(turn.start),
                "end": float(turn.end),
            }
        )

    segments.sort(
        key=lambda item: (item["start"], item["end"], item["speaker"])
    )

    duration_seconds = time.perf_counter() - start_time
    model_name = _PIPELINE_MODEL or settings.DIARIZATION_MODEL
    logger.info(
        "Diarization completed",
        extra={
            "model_name": model_name,
            "speaker_count": len(speaker_labels),
            "segment_count": len(segments),
            "duration_seconds": duration_seconds,
        },
    )

    return segments