"""
Database administration endpoints.

Every deployed environment runs on PostgreSQL (Supabase), so the legacy
SQLite file backup/restore/merge operations no longer apply. These endpoints
now report connection status and return pg_dump / Supabase instructions
instead of streaming ``.db`` files, and the removed SQLite-only operations
return 501 Not Implemented. All operations require superuser privileges.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.database import engine
from backend.middleware.auth_dependency import get_current_user
from backend.models.user import User
from backend.services.schema_inspector import get_schema_version
from backend.utils.logger import logger

router = APIRouter(prefix="/database", tags=["database"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verify the caller is a superuser; database administration is admin-only.

    Raises:
        HTTPException 403: caller is not a superuser.
    """
    if not current_user.is_superuser:
        logger.warning(
            f"Admin access denied: User {current_user.email} "
            f"attempted database operation without superuser privileges"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for database operations",
        )
    return current_user


@router.get("/status")
async def database_status(admin: User = Depends(require_admin)) -> dict:
    """Report database connectivity, backend engine, host, and schema version."""
    url = engine.url
    return {
        "status": "connected",
        "engine": url.get_backend_name(),
        "database_host": url.host,
        "database_name": url.database,
        "schema_version": get_schema_version(engine),
    }


@router.get("/backup")
async def backup_instructions(admin: User = Depends(require_admin)) -> dict:
    """
    Return instructions for backing up the PostgreSQL database.

    SQLite file backups no longer apply; use ``pg_dump`` or Supabase's managed
    backups instead of downloading a ``.db`` file.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return {
        "message": (
            "This deployment runs on PostgreSQL. Create a backup with pg_dump or "
            "use Supabase's managed backups — the app no longer streams .db files."
        ),
        "options": {
            "pg_dump": (
                'pg_dump "$DATABASE_URL" --no-owner --no-privileges ' f"-f backup_{timestamp}.sql"
            ),
            "dashboard": (
                "Supabase Dashboard -> Database -> Backups: use scheduled backups "
                "or Point-in-Time Recovery to download a snapshot."
            ),
        },
    }


@router.post("/restore")
async def restore_not_available(admin: User = Depends(require_admin)) -> dict:
    """SQLite restore has been removed; restore PostgreSQL via pg_restore/Supabase."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "SQLite restore is not available on PostgreSQL. Restore with "
            "psql/pg_restore from a pg_dump file, or use the Supabase dashboard."
        ),
    )


@router.post("/merge")
async def merge_not_available(admin: User = Depends(require_admin)) -> dict:
    """SQLite merge has been removed; not supported on PostgreSQL."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "SQLite merge is not available on PostgreSQL. Merge database content "
            "with SQL/ETL against the target database instead."
        ),
    )


@router.delete("/cleanup-backups")
async def cleanup_backups_not_available(admin: User = Depends(require_admin)) -> dict:
    """Local SQLite backup files no longer exist; cleanup does not apply."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Local backup cleanup is not available on PostgreSQL. Backup retention "
            "is managed by Supabase."
        ),
    )
