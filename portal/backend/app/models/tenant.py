"""Tenant model for white-label multi-tenancy."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Tenant(Base):
    """
    Tenant model for white-label agency support.

    Attributes:
        tenant_id: Unique tenant identifier
        tenant_name: Agency/organization name
        subdomain: Subdomain for portal access (agency.yourplatform.com)
        custom_domain: Optional custom domain (agency.com)
        logo_url: URL to agency logo
        primary_color: Brand primary color (hex)
        secondary_color: Brand secondary color (hex)
        company_name: Display company name
        plan_tier: Subscription tier (standard, white_label)
        monthly_fee: Recurring monthly fee
        is_active: Tenant account status
        created_at: Tenant creation timestamp
    """

    __tablename__ = "tenants"

    tenant_id = Column(String, primary_key=True, default=generate_uuid)
    tenant_name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=True)
    custom_domain = Column(String, nullable=True)

    # Branding
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, default="#3B82F6")
    secondary_color = Column(String, default="#1E40AF")
    company_name = Column(String, nullable=True)

    # Billing
    plan_tier = Column(String, default="standard")  # standard, white_label
    monthly_fee = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant")

    def __repr__(self):
        return f"<Tenant(tenant_id={self.tenant_id}, name={self.tenant_name}, subdomain={self.subdomain})>"
