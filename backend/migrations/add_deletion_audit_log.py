"""Migration: create deletion_audit_log table for GDPR/CCPA erasure audit trail.

Run once:
    cd project
    python backend/migrations/add_deletion_audit_log.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database import engine
from backend.models.deletion_audit_log import DeletionAuditLog
from sqlalchemy import inspect


def run():
    inspector = inspect(engine)
    if "deletion_audit_log" in inspector.get_table_names():
        print("deletion_audit_log table already exists — skipping.")
        return

    DeletionAuditLog.__table__.create(engine)
    print("deletion_audit_log table created.")


if __name__ == "__main__":
    run()
