#!/usr/bin/env python3
"""Apply missing indexes to posts table"""
from backend.database import engine
from sqlalchemy import text, inspect

def main():
    conn = engine.connect()

    # Check existing indexes
    inspector = inspect(engine)
    existing = {idx['name'] for idx in inspector.get_indexes('posts')}
    print(f"Existing indexes: {existing}")

    # Apply missing indexes
    missing_indexes = [
        ("ix_posts_project_status", "CREATE INDEX IF NOT EXISTS ix_posts_project_status ON posts(project_id, status)"),
        ("ix_posts_template_name", "CREATE INDEX IF NOT EXISTS ix_posts_template_name ON posts(template_name)")
    ]

    for idx_name, sql in missing_indexes:
        if idx_name not in existing:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Created {idx_name}")
            except Exception as e:
                print(f"[ERROR] Error creating {idx_name}: {e}")
        else:
            print(f"[EXISTS] {idx_name} already exists")

    conn.close()

    # Verify final state
    inspector = inspect(engine)
    final_indexes = inspector.get_indexes('posts')
    print(f"\nFinal indexes ({len(final_indexes)} total):")
    for idx in final_indexes:
        print(f"  - {idx['name']}: {idx['column_names']}")

if __name__ == "__main__":
    main()
