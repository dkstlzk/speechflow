from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
    )
    iteration = Column(Integer, default=1, nullable=False, server_default="1")
    summary = Column(Text)
    mom = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship(
        "Session",
        backref=backref(
            "summaries", cascade="all, delete-orphan", passive_deletes=True
        ),
    )
