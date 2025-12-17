#!/usr/bin/env python3
"""
Database initialization script for Render deployment.

This script is called during Render's build process to create
all database tables. Run this after the PostgreSQL database is created
but before starting the FastAPI application.

Usage:
    python init_db.py
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database import Base, engine
import models  # noqa: F401 - Import all models so Base.metadata knows about them


def init_database():
    """Create all database tables."""
    print("🔧 Initializing database...")
    print(f"📊 Database URL: {engine.url}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")

        # List created tables
        inspector = engine.dialect.get_inspector(engine.connect())
        tables = inspector.get_table_names()
        print(f"📋 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")

        return True
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
