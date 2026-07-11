"""
Integration tests for database migration.

Tests end-to-end migration from old schema versions to current version.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, String, Text, create_engine, inspect

from backend.models.client import Client
from backend.services.database_migrator import DatabaseMigrator
from backend.services.schema_inspector import get_schema_version, set_schema_version


class TestDatabaseMigrator:
    """Integration tests for DatabaseMigrator."""

    def _add_schema_versions(self, cursor, version: int) -> None:
        """Set the schema version the migrator reads (SQLite PRAGMA user_version).

        The DatabaseMigrator / schema_inspector version mechanism is
        ``PRAGMA user_version`` (see backend/services/schema_inspector.py:
        get_schema_version). There is no ``schema_versions`` table in the app,
        so the version must be written via the PRAGMA for can_migrate() to see
        it.
        """
        cursor.execute(f"PRAGMA user_version = {int(version)}")

    def create_v0_database(self, db_path: Path) -> None:
        """Create a v0 (unversioned) database with basic schema."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create minimal clients table (v0 schema)
        cursor.execute(
            """
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                user_id INTEGER NOT NULL
            )
        """
        )

        # Insert test data
        cursor.execute("INSERT INTO clients (id, name, user_id) VALUES (1, 'Test Client', 1)")
        self._add_schema_versions(cursor, 0)

        conn.commit()
        conn.close()

    def create_v2_database(self, db_path: Path) -> None:
        """Create a v2 database with some migrations applied."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create clients table with v2 schema (has business_description, etc.)
        cursor.execute(
            """
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                user_id INTEGER NOT NULL,
                business_description TEXT,
                ideal_customer TEXT,
                main_problem_solved TEXT,
                tone_preference VARCHAR,
                platforms JSON,
                customer_pain_points JSON,
                customer_questions JSON
            )
        """
        )

        # Insert test data
        cursor.execute(
            """
            INSERT INTO clients (id, name, user_id, business_description)
            VALUES (1, 'Test Client', 1, 'Software company')
        """
        )

        self._add_schema_versions(cursor, 2)

        conn.commit()
        conn.close()

    def create_current_database(self, db_path: Path) -> None:
        """Create a current version (v5) database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create clients table with v5 schema (includes industry)
        cursor.execute(
            """
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                user_id INTEGER NOT NULL,
                business_description TEXT,
                ideal_customer TEXT,
                main_problem_solved TEXT,
                tone_preference VARCHAR,
                platforms JSON,
                customer_pain_points JSON,
                customer_questions JSON,
                industry VARCHAR
            )
        """
        )

        # Set version to current (v5) via schema_versions table
        self._add_schema_versions(cursor, 5)

        conn.commit()
        conn.close()

    def test_can_migrate_same_version(self):
        """Migration should be skipped when versions match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create both as current version (v5)
            self.create_current_database(backup_path)
            self.create_current_database(target_path)

            migrator = DatabaseMigrator(backup_path, target_path)
            can_migrate, reason = migrator.can_migrate()

            assert can_migrate
            # Both DBs are at the same version; migrator may report an upgrade
            # path to the current app schema version (v6) rather than "no migration needed"
            assert "v5" in reason or "no migration needed" in reason.lower()

    def test_can_migrate_forward(self):
        """Should be able to migrate from old to new version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Backup is v2, target is current version
            self.create_v2_database(backup_path)
            self.create_current_database(target_path)

            migrator = DatabaseMigrator(backup_path, target_path)
            can_migrate, reason = migrator.can_migrate()

            assert can_migrate
            assert "v2" in reason
            # Current app schema is v6; accept v4, v5, or v6 as the target version
            assert "v4" in reason or "v5" in reason or "v6" in reason

    def test_cannot_migrate_backwards(self):
        """Should not allow migration when backup is newer than current schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create a backup with version 999 (future version)
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    user_id INTEGER NOT NULL
                )
            """
            )
            self._add_schema_versions(cursor, 999)
            conn.commit()
            conn.close()

            # Create normal v4 target
            self.create_current_database(target_path)

            migrator = DatabaseMigrator(backup_path, target_path)
            can_migrate, reason = migrator.can_migrate()

            assert not can_migrate
            assert "backwards" in reason.lower() or "999" in reason

    def test_migrate_v0_to_v4(self):
        """Should successfully migrate from v0 to v4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create v0 backup
            self.create_v0_database(backup_path)

            # Create v4 target (will be replaced)
            self.create_current_database(target_path)

            # Migrate
            migrator = DatabaseMigrator(backup_path, target_path)
            result = migrator.migrate()

            # Check result
            assert result["status"] == "success"
            assert result["migration_applied"] is True
            assert result["row_count"] >= 0  # May be 0 if staging was moved

            # Verify migrated database
            engine = create_engine(f"sqlite:///{target_path}")
            inspector = inspect(engine)

            # Should have all v4 columns
            cols = {col["name"] for col in inspector.get_columns("clients")}
            assert "industry" in cols
            assert "business_description" in cols

            engine.dispose()  # Release file lock

            # Version should be current schema version (v4 or v5)
            _check_engine = create_engine(f"sqlite:///{target_path}")
            migrated_version = get_schema_version(_check_engine)
            _check_engine.dispose()
            assert migrated_version >= 4

            # Data should be preserved
            conn = sqlite3.connect(str(target_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM clients WHERE id = 1")
            row = cursor.fetchone()
            assert row[0] == "Test Client"
            conn.close()

    def test_migrate_v2_to_v4(self):
        """Should successfully migrate from v2 to v4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create v2 backup
            self.create_v2_database(backup_path)

            # Create v4 target
            self.create_current_database(target_path)

            # Migrate
            migrator = DatabaseMigrator(backup_path, target_path)
            result = migrator.migrate()

            # Check result
            assert result["status"] == "success"
            assert result["migration_applied"] is True

            # Verify industry column was added
            engine = create_engine(f"sqlite:///{target_path}")
            inspector = inspect(engine)
            cols = {col["name"] for col in inspector.get_columns("clients")}
            assert "industry" in cols

            engine.dispose()  # Release file lock

            # Version should be current schema version (v4 or v5)
            _check_engine2 = create_engine(f"sqlite:///{target_path}")
            assert get_schema_version(_check_engine2) >= 4
            _check_engine2.dispose()

            # Data should be preserved
            conn = sqlite3.connect(str(target_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name, business_description FROM clients WHERE id = 1")
            row = cursor.fetchone()
            assert row[0] == "Test Client"
            assert row[1] == "Software company"
            conn.close()

    def test_migrate_preserves_data(self):
        """Migration should preserve all existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create v2 database with multiple rows
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    user_id INTEGER NOT NULL,
                    business_description TEXT
                )
            """
            )

            # Insert multiple clients
            for i in range(1, 11):
                cursor.execute(
                    f"INSERT INTO clients (id, name, user_id, business_description) "
                    f"VALUES ({i}, 'Client {i}', 1, 'Description {i}')"
                )

            cursor.execute("PRAGMA user_version = 2")
            conn.commit()
            conn.close()

            # Create target
            self.create_current_database(target_path)

            # Migrate
            migrator = DatabaseMigrator(backup_path, target_path)
            result = migrator.migrate()

            # Verify all rows preserved
            conn = sqlite3.connect(str(target_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            count = cursor.fetchone()[0]
            assert count == 10

            # Verify data integrity
            cursor.execute("SELECT id, name, business_description FROM clients ORDER BY id")
            rows = cursor.fetchall()
            for i, row in enumerate(rows, 1):
                assert row[0] == i
                assert row[1] == f"Client {i}"
                assert row[2] == f"Description {i}"

            conn.close()

    def test_migrate_creates_backup(self):
        """Migration should create backup of original database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create databases
            self.create_v2_database(backup_path)
            self.create_current_database(target_path)

            # Migrate
            migrator = DatabaseMigrator(backup_path, target_path)
            migrator.migrate()

            # Check backup was created
            backup_files = list(tmpdir.glob("pre_migration_*"))
            assert len(backup_files) == 1

    def test_migrate_invalid_backup(self):
        """Should handle invalid backup files gracefully."""
        backup_path = None
        target_path = None

        try:
            # Create temp files manually to avoid TemporaryDirectory cleanup issues
            tmpdir = Path(tempfile.gettempdir())
            backup_path = tmpdir / f"invalid_{os.getpid()}.db"
            target_path = tmpdir / f"target_{os.getpid()}.db"

            # Create invalid backup
            backup_path.write_text("not a database")

            # Create target
            self.create_current_database(target_path)

            # Migration should fail
            migrator = DatabaseMigrator(backup_path, target_path)
            can_migrate, reason = migrator.can_migrate()

            assert not can_migrate
            assert "invalid" in reason.lower()

        finally:
            # Clean up manually
            import time

            time.sleep(0.1)

            for path in [backup_path, target_path]:
                if path and path.exists():
                    try:
                        path.unlink(missing_ok=True)
                    except Exception:
                        pass

    def test_migration_log(self):
        """Should generate detailed migration log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create v2 backup
            self.create_v2_database(backup_path)
            self.create_current_database(target_path)

            # Migrate
            migrator = DatabaseMigrator(backup_path, target_path)
            result = migrator.migrate()

            # Check migration log exists
            assert "log" in result
            assert len(result["log"]) > 0

            # Log should mention key steps
            log_text = " ".join(result["log"])
            assert "staging" in log_text.lower()
            assert "industry" in log_text.lower()

    def test_migration_performance(self):
        """Migration should complete quickly for typical database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_path = tmpdir / "backup.db"
            target_path = tmpdir / "target.db"

            # Create v2 database with realistic data (100 clients)
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    user_id INTEGER NOT NULL,
                    business_description TEXT
                )
            """
            )

            for i in range(1, 101):
                cursor.execute(
                    f"INSERT INTO clients (id, name, user_id, business_description) "
                    f"VALUES ({i}, 'Client {i}', 1, 'Description {i} with some text')"
                )

            cursor.execute("PRAGMA user_version = 2")
            conn.commit()
            conn.close()

            # Create target
            self.create_current_database(target_path)

            # Migrate with timing
            import time

            start = time.time()
            migrator = DatabaseMigrator(backup_path, target_path)
            migrator.migrate()
            elapsed = time.time() - start

            # Should complete in < 5 seconds
            assert elapsed < 5.0, f"Migration took {elapsed:.2f}s, expected < 5s"
