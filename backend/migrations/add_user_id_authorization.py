"""
Migration: Add user_id fields for authorization (TR-021)

This migration adds user_id foreign keys to Project and Client models
to enable IDOR prevention and resource ownership tracking.

IMPORTANT: Run this after deploying the authorization middleware.

Usage:
    python backend/migrations/add_user_id_authorization.py

Steps:
1. Adds user_id column to projects table
2. Adds user_id column to clients table
3. Creates foreign key constraints to users table
4. Creates indexes on user_id columns
5. Migrates existing data (sets user_id to first admin user)

Rollback:
    python backend/migrations/add_user_id_authorization.py --rollback
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from backend.database import SessionLocal
from backend.models import User
from backend.utils.logger import logger


def get_first_admin_user(db) -> str:
    """Get the first admin user to assign as owner of existing resources."""
    user = db.query(User).filter(User.is_superuser).first()
    if not user:
        # Fallback to first user if no admin exists
        user = db.query(User).first()

    if not user:
        raise ValueError(
            "No users found in database. Please create at least one user before running migration."
        )

    return user.id


def apply_migration():
    """Apply the migration to add user_id fields."""
    db = SessionLocal()

    try:
        logger.info("Starting migration: add_user_id_authorization")

        # Get default user for existing records
        default_user_id = get_first_admin_user(db)
        logger.info(f"Using user {default_user_id} as owner for existing resources")

        # Check if columns already exist
        result = db.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='projects' AND column_name='user_id'
        """
            )
        )

        if result.fetchone():
            logger.warning("Migration already applied (user_id columns exist). Skipping.")
            return

        logger.info("Step 1: Adding user_id column to projects table...")
        db.execute(
            text(
                """
            ALTER TABLE projects
            ADD COLUMN user_id VARCHAR NOT NULL DEFAULT :default_user_id
        """
            ),
            {"default_user_id": default_user_id},
        )

        logger.info("Step 2: Adding user_id column to clients table...")
        db.execute(
            text(
                """
            ALTER TABLE clients
            ADD COLUMN user_id VARCHAR NOT NULL DEFAULT :default_user_id
        """
            ),
            {"default_user_id": default_user_id},
        )

        logger.info("Step 3: Creating foreign key constraint for projects...")
        db.execute(
            text(
                """
            ALTER TABLE projects
            ADD CONSTRAINT fk_projects_user_id
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
        """
            )
        )

        logger.info("Step 4: Creating foreign key constraint for clients...")
        db.execute(
            text(
                """
            ALTER TABLE clients
            ADD CONSTRAINT fk_clients_user_id
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
        """
            )
        )

        logger.info("Step 5: Creating index on projects.user_id...")
        db.execute(
            text(
                """
            CREATE INDEX ix_projects_user_id ON projects(user_id)
        """
            )
        )

        logger.info("Step 6: Creating index on clients.user_id...")
        db.execute(
            text(
                """
            CREATE INDEX ix_clients_user_id ON clients(user_id)
        """
            )
        )

        # Remove default constraint (allow explicit user_id going forward)
        logger.info("Step 7: Removing default constraints...")
        db.execute(
            text(
                """
            ALTER TABLE projects ALTER COLUMN user_id DROP DEFAULT
        """
            )
        )
        db.execute(
            text(
                """
            ALTER TABLE clients ALTER COLUMN user_id DROP DEFAULT
        """
            )
        )

        db.commit()
        logger.info("Migration completed successfully!")
        logger.info("Authorization middleware is now active. All resources are owned by users.")

    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


def rollback_migration():
    """Rollback the migration (remove user_id fields)."""
    db = SessionLocal()

    try:
        logger.info("Starting rollback: add_user_id_authorization")

        # Check if columns exist
        result = db.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='projects' AND column_name='user_id'
        """
            )
        )

        if not result.fetchone():
            logger.warning(
                "Migration not applied (user_id columns don't exist). Nothing to rollback."
            )
            return

        logger.info("Step 1: Dropping foreign key constraint on projects...")
        db.execute(
            text(
                """
            ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_user_id
        """
            )
        )

        logger.info("Step 2: Dropping foreign key constraint on clients...")
        db.execute(
            text(
                """
            ALTER TABLE clients DROP CONSTRAINT IF EXISTS fk_clients_user_id
        """
            )
        )

        logger.info("Step 3: Dropping index on projects.user_id...")
        db.execute(
            text(
                """
            DROP INDEX IF EXISTS ix_projects_user_id
        """
            )
        )

        logger.info("Step 4: Dropping index on clients.user_id...")
        db.execute(
            text(
                """
            DROP INDEX IF EXISTS ix_clients_user_id
        """
            )
        )

        logger.info("Step 5: Dropping user_id column from projects...")
        db.execute(
            text(
                """
            ALTER TABLE projects DROP COLUMN IF EXISTS user_id
        """
            )
        )

        logger.info("Step 6: Dropping user_id column from clients...")
        db.execute(
            text(
                """
            ALTER TABLE clients DROP COLUMN IF EXISTS user_id
        """
            )
        )

        db.commit()
        logger.info("Rollback completed successfully!")
        logger.warning("Authorization middleware is now INACTIVE. IDOR vulnerability present.")

    except Exception as e:
        db.rollback()
        logger.error(f"Rollback failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add user_id authorization fields")
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback the migration (remove user_id fields)"
    )

    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        apply_migration()
