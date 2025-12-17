"""
Task scheduling system for delayed/scheduled execution
"""

import json
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScheduleFrequency(str, Enum):
    """Frequency options for recurring tasks"""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class TaskStatus(str, Enum):
    """Status of scheduled tasks"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask(BaseModel):
    """A task scheduled for future execution"""

    task_id: str
    description: str
    tool_name: str
    tool_params: Dict[str, Any]
    scheduled_for: datetime
    frequency: ScheduleFrequency = ScheduleFrequency.ONCE
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    execution_count: int = 0
    max_executions: Optional[int] = None  # For recurring tasks
    last_error: Optional[str] = None

    def should_execute_now(self) -> bool:
        """Check if task should be executed now"""
        if self.status not in [TaskStatus.PENDING]:
            return False

        now = datetime.now()
        execution_time = self.next_execution or self.scheduled_for
        return now >= execution_time

    def calculate_next_execution(self) -> Optional[datetime]:
        """Calculate next execution time for recurring tasks"""
        if self.frequency == ScheduleFrequency.ONCE:
            return None

        base_time = self.executed_at or datetime.now()

        if self.frequency == ScheduleFrequency.DAILY:
            return base_time + timedelta(days=1)
        elif self.frequency == ScheduleFrequency.WEEKLY:
            return base_time + timedelta(weeks=1)
        elif self.frequency == ScheduleFrequency.BIWEEKLY:
            return base_time + timedelta(weeks=2)
        elif self.frequency == ScheduleFrequency.MONTHLY:
            return base_time + timedelta(days=30)

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary"""
        # Convert ISO strings to datetime
        for field in ["scheduled_for", "created_at", "executed_at", "next_execution"]:
            if field in data and data[field] and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)


class TaskScheduler:
    """Manages scheduled task execution"""

    def __init__(self, db_path: str = "data/agent_scheduled_tasks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.task_id_counter = 0

    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Initialize database schema"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_params TEXT NOT NULL,
                    scheduled_for TIMESTAMP NOT NULL,
                    frequency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    executed_at TIMESTAMP,
                    next_execution TIMESTAMP,
                    execution_count INTEGER DEFAULT 0,
                    max_executions INTEGER,
                    last_error TEXT
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_scheduled_for
                ON scheduled_tasks(scheduled_for)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON scheduled_tasks(status)
            """
            )
            conn.commit()
        finally:
            conn.close()

    def schedule_task(
        self,
        description: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        execute_in: Optional[timedelta] = None,
        execute_at: Optional[datetime] = None,
        frequency: ScheduleFrequency = ScheduleFrequency.ONCE,
        max_executions: Optional[int] = None,
    ) -> ScheduledTask:
        """Schedule a new task"""
        # Determine execution time
        if execute_at:
            scheduled_for = execute_at
        elif execute_in:
            scheduled_for = datetime.now() + execute_in
        else:
            scheduled_for = datetime.now()

        self.task_id_counter += 1
        task = ScheduledTask(
            task_id=f"scheduled_{int(datetime.now().timestamp())}_{self.task_id_counter}",
            description=description,
            tool_name=tool_name,
            tool_params=tool_params,
            scheduled_for=scheduled_for,
            frequency=frequency,
            max_executions=max_executions,
        )

        self._save_task(task)
        return task

    def _save_task(self, task: ScheduledTask):
        """Save task to database"""
        conn = self._get_connection()
        try:
            task.to_dict()
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_tasks
                (task_id, description, tool_name, tool_params, scheduled_for,
                 frequency, status, created_at, executed_at, next_execution,
                 execution_count, max_executions, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task.task_id,
                    task.description,
                    task.tool_name,
                    json.dumps(task.tool_params),
                    task.scheduled_for.isoformat(),
                    task.frequency.value,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.executed_at.isoformat() if task.executed_at else None,
                    task.next_execution.isoformat() if task.next_execution else None,
                    task.execution_count,
                    task.max_executions,
                    task.last_error,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get all tasks due for execution"""
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """
                SELECT * FROM scheduled_tasks
                WHERE status = ?
                AND (next_execution IS NULL AND scheduled_for <= ?)
                OR (next_execution IS NOT NULL AND next_execution <= ?)
                ORDER BY scheduled_for ASC
            """,
                (TaskStatus.PENDING.value, now, now),
            )

            tasks = []
            for row in cursor.fetchall():
                task_dict = {
                    "task_id": row[0],
                    "description": row[1],
                    "tool_name": row[2],
                    "tool_params": json.loads(row[3]),
                    "scheduled_for": row[4],
                    "frequency": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "executed_at": row[8],
                    "next_execution": row[9],
                    "execution_count": row[10],
                    "max_executions": row[11],
                    "last_error": row[12],
                }
                tasks.append(ScheduledTask.from_dict(task_dict))

            return tasks
        finally:
            conn.close()

    def mark_task_executed(self, task: ScheduledTask, success: bool, error: Optional[str] = None):
        """Mark task as executed and schedule next execution if recurring"""
        task.execution_count += 1
        task.executed_at = datetime.now()

        if not success:
            task.status = TaskStatus.FAILED
            task.last_error = error
        elif task.frequency == ScheduleFrequency.ONCE:
            task.status = TaskStatus.COMPLETED
        elif task.max_executions and task.execution_count >= task.max_executions:
            task.status = TaskStatus.COMPLETED
        else:
            # Recurring task - schedule next execution
            task.next_execution = task.calculate_next_execution()
            task.status = TaskStatus.PENDING

        self._save_task(task)

    def cancel_task(self, task_id: str):
        """Cancel a scheduled task"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE scheduled_tasks
                SET status = ?
                WHERE task_id = ?
            """,
                (TaskStatus.CANCELLED.value, task_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_upcoming_tasks(self, limit: int = 10) -> List[ScheduledTask]:
        """Get upcoming scheduled tasks"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM scheduled_tasks
                WHERE status = ?
                ORDER BY
                    CASE
                        WHEN next_execution IS NOT NULL THEN next_execution
                        ELSE scheduled_for
                    END ASC
                LIMIT ?
            """,
                (TaskStatus.PENDING.value, limit),
            )

            tasks = []
            for row in cursor.fetchall():
                task_dict = {
                    "task_id": row[0],
                    "description": row[1],
                    "tool_name": row[2],
                    "tool_params": json.loads(row[3]),
                    "scheduled_for": row[4],
                    "frequency": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "executed_at": row[8],
                    "next_execution": row[9],
                    "execution_count": row[10],
                    "max_executions": row[11],
                    "last_error": row[12],
                }
                tasks.append(ScheduledTask.from_dict(task_dict))

            return tasks
        finally:
            conn.close()

    def get_task_summary(self) -> str:
        """Get summary of scheduled tasks"""
        upcoming = self.get_upcoming_tasks(limit=5)

        if not upcoming:
            return "📅 No upcoming scheduled tasks"

        summary = "**Upcoming Scheduled Tasks:**\n\n"

        for i, task in enumerate(upcoming, 1):
            execution_time = task.next_execution or task.scheduled_for
            time_str = self._format_relative_time(execution_time)

            recurring_badge = ""
            if task.frequency != ScheduleFrequency.ONCE:
                recurring_badge = f" (🔄 {task.frequency.value})"

            summary += f"{i}. {task.description}{recurring_badge}\n"
            summary += f"   ⏰ {time_str}\n"
            summary += f"   🔧 Tool: {task.tool_name}\n\n"

        return summary

    @staticmethod
    def _format_relative_time(dt: datetime) -> str:
        """Format datetime as relative time"""
        now = datetime.now()
        delta = dt - now

        if delta.total_seconds() < 0:
            return "Overdue"
        elif delta.total_seconds() < 60:
            return "In a few seconds"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"In {minutes} minute{'s' if minutes > 1 else ''}"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"In {hours} hour{'s' if hours > 1 else ''}"
        elif delta.days == 1:
            return "Tomorrow"
        elif delta.days < 7:
            return f"In {delta.days} days"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"In {weeks} week{'s' if weeks > 1 else ''}"
        else:
            return dt.strftime("%B %d, %Y")
