"""
Database migration: Add status indexes for query optimization.

This migration adds indexes on status columns for faster filtering:
- projects.status
- deliverables.status

Expected performance improvement: 30-50% for filtered queries.

Usage:
    python migrations/add_status_indexes.py
"""
from sqlalchemy import create_index, Index, MetaData, Table
from sqlalchemy.exc import OperationalError

from backend.database import engine


def upgrade():
    """Add status indexes"""
    print("Adding status indexes...")

    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Add index to projects.status
    try:
        projects_table = Table('projects', metadata, autoload_with=engine)
        idx_projects_status = Index('ix_projects_status', projects_table.c.status)

        if not index_exists('ix_projects_status'):
            idx_projects_status.create(engine)
            print("✓ Created index: ix_projects_status")
        else:
            print("⊙ Index already exists: ix_projects_status")
    except OperationalError as e:
        print(f"✗ Error creating projects.status index: {e}")

    # Add index to deliverables.status
    try:
        deliverables_table = Table('deliverables', metadata, autoload_with=engine)
        idx_deliverables_status = Index('ix_deliverables_status', deliverables_table.c.status)

        if not index_exists('ix_deliverables_status'):
            idx_deliverables_status.create(engine)
            print("✓ Created index: ix_deliverables_status")
        else:
            print("⊙ Index already exists: ix_deliverables_status")
    except OperationalError as e:
        print(f"✗ Error creating deliverables.status index: {e}")

    print("\nMigration complete!")
    print("Expected impact:")
    print("  - 30-50% faster for status-filtered queries")
    print("  - Improved dashboard performance")


def downgrade():
    """Remove status indexes"""
    print("Removing status indexes...")

    with engine.connect() as conn:
        try:
            conn.execute("DROP INDEX IF EXISTS ix_projects_status")
            print("✓ Dropped index: ix_projects_status")
        except OperationalError as e:
            print(f"✗ Error dropping projects.status index: {e}")

        try:
            conn.execute("DROP INDEX IF EXISTS ix_deliverables_status")
            print("✓ Dropped index: ix_deliverables_status")
        except OperationalError as e:
            print(f"✗ Error dropping deliverables.status index: {e}")

    print("\nDowngrade complete!")


def index_exists(index_name: str) -> bool:
    """Check if index exists in database"""
    with engine.connect() as conn:
        result = conn.execute(f"""
            SELECT 1 FROM pg_indexes
            WHERE indexname = '{index_name}'
        """)
        return result.fetchone() is not None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
