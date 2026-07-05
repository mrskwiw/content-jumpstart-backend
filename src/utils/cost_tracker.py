"""Cost tracking for API usage and project profitability

Tracks token usage and costs for all API calls to enable:
- Per-project cost analysis
- Budget alerts and monitoring
- Profitability calculations
- Usage trends and optimization

Usage:
    tracker = CostTracker()

    # Track an API call
    tracker.track_api_call(
        project_id="Client_20250101_120000",
        operation="post_generation",
        model="claude-sonnet-4-5-20250929",
        input_tokens=1500,
        output_tokens=800
    )

    # Get project costs
    cost = tracker.get_project_cost("Client_20250101_120000")
    print(f"Total cost: ${cost:.2f}")
"""

import json
import uuid
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from ..utils.logger import logger


def _open_session():
    """Open a SQLAlchemy session bound to the application database.

    Cost tracking is now backed by the app's database (Postgres in production)
    rather than a local SQLite file — a local file is lost on ephemeral hosts
    (e.g. Render) and isn't per-customer. Returns ``None`` if the DB is
    unavailable, in which case all persistence degrades gracefully (calls still
    return their computed cost; reads return empty/zero) instead of crashing.

    Tests monkeypatch this to return an in-memory session.
    """
    try:
        from backend.database import SessionLocal

        return SessionLocal()
    except Exception as exc:  # pragma: no cover - defensive (import/DB config issues)
        logger.debug(f"Cost tracker: DB session unavailable ({exc}); persistence disabled")
        return None


def _as_dt(value: Any) -> datetime:
    """Coerce a DB timestamp (native datetime on Postgres, ISO str on SQLite)."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


# Model pricing (as of Dec 2025)
# Source: https://www.anthropic.com/pricing
MODEL_PRICING = {
    "claude-3-5-sonnet-20241022": {
        "input": 3.0,  # $3 per million input tokens
        "output": 15.0,  # $15 per million output tokens
        "cache_write": 3.75,  # $3.75 per million cache write tokens
        "cache_read": 0.3,  # $0.30 per million cache read tokens
    },
    "claude-sonnet-4-5-20250929": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.3,
    },
    "claude-3-opus-20240229": {
        "input": 15.0,
        "output": 75.0,
        "cache_write": 18.75,
        "cache_read": 1.5,
    },
    "claude-3-haiku-20240307": {
        "input": 0.25,
        "output": 1.25,
        "cache_write": 0.3,
        "cache_read": 0.03,
    },
}


@dataclass
class APICall:
    """Record of a single API call"""

    call_id: int
    project_id: str
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ProjectCost:
    """Cost summary for a project"""

    project_id: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    total_cost: float
    first_call: datetime
    last_call: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["first_call"] = self.first_call.isoformat()
        data["last_call"] = self.last_call.isoformat()
        return data


class CostTracker:
    """Track API costs and usage for projects"""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize cost tracker.

        Args:
            db_path: Deprecated. Accepted for backward compatibility but ignored —
                cost data is persisted to the application database via
                ``_open_session()`` (see module docstring). Schema (``api_calls``,
                ``budget_alerts``) is provisioned with the app schema, not here.
        """
        # Retained only so old callers passing db_path don't break.
        self.db_path = db_path

    def track_api_call(
        self,
        project_id: str,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> float:
        """Track an API call and return its cost

        Args:
            project_id: Project identifier (e.g., "Client_20250101_120000")
            operation: Operation type (e.g., "brief_parsing", "post_generation")
            model: Model used (e.g., "claude-3-5-sonnet-20241022")
            input_tokens: Input token count
            output_tokens: Output token count
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache

        Returns:
            Cost of this API call in USD
        """
        cost = self.calculate_cost(
            model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )

        session = _open_session()
        if session is None:
            # DB unavailable — still return the computed cost (fail-open on tracking).
            return cost

        call_id = uuid.uuid4().hex
        try:
            session.execute(
                text(
                    """
                    INSERT INTO api_calls (
                        call_id, project_id, operation, model,
                        input_tokens, output_tokens,
                        cache_creation_tokens, cache_read_tokens,
                        cost, timestamp
                    ) VALUES (
                        :call_id, :project_id, :operation, :model,
                        :input_tokens, :output_tokens,
                        :cache_creation_tokens, :cache_read_tokens,
                        :cost, :timestamp
                    )
                    """
                ),
                {
                    "call_id": call_id,
                    "project_id": project_id,
                    "operation": operation,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "cost": cost,
                    "timestamp": datetime.utcnow(),
                },
            )
            session.commit()
            logger.debug(
                f"Tracked API call {call_id}: {project_id} | {operation} | "
                f"{input_tokens}in + {output_tokens}out = ${cost:.4f}"
            )
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to record API call ({exc})")
            with suppress(Exception):
                session.rollback()
        finally:
            with suppress(Exception):
                session.close()

        # Check budget alert (best-effort; opens its own session)
        self._check_budget_alert(project_id)

        return cost

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> float:
        """Calculate cost for token usage

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            cache_creation_tokens: Cache write tokens
            cache_read_tokens: Cache read tokens

        Returns:
            Cost in USD
        """
        if model not in MODEL_PRICING:
            logger.warning(f"Unknown model '{model}', using Sonnet pricing")
            model = "claude-3-5-sonnet-20241022"

        pricing = MODEL_PRICING[model]

        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + (cache_creation_tokens / 1_000_000) * pricing["cache_write"]
            + (cache_read_tokens / 1_000_000) * pricing["cache_read"]
        )

        return cost

    def get_project_cost(self, project_id: str) -> ProjectCost:
        """Get cost summary for a project

        Args:
            project_id: Project identifier

        Returns:
            ProjectCost object with aggregated statistics
        """
        empty = ProjectCost(
            project_id=project_id,
            total_calls=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cache_creation_tokens=0,
            total_cache_read_tokens=0,
            total_cost=0.0,
            first_call=datetime.now(),
            last_call=datetime.now(),
        )

        session = _open_session()
        if session is None:
            return empty

        try:
            row = session.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_calls,
                        SUM(input_tokens) AS total_input,
                        SUM(output_tokens) AS total_output,
                        SUM(cache_creation_tokens) AS total_cache_creation,
                        SUM(cache_read_tokens) AS total_cache_read,
                        SUM(cost) AS total_cost,
                        MIN(timestamp) AS first_call,
                        MAX(timestamp) AS last_call
                    FROM api_calls
                    WHERE project_id = :project_id
                    """
                ),
                {"project_id": project_id},
            ).fetchone()
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to read project cost ({exc})")
            return empty
        finally:
            with suppress(Exception):
                session.close()

        if not row or not row[0]:
            return empty

        return ProjectCost(
            project_id=project_id,
            total_calls=row[0],
            total_input_tokens=row[1] or 0,
            total_output_tokens=row[2] or 0,
            total_cache_creation_tokens=row[3] or 0,
            total_cache_read_tokens=row[4] or 0,
            total_cost=row[5] or 0.0,
            first_call=_as_dt(row[6]),
            last_call=_as_dt(row[7]),
        )

    def get_project_calls(self, project_id: str) -> List[APICall]:
        """Get all API calls for a project

        Args:
            project_id: Project identifier

        Returns:
            List of APICall objects
        """
        session = _open_session()
        if session is None:
            return []

        try:
            rows = session.execute(
                text(
                    """
                    SELECT
                        call_id, project_id, operation, model,
                        input_tokens, output_tokens,
                        cache_creation_tokens, cache_read_tokens,
                        cost, timestamp
                    FROM api_calls
                    WHERE project_id = :project_id
                    ORDER BY timestamp DESC, call_id DESC
                    """
                ),
                {"project_id": project_id},
            ).fetchall()
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to read project calls ({exc})")
            return []
        finally:
            with suppress(Exception):
                session.close()

        return [
            APICall(
                call_id=row[0],
                project_id=row[1],
                operation=row[2],
                model=row[3],
                input_tokens=row[4],
                output_tokens=row[5],
                cache_creation_tokens=row[6],
                cache_read_tokens=row[7],
                cost=row[8],
                timestamp=_as_dt(row[9]),
            )
            for row in rows
        ]

    def get_all_projects(self) -> List[str]:
        """Get list of all tracked projects

        Returns:
            List of project IDs
        """
        session = _open_session()
        if session is None:
            return []

        try:
            rows = session.execute(
                text(
                    """
                    SELECT project_id, MAX(timestamp) AS last_call
                    FROM api_calls
                    GROUP BY project_id
                    ORDER BY last_call DESC
                    """
                )
            ).fetchall()
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to list projects ({exc})")
            return []
        finally:
            with suppress(Exception):
                session.close()

        return [row[0] for row in rows]

    def get_total_costs(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get total costs across all projects

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with aggregated statistics
        """
        zeros = {
            "total_projects": 0,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "avg_cost_per_project": 0.0,
        }

        session = _open_session()
        if session is None:
            return zeros

        where_clause = []
        params: Dict[str, Any] = {}
        if start_date:
            where_clause.append("timestamp >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where_clause.append("timestamp <= :end_date")
            params["end_date"] = end_date
        where_sql = "WHERE " + " AND ".join(where_clause) if where_clause else ""

        try:
            row = session.execute(
                text(  # nosec B608 - where_sql is built from fixed fragments, values are bound params
                    f"""
                    SELECT
                        COUNT(DISTINCT project_id) AS total_projects,
                        COUNT(*) AS total_calls,
                        SUM(input_tokens) AS total_input,
                        SUM(output_tokens) AS total_output,
                        SUM(cost) AS total_cost
                    FROM api_calls
                    {where_sql}
                    """
                ),
                params,
            ).fetchone()
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to read total costs ({exc})")
            return zeros
        finally:
            with suppress(Exception):
                session.close()

        return {
            "total_projects": row[0] or 0,
            "total_calls": row[1] or 0,
            "total_input_tokens": row[2] or 0,
            "total_output_tokens": row[3] or 0,
            "total_cost": row[4] or 0.0,
            "avg_cost_per_project": (row[4] or 0.0) / (row[0] or 1),
        }

    def set_budget_alert(self, project_id: str, budget_limit: float, alert_threshold: float = 0.8):
        """Set budget alert for a project

        Args:
            project_id: Project identifier
            budget_limit: Budget limit in USD
            alert_threshold: Threshold to trigger alert (0.0-1.0, default 0.8 = 80%)
        """
        session = _open_session()
        if session is None:
            return

        try:
            # Upsert on project_id (works on both SQLite 3.24+ and PostgreSQL).
            session.execute(
                text(
                    """
                    INSERT INTO budget_alerts
                        (alert_id, project_id, budget_limit, alert_threshold, enabled)
                    VALUES (:alert_id, :project_id, :budget_limit, :alert_threshold, 1)
                    ON CONFLICT (project_id) DO UPDATE SET
                        budget_limit = excluded.budget_limit,
                        alert_threshold = excluded.alert_threshold,
                        enabled = 1
                    """
                ),
                {
                    "alert_id": uuid.uuid4().hex,
                    "project_id": project_id,
                    "budget_limit": budget_limit,
                    "alert_threshold": alert_threshold,
                },
            )
            session.commit()
            logger.info(
                f"Budget alert set for {project_id}: "
                f"${budget_limit:.2f} (alert at {alert_threshold*100:.0f}%)"
            )
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to set budget alert ({exc})")
            with suppress(Exception):
                session.rollback()
        finally:
            with suppress(Exception):
                session.close()

    def _check_budget_alert(self, project_id: str):
        """Check if project has exceeded budget alert threshold"""
        session = _open_session()
        if session is None:
            return

        try:
            row = session.execute(
                text(
                    """
                    SELECT budget_limit, alert_threshold
                    FROM budget_alerts
                    WHERE project_id = :project_id AND enabled = 1
                    """
                ),
                {"project_id": project_id},
            ).fetchone()
        except Exception as exc:
            logger.warning(f"Cost tracker: failed to read budget alert ({exc})")
            return
        finally:
            with suppress(Exception):
                session.close()

        if not row:
            return  # No alert set

        budget_limit, alert_threshold = row[0], row[1]

        # Get current cost
        project_cost = self.get_project_cost(project_id)
        current_cost = project_cost.total_cost

        # Check threshold
        if current_cost >= budget_limit * alert_threshold:
            percent = (current_cost / budget_limit) * 100
            logger.warning(
                f"⚠️  BUDGET ALERT: {project_id} has used ${current_cost:.2f} "
                f"of ${budget_limit:.2f} budget ({percent:.0f}%)"
            )

    def export_to_json(self, output_path: Path, project_id: Optional[str] = None):
        """Export cost data to JSON

        Args:
            output_path: Path to save JSON file
            project_id: Optional project to export (None = all projects)
        """
        data: Dict[str, Any]
        if project_id:
            calls = self.get_project_calls(project_id)
            data = {
                "project_id": project_id,
                "summary": self.get_project_cost(project_id).to_dict(),
                "calls": [call.to_dict() for call in calls],
            }
        else:
            projects = self.get_all_projects()
            data = {"total_summary": self.get_total_costs(), "projects": []}

            for proj_id in projects:
                data["projects"].append(
                    {
                        "project_id": proj_id,
                        "summary": self.get_project_cost(proj_id).to_dict(),
                    }
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Cost data exported to {output_path}")


# Singleton instance
_default_tracker: Optional[CostTracker] = None


def get_default_tracker() -> CostTracker:
    """Get or create default cost tracker instance"""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = CostTracker()
    return _default_tracker
