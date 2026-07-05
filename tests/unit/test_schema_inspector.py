"""
Unit tests for schema_inspector module.

Tests schema version tracking, snapshot extraction, and comparison.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base

from backend.services.schema_inspector import (
    ColumnInfo,
    SchemaDiff,
    compare_schemas,
    get_schema_snapshot,
    get_schema_version,
    set_schema_version,
)

Base = declarative_base()


class TestTable(Base):
    """Test table for schema inspection."""

    __tablename__ = "test_table"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)


class TestSchemaVersion:
    """Tests for schema version get/set operations."""

    def test_get_version_from_new_database(self):
        """New databases should return version 0."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Create empty database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

            # Version should be 0
            version = get_schema_version(db_path)
            assert version == 0

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_set_and_get_version(self):
        """Should be able to set and retrieve schema version."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Create database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

            # Set version
            set_schema_version(db_path, 42)

            # Get version
            version = get_schema_version(db_path)
            assert version == 42

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_version_with_engine(self):
        """Should work with SQLAlchemy engine."""
        engine = create_engine("sqlite:///:memory:")

        # Create table
        Base.metadata.create_all(engine)

        # Set and get version
        set_schema_version(engine, 10)
        version = get_schema_version(engine)
        assert version == 10


class TestSchemaSnapshot:
    """Tests for schema snapshot extraction."""

    def test_snapshot_empty_database(self):
        """Empty database should return empty schema."""
        engine = create_engine("sqlite:///:memory:")
        schema = get_schema_snapshot(engine)
        assert schema == {}

    def test_snapshot_with_table(self):
        """Should extract schema from database with tables."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        schema = get_schema_snapshot(engine)

        # Should have test_table
        assert "test_table" in schema

        # Check columns
        cols = {col.name: col for col in schema["test_table"]}
        assert "id" in cols
        assert "name" in cols
        assert "description" in cols

        # Check types
        assert "INTEGER" in cols["id"].type
        assert "VARCHAR" in cols["name"].type or "TEXT" in cols["name"].type
        assert "TEXT" in cols["description"].type

        # Check nullability
        assert not cols["name"].nullable
        assert cols["description"].nullable

    def test_snapshot_from_file(self):
        """Should extract schema from database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Create database
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(engine)
            engine.dispose()  # Release file lock before snapshot

            # Get snapshot
            schema = get_schema_snapshot(db_path)

            assert "test_table" in schema
            assert len(schema["test_table"]) == 3  # id, name, description

        finally:
            Path(db_path).unlink(missing_ok=True)


class TestSchemaComparison:
    """Tests for schema comparison."""

    def test_compare_identical_schemas(self):
        """Identical schemas should have no differences."""
        engine1 = create_engine("sqlite:///:memory:")
        engine2 = create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine1)
        Base.metadata.create_all(engine2)

        diff = compare_schemas(engine1, engine2)

        assert not diff.has_changes()
        assert diff.added_columns == {}
        assert diff.dropped_columns == {}
        assert diff.renamed_columns == {}

    def test_compare_added_column(self):
        """Should detect added columns."""
        # Old schema
        old_schema = {"test_table": [ColumnInfo("id", "INTEGER", False, None)]}

        # New schema with added column
        new_schema = {
            "test_table": [
                ColumnInfo("id", "INTEGER", False, None),
                ColumnInfo("name", "VARCHAR", True, None),
            ]
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_changes()
        assert "test_table" in diff.added_columns
        assert len(diff.added_columns["test_table"]) == 1
        assert diff.added_columns["test_table"][0].name == "name"

    def test_compare_dropped_column(self):
        """Should detect dropped columns."""
        # Old schema with extra column
        old_schema = {
            "test_table": [
                ColumnInfo("id", "INTEGER", False, None),
                ColumnInfo("obsolete", "TEXT", True, None),
            ]
        }

        # New schema without obsolete column
        new_schema = {"test_table": [ColumnInfo("id", "INTEGER", False, None)]}

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_changes()
        assert "test_table" in diff.dropped_columns
        assert "obsolete" in diff.dropped_columns["test_table"]

    def test_compare_multiple_tables(self):
        """Should compare multiple tables."""
        old_schema = {
            "table1": [ColumnInfo("id", "INTEGER", False, None)],
            "table2": [ColumnInfo("id", "INTEGER", False, None)],
        }

        new_schema = {
            "table1": [
                ColumnInfo("id", "INTEGER", False, None),
                ColumnInfo("new_col", "TEXT", True, None),
            ],
            "table2": [ColumnInfo("id", "INTEGER", False, None)],
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_changes()
        assert "table1" in diff.added_columns
        assert "table2" not in diff.added_columns

    def test_compare_with_versions(self):
        """Should track version differences."""
        engine1 = create_engine("sqlite:///:memory:")
        engine2 = create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine1)
        Base.metadata.create_all(engine2)

        set_schema_version(engine1, 1)
        set_schema_version(engine2, 4)

        diff = compare_schemas(engine1, engine2)

        assert diff.version_diff == (1, 4)


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_column_info_creation(self):
        """Should create ColumnInfo with all fields."""
        col = ColumnInfo(name="test", type="VARCHAR", nullable=True, default="default_value")

        assert col.name == "test"
        assert col.type == "VARCHAR"
        assert col.nullable is True
        assert col.default == "default_value"

    def test_column_info_equality(self):
        """ColumnInfo instances should be comparable."""
        col1 = ColumnInfo("test", "VARCHAR", True, None)
        col2 = ColumnInfo("test", "VARCHAR", True, None)
        col3 = ColumnInfo("other", "VARCHAR", True, None)

        assert col1 == col2
        assert col1 != col3


class TestSchemaDiff:
    """Tests for SchemaDiff dataclass."""

    def test_has_changes_with_additions(self):
        """Should detect changes when columns added."""
        diff = SchemaDiff(
            added_columns={"table": [ColumnInfo("new", "TEXT", True, None)]},
            dropped_columns={},
            renamed_columns={},
            version_diff=(1, 2),
        )

        assert diff.has_changes()

    def test_has_changes_with_drops(self):
        """Should detect changes when columns dropped."""
        diff = SchemaDiff(
            added_columns={},
            dropped_columns={"table": ["old_col"]},
            renamed_columns={},
            version_diff=(1, 2),
        )

        assert diff.has_changes()

    def test_has_changes_with_renames(self):
        """Should detect changes when columns renamed."""
        diff = SchemaDiff(
            added_columns={},
            dropped_columns={},
            renamed_columns={"table": {"old": "new"}},
            version_diff=(1, 2),
        )

        assert diff.has_changes()

    def test_has_changes_none(self):
        """Should return False when no changes."""
        diff = SchemaDiff(
            added_columns={}, dropped_columns={}, renamed_columns={}, version_diff=(1, 1)
        )

        assert not diff.has_changes()
