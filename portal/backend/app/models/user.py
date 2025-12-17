"""User model for authentication and authorization."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class User(Base):
    """
    User model representing client accounts.

    Attributes:
        user_id: Unique user identifier (UUID hex)
        tenant_id: Foreign key to tenant (for white-label multi-tenancy)
        email: Unique email address
        password_hash: Bcrypt hashed password
        full_name: User's full name
        company_name: Optional company name
        role: User role (client, admin, agency)
        is_active: Account status
        email_verified: Email verification status
        created_at: Account creation timestamp
        last_login: Last successful login timestamp
    """

    __tablename__ = "users"

    user_id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    role = Column(String, default="client")  # client, admin, agency
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    file_uploads = relationship("FileUpload", back_populates="user", cascade="all, delete-orphan")
    revisions = relationship("Revision", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email}, role={self.role})>"
