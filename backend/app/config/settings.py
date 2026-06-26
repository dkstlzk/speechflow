import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_PATH)

from .constants import DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_MAX_UPLOAD_MB

@dataclass(frozen=True)
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    SOCKETIO_ASYNC_MODE: str = os.getenv("SOCKETIO_ASYNC_MODE", "threading")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    PROJECT_ROOT: str = str(Path(__file__).resolve().parents[3])
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(Path(PROJECT_ROOT) / "temp"))
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", str(Path(PROJECT_ROOT) / "exports"))
    MODEL_DIR: str = os.getenv("MODEL_DIR", str(Path(PROJECT_ROOT) / "ml_models"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", str(Path(PROJECT_ROOT) / "temp"))
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
    MAX_CONTENT_LENGTH: int = MAX_UPLOAD_MB * 1024 * 1024
    ALLOWED_EXTENSIONS: tuple = tuple(
        ext.strip()
        for ext in os.getenv(
            "ALLOWED_EXTENSIONS",
            ",".join(sorted(DEFAULT_ALLOWED_EXTENSIONS)),
        ).split(",")
        if ext.strip()
    )
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small.en")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    DIARIZATION_MODEL: str = os.getenv(
        "DIARIZATION_MODEL", "pyannote/speaker-diarization-community-1"
    )
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD")
    QUICK_DIARIZATION_THRESHOLD: float = float(os.getenv("QUICK_DIARIZATION_THRESHOLD", "0.3"))

    def __post_init__(self):
        if not self.SECRET_KEY:
            raise RuntimeError("SECRET_KEY environment variable must be set")
        if not self.DATABASE_URL:
            raise RuntimeError("DATABASE_URL environment variable is required")
        if not self.ADMIN_PASSWORD:
            raise RuntimeError("ADMIN_PASSWORD environment variable is required (set it in .env to enable the auth wall)")

settings = Settings()
