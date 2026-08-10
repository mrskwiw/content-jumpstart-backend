"""Communication model for client interactions"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Communication(Base):
    """Client communication record (emails, calls, notes)"""

    __tablename__ = "communications"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Who logged it
    type = Column(String, nullable=False)  # email, call, meeting, note
    subject = Column(String, nullable=False)
    content = Column(Text)  # Email body, call notes, etc.
    direction = Column(String)  # inbound, outbound
    duration = Column(String)  # For calls: "15 minutes"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="communications")
    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "type": self.type,
            "subject": self.subject,
            "content": self.content,
            "direction": self.direction,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
