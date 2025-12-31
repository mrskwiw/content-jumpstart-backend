"""
User model for authentication.
"""
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from database import Base


class User(Base):
    """User account for operator authentication"""

    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.email}>"
