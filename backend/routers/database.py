"""
Database backup and restore endpoints.

Provides functionality to download and upload SQLite database files
for backup and restore operations.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, engine
from backend.middleware.auth_dependency import get_current_user
from backend.models.user import User
from backend.services.database_migrator import DatabaseMigrator
from backend.services.schema_inspector import get_schema_version
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


def _is_in_memory_db() -> bool:
    """Return True when the engine is backed by an in-memory SQLite database."""
    return str(engine.url) == "sqlite:///:memory:"


def get_database_path() -> Path:
    """
    Get the path to the file-based SQLite database.

    Returns:
        Path: Absolute path to the database file

    Raises:
        HTTPException: If database is not a file-based SQLite database
    """
    db_url = str(engine.url)

    if not db_url.startswith("sqlite:///"):
        raise HTTPException(
            status_code=400, detail="Backup/restore only supported for SQLite databases"
        )

    db_path = db_url.replace("sqlite:///", "")

    if db_path == ":memory:":
        raise HTTPException(
            status_code=400,
            detail="Use the in-memory backup path — call _backup_in_memory_db() instead",
        )

    abs_path = Path(db_path).resolve()
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"Database file not found at {abs_path}")

    return abs_path


def _backup_in_memory_db(backup_path: Path) -> None:
    """
    Dump the live in-memory SQLite database to a file using the sqlite3 backup API.

    SQLite's Connection.backup() performs a hot, consistent snapshot of the
    in-memory database into an on-disk file without interrupting active sessions.
    """
    raw_conn = engine.raw_connection()
    try:
        dest = sqlite3.connect(str(backup_path))
        try:
            raw_conn.backup(dest)
        finally:
            dest.close()
    finally:
        raw_conn.close()


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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"jumpstart_backup_{timestamp}.db"

    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / backup_filename

    if _is_in_memory_db():
        # Serialize the live in-memory database to a file via the sqlite3 backup API
        logger.info("Backing up in-memory SQLite database via sqlite3 backup API")
        _backup_in_memory_db(backup_path)
    else:
        # File-based SQLite: safe to copy the file directly
        db_path = get_database_path()
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
    Restore database from an uploaded SQLite backup file.

    **ADMIN ONLY**: Requires superuser privileges.

    Behaviour:
    - File-based SQLite: replaces the database file on disk (preferred).
    - In-memory SQLite (PostgreSQL unavailable at startup): loads the backup
      into the live in-memory engine via the sqlite3 backup API so the
      restored data is immediately available for the current session.

    ⚠️ **DESTRUCTIVE OPERATION**: All current data will be replaced.

    Args:
        file: Uploaded SQLite .db backup file
        admin: Authenticated admin user (verified by require_admin dependency)
        db: Database session (closed before restore)

    Returns:
        dict: Status message and restore details

    Raises:
        HTTPException 400: Invalid file
        HTTPException 403: Not an admin
        HTTPException 500: Restore failed
    """
    logger.warning(f"Admin {admin.email} attempting database restore from {file.filename}")

    if not file.filename or not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .db file")

    contents = await file.read()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write upload to a temp file so we can validate and read it with sqlite3
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    temp_path = backup_dir / f"temp_restore_{timestamp}.db"

    try:
        temp_path.write_bytes(contents)

        # Validate it is a readable SQLite database with at least one table
        validation_error = None
        check_conn = None
        try:
            check_conn = sqlite3.connect(str(temp_path))
            tables = check_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
            if not tables:
                validation_error = ValueError("Backup contains no tables")
        except Exception as e:
            validation_error = e
        finally:
            # Always close before doing anything else — Windows holds the lock otherwise
            if check_conn is not None:
                check_conn.close()
        if validation_error is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SQLite backup file: {validation_error}",
            )

        if _is_in_memory_db():
            # ── In-memory path ────────────────────────────────────────────────
            # Load the backup file into the live in-memory engine via sqlite3 backup API.
            # Do NOT call engine.dispose() here — in-memory SQLite has no file lock to
            # release, and dispose() invalidates connections held by other SQLAlchemy
            # sessions in this same request (e.g. the auth dependency), causing
            # "can't checkout a detached connection fairy" on every subsequent request.
            logger.info("Restoring backup into in-memory SQLite engine")

            src_conn = sqlite3.connect(str(temp_path))
            dest_fairy = engine.raw_connection()
            try:
                # engine.raw_connection() returns a _ConnectionFairy (SQLAlchemy proxy).
                # sqlite3.Connection.backup() requires a real sqlite3.Connection as
                # target — unwrap via driver_connection (SA 2.0) or connection (SA 1.4).
                actual_dest = (
                    getattr(dest_fairy, "driver_connection", None) or dest_fairy.connection
                )
                src_conn.backup(actual_dest)
                dest_fairy.commit()
            finally:
                src_conn.close()
                dest_fairy.close()

            return {
                "message": "Database restored into in-memory engine successfully. "
                "Data will persist for the lifetime of this server process.",
                "restored_from": file.filename,
                "target": "in-memory",
                "timestamp": timestamp,
                "warning": (
                    "User settings (API keys, web search provider) have been restored from "
                    "this backup. If those settings were configured after the backup was "
                    "created, please re-enter them in Settings → API Keys."
                ),
            }

        else:
            # ── File-based SQLite path ────────────────────────────────────────
            db_path = get_database_path()

            # Check schema versions to determine restore strategy
            backup_version = get_schema_version(temp_path)
            current_version = get_schema_version(db_path)

            logger.info(f"Backup version: {backup_version}, Current version: {current_version}")

            # Fast path: versions match, simple restore
            if backup_version == current_version:
                logger.info("Schema versions match, using fast restore path")
                pre_restore_backup = backup_dir / f"pre_restore_backup_{timestamp}.db"

                try:
                    # engine.dispose() releases the OS file lock so shutil.move can swap the file.
                    # Do NOT call db.close() here — let the get_db dependency lifecycle handle it;
                    # premature close leaves the session in an inconsistent state.
                    engine.dispose()
                    shutil.copy2(db_path, pre_restore_backup)
                    shutil.move(str(temp_path), str(db_path))

                    # Re-apply column migrations that track schema changes outside of
                    # PRAGMA user_version (e.g. qa_score). The backup may pre-date these
                    # columns even when schema versions match, so always run them after
                    # any restore to keep the live DB in sync with the ORM models.
                    from backend.migrations.add_run_qa_score import (
                        run_migration as migrate_qa_score,
                    )
                    from backend.migrations.add_deletion_audit_log import (
                        run as migrate_deletion_audit_log,
                    )

                    migrate_qa_score()
                    migrate_deletion_audit_log()

                    return {
                        "message": "Database restored successfully",
                        "backup_created": str(pre_restore_backup),
                        "restored_from": file.filename,
                        "target": str(db_path),
                        "timestamp": timestamp,
                        "migration_applied": False,
                        "backup_version": backup_version,
                        "current_version": current_version,
                        "warning": (
                            "User settings (API keys, web search provider) have been restored "
                            "from this backup. If those settings were configured after the "
                            "backup was created, please re-enter them in Settings → API Keys."
                        ),
                    }

                except Exception as e:
                    if pre_restore_backup.exists():
                        shutil.copy2(pre_restore_backup, db_path)
                    raise HTTPException(status_code=500, detail=f"Database restore failed: {e}")

            # Migration path: versions differ, intelligent restore with schema migration
            else:
                logger.info("Schema version mismatch, using intelligent migration path")

                # Dispose engine before migration (releases file locks)
                engine.dispose()

                # Create migrator
                migrator = DatabaseMigrator(temp_path, db_path)

                # Check if migration is possible
                can_migrate, reason = migrator.can_migrate()
                if not can_migrate:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot migrate database: {reason}. "
                        "Please use a backup with compatible schema version.",
                    )

                # Execute migration
                try:
                    result = migrator.migrate()

                    # Re-apply column migrations that may not be tracked by the migrator
                    from backend.migrations.add_run_qa_score import (
                        run_migration as migrate_qa_score,
                    )
                    from backend.migrations.add_deletion_audit_log import (
                        run as migrate_deletion_audit_log,
                    )

                    migrate_qa_score()
                    migrate_deletion_audit_log()

                    return {
                        "message": f"Database restored and migrated successfully from v{backup_version} to v{current_version}",
                        "restored_from": file.filename,
                        "target": str(db_path),
                        "timestamp": timestamp,
                        "migration_applied": True,
                        "backup_version": backup_version,
                        "current_version": current_version,
                        "changes": result.get("changes", []),
                        "rows_migrated": result.get("row_count", 0),
                        "migration_log": result.get("log", []),
                        "warning": (
                            "User settings (API keys, web search provider) have been restored "
                            "from this backup. If those settings were configured after the "
                            "backup was created, please re-enter them in Settings → API Keys."
                        ),
                    }

                except Exception as e:
                    logger.error(f"Migration failed: {e}")
                    raise HTTPException(status_code=500, detail=f"Database migration failed: {e}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database restore failed: {e}")
    finally:
        # Clean up temp file if it still exists (file-based path moves it away).
        # On Windows, sqlite3 may briefly hold a lock; ignore cleanup errors.
        try:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
        except OSError:
            pass


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
