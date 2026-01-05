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
        model="claude-3-5-sonnet-20241022",
        input_tokens=1500,
        output_tokens=800
    )

    # Get project costs
    cost = tracker.get_project_cost("Client_20250101_120000")
    print(f"Total cost: ${cost:.2f}")
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import logger

# Model pricing (as of Dec 2025)
# Source: https://www.anthropic.com/pricing
MODEL_PRICING = {
    "claude-3-5-sonnet-20241022": {
        "input": 0.003,  # $3 per million input tokens
        "output": 0.015,  # $15 per million output tokens
        "cache_write": 0.00375,  # $3.75 per million cache write tokens
        "cache_read": 0.0003,  # $0.30 per million cache read tokens
    },
    "claude-3-5-sonnet-latest": {
        "input": 0.003,
        "output": 0.015,
        "cache_write": 0.00375,
        "cache_read": 0.0003,
    },
    "claude-3-opus-20240229": {
        "input": 0.015,
        "output": 0.075,
        "cache_write": 0.01875,
        "cache_read": 0.0015,
    },
    "claude-3-haiku-20240307": {
        "input": 0.00025,
        "output": 0.00125,
        "cache_write": 0.0003,
        "cache_read": 0.00003,
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
        """Initialize cost tracker

        Args:
            db_path: Path to SQLite database (default: data/cost_tracking.db)
        """
        if db_path is None:
            db_path = Path("data/cost_tracking.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()
        logger.debug(f"Cost tracker initialized: {self.db_path}")

    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # API calls table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_calls (
                call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cache_creation_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cost REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_id ON api_calls(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON api_calls(timestamp)")

        # Budget alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                budget_limit REAL NOT NULL,
                alert_threshold REAL DEFAULT 0.8,
                enabled INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(project_id)
            )
        """
        )

        conn.commit()
        conn.close()

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

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO api_calls (
                project_id, operation, model,
                input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens,
                cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                operation,
                model,
                input_tokens,
                output_tokens,
                cache_creation_tokens,
                cache_read_tokens,
                cost,
            ),
        )

        call_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.debug(
            f"Tracked API call {call_id}: {project_id} | {operation} | "
            f"{input_tokens}in + {output_tokens}out = ${cost:.4f}"
        )

        # Check budget alert
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_calls,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cache_creation_tokens) as total_cache_creation,
                SUM(cache_read_tokens) as total_cache_read,
                SUM(cost) as total_cost,
                MIN(timestamp) as first_call,
                MAX(timestamp) as last_call
            FROM api_calls
            WHERE project_id = ?
        """,
            (project_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row or row[0] == 0:
            # No calls for this project
            return ProjectCost(
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

        return ProjectCost(
            project_id=project_id,
            total_calls=row[0],
            total_input_tokens=row[1] or 0,
            total_output_tokens=row[2] or 0,
            total_cache_creation_tokens=row[3] or 0,
            total_cache_read_tokens=row[4] or 0,
            total_cost=row[5] or 0.0,
            first_call=datetime.fromisoformat(row[6]),
            last_call=datetime.fromisoformat(row[7]),
        )

    def get_project_calls(self, project_id: str) -> List[APICall]:
        """Get all API calls for a project

        Args:
            project_id: Project identifier

        Returns:
            List of APICall objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                call_id, project_id, operation, model,
                input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens,
                cost, timestamp
            FROM api_calls
            WHERE project_id = ?
            ORDER BY timestamp DESC, call_id DESC
        """,
            (project_id,),
        )

        calls = []
        for row in cursor.fetchall():
            calls.append(
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
                    timestamp=datetime.fromisoformat(row[9]),
                )
            )

        conn.close()
        return calls

    def get_all_projects(self) -> List[str]:
        """Get list of all tracked projects

        Returns:
            List of project IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT project_id
            FROM api_calls
            ORDER BY MAX(timestamp) DESC
        """
        )

        projects = [row[0] for row in cursor.fetchall()]
        conn.close()

        return projects

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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        where_clause = []
        params = []

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date.isoformat())
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date.isoformat())

        where_sql = "WHERE " + " AND ".join(where_clause) if where_clause else ""

        cursor.execute(
            f"""
            SELECT
                COUNT(DISTINCT project_id) as total_projects,
                COUNT(*) as total_calls,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cost) as total_cost
            FROM api_calls
            {where_sql}
        """,
            params,
        )

        row = cursor.fetchone()
        conn.close()

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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO budget_alerts
            (project_id, budget_limit, alert_threshold, enabled)
            VALUES (?, ?, ?, 1)
        """,
            (project_id, budget_limit, alert_threshold),
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Budget alert set for {project_id}: "
            f"${budget_limit:.2f} (alert at {alert_threshold*100:.0f}%)"
        )

    def _check_budget_alert(self, project_id: str):
        """Check if project has exceeded budget alert threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get budget alert settings
        cursor.execute(
            """
            SELECT budget_limit, alert_threshold
            FROM budget_alerts
            WHERE project_id = ? AND enabled = 1
        """,
            (project_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return  # No alert set

        budget_limit, alert_threshold = row

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
