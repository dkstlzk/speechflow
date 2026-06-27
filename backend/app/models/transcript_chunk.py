from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker_id = Column(Integer, ForeignKey("speakers.id", ondelete="SET NULL"))
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    is_partial = Column(Boolean, default=False)
    speaker_source = Column(String(20), default=None, server_default=None)
    language = Column(String(10), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship(
        "Session",
        backref=backref(
            "transcript_chunks", cascade="all, delete-orphan", passive_deletes=True
        ),
    )
    speaker = relationship("Speaker", backref="transcript_chunks")

    __table_args__ = (
        UniqueConstraint("session_id", "chunk_index", name="uix_session_chunk"),
    )
