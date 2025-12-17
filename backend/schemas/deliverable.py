"""
Pydantic schemas for Deliverable API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeliverableBase(BaseModel):
    """Base deliverable schema"""

    format: str  # txt, docx, pdf


class DeliverableResponse(DeliverableBase):
    """Schema for deliverable response"""

    id: str
    project_id: str
    client_id: str
    run_id: Optional[str] = None
    path: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    proof_url: Optional[str] = None
    proof_notes: Optional[str] = None
    checksum: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )


class MarkDeliveredRequest(BaseModel):
    """Schema for marking deliverable as delivered"""

    delivered_at: datetime
    proof_url: Optional[str] = None
    proof_notes: Optional[str] = None
