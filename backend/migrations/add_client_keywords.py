"""Migration: Add client_keywords table for editable per-client keyword lists.

Creates the client_keywords table so customers can view and edit all keyword types
(primary, secondary, negative, quick_win) that affect SEO research and generation runs.

Usage:
    python backend/migrations/add_client_keywords.py
    python backend/migrations/add_client_keywords.py --rollback
"""

import argparse
import sys
from pathlib import Path

# Put the project root (parent of `backend/`) on sys.path so `import backend.*`
# resolves when this script is run standalone: python backend/migrations/add_client_keywords.py
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database import engine  # noqa: E402  (after sys.path setup above)
from backend.utils.logger import logger  # noqa: E402


def upgrade():
    """Create the client_keywords table and its indexes.

    DDL is emitted from the SQLAlchemy model so it is dialect-correct on both
    SQLite (dev) and PostgreSQL (production) — the previous hand-written SQL used
    SQLite-only syntax (AUTOINCREMENT, DATETIME, boolean DEFAULT 1) that fails on
    Postgres. `checkfirst=True` makes this idempotent (CREATE ... IF NOT EXISTS),
    and `Table.create` also emits the indexes declared in the model's __table_args__.
    """
    # Import the whole package so the model registry (and FK targets) are populated.
    import backend.models  # noqa: F401
    from backend.models.client_keywords import ClientKeyword

    ClientKeyword.__table__.create(bind=engine, checkfirst=True)
    logger.info("Migration applied: client_keywords table created")


def rollback():
    """Drop the client_keywords table and its indexes (dialect-aware, idempotent)."""
    import backend.models  # noqa: F401
    from backend.models.client_keywords import ClientKeyword

    ClientKeyword.__table__.drop(bind=engine, checkfirst=True)
    logger.info("Rollback applied: client_keywords table dropped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add client_keywords table")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Drop the client_keywords table and indexes",
    )
    args = parser.parse_args()
    if args.rollback:
        rollback()
    else:
        upgrade()
