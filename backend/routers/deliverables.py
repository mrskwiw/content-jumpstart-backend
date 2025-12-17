"""Deliverables router"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from middleware.auth_dependency import get_current_user
from schemas.deliverable import DeliverableResponse, MarkDeliveredRequest
from services import crud
from sqlalchemy.orm import Session

from database import get_db
from models import User

router = APIRouter()


@router.get("/", response_model=List[DeliverableResponse])
async def list_deliverables(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List deliverables with optional filters"""
    return crud.get_deliverables(db, skip=skip, limit=limit, status=status, client_id=client_id)


@router.get("/{deliverable_id}", response_model=DeliverableResponse)
async def get_deliverable(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get deliverable by ID"""
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return deliverable


@router.patch("/{deliverable_id}/mark-delivered", response_model=DeliverableResponse)
async def mark_delivered(
    deliverable_id: str,
    request: MarkDeliveredRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark deliverable as delivered"""
    deliverable = crud.mark_deliverable_delivered(
        db, deliverable_id, request.delivered_at, request.proof_url, request.proof_notes
    )
    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return deliverable
