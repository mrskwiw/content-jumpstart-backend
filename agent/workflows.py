"""
Multi-step workflow definitions for common operations
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStage(str, Enum):
    """Stages in a workflow"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowDefinition:
    """Base class for workflow definitions"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []

    def add_step(
        self,
        step_id: str,
        description: str,
        tool: str,
        params: Dict[str, Any],
        required: bool = True,
    ):
        """Add a step to the workflow"""
        self.steps.append(
            {
                "step_id": step_id,
                "description": description,
                "tool": tool,
                "params": params,
                "required": required,
                "status": WorkflowStage.NOT_STARTED,
            }
        )

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """Get the next step to execute"""
        for step in self.steps:
            if step["status"] == WorkflowStage.NOT_STARTED:
                return step
        return None

    def mark_step_complete(self, step_id: str):
        """Mark a step as completed"""
        for step in self.steps:
            if step["step_id"] == step_id:
                step["status"] = WorkflowStage.COMPLETED
                break

    def mark_step_failed(self, step_id: str, error: str):
        """Mark a step as failed"""
        for step in self.steps:
            if step["step_id"] == step_id:
                step["status"] = WorkflowStage.FAILED
                step["error"] = error
                break

    def is_complete(self) -> bool:
        """Check if all required steps are complete"""
        for step in self.steps:
            if step["required"] and step["status"] != WorkflowStage.COMPLETED:
                return False
        return True

    def get_progress(self) -> float:
        """Get workflow progress (0.0-1.0)"""
        if not self.steps:
            return 0.0

        completed = sum(1 for step in self.steps if step["status"] == WorkflowStage.COMPLETED)
        return completed / len(self.steps)


# ============================================================================
# WORKFLOW TEMPLATES
# ============================================================================


def create_onboarding_workflow(
    client_name: str, brief_path: Optional[str] = None
) -> WorkflowDefinition:
    """Create client onboarding workflow"""
    workflow = WorkflowDefinition(
        name="client_onboarding", description=f"Onboard new client: {client_name}"
    )

    if not brief_path:
        workflow.add_step(
            step_id="create_brief",
            description="Create client brief interactively",
            tool="interactive_brief",
            params={"client_name": client_name},
            required=True,
        )

    workflow.add_step(
        step_id="upload_samples",
        description="Upload voice samples (optional)",
        tool="upload_voice_samples",
        params={"client_name": client_name},
        required=False,
    )

    workflow.add_step(
        step_id="generate_posts",
        description="Generate 30 posts",
        tool="generate_posts",
        params={
            "client_name": client_name,
            "brief_path": brief_path or f"data/briefs/{client_name}_brief.txt",
            "num_posts": 30,
        },
        required=True,
    )

    workflow.add_step(
        step_id="review_qa",
        description="Review QA report",
        tool="display_qa_report",
        params={},
        required=True,
    )

    workflow.add_step(
        step_id="send_deliverable",
        description="Send deliverable to client",
        tool="send_deliverable",
        params={"client_name": client_name},
        required=True,
    )

    return workflow


def create_revision_workflow(
    client_name: str, project_id: str, revision_request: str
) -> WorkflowDefinition:
    """Create revision workflow"""
    workflow = WorkflowDefinition(
        name="revision_processing", description=f"Process revision for {client_name}"
    )

    workflow.add_step(
        step_id="read_request",
        description="Parse revision request",
        tool="read_file",
        params={"file_path": revision_request},
        required=True,
    )

    workflow.add_step(
        step_id="regenerate",
        description="Regenerate requested posts",
        tool="process_revision",
        params={"client_name": client_name, "project_id": project_id},
        required=True,
    )

    workflow.add_step(
        step_id="qa_check",
        description="Quality check revised posts",
        tool="validate_posts",
        params={},
        required=True,
    )

    workflow.add_step(
        step_id="send_revision",
        description="Send revised deliverable",
        tool="send_deliverable",
        params={"client_name": client_name},
        required=True,
    )

    return workflow


def create_feedback_collection_workflow(client_name: str, project_id: str) -> WorkflowDefinition:
    """Create feedback collection workflow"""
    workflow = WorkflowDefinition(
        name="feedback_collection", description=f"Collect feedback from {client_name}"
    )

    workflow.add_step(
        step_id="collect_post_feedback",
        description="Collect post-level feedback",
        tool="collect_feedback",
        params={"client_name": client_name, "project_id": project_id},
        required=True,
    )

    workflow.add_step(
        step_id="collect_satisfaction",
        description="Collect satisfaction survey",
        tool="collect_satisfaction",
        params={"client_name": client_name, "project_id": project_id},
        required=True,
    )

    workflow.add_step(
        step_id="analyze_feedback",
        description="Analyze feedback patterns",
        tool="analyze_feedback",
        params={"client_name": client_name},
        required=False,
    )

    return workflow


def create_batch_processing_workflow(items: List[Dict[str, Any]]) -> WorkflowDefinition:
    """Create batch processing workflow for multiple pending items"""
    workflow = WorkflowDefinition(
        name="batch_processing", description=f"Process {len(items)} pending items"
    )

    for idx, item in enumerate(items):
        workflow.add_step(
            step_id=f"item_{idx}",
            description=item.get("description", f"Process item {idx}"),
            tool=item.get("tool", "unknown"),
            params=item.get("params", {}),
            required=True,
        )

    return workflow


# ============================================================================
# WORKFLOW EXECUTOR
# ============================================================================


class WorkflowExecutor:
    """Executes workflows step by step"""

    def __init__(self, agent_tools):
        self.tools = agent_tools

    async def execute_workflow(
        self, workflow: WorkflowDefinition, on_step_complete=None, on_step_failed=None
    ) -> Dict[str, Any]:
        """Execute a workflow step by step"""
        results = []

        while not workflow.is_complete():
            step = workflow.get_next_step()
            if not step:
                break

            # Update status
            step["status"] = WorkflowStage.IN_PROGRESS

            try:
                # Get tool method
                tool_method = getattr(self.tools, step["tool"], None)
                if not tool_method:
                    raise Exception(f"Tool not found: {step['tool']}")

                # Execute tool
                result = await tool_method(**step["params"])

                if result.get("success"):
                    workflow.mark_step_complete(step["step_id"])
                    results.append(result)

                    if on_step_complete:
                        on_step_complete(step, result)
                else:
                    error = result.get("error", "Unknown error")
                    workflow.mark_step_failed(step["step_id"], error)

                    if on_step_failed:
                        on_step_failed(step, error)

                    # Stop if required step fails
                    if step["required"]:
                        break

            except Exception as e:
                error = str(e)
                workflow.mark_step_failed(step["step_id"], error)

                if on_step_failed:
                    on_step_failed(step, error)

                # Stop if required step fails
                if step["required"]:
                    break

        return {
            "workflow": workflow.name,
            "completed": workflow.is_complete(),
            "progress": workflow.get_progress(),
            "results": results,
        }
