"""Pydantic schemas for Stripe payment endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CheckoutSessionRequest(BaseModel):
    package_id: str
    success_url: str
    cancel_url: str
    project_id: Optional[str] = None
    # Refund/Terms consent — enforced server-side (a client-only checkbox is
    # bypassable). Must be True; the accepted version is persisted for audit.
    accepted_terms: bool = False
    consent_version: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class PaymentStatusResponse(BaseModel):
    session_id: str
    status: str  # pending | completed | failed | expired
    credits: Optional[int] = None
    project_id: Optional[str] = None


class PaymentHistoryItem(BaseModel):
    id: str
    session_id: str
    amount_usd: Optional[float] = None
    credits: Optional[int] = None
    status: str
    package_id: Optional[str] = None
    created_at: datetime


class BillingPortalRequest(BaseModel):
    return_url: str

    model_config = ConfigDict(extra="forbid")


class BillingPortalResponse(BaseModel):
    portal_url: str
