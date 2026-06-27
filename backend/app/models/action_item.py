from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iteration = Column(Integer, default=1, nullable=False, server_default="1")
    text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="open")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship(
        "Session",
        backref=backref(
            "action_items", cascade="all, delete-orphan", passive_deletes=True
        ),
    )
