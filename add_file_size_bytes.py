#!/usr/bin/env python
"""Add file_size_bytes column to deliverables table"""
import sys
sys.path.insert(0, 'backend')

from database import engine, SessionLocal
from sqlalchemy import text

def add_column():
    """Add file_size_bytes column to deliverables table if it doesn't exist"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(deliverables)"))
        columns = [row[1] for row in result]

        if 'file_size_bytes' in columns:
            print("✓ Column 'file_size_bytes' already exists")
            return

        print("Adding 'file_size_bytes' column to deliverables table...")

        # Add the column
        conn.execute(text("ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER"))
        conn.commit()

        print("✓ Column added successfully")

        # Verify
        result = conn.execute(text("PRAGMA table_info(deliverables)"))
        columns = [row[1] for row in result]
        print(f"Deliverables table now has columns: {columns}")

if __name__ == '__main__':
    add_column()
