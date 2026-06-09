from ...config.logging import get_logger
from ...services.transcription.whisper_service import WhisperTranscriptionService

logger = get_logger(__name__)

transcriber = WhisperTranscriptionService()

try:
    from silero_vad import load_silero_vad
    vad_model = load_silero_vad(onnx=True)
    logger.info("[VAD] Silero VAD loaded successfully (ONNX CPU Mode).")
except Exception as e:
    logger.error(f"[VAD] Error loading Silero VAD. Running without VAD. Error: {e}")
    vad_model = None
