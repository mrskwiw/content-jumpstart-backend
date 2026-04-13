"""
Migration: Add qa_score column to runs table.
Date: 2026-04-11

Adds:
  - qa_score (FLOAT, nullable) — composite QA quality score (0.0–1.0) computed by
    QAAgent after each generation run. NULL for runs created before this migration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from backend.database import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar() > 0


def run_migration() -> bool:
    print("Starting migration: add_run_qa_score")

    try:
        with engine.connect() as conn:
            if _column_exists(conn, "runs", "qa_score"):
                print("  Column 'qa_score' already exists — skipping.")
            else:
                conn.execute(text("ALTER TABLE runs ADD COLUMN qa_score FLOAT"))
                print("  Added column 'qa_score' (FLOAT) to runs.")
            conn.commit()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return False

    print("\nMigration add_run_qa_score completed successfully!")
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
