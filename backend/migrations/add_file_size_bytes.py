"""
Migration: Add file_size_bytes column and calculate sizes for existing deliverables
Date: 2025-12-19
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables before importing
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from database import get_db, engine
from models.deliverable import Deliverable
from sqlalchemy import text


def calculate_file_size(file_path: str) -> int:
    """Calculate actual file size in bytes"""
    try:
        # Base path is data/outputs/
        base_path = Path(__file__).parent.parent.parent / "data" / "outputs"
        full_path = base_path / file_path

        if full_path.exists():
            return full_path.stat().st_size
        else:
            print(f"Warning: File not found: {full_path}")
            return 0
    except Exception as e:
        print(f"Error calculating size for {file_path}: {e}")
        return 0


def run_migration():
    """Run the migration"""
    print("Starting migration: Add file_size_bytes column")

    # Step 1: Add column to database
    print("Step 1: Adding file_size_bytes column...")
    try:
        with engine.connect() as conn:
            # Check if column already exists (PostgreSQL syntax)
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name='deliverables' AND column_name='file_size_bytes'
            """))
            column_exists = result.scalar() > 0

            if not column_exists:
                conn.execute(text("ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER"))
                conn.commit()
                print("Column added successfully")
            else:
                print("Column already exists, skipping")

    except Exception as e:
        print(f"Error adding column: {e}")
        return False

    # Step 2: Calculate file sizes for existing deliverables
    print("\nStep 2: Calculating file sizes for existing deliverables...")
    try:
        db = next(get_db())
        deliverables = db.query(Deliverable).all()

        updated_count = 0
        for deliverable in deliverables:
            if deliverable.file_size_bytes is None:
                file_size = calculate_file_size(deliverable.path)
                deliverable.file_size_bytes = file_size
                updated_count += 1

                if updated_count % 10 == 0:
                    print(f"  Processed {updated_count} deliverables...")

        db.commit()
        print(f"Updated {updated_count} deliverables with file sizes")

    except Exception as e:
        print(f"Error calculating file sizes: {e}")
        db.rollback()
        return False
    finally:
        db.close()

    # Step 3: Add index for performance
    print("\nStep 3: Adding index on file_size_bytes...")
    try:
        with engine.connect() as conn:
            # Check if index already exists (PostgreSQL syntax)
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE indexname='idx_deliverables_file_size'
            """))
            index_exists = result.scalar() > 0

            if not index_exists:
                conn.execute(text("CREATE INDEX idx_deliverables_file_size ON deliverables(file_size_bytes)"))
                conn.commit()
                print("Index created successfully")
            else:
                print("Index already exists, skipping")

    except Exception as e:
        print(f"Error creating index: {e}")
        return False

    print("\n" + "="*50)
    print("Migration completed successfully!")
    print("="*50)
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
