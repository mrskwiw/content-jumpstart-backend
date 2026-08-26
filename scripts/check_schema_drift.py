#!/usr/bin/env python
"""Fail if the ORM models declare a column the provisioning schema does not create.

Why this gate exists (Bug #239)
-------------------------------
Three artifacts have to agree about the shape of the database, and nothing
compared them:

1. the ORM models        — what the running app selects
2. ``scripts/schema.sql`` — what a **newly provisioned** instance gets
3. ``init_db()``          — what an **already provisioned** instance gets

``users.must_change_password`` was added to (1) and (2) but not (3), so every
existing instance crash-looped at startup on ``db.query(User).count()`` while
Render kept serving the last good deploy. Three deploys failed over two weeks
and nothing said so.

This script covers the (1) vs (2) edge: a column added to a model but never
added to ``schema.sql`` silently breaks every instance provisioned afterwards.
The (1) vs (3) edge is covered at runtime by ``check_model_drift`` in
``backend/services/schema_inspector.py``, which the app runs on every boot.

Comparison is by **column name**, parsed straight out of the ``CREATE TABLE``
statements. Types are deliberately not compared: ``schema.sql`` is PostgreSQL
DDL while the models are dialect-neutral, so a type comparison would be a
permanent source of false positives.

Usage::

    python scripts/check_schema_drift.py            # exit 1 on drift
    python scripts/check_schema_drift.py --schema PATH

Exits 0 and prints a SKIP when the schema file cannot be found — it lives at
the repo root, outside this git repo, so it is genuinely absent in some
checkouts. Skipping loudly beats failing a gate nobody can satisfy, and beats
passing one that never ran.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Run from project/ — make the package importable regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

#: The authoritative provisioning schema — the file provision_customer.py applies
#: to a new customer database. It lives at the *repo root*, which is outside this
#: git repo, so it is absent in a plain CI checkout and the run skips.
#:
#: Deliberately the only candidate. ``src/database/schema.sql`` is tracked and
#: looks like an alternative, but it is a stale 12-table fragment (the real schema
#: has 41 tables); falling back to it would fail this gate on every run for reasons
#: that have nothing to do with the commit under test, and a gate that cries wolf
#: gets switched off. Pass --schema explicitly to check any other file.
_SCHEMA_CANDIDATES = (_PROJECT_ROOT.parent / "scripts" / "schema.sql",)

_CREATE_TABLE_RE = re.compile(
    # The body is terminated by a ");" that closes the statement. Anchoring to a
    # newline (rather than just ")") keeps a trailing "NUMERIC(10,2)" from ending
    # the match early; leading whitespace is tolerated so indented DDL parses too.
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"']?(\w+)[\"']?\s*\((.*?)\n\s*\);",
    re.IGNORECASE | re.DOTALL,
)

#: Table-level constraints that open a line but are not column definitions.
_NOT_A_COLUMN = (
    "primary",
    "foreign",
    "unique",
    "check",
    "constraint",
    "exclude",
)


def _strip_sql_comments(sql: str) -> str:
    """Remove ``--`` line comments, which frequently trail column definitions."""
    return re.sub(r"--[^\n]*", "", sql)


def parse_schema_sql(sql: str) -> dict[str, set[str]]:
    """Extract ``{table_name: {column_name, ...}}`` from CREATE TABLE statements.

    Args:
        sql: The full text of a schema DDL file.

    Returns:
        Mapping of table name to the set of column names it declares.
    """
    sql = _strip_sql_comments(sql)
    tables: dict[str, set[str]] = {}

    for table_name, body in _CREATE_TABLE_RE.findall(sql):
        columns: set[str] = set()
        depth = 0
        current: list[str] = []
        # Split on top-level commas only: NUMERIC(10,2) and multi-column
        # constraints both contain commas inside parentheses.
        for char in body:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                current, chunk = [], "".join(current)
                _maybe_add_column(chunk, columns)
                continue
            current.append(char)
        _maybe_add_column("".join(current), columns)

        tables[table_name.lower()] = columns

    return tables


def _maybe_add_column(chunk: str, columns: set[str]) -> None:
    """Record the column name in ``chunk`` unless it is a table constraint."""
    chunk = chunk.strip()
    if not chunk:
        return
    first = chunk.split()[0].strip('"').strip("'")
    if first.lower() in _NOT_A_COLUMN:
        return
    columns.add(first.lower())


def load_model_tables() -> dict[str, set[str]]:
    """Return ``{table_name: {column_name, ...}}`` as declared by the ORM models."""
    from backend.database import Base
    import backend.models  # noqa: F401  — registers every model on Base.metadata

    return {
        name.lower(): {col.name.lower() for col in table.columns}
        for name, table in Base.metadata.tables.items()
    }


def find_schema_file(explicit: str | None) -> Path | None:
    """Resolve the schema file to check against, or None if absent."""
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    return next((c for c in _SCHEMA_CANDIDATES if c.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", help="Path to schema.sql (default: search known locations)")
    args = parser.parse_args()

    schema_path = find_schema_file(args.schema)
    if schema_path is None:
        searched = args.schema or ", ".join(str(c) for c in _SCHEMA_CANDIDATES)
        print(f"SKIP: no provisioning schema found (looked in: {searched})")
        print("      Cannot verify model-vs-schema drift in this checkout.")
        return 0

    schema_tables = parse_schema_sql(schema_path.read_text(encoding="utf-8"))
    model_tables = load_model_tables()

    print(f"Checking {len(model_tables)} model tables against {schema_path}")
    print(f"  schema.sql declares {len(schema_tables)} tables")

    missing_tables = sorted(t for t in model_tables if t not in schema_tables)
    missing_columns = {
        table: sorted(cols - schema_tables[table])
        for table, cols in model_tables.items()
        if table in schema_tables and (cols - schema_tables[table])
    }

    if not missing_tables and not missing_columns:
        print("OK: schema.sql creates every table and column the ORM declares.")
        return 0

    print("\nDRIFT: the ORM declares things schema.sql does not create.")
    print("A newly provisioned instance would be missing these and fail at runtime.\n")
    for table in missing_tables:
        print(f"  missing table:  {table}")
    for table, cols in sorted(missing_columns.items()):
        for col in cols:
            print(f"  missing column: {table}.{col}")
    print("\nFix: add them to scripts/schema.sql AND give already-provisioned")
    print("instances an upgrade path (backend/database.py init_db + schema_mapping.json).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
