from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    summary = Column(Text)
    mom = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("Session", backref="summaries")
