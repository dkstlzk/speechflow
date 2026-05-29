DEFAULT_ALLOWED_EXTENSIONS = {"wav", "mp3", "mp4", "m4a", "webm"}
DEFAULT_MAX_UPLOAD_MB = 200
DEFAULT_LOG_LEVEL = "INFO"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOGGER_NAMES = {
    "upload": "upload",
    "ffmpeg": "ffmpeg",
    "transcription": "transcription",
    "diarization": "diarization",
    "summarization": "summarization",
    "persistence": "persistence",
    "session": "session",
    "websocket": "websocket",
    "workers": "workers",
}
