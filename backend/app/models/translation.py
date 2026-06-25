from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from ..db.base import Base

class SessionTranslation(Base):
    __tablename__ = "session_translations"
    __table_args__ = (
        UniqueConstraint('session_id', 'target_language', name='uix_session_translation_language'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_language = Column(String(10), nullable=False)
    translated_transcript = Column(Text, nullable=True)
    translated_summary = Column(Text, nullable=True)
    translated_mom = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="translating") # translating, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
