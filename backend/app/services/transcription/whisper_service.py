"""Whisper transcription service.

Defines interfaces for file-based and streaming transcription.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Union

import numpy as np
from faster_whisper import WhisperModel

from ...config.logging import get_logger
from ...config.settings import settings

logger = get_logger("transcription")


@dataclass
class TranscriptionResult:
    text: str
    segments: List[Dict]
    language: Optional[str] = None
    language_probability: Optional[float] = None


class WhisperTranscriptionService:
    """CPU-only Whisper transcription service."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        model: Optional[WhisperModel] = None,
    ) -> None:

        self.model_name = model_name or settings.WHISPER_MODEL
        self.device = device or settings.WHISPER_DEVICE
        self.compute_type = compute_type or settings.WHISPER_COMPUTE_TYPE
        self._model = model
        
        import threading
        self._lock = threading.Lock()

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info(
                        "Loading Whisper model",
                        extra={
                            "model": self.model_name,
                            "device": self.device,
                            "compute_type": self.compute_type,
                        },
                    )
                    self._model = WhisperModel(
                        self.model_name, device=self.device, compute_type=self.compute_type, cpu_threads=2
                    )
        return self._model

    def transcribe(self, audio: Union[str, np.ndarray], language: Optional[str] = None, fast_mode: bool = False) -> TranscriptionResult:
        model = self._get_model()
        
        ALLOWED_LANGUAGES = {"en", "hi", "mr", "gu", "ta", "te", "or", "nl", "ru", "es"}
        
        best_lang = language
        best_prob = 0.0
        
        if not best_lang and not fast_mode:
            # Perform custom language detection to restrict the pool of allowed languages
            try:
                detected_lang, detected_prob, all_probs = model.detect_language(
                    audio=audio, vad_filter=True
                )
                
                # Filter the probability list to only our allowed languages
                filtered_probs = [
                    (lang, prob) for lang, prob in all_probs if lang in ALLOWED_LANGUAGES
                ]
                
                # Pick the allowed language with the highest probability, fallback to English
                if filtered_probs:
                    filtered_probs.sort(key=lambda x: x[1], reverse=True)
                    best_lang = filtered_probs[0][0]
                    best_prob = filtered_probs[0][1]
                else:
                    best_lang = "en"
                    best_prob = 0.0
                    
                logger.debug(f"[WhisperService] Language restricted detection: Raw={detected_lang}({detected_prob:.2f}), Best Allowed={best_lang}({best_prob:.2f})")
                
            except Exception as e:
                logger.warning(f"[WhisperService] Failed language detection pass: {e}")
                best_lang = "en"
                best_prob = 0.0

        if not best_lang:
            # Absolute safety fallback to prevent unconstrained language detection
            best_lang = "en"

        # Run transcription with the restricted language forced
        segments, info = model.transcribe(
            audio,
            language=best_lang,
            condition_on_previous_text=False,
            vad_filter=True,
            beam_size=1,
            hallucination_silence_threshold=1,
            without_timestamps=fast_mode,
        )

        ordered_segments: List[Dict] = []
        for index, segment in enumerate(segments):
            ordered_segments.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text.strip(),
                    "order": index,
                }
            )

        full_text = " ".join(item["text"] for item in ordered_segments).strip()

        if best_lang:
            logger.info(
                "Language detected",
                extra={"language": best_lang, "probability": f"{best_prob:.2f}"},
            )

        return TranscriptionResult(
            text=full_text,
            segments=ordered_segments,
            language=best_lang,
            language_probability=round(best_prob, 3),
        )


def transcribe_audio_file(audio_path: str) -> List[Dict]:
    """Return Whisper segments for a normalized audio file."""
    service = WhisperTranscriptionService()
    return service.transcribe(audio_path).segments
