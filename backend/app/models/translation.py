from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base


class SessionTranslation(Base):
    __tablename__ = "session_translations"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "target_language", name="uix_session_translation_language"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_language = Column(String(10), nullable=False)
    translated_transcript = Column(Text, nullable=True)
    translated_summary = Column(Text, nullable=True)
    translated_mom = Column(Text, nullable=True)
    status = Column(
        String(20), nullable=False, default="translating"
    )  # translating, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks = relationship(
        "TranslatedChunk",
        back_populates="translation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TranslatedChunk(Base):
    __tablename__ = "translated_chunks"
    __table_args__ = (
        UniqueConstraint("translation_id", "chunk_id", name="uix_translation_chunk"),
    )

    id = Column(Integer, primary_key=True, index=True)
    translation_id = Column(
        Integer,
        ForeignKey("session_translations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("transcript_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    translated_text = Column(Text, nullable=False)

    translation = relationship(
        "SessionTranslation",
        back_populates="chunks",
    )
    chunk = relationship("TranscriptChunk")
