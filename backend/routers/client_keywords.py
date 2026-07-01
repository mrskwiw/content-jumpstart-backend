"""API router for client keyword management."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import verify_client_ownership
from backend.models.client import Client
from backend.models.client_keywords import ClientKeyword
from backend.models.user import User
from backend.schemas.keyword_schemas import (
    KeywordBulkUpsert,
    KeywordCreate,
    KeywordImportResponse,
    KeywordListResponse,
    KeywordResponse,
    KeywordUpdate,
)
from backend.services import crud_client_keywords as kw_crud
from backend.utils.logger import logger

router = APIRouter()


async def _owned_client(
    client: Client = Depends(verify_client_ownership),
    current_user: User = Depends(get_current_user),
) -> Client:
    """Strict ownership dependency for keyword endpoints.

    verify_client_ownership is gated by ENFORCE_RESOURCE_OWNERSHIP (default False),
    which means it passes for every authenticated user in the default runtime.
    This dependency always enforces per-user ownership, independent of that flag,
    because keyword endpoints are customer-facing and require hard per-user isolation.

    Superusers are granted access regardless of client ownership.
    """
    owner_id = str(client.user_id) if hasattr(client, "user_id") else None
    requester_id = str(current_user.id)
    is_superuser = getattr(current_user, "is_superuser", False)

    if not is_superuser and owner_id != requester_id:
        logger.warning(
            f"Keyword access denied: user {requester_id} attempted access to "
            f"client {str(client.id)} owned by {owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return client


def _to_response(kw: ClientKeyword) -> KeywordResponse:
    return KeywordResponse.model_validate(kw)


@router.get("/{client_id}/keywords", response_model=KeywordListResponse)
async def list_keywords(
    type: Optional[str] = Query(None, description="Filter by keyword_type"),
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Return all active keywords for a client, grouped by type."""
    rows = kw_crud.get_keywords_for_client(db, str(client.id), keyword_type=type)
    grouped: dict = {"primary": [], "secondary": [], "negative": [], "quick_win": []}
    for kw in rows:
        bucket = grouped.get(kw.keyword_type)
        if bucket is not None:
            bucket.append(_to_response(kw))
    total = sum(len(v) for v in grouped.values())
    return KeywordListResponse(**grouped, total=total)


@router.post(
    "/{client_id}/keywords",
    response_model=KeywordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_keyword(
    body: KeywordCreate,
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Add a single keyword to a client's keyword list."""
    try:
        kw = kw_crud.create_keyword(db, str(client.id), body, source="manual")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if kw is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Keyword already exists for this client and type.",
        )
    logger.info(
        f"Keyword added: client={str(client.id)} type={body.keyword_type} kw={body.keyword!r}"
    )
    return _to_response(kw)


@router.put("/{client_id}/keywords/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    body: KeywordUpdate,
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Update an existing keyword."""
    try:
        kw = kw_crud.update_keyword(db, keyword_id, str(client.id), body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not kw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return _to_response(kw)


@router.delete("/{client_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: int,
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Soft-delete a keyword (sets is_active=False)."""
    deleted = kw_crud.soft_delete_keyword(db, keyword_id, str(client.id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")


@router.post("/{client_id}/keywords/bulk", response_model=KeywordImportResponse)
async def bulk_upsert_keywords(
    body: KeywordBulkUpsert,
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Bulk-upsert keywords. Merges with existing — does not delete."""
    result = kw_crud.bulk_upsert_keywords(db, str(client.id), body.keywords, source="manual")
    return KeywordImportResponse(
        imported=result["imported"],
        skipped=result["skipped"],
        message=f"Done: {result['imported']} added, {result['skipped']} already existed.",
    )


@router.post("/{client_id}/keywords/import/{result_id}", response_model=KeywordImportResponse)
async def import_from_research(
    result_id: str,
    client: Client = Depends(_owned_client),
    db: Session = Depends(get_db),
):
    """Seed keyword list from an existing SEO research result."""
    from backend.models import ResearchResult

    rr = (
        db.query(ResearchResult)
        .filter(
            ResearchResult.id == result_id,
            ResearchResult.client_id == str(client.id),
            ResearchResult.tool_name == "seo_keyword_research",
        )
        .first()
    )
    if not rr or not rr.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SEO research result not found for this client.",
        )

    result_data: dict = dict(rr.data) if isinstance(rr.data, dict) else {}
    result = kw_crud.seed_from_research_result(db, str(client.id), result_id, result_data)
    deactivated = result.get("deactivated", 0)
    return KeywordImportResponse(
        imported=result["imported"],
        skipped=result["skipped"],
        deactivated=deactivated,
        message=(
            f"Imported {result['imported']} keywords from research result"
            + (f", deactivated {deactivated} stale." if deactivated else ".")
        ),
    )
