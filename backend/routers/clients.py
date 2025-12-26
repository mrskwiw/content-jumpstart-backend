"""Clients router"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from middleware.auth_dependency import get_current_user
from schemas.client import ClientCreate, ClientUpdate, ClientResponse
from services import crud
from sqlalchemy.orm import Session

from database import get_db
from models import User

router = APIRouter()


@router.get("/", response_model=List[ClientResponse])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all clients"""
    return crud.get_clients(db, skip=skip, limit=limit)


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new client"""
    return crud.create_client(db, client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get client by ID"""
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update client"""
    client = crud.update_client(db, client_id, client_update)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client
