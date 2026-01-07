"""
Pydantic schemas for Client API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr


class ClientBase(BaseModel):
    """Base client schema"""

    name: str
    email: Optional[EmailStr] = None
    business_description: Optional[str] = None
    ideal_customer: Optional[str] = None
    main_problem_solved: Optional[str] = None
    tone_preference: Optional[str] = "professional"
    platforms: Optional[List[str]] = None
    customer_pain_points: Optional[List[str]] = None
    customer_questions: Optional[List[str]] = None


class ClientCreate(ClientBase):
    """
    Schema for creating a client.

    TR-022: Mass assignment protection
    - Only allows: name, email, business_description, ideal_customer, main_problem_solved,
                   tone_preference, platforms, customer_pain_points, customer_questions
    - Protected fields set by system: id, user_id, created_at
    """

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class ClientUpdate(BaseModel):
    """
    Schema for updating a client (all fields optional).

    TR-022: Mass assignment protection
    - Only allows: name, email, business_description, ideal_customer, main_problem_solved,
                   tone_preference, platforms, customer_pain_points, customer_questions
    - Protected fields (never updatable): id, user_id, created_at
    """

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    business_description: Optional[str] = None
    ideal_customer: Optional[str] = None
    main_problem_solved: Optional[str] = None
    tone_preference: Optional[str] = None
    platforms: Optional[List[str]] = None
    customer_pain_points: Optional[List[str]] = None
    customer_questions: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields like user_id


class ClientResponse(ClientBase):
    """
    Schema for client response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),  # Convert snake_case to camelCase
    )
