import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://speechflow:speechflow@localhost:5432/speechflow",
    )
    SOCKETIO_ASYNC_MODE: str = os.getenv("SOCKETIO_ASYNC_MODE", "threading")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "temp")
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", "exports")
    TRANSCRIPTS_DIR: str = os.getenv("TRANSCRIPTS_DIR", "transcripts")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "ml_models")
