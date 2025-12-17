"""
Enhanced agent core with Week 2 intelligence features:
- Workflow planning
- Proactive suggestions
- Batch operations
- Error recovery
- Scheduling
- Email integration
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import anthropic

from .context import ContextManager, ConversationContext
from .email_system import EmailSystem
from .error_recovery import ErrorRecoverySystem, RetryConfig

# Week 2 imports
from .planner import TaskType, WorkflowPlan, WorkflowPlanner
from .prompts import AGENT_SYSTEM_PROMPT, build_conversation_context_prompt, get_tool_descriptions
from .scheduler import TaskScheduler
from .suggestions import Suggestion, SuggestionEngine
from .tools import AgentTools
from .workflows import WorkflowExecutor


class AgentResponse:
    """Response from the agent"""

    def __init__(
        self,
        message: str,
        tool_calls: Optional[List[Dict]] = None,
        context_updates: Optional[Dict] = None,
        workflow_plan: Optional[WorkflowPlan] = None,
        suggestions: Optional[List[Suggestion]] = None,
    ):
        self.message = message
        self.tool_calls = tool_calls or []
        self.context_updates = context_updates or {}
        self.workflow_plan = workflow_plan
        self.suggestions = suggestions or []


class ContentAgentCoreEnhanced:
    """Enhanced agent orchestrator with intelligence features"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        session_id: Optional[str] = None,
    ):
        # Core components (Week 1)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.tools = AgentTools()
        self.workflow_executor = WorkflowExecutor(self.tools)
        self.context_manager = ContextManager()

        # Intelligence components (Week 2)
        self.planner = WorkflowPlanner()
        self.suggestion_engine = SuggestionEngine(db=self.tools.db)
        self.error_recovery = ErrorRecoverySystem()
        self.scheduler = TaskScheduler()
        self.email_system = EmailSystem()

        # Initialize or load session
        if session_id and self.context_manager.load_context(session_id):
            self.context = self.context_manager.load_context(session_id)
            # Load conversation history from database
            self.messages = self._load_messages_from_db()
        else:
            self.context = ConversationContext(session_id=session_id or str(uuid.uuid4()))
            # Conversation history
            self.messages: List[Dict[str, Any]] = []

        # Current workflow execution
        self.current_workflow: Optional[WorkflowPlan] = None
        self.completed_task_ids: List[str] = []

    async def handle_message(self, user_message: str) -> AgentResponse:
        """
        Process user message with intelligence features

        Enhanced with:
        - Proactive suggestions check
        - Workflow planning
        - Error recovery
        - Batch operation detection
        """
        # Check for proactive suggestions on startup
        suggestions = []
        if len(self.messages) == 0:  # First message
            suggestions = self.suggestion_engine.generate_suggestions()

        # Check for special commands
        if user_message.lower() in ["what needs my attention?", "what's pending?", "daily summary"]:
            summary = self.suggestion_engine.get_daily_summary()
            return AgentResponse(message=summary, suggestions=suggestions)

        if user_message.lower() in ["show scheduled tasks", "what's scheduled?"]:
            summary = self.scheduler.get_task_summary()
            return AgentResponse(message=summary)

        # Check for batch operation intent
        if "all pending" in user_message.lower() or "batch" in user_message.lower():
            return await self._handle_batch_operations()

        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Save user message to database
        self._save_message_to_db("user", user_message)

        # Build system prompt with tools and context
        system_prompt = self._build_enhanced_system_prompt()

        # Call Claude API with tool use and error recovery
        success, response_obj, error_record = await self.error_recovery.execute_with_retry_async(
            func=lambda: self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=self.messages,
                tools=self._get_enhanced_tool_definitions(),
                temperature=0.7,
            ),
            config=RetryConfig(max_retries=3),
            context={"operation": "api_call", "user_message": user_message[:100]},
        )

        if not success:
            error_prompt = self.error_recovery.format_recovery_prompt(error_record)
            return AgentResponse(message=error_prompt)

        response = response_obj

        # Process response
        assistant_message = {"role": "assistant", "content": []}
        tool_calls = []

        for content_block in response.content:
            if content_block.type == "text":
                assistant_message["content"].append(content_block)
            elif content_block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    }
                )
                assistant_message["content"].append(content_block)

        self.messages.append(assistant_message)

        # Save assistant message to database
        self._save_message_to_db("assistant", assistant_message["content"])

        # Execute tools with error recovery if requested
        if tool_calls:
            tool_results = await self._execute_tool_calls_with_recovery(tool_calls)

            # Add tool results to messages
            tool_result_messages = []
            for result in tool_results:
                tool_result_messages.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result["tool_use_id"],
                        "content": result["content"],
                    }
                )

            self.messages.append({"role": "user", "content": tool_result_messages})

            # Get follow-up response from Claude
            follow_up = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=self.messages,
                temperature=0.7,
            )

            response_text = self._extract_text_from_response(follow_up)
            self.messages.append({"role": "assistant", "content": follow_up.content})

            # Save follow-up assistant message to database
            self._save_message_to_db("assistant", follow_up.content)
        else:
            response_text = self._extract_text_from_response(response)

        # Update context
        self.context.add_action(
            {
                "timestamp": datetime.now().isoformat(),
                "description": user_message[:100],
                "tool_calls": len(tool_calls),
            }
        )

        # Save context
        self.context_manager.save_context(self.context)

        return AgentResponse(message=response_text, tool_calls=tool_calls, suggestions=suggestions)

    async def _handle_batch_operations(self) -> AgentResponse:
        """Handle batch operation requests"""
        # Get pending items from database
        pending_feedback = []
        pending_revisions = []
        pending_deliverables = []
        overdue_invoices = []

        # Query database for pending items
        try:
            with self.tools.db._get_connection() as conn:
                cursor = conn.cursor()

                # Get projects missing feedback (>2 weeks old)
                cursor.execute(
                    """
                    SELECT DISTINCT client_name
                    FROM client_history
                    WHERE feedback_count = 0
                    AND created_at < ?
                """,
                    ((datetime.now() - timedelta(weeks=2)).isoformat(),),
                )
                pending_feedback = [row[0] for row in cursor.fetchall()]

        except Exception:
            pass

        # Create batch workflow plan
        workflow_plan = self.planner.plan_batch_operations(
            pending_feedback=pending_feedback,
            pending_revisions=pending_revisions,
            pending_deliverables=pending_deliverables,
            overdue_invoices=overdue_invoices,
        )

        # Return plan for user approval
        return AgentResponse(message=workflow_plan.to_summary(), workflow_plan=workflow_plan)

    async def _execute_tool_calls_with_recovery(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls with error recovery"""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]

            # Execute with retry logic
            success, result, error_record = await self.error_recovery.execute_with_retry_async(
                func=lambda: self._execute_single_tool(tool_name, tool_input),
                config=RetryConfig(max_retries=3),
                context={"tool": tool_name, "input": tool_input},
            )

            if success:
                results.append({"tool_use_id": tool_call["id"], "content": str(result)})
            else:
                results.append(
                    {
                        "tool_use_id": tool_call["id"],
                        "content": str(
                            {
                                "success": False,
                                "error": error_record.message if error_record else "Unknown error",
                            }
                        ),
                    }
                )

        return results

    async def _execute_single_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a single tool"""
        tool_method = getattr(self.tools, tool_name, None)

        if not tool_method:
            raise ValueError(f"Tool not found: {tool_name}")

        if asyncio.iscoroutinefunction(tool_method):
            return await tool_method(**tool_input)
        else:
            return tool_method(**tool_input)

    def plan_workflow(self, intent: str, context: Dict[str, Any]) -> WorkflowPlan:
        """
        Create intelligent workflow plan based on user intent

        Examples:
        - "Onboard new client Acme Corp" -> onboarding workflow
        - "Process all pending tasks" -> batch workflow
        - "Generate posts for ClientX" -> simple workflow
        """
        # Detect workflow type from intent
        if "onboard" in intent.lower():
            client_name = context.get("client_name", "Unknown Client")
            return self.planner.plan_onboarding_workflow(
                client_name=client_name,
                has_brief=context.get("has_brief", False),
                has_voice_samples=context.get("has_voice_samples", False),
            )

        elif "batch" in intent.lower() or "all pending" in intent.lower():
            return self.planner.plan_batch_operations(
                pending_feedback=context.get("pending_feedback", []),
                pending_revisions=context.get("pending_revisions", []),
                pending_deliverables=context.get("pending_deliverables", []),
                overdue_invoices=context.get("overdue_invoices", []),
            )

        else:
            # Simple single-tool workflow
            tool_name = context.get("tool_name", "generate_posts")
            tool_params = context.get("tool_params", {})
            task_type = context.get("task_type", TaskType.GENERATE_POSTS)

            return self.planner.plan_simple_workflow(
                intent=intent, tool_name=tool_name, tool_params=tool_params, task_type=task_type
            )

    async def execute_workflow(self, workflow_plan: WorkflowPlan) -> Dict[str, Any]:
        """Execute a complete workflow plan"""
        self.current_workflow = workflow_plan
        self.completed_task_ids = []

        results = {
            "plan_id": workflow_plan.plan_id,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "task_results": [],
        }

        while True:
            next_task = workflow_plan.get_next_executable_task(self.completed_task_ids)

            if not next_task:
                break  # All tasks completed

            # Execute task with error recovery
            success, result, error_record = await self.error_recovery.execute_with_retry_async(
                func=lambda: self._execute_single_tool(next_task.tool_name, next_task.tool_params),
                config=RetryConfig(
                    max_retries=next_task.max_retries if next_task.retry_on_failure else 0
                ),
                context={"task_id": next_task.task_id, "task_type": next_task.task_type},
            )

            if success:
                self.completed_task_ids.append(next_task.task_id)
                results["completed_tasks"] += 1
                results["task_results"].append(
                    {"task_id": next_task.task_id, "success": True, "result": result}
                )
            else:
                results["failed_tasks"] += 1
                results["task_results"].append(
                    {
                        "task_id": next_task.task_id,
                        "success": False,
                        "error": error_record.message if error_record else "Unknown error",
                    }
                )

                # Check if we can continue after failure
                if not next_task.can_fail:
                    break  # Stop workflow execution

        return results

    def _build_enhanced_system_prompt(self) -> str:
        """Build system prompt with intelligence features"""
        # Get tool descriptions
        available_tools = self.tools.get_available_tools()
        tool_desc = get_tool_descriptions(available_tools)

        # Build base prompt
        prompt = AGENT_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)

        # Add conversation context
        context_info = build_conversation_context_prompt(self.context)
        if context_info:
            prompt += "\n\n" + context_info

        # Add Week 2 intelligence guidance
        prompt += """

INTELLIGENCE FEATURES (Week 2):

You now have enhanced capabilities:

1. **Workflow Planning**: When you detect multi-step requests, use the plan_workflow method to create execution plans.
   Ask user for approval before executing complex workflows.

2. **Proactive Suggestions**: On startup, check for pending items and suggest actions:
   - Missing feedback (>2 weeks old)
   - Overdue invoices
   - Pending deliverables
   - Client milestones

3. **Batch Operations**: When user says "process all pending" or "handle urgent items",
   detect all pending work and create batch workflow.

4. **Error Recovery**: API failures, timeouts, and network errors are automatically retried
   with exponential backoff. You'll be notified if max retries exhausted.

5. **Scheduling**: You can schedule future tasks using the scheduler.

6. **Email Integration**: You can send deliverables, reminders, and invoices via email.

Always be proactive and suggest next actions based on context.
"""

        return prompt

    def _get_enhanced_tool_definitions(self) -> List[Dict]:
        """
        Get enhanced tool definitions including ALL available tools

        Dynamically generates Claude function calling schemas from AgentTools
        """
        # Get all available tools from AgentTools
        available_tools = self.tools.get_available_tools()

        # Convert to Claude function calling format
        tool_definitions = []

        for tool in available_tools:
            # Parse parameters string to create schema
            params_str = tool.get("parameters", "")
            properties = {}
            required = []

            if params_str:
                # Simple parameter parsing: "param1, param2 (optional), param3 (default value)"
                for param in params_str.split(","):
                    param = param.strip()

                    # Check if optional or has default
                    is_optional = "(optional)" in param or "(default" in param
                    param_name = param.split("(")[0].strip()

                    # Add to schema
                    properties[param_name] = {"type": "string"}

                    if not is_optional:
                        required.append(param_name)

            # Create tool definition
            tool_def = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": {"type": "object", "properties": properties, "required": required},
            }

            tool_definitions.append(tool_def)

        # Add Week 2 special tools (scheduler and email)
        tool_definitions.extend(
            [
                {
                    "name": "schedule_task",
                    "description": "Schedule a task for future execution",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "tool_name": {"type": "string"},
                            "tool_params": {"type": "object"},
                            "execute_in_minutes": {"type": "integer"},
                        },
                        "required": ["description", "tool_name", "tool_params"],
                    },
                },
                {
                    "name": "send_email",
                    "description": "Send an email (deliverable, reminder, invoice, etc.)",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "email_type": {"type": "string"},
                            "client_name": {"type": "string"},
                            "client_email": {"type": "string"},
                            "variables": {"type": "object"},
                        },
                        "required": ["email_type", "client_name", "client_email"],
                    },
                },
            ]
        )

        return tool_definitions

    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Claude response"""
        text_parts = []
        for content_block in response.content:
            if hasattr(content_block, "text"):
                text_parts.append(content_block.text)
        return "\n".join(text_parts)

    def reset_conversation(self):
        """Reset conversation history (keep session context)"""
        self.messages = []
        self.context.recent_actions = []
        self.context.pending_decisions = []
        self.context_manager.save_context(self.context)

    def _load_messages_from_db(self) -> List[Dict[str, Any]]:
        """Load conversation history from database when resuming session"""
        db_messages = self.context_manager.load_conversation(self.context.session_id)

        # Convert to Claude API format
        messages = []
        for msg in db_messages:
            # Skip messages with empty content (violates API requirement)
            content = msg.get("content", "")
            if not content or (isinstance(content, str) and not content.strip()):
                continue

            # Simple format for now - just role and content
            messages.append({"role": msg["role"], "content": content})

        return messages

    def _save_message_to_db(self, role: str, content: Any, metadata: Optional[Dict] = None):
        """Save a message to database"""
        # Extract text content if it's a complex message
        if isinstance(content, list):
            # Handle content blocks
            text_parts = []
            for block in content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
            content_text = "\n".join(text_parts) if text_parts else ""
        elif hasattr(content, "text"):
            content_text = content.text
        else:
            content_text = str(content) if content else ""

        # Don't save empty messages (violates API requirement)
        if not content_text or not content_text.strip():
            return

        # Save to database
        self.context_manager.save_message(
            session_id=self.context.session_id, role=role, content=content_text, metadata=metadata
        )

    def export_conversation(self, output_path: Optional[str] = None) -> str:
        """
        Export current conversation to markdown format

        Args:
            output_path: Optional file path to save markdown to

        Returns:
            Markdown-formatted conversation
        """
        from pathlib import Path

        if output_path:
            return self.context_manager.export_conversation_markdown(
                self.context.session_id, output_path=Path(output_path)
            )
        else:
            return self.context_manager.export_conversation_markdown(self.context.session_id)

    def search_conversation(self, query: str, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search conversation history for a query string

        Args:
            query: Search query
            role: Optional filter by role (user/assistant)

        Returns:
            List of matching messages
        """
        return self.context_manager.search_conversation(
            self.context.session_id, query=query, role=role
        )
