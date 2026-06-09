from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, backref

from ..db.base import Base


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_label = Column(String(64), nullable=False)
    display_name = Column(String(255))

    session = relationship("Session", backref=backref("speakers", cascade="all, delete-orphan", passive_deletes=True))
