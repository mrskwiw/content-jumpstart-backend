"""
Intelligent workflow planning for the agent
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks the agent can execute"""

    GENERATE_POSTS = "generate_posts"
    COLLECT_FEEDBACK = "collect_feedback"
    PROCESS_REVISION = "process_revision"
    SEND_DELIVERABLE = "send_deliverable"
    ANALYZE_VOICE = "analyze_voice"
    CREATE_INVOICE = "create_invoice"
    SEND_REMINDER = "send_reminder"
    REVIEW_QA = "review_qa"


class TaskPriority(str, Enum):
    """Task priority levels"""

    URGENT = "urgent"  # Overdue or critical
    HIGH = "high"  # Due today or this week
    NORMAL = "normal"  # Due later
    LOW = "low"  # No deadline


class PlannedTask(BaseModel):
    """A single task in a workflow plan"""

    task_id: str
    task_type: TaskType
    description: str
    tool_name: str
    tool_params: Dict[str, Any]
    estimated_duration_seconds: int
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: List[str] = Field(default_factory=list)  # Task IDs
    can_fail: bool = True  # Can workflow continue if this fails?
    retry_on_failure: bool = True
    max_retries: int = 3


class WorkflowPlan(BaseModel):
    """A complete execution plan for a user request"""

    plan_id: str
    intent: str  # Original user request
    tasks: List[PlannedTask]
    total_estimated_duration_seconds: int
    requires_confirmation: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[PlannedTask]:
        """Get all tasks of a specific priority"""
        return [t for t in self.tasks if t.priority == priority]

    def get_next_executable_task(self, completed_task_ids: List[str]) -> Optional[PlannedTask]:
        """Get next task that can be executed (all dependencies met)"""
        for task in self.tasks:
            if task.task_id in completed_task_ids:
                continue

            # Check if all dependencies are met
            if all(dep_id in completed_task_ids for dep_id in task.depends_on):
                return task

        return None

    def to_summary(self) -> str:
        """Convert plan to human-readable summary"""
        summary = f"**Workflow Plan:** {self.intent}\n\n"
        summary += f"**Estimated Time:** {self._format_duration(self.total_estimated_duration_seconds)}\n\n"
        summary += f"**Steps ({len(self.tasks)}):**\n"

        for i, task in enumerate(self.tasks, 1):
            emoji = self._get_task_emoji(task.task_type)
            duration = self._format_duration(task.estimated_duration_seconds)
            summary += f"{i}. {emoji} {task.description} (~{duration})\n"

            if task.depends_on:
                summary += f"   └─ Requires: {', '.join(f'Step {self.tasks.index(t)+1}' for t in self.tasks if t.task_id in task.depends_on)}\n"

        if self.requires_confirmation:
            summary += "\n**Proceed?** (Yes/No/Adjust)"

        return summary

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format duration in human-readable form"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

    @staticmethod
    def _get_task_emoji(task_type: TaskType) -> str:
        """Get emoji for task type"""
        emoji_map = {
            TaskType.GENERATE_POSTS: "🎨",
            TaskType.COLLECT_FEEDBACK: "📝",
            TaskType.PROCESS_REVISION: "🔄",
            TaskType.SEND_DELIVERABLE: "📦",
            TaskType.ANALYZE_VOICE: "🎤",
            TaskType.CREATE_INVOICE: "💰",
            TaskType.SEND_REMINDER: "📧",
            TaskType.REVIEW_QA: "✅",
        }
        return emoji_map.get(task_type, "📌")


class WorkflowPlanner:
    """Intelligent workflow planning system"""

    def __init__(self):
        # Task duration estimates (seconds)
        self.duration_estimates = {
            TaskType.GENERATE_POSTS: 60,
            TaskType.COLLECT_FEEDBACK: 10,
            TaskType.PROCESS_REVISION: 45,
            TaskType.SEND_DELIVERABLE: 5,
            TaskType.ANALYZE_VOICE: 20,
            TaskType.CREATE_INVOICE: 5,
            TaskType.SEND_REMINDER: 3,
            TaskType.REVIEW_QA: 10,
        }

    def plan_onboarding_workflow(
        self, client_name: str, has_brief: bool = False, has_voice_samples: bool = False
    ) -> WorkflowPlan:
        """Plan complete client onboarding workflow"""
        tasks = []
        task_id_counter = 0

        # Step 1: Parse or create brief (if needed)
        if not has_brief:
            task_id_counter += 1
            tasks.append(
                PlannedTask(
                    task_id=f"task_{task_id_counter}",
                    task_type=TaskType.ANALYZE_VOICE,  # Using analyze_voice as placeholder
                    description=f"Create client brief for {client_name}",
                    tool_name="create_brief",
                    tool_params={"client_name": client_name},
                    estimated_duration_seconds=300,  # 5 minutes interactive
                    priority=TaskPriority.HIGH,
                    can_fail=False,  # Must have brief
                )
            )

        # Step 2: Analyze voice samples (if provided)
        if has_voice_samples:
            task_id_counter += 1
            tasks.append(
                PlannedTask(
                    task_id=f"task_{task_id_counter}",
                    task_type=TaskType.ANALYZE_VOICE,
                    description="Analyze voice samples",
                    tool_name="analyze_voice_samples",
                    tool_params={"client_name": client_name},
                    estimated_duration_seconds=20,
                    priority=TaskPriority.NORMAL,
                    depends_on=[tasks[0].task_id] if not has_brief else [],
                )
            )

        # Step 3: Generate posts
        task_id_counter += 1
        generate_task_id = f"task_{task_id_counter}"
        tasks.append(
            PlannedTask(
                task_id=generate_task_id,
                task_type=TaskType.GENERATE_POSTS,
                description=f"Generate 30 posts for {client_name}",
                tool_name="generate_posts",
                tool_params={
                    "client_name": client_name,
                    "brief_path": f"data/briefs/{client_name}_brief.txt",
                    "num_posts": 30,
                },
                estimated_duration_seconds=60,
                priority=TaskPriority.HIGH,
                depends_on=[t.task_id for t in tasks],  # Depends on all previous
                can_fail=False,  # Critical step
            )
        )

        # Step 4: Review QA report
        task_id_counter += 1
        qa_task_id = f"task_{task_id_counter}"
        tasks.append(
            PlannedTask(
                task_id=qa_task_id,
                task_type=TaskType.REVIEW_QA,
                description="Review quality report",
                tool_name="get_project_status",
                tool_params={"client_name": client_name},
                estimated_duration_seconds=10,
                priority=TaskPriority.NORMAL,
                depends_on=[generate_task_id],
            )
        )

        # Step 5: Send deliverable
        task_id_counter += 1
        tasks.append(
            PlannedTask(
                task_id=f"task_{task_id_counter}",
                task_type=TaskType.SEND_DELIVERABLE,
                description="Send deliverable to client",
                tool_name="send_deliverable",
                tool_params={"client_name": client_name},
                estimated_duration_seconds=5,
                priority=TaskPriority.HIGH,
                depends_on=[qa_task_id],
            )
        )

        total_duration = sum(t.estimated_duration_seconds for t in tasks)

        return WorkflowPlan(
            plan_id=f"onboarding_{client_name}_{int(datetime.now().timestamp())}",
            intent=f"Onboard new client: {client_name}",
            tasks=tasks,
            total_estimated_duration_seconds=total_duration,
            requires_confirmation=True,
        )

    def plan_batch_operations(
        self,
        pending_feedback: List[str] = None,
        pending_revisions: List[str] = None,
        pending_deliverables: List[str] = None,
        overdue_invoices: List[str] = None,
    ) -> WorkflowPlan:
        """Plan batch processing of pending items"""
        tasks = []
        task_id_counter = 0

        # Group tasks by priority
        # 1. URGENT: Overdue invoices
        if overdue_invoices:
            for client in overdue_invoices:
                task_id_counter += 1
                tasks.append(
                    PlannedTask(
                        task_id=f"task_{task_id_counter}",
                        task_type=TaskType.SEND_REMINDER,
                        description=f"Send invoice reminder to {client}",
                        tool_name="send_email",
                        tool_params={"client_name": client, "email_type": "invoice_reminder"},
                        estimated_duration_seconds=3,
                        priority=TaskPriority.URGENT,
                        retry_on_failure=True,
                    )
                )

        # 2. HIGH: Pending revisions
        if pending_revisions:
            for client in pending_revisions:
                task_id_counter += 1
                tasks.append(
                    PlannedTask(
                        task_id=f"task_{task_id_counter}",
                        task_type=TaskType.PROCESS_REVISION,
                        description=f"Process revision for {client}",
                        tool_name="process_revision",
                        tool_params={"client_name": client},
                        estimated_duration_seconds=45,
                        priority=TaskPriority.HIGH,
                        retry_on_failure=True,
                        max_retries=2,
                    )
                )

        # 3. NORMAL: Pending deliverables
        if pending_deliverables:
            for client in pending_deliverables:
                task_id_counter += 1
                tasks.append(
                    PlannedTask(
                        task_id=f"task_{task_id_counter}",
                        task_type=TaskType.SEND_DELIVERABLE,
                        description=f"Send deliverable to {client}",
                        tool_name="send_deliverable",
                        tool_params={"client_name": client},
                        estimated_duration_seconds=5,
                        priority=TaskPriority.NORMAL,
                    )
                )

        # 4. LOW: Pending feedback collection
        if pending_feedback:
            for client in pending_feedback:
                task_id_counter += 1
                tasks.append(
                    PlannedTask(
                        task_id=f"task_{task_id_counter}",
                        task_type=TaskType.COLLECT_FEEDBACK,
                        description=f"Collect feedback from {client}",
                        tool_name="send_email",
                        tool_params={"client_name": client, "email_type": "feedback_request"},
                        estimated_duration_seconds=10,
                        priority=TaskPriority.LOW,
                    )
                )

        total_duration = sum(t.estimated_duration_seconds for t in tasks)

        return WorkflowPlan(
            plan_id=f"batch_{int(datetime.now().timestamp())}",
            intent="Process all pending tasks",
            tasks=tasks,
            total_estimated_duration_seconds=total_duration,
            requires_confirmation=True,
        )

    def plan_simple_workflow(
        self,
        intent: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        task_type: TaskType = TaskType.GENERATE_POSTS,
    ) -> WorkflowPlan:
        """Plan a simple single-tool workflow"""
        task = PlannedTask(
            task_id="task_1",
            task_type=task_type,
            description=intent,
            tool_name=tool_name,
            tool_params=tool_params,
            estimated_duration_seconds=self.duration_estimates.get(task_type, 30),
            priority=TaskPriority.NORMAL,
            can_fail=False,
        )

        return WorkflowPlan(
            plan_id=f"simple_{int(datetime.now().timestamp())}",
            intent=intent,
            tasks=[task],
            total_estimated_duration_seconds=task.estimated_duration_seconds,
            requires_confirmation=False,  # Simple tasks don't need confirmation
        )
