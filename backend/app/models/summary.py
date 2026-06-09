from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from ..db.base import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary = Column(Text)
    mom = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("Session", backref=backref("summaries", cascade="all, delete-orphan", passive_deletes=True))
