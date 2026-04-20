"""
Database merge service.

Imports content records (clients, projects, posts, etc.) from a source
database into the live target database without overwriting users, credits,
or settings.

Preserved (never touched):
    users, credit_transactions, credit_packages, settings,
    stripe_payments, deletion_audit_log, trends

Merged (new records added, IDs remapped):
    clients, projects, runs, briefs, posts, research_results,
    deliverables, communications, mined_stories, story_usage

User matching: source users are matched to target users by email address.
Unmatched source users are assigned to the first superuser in the target
(or first user if no superuser exists). All primary and foreign keys are
remapped to avoid ID conflicts.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.utils.logger import logger


# Tables that are NEVER read from the source — always preserved in the target
PRESERVE_TABLES: frozenset[str] = frozenset(
    {
        "users",
        "credit_transactions",
        "credit_packages",
        "settings",
        "stripe_payments",
        "deletion_audit_log",
        "trends",
    }
)

# Merge order matters: parents must be inserted before children
MERGE_ORDER: list[str] = [
    "clients",
    "projects",
    "runs",
    "briefs",
    "posts",
    "research_results",
    "deliverables",
    "communications",
    "mined_stories",
    "story_usage",
]

# FK columns to remap per table: {fk_column → parent_table}
_FK_MAP: dict[str, dict[str, str]] = {
    "projects": {"client_id": "clients"},
    "runs": {"project_id": "projects"},
    "briefs": {"project_id": "projects"},
    "posts": {"project_id": "projects", "run_id": "runs"},
    "research_results": {"client_id": "clients", "project_id": "projects"},
    "deliverables": {"project_id": "projects", "client_id": "clients", "run_id": "runs"},
    "communications": {"client_id": "clients"},
    "mined_stories": {"client_id": "clients"},
    "story_usage": {"story_id": "mined_stories"},
}

# Columns used to detect duplicate records (checked after FK remapping)
_DUPLICATE_KEYS: dict[str, list[str]] = {
    "clients": ["user_id", "name"],
    "projects": ["client_id", "name"],
    "runs": ["project_id", "started_at"],
    "briefs": ["project_id"],
    "posts": ["project_id", "template_id", "variant"],
    "research_results": ["client_id", "tool_name", "created_at"],
    "deliverables": ["project_id", "format", "created_at"],
    "communications": ["client_id", "created_at"],
    "mined_stories": ["client_id", "created_at"],
    "story_usage": ["story_id", "created_at"],
}


class _DryRunRollback(Exception):
    """Raised inside a SQLAlchemy transaction to trigger rollback without error."""


@dataclass
class MergeResult:
    """Results from a merge (or dry-run preview) operation."""

    merged: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    user_mapping: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_merged(self) -> int:
        """Total rows inserted across all tables."""
        return sum(self.merged.values())

    @property
    def total_skipped(self) -> int:
        """Total rows skipped (duplicates or unmapped users)."""
        return sum(self.skipped.values())


class DatabaseMerger:
    """
    Merges content records from a source (backup) database into the live
    target database.

    Source reads: sqlite3 directly (the uploaded backup file).
    Target reads/writes: SQLAlchemy engine (works for both file-based and
    in-memory SQLite).
    """

    def __init__(self, source_path: str | Path, target_engine: Engine) -> None:
        self.source_path = Path(source_path)
        self.target_engine = target_engine

    def merge(self, dry_run: bool = False) -> MergeResult:
        """
        Execute the merge (or preview it if dry_run=True).

        When dry_run=True the entire operation runs inside a transaction that
        is rolled back at the end — so the counts are accurate but nothing is
        committed.

        Args:
            dry_run: Compute and return counts without persisting any changes.

        Returns:
            MergeResult with per-table counts, user mapping, and warnings.

        Raises:
            Exception: If the merge fails partway through (target is unchanged
                because the transaction is rolled back on error).
        """
        result = MergeResult(dry_run=dry_run)
        src = sqlite3.connect(str(self.source_path))

        try:
            src_tables = _src_tables(src)

            try:
                with self.target_engine.begin() as tgt:
                    tgt_tables = _tgt_tables(tgt)
                    user_id_map = self._build_user_map(src, tgt, result)

                    id_maps: dict[str, dict[int, int]] = {}
                    for table in MERGE_ORDER:
                        if table not in src_tables or table not in tgt_tables:
                            continue

                        src_cols = _src_columns(src, table)
                        tgt_cols_set = set(_tgt_columns(tgt, table))
                        # Transfer only columns present in both schemas
                        cols = [c for c in src_cols if c in tgt_cols_set]

                        if "id" not in cols:
                            continue

                        n_merged, n_skipped, id_map = self._merge_table(
                            src, tgt, table, cols, user_id_map, id_maps, dry_run
                        )
                        id_maps[table] = id_map
                        if n_merged:
                            result.merged[table] = n_merged
                        if n_skipped:
                            result.skipped[table] = n_skipped

                    if dry_run:
                        raise _DryRunRollback()

            except _DryRunRollback:
                # Transaction rolled back — counts are still accurate
                pass

        finally:
            src.close()

        logger.info(
            "Merge %s: %d rows merged, %d skipped",
            "preview" if dry_run else "complete",
            result.total_merged,
            result.total_skipped,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_user_map(
        self,
        src: sqlite3.Connection,
        tgt: Any,  # SQLAlchemy Connection
        result: MergeResult,
    ) -> dict[int, int]:
        """
        Map source user IDs → target user IDs by matching email addresses.

        Unmatched source users are mapped to the first superuser in the target
        (or the first user if no superuser exists). Records belonging to a
        source user with no target match AND no fallback are skipped.
        """
        src_users: dict[int, str] = {
            row[0]: row[1] for row in src.execute("SELECT id, email FROM users").fetchall()
        }
        tgt_by_email: dict[str, int] = {
            row.email: row.id for row in tgt.execute(text("SELECT id, email FROM users")).fetchall()
        }

        fallback = tgt.execute(
            text("SELECT id FROM users WHERE is_superuser = 1 ORDER BY id LIMIT 1")
        ).fetchone()
        if not fallback:
            fallback = tgt.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
        fallback_id: int | None = fallback.id if fallback else None

        id_map: dict[int, int] = {}
        for uid, email in src_users.items():
            if email in tgt_by_email:
                id_map[uid] = tgt_by_email[email]
                result.user_mapping[email] = "matched"
            elif fallback_id is not None:
                id_map[uid] = fallback_id
                result.user_mapping[email] = "assigned_to_admin"
                result.warnings.append(
                    f"Source user '{email}' not found in target — records assigned to admin"
                )
            else:
                result.user_mapping[email] = "skipped_no_target_user"
                result.warnings.append(
                    f"Source user '{email}' not found and no fallback user exists — records skipped"
                )

        return id_map

    def _merge_table(
        self,
        src: sqlite3.Connection,
        tgt: Any,  # SQLAlchemy Connection
        table: str,
        cols: list[str],
        user_id_map: dict[int, int],
        id_maps: dict[str, dict[int, int]],
        dry_run: bool,
    ) -> tuple[int, int, dict[int, int]]:
        """
        Merge one table from source into target.

        Returns:
            (n_merged, n_skipped, old_id_to_new_id_map)
        """
        col_csv = ", ".join(f'"{c}"' for c in cols)
        src_rows = src.execute(f'SELECT {col_csv} FROM "{table}"').fetchall()
        if not src_rows:
            return 0, 0, {}

        max_row = tgt.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table}"')).fetchone()
        next_id: int = (max_row[0] if max_row else 0) + 1

        dup_keys = _DUPLICATE_KEYS.get(table)
        id_map: dict[int, int] = {}
        n_merged = n_skipped = 0

        for row in src_rows:
            row_dict: dict[str, Any] = dict(zip(cols, tuple(row)))
            old_id: int = row_dict["id"]

            # Remap user_id → target user
            if "user_id" in row_dict and row_dict["user_id"] is not None:
                mapped = user_id_map.get(row_dict["user_id"])
                if mapped is None:
                    # No mapping for this user — skip the record entirely
                    n_skipped += 1
                    continue
                row_dict["user_id"] = mapped

            # Remap all known foreign key columns
            for fk_col, parent_table in _FK_MAP.get(table, {}).items():
                if fk_col in row_dict and row_dict[fk_col] is not None:
                    row_dict[fk_col] = id_maps.get(parent_table, {}).get(
                        row_dict[fk_col], row_dict[fk_col]
                    )

            # Skip duplicates
            if dup_keys and _is_duplicate(tgt, table, row_dict, dup_keys):
                n_skipped += 1
                id_map[old_id] = old_id  # self-reference; unused for meaningful FK
                continue

            # Assign a new non-conflicting PK
            new_id = next_id
            next_id += 1
            row_dict["id"] = new_id
            id_map[old_id] = new_id

            if not dry_run:
                param_list = ", ".join(f":{c}" for c in cols)
                params = {c: row_dict.get(c) for c in cols}
                tgt.execute(
                    text(f'INSERT OR IGNORE INTO "{table}" ({col_csv})' f" VALUES ({param_list})"),
                    params,
                )

            n_merged += 1

        return n_merged, n_skipped, id_map


# ------------------------------------------------------------------
# Module-level utilities
# ------------------------------------------------------------------


def _src_tables(src: sqlite3.Connection) -> set[str]:
    """Return set of table names in the source SQLite database."""
    return {
        row[0]
        for row in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def _tgt_tables(tgt: Any) -> set[str]:
    """Return set of table names in the target database via SQLAlchemy."""
    rows = tgt.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {row[0] for row in rows}


def _src_columns(src: sqlite3.Connection, table: str) -> list[str]:
    """Return ordered column names for a table in the source database."""
    return [row[1] for row in src.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _tgt_columns(tgt: Any, table: str) -> list[str]:
    """Return ordered column names for a table in the target database."""
    rows = tgt.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    return [row[1] for row in rows]


def _is_duplicate(tgt: Any, table: str, row: dict[str, Any], keys: list[str]) -> bool:
    """
    Return True if a record matching all non-None key values already exists
    in the target table.
    """
    present = [(k, row[k]) for k in keys if k in row and row[k] is not None]
    if not present:
        return False
    where = " AND ".join(f'"{k}" = :{k}' for k, _ in present)
    params = {k: v for k, v in present}
    result = tgt.execute(
        text(f'SELECT 1 FROM "{table}" WHERE {where} LIMIT 1'),
        params,
    ).fetchone()
    return result is not None
