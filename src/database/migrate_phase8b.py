"""Phase 8B Database Migration Script

Migrates existing projects.db from Phase 8A schema to Phase 8B schema.
Adds client memory fields while preserving existing data.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def migrate_database(db_path: Path):
    """Migrate database to Phase 8B schema"""

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(client_history)")
        columns = {row[1] for row in cursor.fetchall()}

        if "last_updated" in columns:
            print("[OK] Database already migrated to Phase 8B")
            return

        print("Starting Phase 8B migration...")

        # ========================================
        # 1. Add new columns to client_history
        # ========================================
        print("  Adding new columns to client_history...")

        # Preference tracking
        cursor.execute(
            "ALTER TABLE client_history ADD COLUMN preferred_templates TEXT DEFAULT '[]'"
        )
        cursor.execute("ALTER TABLE client_history ADD COLUMN avoided_templates TEXT DEFAULT '[]'")
        cursor.execute("ALTER TABLE client_history ADD COLUMN voice_adjustments TEXT DEFAULT '{}'")
        cursor.execute(
            "ALTER TABLE client_history ADD COLUMN optimal_word_count_min INTEGER DEFAULT 150"
        )
        cursor.execute(
            "ALTER TABLE client_history ADD COLUMN optimal_word_count_max INTEGER DEFAULT 250"
        )
        cursor.execute(
            "ALTER TABLE client_history ADD COLUMN preferred_cta_types TEXT DEFAULT '[]'"
        )

        # Voice patterns
        cursor.execute("ALTER TABLE client_history ADD COLUMN voice_archetype TEXT")
        cursor.execute("ALTER TABLE client_history ADD COLUMN average_readability_score REAL")
        cursor.execute("ALTER TABLE client_history ADD COLUMN signature_phrases TEXT DEFAULT '[]'")

        # Quality profile
        cursor.execute("ALTER TABLE client_history ADD COLUMN custom_quality_profile_json TEXT")

        # Relationship
        cursor.execute(
            "ALTER TABLE client_history ADD COLUMN next_project_discount REAL DEFAULT 0.0"
        )
        cursor.execute("ALTER TABLE client_history ADD COLUMN last_updated TIMESTAMP")

        # Set last_updated for existing records
        cursor.execute(
            "UPDATE client_history SET last_updated = CURRENT_TIMESTAMP WHERE last_updated IS NULL"
        )

        print("  [OK] client_history columns added")

        # ========================================
        # 2. Add new columns to template_performance
        # ========================================
        print("  Adding new columns to template_performance...")

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='template_performance'"
        )
        if cursor.fetchone():
            cursor.execute(
                "ALTER TABLE template_performance ADD COLUMN average_quality_score REAL DEFAULT 0.0"
            )
            cursor.execute(
                "ALTER TABLE template_performance ADD COLUMN client_kept_count INTEGER DEFAULT 0"
            )
            print("  [OK] template_performance columns added")
        else:
            print("  [WARN] template_performance table doesn't exist yet (will be created)")

        # ========================================
        # 3. Create new tables
        # ========================================
        print("  Creating new tables...")

        # Client Feedback Themes
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client_feedback_themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                theme_type TEXT NOT NULL,
                feedback_phrase TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_name) REFERENCES client_history(client_name)
            )
        """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_themes_client ON client_feedback_themes(client_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_themes_type ON client_feedback_themes(theme_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_themes_client_type ON client_feedback_themes(client_name, theme_type)"
        )

        print("  [OK] client_feedback_themes table created")

        # Client Voice Samples
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client_voice_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                project_id TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                average_readability REAL,
                voice_archetype TEXT,
                dominant_tone TEXT,
                average_word_count INTEGER,
                question_usage_rate REAL,
                common_hooks TEXT,
                common_transitions TEXT,
                common_ctas TEXT,
                key_phrases TEXT,
                FOREIGN KEY (client_name) REFERENCES client_history(client_name),
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_voice_samples_client ON client_voice_samples(client_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_voice_samples_project ON client_voice_samples(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_voice_samples_date ON client_voice_samples(generated_at)"
        )

        print("  [OK] client_voice_samples table created")

        # ========================================
        # 4. Create new indexes
        # ========================================
        print("  Creating new indexes...")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_history_updated ON client_history(last_updated)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_template_perf_client_template ON template_performance(client_name, template_id)"
        )

        print("  [OK] Indexes created")

        # Commit all changes
        conn.commit()

        print("[OK] Migration completed successfully!")

        # Show summary
        cursor.execute("SELECT COUNT(*) FROM client_history")
        client_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]

        print("\nDatabase Summary:")
        print(f"  - Clients: {client_count}")
        print(f"  - Projects: {project_count}")
        print("  - Ready for Phase 8B features [OK]")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {str(e)}")
        raise

    finally:
        conn.close()


def main():
    """Run migration on default database"""
    db_path = Path.cwd() / "data" / "projects.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("No migration needed - database will be created with Phase 8B schema")
        return

    # Backup existing database
    backup_path = db_path.parent / f"projects_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"Creating backup: {backup_path}")

    import shutil

    shutil.copy2(db_path, backup_path)
    print("[OK] Backup created")

    # Run migration
    migrate_database(db_path)


if __name__ == "__main__":
    main()
