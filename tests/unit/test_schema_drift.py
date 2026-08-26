"""Tests for the Bug #239 schema-drift guards.

Bug #239: ``users.must_change_password`` reached the ORM models and
``scripts/schema.sql`` but never got an upgrade path for already-provisioned
databases. Every existing instance then crash-looped at startup on
``db.query(User).count()`` — and because Render keeps the last good deploy
serving when a new one fails, three failed deploys over two weeks looked
exactly like a healthy site.

Two guards came out of it, and these tests cover both:

* ``check_model_drift`` — runtime, run on every boot against the real database.
* ``scripts/check_schema_drift.py`` — CI, models vs the provisioning schema.
"""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from backend.services.schema_inspector import ModelDrift, check_model_drift

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_schema_drift.py"
_spec = importlib.util.spec_from_file_location("check_schema_drift", _SCRIPT)
assert _spec and _spec.loader
check_schema_drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_schema_drift)


# ---------------------------------------------------------------------------
# parse_schema_sql
# ---------------------------------------------------------------------------


class TestParseSchemaSql:
    def test_extracts_tables_and_columns(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id                   TEXT PRIMARY KEY,
            email                VARCHAR(255) NOT NULL,
            must_change_password BOOLEAN DEFAULT false NOT NULL
        );
        """
        assert check_schema_drift.parse_schema_sql(sql) == {
            "users": {"id", "email", "must_change_password"}
        }

    def test_ignores_trailing_line_comments(self):
        """schema.sql annotates columns inline — the comment is not a column."""
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id                   TEXT PRIMARY KEY,
            must_change_password BOOLEAN DEFAULT false NOT NULL,  -- S-01.4f
            email_verified       BOOLEAN DEFAULT true NOT NULL
        );
        """
        assert check_schema_drift.parse_schema_sql(sql)["users"] == {
            "id",
            "must_change_password",
            "email_verified",
        }

    def test_does_not_split_inside_parentheses(self):
        """NUMERIC(10,2) contains a comma that is not a column separator."""
        sql = """
        CREATE TABLE costs (
            id     TEXT PRIMARY KEY,
            amount NUMERIC(10,2) NOT NULL
        );
        """
        assert check_schema_drift.parse_schema_sql(sql)["costs"] == {"id", "amount"}

    def test_table_constraints_are_not_columns(self):
        sql = """
        CREATE TABLE team_members (
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            PRIMARY KEY (team_id, user_id),
            UNIQUE (user_id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
        """
        assert check_schema_drift.parse_schema_sql(sql)["team_members"] == {
            "team_id",
            "user_id",
        }


# ---------------------------------------------------------------------------
# find_schema_file — the CI checkout skips honestly rather than failing
# ---------------------------------------------------------------------------


class TestFindSchemaFile:
    def test_missing_explicit_path_returns_none(self):
        assert check_schema_drift.find_schema_file("/no/such/schema.sql") is None

    def test_stale_in_repo_copy_is_not_a_fallback(self):
        """src/database/schema.sql is a stale 12-table fragment.

        Falling back to it would fail the gate on every run for reasons
        unrelated to the commit under test, and a gate that cries wolf gets
        switched off.
        """
        candidates = [str(p) for p in check_schema_drift._SCHEMA_CANDIDATES]
        assert not any("src" in c and "database" in c for c in candidates)


# ---------------------------------------------------------------------------
# check_model_drift — the runtime guard
# ---------------------------------------------------------------------------


class TestCheckModelDrift:
    def test_reports_column_the_orm_expects_but_db_lacks(self):
        """The exact #239 shape: table present, one column missing."""
        engine = create_engine("sqlite:///:memory:")
        from backend.database import Base
        import backend.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            # SQLite cannot DROP COLUMN on older versions; rebuild users without it.
            conn.execute(text("ALTER TABLE users RENAME TO users_old"))
            cols = [
                c.name
                for c in Base.metadata.tables["users"].columns
                if c.name != "must_change_password"
            ]
            col_list = ", ".join(cols)
            conn.execute(text(f"CREATE TABLE users AS SELECT {col_list} FROM users_old"))
            conn.execute(text("DROP TABLE users_old"))
            conn.commit()

        drift = check_model_drift(engine)

        assert drift.has_drift()
        assert "must_change_password" in drift.missing_columns.get("users", [])
        assert "must_change_password" in drift.describe()

    def test_no_drift_when_database_matches_models(self):
        engine = create_engine("sqlite:///:memory:")
        from backend.database import Base
        import backend.models  # noqa: F401

        Base.metadata.create_all(bind=engine)

        drift = check_model_drift(engine)

        assert not drift.has_drift()
        assert drift.describe() == "no drift: database matches the ORM models"

    def test_reports_missing_table(self):
        engine = create_engine("sqlite:///:memory:")  # nothing created at all

        drift = check_model_drift(engine)

        assert drift.has_drift()
        assert "users" in drift.missing_tables

    def test_extra_database_columns_are_not_drift(self):
        """A column the ORM does not know about is harmless legacy baggage."""
        engine = create_engine("sqlite:///:memory:")
        from backend.database import Base
        import backend.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN legacy_field TEXT"))
            conn.commit()

        assert not check_model_drift(engine).has_drift()


class TestModelDriftDescribe:
    def test_empty_drift_describes_cleanly(self):
        assert ModelDrift([], {}).describe() == "no drift: database matches the ORM models"

    def test_describes_tables_and_columns_together(self):
        drift = ModelDrift(["teams"], {"users": ["must_change_password"]})
        described = drift.describe()
        assert "teams" in described
        assert "users missing: must_change_password" in described
