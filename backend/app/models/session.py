from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from ..db.base import Base
from .enums import SessionStatus


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index(
            "idx_sessions_created_at",
            "created_at",
            postgresql_using="btree",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_type = Column(String(32), nullable=False)
    status = Column(
        SAEnum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.PENDING,
    )
    original_filename = Column(String(255))
    duration_seconds = Column(Float)
    processing_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime)
    transcript_type = Column(
        String(32),
        nullable=True,
    )
    title = Column(String(255), nullable=True)
    host_name = Column(String(255), nullable=True)
    participants = Column(Text, nullable=True)
    audio_path = Column(String(512), nullable=True)
    diarization_mode = Column(String(32), nullable=True)
    diarized_at = Column(DateTime, nullable=True)
    detected_language = Column(String(10), nullable=True)
    detected_languages = Column(JSON, nullable=True)
    sample_rate = Column(Integer, nullable=True)
