"""
Database backup and restore endpoints.

Provides functionality to download and upload SQLite database files
for backup and restore operations.
"""

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, engine
from backend.middleware.auth_dependency import get_current_user
from backend.models.user import User
from backend.utils.logger import logger

router = APIRouter(prefix="/database", tags=["database"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify user is an admin (superuser).

    Database operations (backup/restore) require admin privileges.

    Raises:
        HTTPException 403: User is not an admin

    Returns:
        User instance if admin
    """
    if not current_user.is_superuser:
        logger.warning(
            f"Admin access denied: User {current_user.email} "
            f"attempted database operation without superuser privileges"
        )
        raise HTTPException(
            status_code=403, detail="Admin privileges required for database operations"
        )
    return current_user


def get_database_path() -> Path:
    """
    Get the path to the SQLite database file.

    Returns:
        Path: Absolute path to the database file

    Raises:
        HTTPException: If database is not SQLite or path cannot be determined
    """
    db_url = str(engine.url)

    # Check if it's a SQLite database
    if not db_url.startswith("sqlite:///"):
        raise HTTPException(
            status_code=400, detail="Backup/restore only supported for SQLite databases"
        )

    # Extract file path from sqlite:///path/to/db.db
    db_path = db_url.replace("sqlite:///", "")

    # Convert to absolute path
    abs_path = Path(db_path).resolve()

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"Database file not found at {abs_path}")

    return abs_path


@router.get("/backup", response_class=FileResponse)
async def download_database_backup(
    admin: User = Depends(require_admin),
) -> FileResponse:
    """
    Download a backup of the SQLite database.

    **ADMIN ONLY**: Requires superuser privileges.

    Creates a timestamped copy of the database file and returns it for download.
    This endpoint downloads the ENTIRE database including all users' data.

    Args:
        admin: Authenticated admin user (verified by require_admin dependency)

    Returns:
        FileResponse: Database file download

    Raises:
        HTTPException 403: User is not an admin
        HTTPException: If database is not SQLite or file cannot be accessed
    """
    logger.info(f"Admin {admin.email} downloading database backup")
    db_path = get_database_path()

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"jumpstart_backup_{timestamp}.db"

    # Create temporary backup directory if it doesn't exist
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create backup copy
    backup_path = backup_dir / backup_filename
    shutil.copy2(db_path, backup_path)

    # Return file for download
    return FileResponse(
        path=str(backup_path),
        filename=backup_filename,
        media_type="application/x-sqlite3",
        headers={"Content-Disposition": f'attachment; filename="{backup_filename}"'},
    )


@router.post("/restore")
async def restore_database_from_backup(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Restore database from an uploaded backup file.

    **ADMIN ONLY**: Requires superuser privileges.

    ⚠️ **DESTRUCTIVE OPERATION**: This will replace the current database with the uploaded file.
    All current data will be lost.

    Args:
        file: Uploaded SQLite database file
        admin: Authenticated admin user (verified by require_admin dependency)
        db: Database session (will be closed before restore)

    Returns:
        dict: Status message and backup info

    Raises:
        HTTPException 403: User is not an admin
        HTTPException: If file is invalid or restore fails
    """
    logger.warning(f"Admin {admin.email} attempting database restore from {file.filename}")
    # Validate file is a SQLite database
    if not file.filename or not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .db file")

    db_path = get_database_path()

    # Create backup of current database before replacing
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_restore_backup = db_path.parent / f"pre_restore_backup_{timestamp}.db"

    try:
        # Close all database connections
        db.close()
        engine.dispose()

        # Backup current database
        shutil.copy2(db_path, pre_restore_backup)

        # Save uploaded file to temporary location
        temp_path = db_path.parent / f"temp_restore_{timestamp}.db"
        with open(temp_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)

        # Validate uploaded file is a valid SQLite database
        import sqlite3

        try:
            conn = sqlite3.connect(str(temp_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()

            if not tables:
                raise ValueError("Database file contains no tables")

        except Exception as e:
            # Clean up temp file
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid SQLite database file: {str(e)}")

        # Replace current database with uploaded file
        shutil.move(str(temp_path), str(db_path))

        return {
            "message": "Database restored successfully",
            "backup_created": str(pre_restore_backup),
            "restored_from": file.filename,
            "timestamp": timestamp,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Restore from backup if something went wrong
        if pre_restore_backup.exists():
            shutil.copy2(pre_restore_backup, db_path)

        raise HTTPException(status_code=500, detail=f"Database restore failed: {str(e)}")


@router.delete("/cleanup-backups")
async def cleanup_old_backups(
    days: int = 30,
    admin: User = Depends(require_admin),
) -> dict:
    """
    Delete backup files older than specified number of days.

    **ADMIN ONLY**: Requires superuser privileges.

    Args:
        days: Number of days to keep backups (default: 30)
        admin: Authenticated admin user (verified by require_admin dependency)

    Returns:
        dict: Number of backups deleted

    Raises:
        HTTPException 403: User is not an admin
    """
    logger.info(f"Admin {admin.email} cleaning up backups older than {days} days")
    backup_dir = Path("data/backups")

    if not backup_dir.exists():
        return {"deleted": 0, "message": "No backup directory found"}

    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    deleted_count = 0

    for backup_file in backup_dir.glob("*.db"):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            deleted_count += 1

    return {
        "deleted": deleted_count,
        "message": f"Deleted {deleted_count} backup(s) older than {days} days",
    }
