from ...config.logging import get_logger
from ...services.transcription.whisper_service import WhisperTranscriptionService
from concurrent.futures import ThreadPoolExecutor

logger = get_logger(__name__)

transcriber = WhisperTranscriptionService()
inference_executor = ThreadPoolExecutor(max_workers=2)

try:
    from silero_vad import load_silero_vad
    vad_model = load_silero_vad(onnx=True)
    logger.info("[VAD] Silero VAD loaded successfully (ONNX CPU Mode).")
except Exception as e:
    logger.error(f"[VAD] Error loading Silero VAD. Running without VAD. Error: {e}")
    vad_model = None
