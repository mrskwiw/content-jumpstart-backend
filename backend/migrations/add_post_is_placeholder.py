"""
Migration: Add is_placeholder column to posts table.
Date: 2026-05-05

Adds:
  - is_placeholder (BOOLEAN, nullable, default 0) — True when the content
    generator exhausted all QA retries and stored an [ERROR:…] stub.
    Placeholder posts are excluded from exports and deliverables.
    NULL on pre-migration rows is treated as False (not a placeholder).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import inspect, text  # noqa: E402

from backend.database import engine  # noqa: E402


def run_migration() -> bool:
    print("Starting migration: add_post_is_placeholder")

    try:
        inspector = inspect(engine)
        existing_columns = [c["name"] for c in inspector.get_columns("posts")]

        if "is_placeholder" in existing_columns:
            print("  Column 'is_placeholder' already exists — skipping.")
        else:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE posts ADD COLUMN is_placeholder BOOLEAN DEFAULT 0"))
                conn.commit()
            print("  Added column 'is_placeholder' (BOOLEAN DEFAULT 0) to posts.")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return False

    print("Migration add_post_is_placeholder completed successfully!")
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
