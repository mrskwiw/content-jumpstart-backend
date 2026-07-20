"""
In-process publishing scheduler (Phase 10).

When RUN_SCHEDULER=true, the FastAPI app runs a background loop that calls
`orchestrator.process_due()` every SCHEDULER_INTERVAL_SECONDS. This is the
"just add an env var" alternative to wiring an external cron at the /process-due
endpoint.

Multi-worker safety: Render can run several Uvicorn workers off one service, and
every worker would otherwise tick. Each tick first tries a Postgres *advisory
lock* — only the one worker that gets it does the run; the rest no-op. (Row-level
FOR UPDATE SKIP LOCKED in process_due already prevents double-publishing; the
advisory lock just avoids redundant passes.) On SQLite (dev) there's a single
process, so the lock step is skipped.
"""

from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import text

from backend.database import SessionLocal
from backend.services.distribution import orchestrator

logger = logging.getLogger(__name__)

# Arbitrary but fixed 64-bit key identifying this app's scheduler lock.
_ADVISORY_LOCK_KEY = 741002_10  # noqa: E501 (readability grouping)


def enabled() -> bool:
    return os.getenv("RUN_SCHEDULER", "false").strip().lower() in ("1", "true", "yes")


def _interval_seconds() -> int:
    try:
        return max(10, int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60")))
    except ValueError:
        return 60


def _tick() -> None:
    """One synchronous scheduler pass (run off the event loop via to_thread)."""
    db = SessionLocal()
    try:
        dialect = db.bind.dialect.name if db.bind is not None else ""
        if dialect == "postgresql":
            got = db.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": _ADVISORY_LOCK_KEY}
            ).scalar()
            if not got:
                return  # another worker owns this tick
            try:
                summary = orchestrator.process_due(db)
            finally:
                db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _ADVISORY_LOCK_KEY})
        else:
            summary = orchestrator.process_due(db)
        if summary and summary.get("processed"):
            logger.info("scheduler tick: %s", summary)
    finally:
        db.close()


async def scheduler_loop(stop: asyncio.Event) -> None:
    """Run `_tick` every interval until `stop` is set."""
    interval = _interval_seconds()
    logger.info("Distribution scheduler started (every %ss)", interval)
    while not stop.is_set():
        try:
            await asyncio.to_thread(_tick)
        except Exception:  # noqa: BLE001 - never let one bad tick kill the loop
            logger.exception("scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("Distribution scheduler stopped")
