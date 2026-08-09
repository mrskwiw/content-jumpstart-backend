"""
Privacy API Router - GDPR/CCPA Compliance Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services import data_privacy_service
from backend.middleware.auth_dependency import get_current_user, require_superuser
from backend.models import Client

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


def _require_client_access(client_id: str, db: Session, current_user) -> None:
    """
    Authorize a privacy operation on a client.

    Loads the client (including soft-deleted rows, so restore works) and raises:
      - 404 if it does not exist
      - 403 if the caller is neither a superuser nor the client's owner

    Prevents IDOR: without this any authenticated operator could
    export/delete/anonymize/restore another user's client by id.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    if not current_user.is_superuser and client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this client")


@router.get("/instance/export")
def export_instance(
    db: Session = Depends(get_db),
    current_user=Depends(require_superuser),
):
    """
    Export the entire instance database as a single JSON bundle (migration).

    Superuser-only. Secret columns (password hashes, MFA secrets, encrypted
    setting values) are redacted. Intended for a customer migrating elsewhere.

    NOT the same as ``GET /account/export`` below, which is one user's GDPR
    subject-access export. Neither is `export_service.py` (DOCX/PDF deliverables).
    See project/CLAUDE.md → "Export means three unrelated things".

    ⚠ Serialises the whole DB into one response; needs streaming before instances
    get large.
    """
    return data_privacy_service.export_full_instance(db)


@router.get("/account/export")
def export_my_account(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export all data associated with the authenticated user's own account
    (GDPR Article 15 / CCPA Right to Know). Secrets are redacted.

    Wider than it sounds: includes the full content tree the user created
    (clients, projects, posts, briefs, runs, deliverables), not just their user
    row. Narrower than ``GET /instance/export`` above, which is the whole-instance
    migration bundle and is superuser-only.
    """
    return data_privacy_service.export_user_data(current_user.id, db)


@router.delete("/account")
def delete_my_account(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Soft-delete and deactivate the authenticated user's own account
    (GDPR Article 17 / CCPA Right to Deletion). Revokes all of the user's
    sessions. Does not delete the clients/projects they created (those belong to
    the instance). Refuses to delete the last active administrator.
    """
    try:
        return data_privacy_service.delete_user_account(current_user.id, db)
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/restore")
def restore_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_superuser),
):
    """Restore a soft-deleted user account (superuser only)."""
    try:
        return data_privacy_service.restore_user_account(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/clients/{client_id}")
def delete_client(
    client_id: str,
    cascade: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_client_access(client_id, db, current_user)
    try:
        result = data_privacy_service.soft_delete_client(client_id, db, cascade)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/clients/{client_id}/anonymize")
def anonymize_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_client_access(client_id, db, current_user)
    try:
        result = data_privacy_service.anonymize_client(client_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/clients/{client_id}/export")
def export_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_client_access(client_id, db, current_user)
    try:
        result = data_privacy_service.export_client_data(client_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/clients/{client_id}/restore")
def restore_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_client_access(client_id, db, current_user)
    try:
        result = data_privacy_service.restore_soft_deleted_client(client_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
