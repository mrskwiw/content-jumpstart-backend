"""COMPLIANCE-01 (AI-content disclosure) — schema rollout for the two new columns.

Every customer runs its own database, so a new column must have an upgrade path or
already-provisioned instances drift from the model (BUGS #239: must_change_password
shipped without an ALTER path and prod deploys crash-looped for two weeks).

- posts.ai_draft_content       TEXT NULL     snapshot of the AI draft at generation
- scheduled_posts.ai_generated BOOLEAN NULL  schedule-time checkbox for free-text posts
"""

import pytest
from sqlalchemy import create_engine, inspect, text

import backend.database
from backend.database import Base, init_db
from backend.migrations import load_migration_rules

NEW_COLUMNS = {"posts": "ai_draft_content", "scheduled_posts": "ai_generated"}


@pytest.fixture
def legacy_engine():
    """A database shaped like an instance provisioned before this release."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for table, column in NEW_COLUMNS.items():
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
    yield engine
    engine.dispose()


def _columns(engine, table):
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_init_db_adds_the_new_columns_to_an_existing_instance(legacy_engine):
    for table, column in NEW_COLUMNS.items():
        assert column not in _columns(legacy_engine, table)  # precondition: old shape

    original = backend.database.engine
    backend.database.engine = legacy_engine
    try:
        init_db()
    finally:
        backend.database.engine = original

    for table, column in NEW_COLUMNS.items():
        assert column in _columns(legacy_engine, table), f"{table}.{column} has no ALTER path"


def test_init_db_is_idempotent_on_an_upgraded_instance(legacy_engine):
    original = backend.database.engine
    backend.database.engine = legacy_engine
    try:
        init_db()
        init_db()  # second boot must not fail or duplicate anything
    finally:
        backend.database.engine = original
    for table, column in NEW_COLUMNS.items():
        assert column in _columns(legacy_engine, table)


def test_schema_version_10_records_the_columns_for_backup_restore():
    # database_migrator replays version_migrations when restoring an older backup.
    config = load_migration_rules()
    assert config["current_version"] >= 10
    v10 = config["version_migrations"]["10"]
    added = {
        table: {c["name"] for c in v10.get(table, {}).get("add_columns", [])}
        for table in NEW_COLUMNS
    }
    for table, column in NEW_COLUMNS.items():
        assert column in added[table], f"v10 is missing {table}.{column}"
