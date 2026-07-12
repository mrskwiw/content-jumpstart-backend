"""
Schema inspection and version management for database migrations.

Provides utilities to:
- Track schema version (SQLite PRAGMA user_version; schema_version table on Postgres)
- Extract complete schema snapshots
- Compare schemas between databases
- Generate column-level diffs for migrations
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from backend.utils.logger import logger


@dataclass
class ColumnInfo:
    """Information about a database column."""

    name: str
    type: str
    nullable: bool
    default: Any


@dataclass
class SchemaDiff:
    """Differences between two database schemas."""

    added_columns: dict[str, list[ColumnInfo]]  # table_name -> list of new columns
    dropped_columns: dict[str, list[str]]  # table_name -> list of dropped column names
    renamed_columns: dict[str, dict[str, str]]  # table_name -> {old_name: new_name}
    version_diff: tuple[int, int]  # (old_version, new_version)

    def has_changes(self) -> bool:
        """Check if there are any schema changes."""
        return bool(self.added_columns or self.dropped_columns or self.renamed_columns)


def get_schema_version(db_path_or_engine: str | Path | Engine) -> int:
    """
    Read the schema version from the database.

    Uses SQLite's ``PRAGMA user_version`` on SQLite, and a dedicated
    ``schema_version`` table on other backends (e.g. PostgreSQL), since
    ``PRAGMA`` is SQLite-only syntax.

    Args:
        db_path_or_engine: Path to database file or SQLAlchemy engine

    Returns:
        Schema version number (0 for unversioned databases)
    """
    if isinstance(db_path_or_engine, (str, Path)):
        engine = create_engine(f"sqlite:///{db_path_or_engine}")
        should_dispose = True
    else:
        engine = db_path_or_engine
        should_dispose = False

    try:
        with engine.connect() as conn:
            if engine.dialect.name == "sqlite":
                result = conn.execute(text("PRAGMA user_version"))
            else:
                # Non-SQLite backends have no PRAGMA; use a version table.
                conn.execute(
                    text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
                )
                conn.commit()
                result = conn.execute(text("SELECT version FROM schema_version LIMIT 1"))
            version = result.scalar() or 0
            logger.debug(f"Schema version: {version}")
            return int(version)
    except Exception as e:
        logger.error(f"Failed to read schema version: {e}")
        return 0
    finally:
        if should_dispose:
            engine.dispose()


def set_schema_version(db_path_or_engine: str | Path | Engine, version: int) -> None:
    """
    Persist the schema version to the database.

    Uses SQLite's ``PRAGMA user_version`` on SQLite, and a single-row
    ``schema_version`` table on other backends (e.g. PostgreSQL).

    Args:
        db_path_or_engine: Path to database file or SQLAlchemy engine
        version: Schema version number to set
    """
    if isinstance(db_path_or_engine, (str, Path)):
        engine = create_engine(f"sqlite:///{db_path_or_engine}")
        should_dispose = True
    else:
        engine = db_path_or_engine
        should_dispose = False

    try:
        with engine.connect() as conn:
            if engine.dialect.name == "sqlite":
                # PRAGMA does not accept bind parameters; version is a validated int.
                conn.execute(text(f"PRAGMA user_version = {int(version)}"))
            else:
                # Upsert the single version row on non-SQLite backends.
                conn.execute(
                    text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
                )
                conn.execute(text("DELETE FROM schema_version"))
                conn.execute(
                    text("INSERT INTO schema_version (version) VALUES (:version)"),
                    {"version": int(version)},
                )
            conn.commit()
            logger.info(f"Set schema version to {version}")
    except Exception as e:
        logger.error(f"Failed to set schema version: {e}")
        raise
    finally:
        if should_dispose:
            engine.dispose()


def get_schema_snapshot(
    db_path_or_engine: str | Path | Engine,
) -> dict[str, list[ColumnInfo]]:
    """
    Extract complete schema snapshot using SQLAlchemy inspector.

    Args:
        db_path_or_engine: Path to database file or SQLAlchemy engine

    Returns:
        Dictionary mapping table_name -> list of ColumnInfo
    """
    if isinstance(db_path_or_engine, (str, Path)):
        engine = create_engine(f"sqlite:///{db_path_or_engine}")
        should_dispose = True
    else:
        engine = db_path_or_engine
        should_dispose = False

    try:
        inspector = inspect(engine)
        schema: dict[str, list[ColumnInfo]] = {}

        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append(
                    ColumnInfo(
                        name=col["name"],
                        type=str(col["type"]),
                        nullable=col.get("nullable", True),
                        default=col.get("default"),
                    )
                )
            schema[table_name] = columns
            logger.debug(f"Table {table_name}: {len(columns)} columns")

        return schema
    finally:
        if should_dispose:
            engine.dispose()


def compare_schemas(
    old_db_or_schema: str | Path | Engine | dict[str, list[ColumnInfo]],
    new_db_or_schema: str | Path | Engine | dict[str, list[ColumnInfo]],
) -> SchemaDiff:
    """
    Generate column-level diff between two schemas.

    Args:
        old_db_or_schema: Old database path/engine or schema snapshot
        new_db_or_schema: New database path/engine or schema snapshot

    Returns:
        SchemaDiff with added, dropped, and renamed columns
    """
    # Get schemas
    if isinstance(old_db_or_schema, dict):
        old_schema = old_db_or_schema
        old_version = 0
    else:
        old_schema = get_schema_snapshot(old_db_or_schema)
        old_version = get_schema_version(old_db_or_schema)

    if isinstance(new_db_or_schema, dict):
        new_schema = new_db_or_schema
        new_version = 0
    else:
        new_schema = get_schema_snapshot(new_db_or_schema)
        new_version = get_schema_version(new_db_or_schema)

    added_columns: dict[str, list[ColumnInfo]] = {}
    dropped_columns: dict[str, list[str]] = {}
    renamed_columns: dict[str, dict[str, str]] = {}

    # Compare each table
    all_tables = set(old_schema.keys()) | set(new_schema.keys())

    for table_name in all_tables:
        old_cols = {col.name: col for col in old_schema.get(table_name, [])}
        new_cols = {col.name: col for col in new_schema.get(table_name, [])}

        # Find added columns
        added = []
        for col_name, col_info in new_cols.items():
            if col_name not in old_cols:
                added.append(col_info)

        if added:
            added_columns[table_name] = added

        # Find dropped columns
        dropped = []
        for col_name in old_cols:
            if col_name not in new_cols:
                dropped.append(col_name)

        if dropped:
            dropped_columns[table_name] = dropped

        # Note: Renamed column detection requires additional heuristics
        # For now, we treat renames as drop + add
        # Future enhancement: detect renames by type + position similarity

    diff = SchemaDiff(
        added_columns=added_columns,
        dropped_columns=dropped_columns,
        renamed_columns=renamed_columns,
        version_diff=(old_version, new_version),
    )

    logger.info(
        f"Schema comparison: {len(added_columns)} tables with additions, "
        f"{len(dropped_columns)} tables with deletions"
    )

    return diff
