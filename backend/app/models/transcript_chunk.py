from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    speaker_id = Column(Integer, ForeignKey("speakers.id"))
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    is_partial = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("Session", backref="transcript_chunks")
    speaker = relationship("Speaker", backref="transcript_chunks")
