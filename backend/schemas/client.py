"""
Pydantic schemas for Client API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class ClientBase(BaseModel):
    """Base client schema"""

    name: str
    email: Optional[EmailStr] = None


class ClientCreate(ClientBase):
    """Schema for creating a client"""



class ClientResponse(ClientBase):
    """Schema for client response"""

    id: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )
