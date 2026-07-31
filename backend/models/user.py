"""
User model for authentication.
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.models.mixins import SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    """User account for operator authentication"""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Credit system fields
    credit_balance = Column(
        Integer, default=1000, nullable=False
    )  # 1000 free welcome credits for all new users
    total_credits_purchased = Column(Integer, default=0, nullable=False)
    total_credits_used = Column(Integer, default=0, nullable=False)

    # Enterprise custom pricing
    is_enterprise = Column(Boolean, default=False, nullable=False)
    custom_credit_rate = Column(Float, nullable=True)  # Custom $/credit rate (e.g., 1.50)
    enterprise_notes = Column(Text, nullable=True)  # Admin notes about enterprise agreement
    # MFA (Two-Factor Authentication) - TR-008
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String, nullable=True)  # TOTP secret (encrypted)
    mfa_backup_codes = Column(Text, nullable=True)  # JSON array of hashed backup codes
    mfa_enforced = Column(Boolean, default=False, nullable=False)  # Admin enforcement flag

    # Set when the user changes their password. Used to revoke pre-change sessions:
    # legacy tokens carrying no "pv" claim are rejected once this is set.
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # S-01.4f: the control plane seeds a claimed instance's admin with this True,
    # so the operator is forced to set their own password on first login. Cleared
    # on any password change/reset.
    must_change_password = Column(Boolean, default=False, nullable=False)

    # GAP-AUTH-02: email verification. `email_verified` flips True when the user
    # confirms their address via the verification link; `email_verified_at` records
    # when. Login is not gated on this unless settings.REQUIRE_EMAIL_VERIFICATION.
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
