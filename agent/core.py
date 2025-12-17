"""
Core agent orchestrator - main conversation loop and intelligence
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic

from .context import ContextManager, ConversationContext
from .prompts import AGENT_SYSTEM_PROMPT, build_conversation_context_prompt, get_tool_descriptions
from .tools import AgentTools
from .workflows import WorkflowExecutor


class AgentResponse:
    """Response from the agent"""

    def __init__(
        self,
        message: str,
        tool_calls: Optional[List[Dict]] = None,
        context_updates: Optional[Dict] = None,
    ):
        self.message = message
        self.tool_calls = tool_calls or []
        self.context_updates = context_updates or {}


class ContentAgentCore:
    """Main agent orchestrator"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        session_id: Optional[str] = None,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.tools = AgentTools()
        self.workflow_executor = WorkflowExecutor(self.tools)
        self.context_manager = ContextManager()

        # Initialize or load session
        if session_id and self.context_manager.load_context(session_id):
            self.context = self.context_manager.load_context(session_id)
        else:
            self.context = ConversationContext(session_id=session_id or str(uuid.uuid4()))

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

    async def handle_message(self, user_message: str) -> AgentResponse:
        """
        Process user message and execute actions

        This is the main entry point for conversational interaction.
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Build system prompt with tools and context
        system_prompt = self._build_system_prompt()

        # Call Claude API with tool use
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=self.messages,
                tools=self._get_tool_definitions(),
                temperature=0.7,
            )

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

            # Execute tools if requested
            if tool_calls:
                tool_results = await self._execute_tool_calls(tool_calls)

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

            return AgentResponse(message=response_text, tool_calls=tool_calls)

        except Exception as e:
            error_message = f"❌ Error: {str(e)}\n\nI encountered an issue processing your request. Please try again or rephrase your question."
            return AgentResponse(message=error_message)

    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute multiple tool calls"""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]

            try:
                # Get tool method
                tool_method = getattr(self.tools, tool_name, None)

                if not tool_method:
                    result = {"success": False, "error": f"Tool not found: {tool_name}"}
                else:
                    # Execute tool
                    if asyncio.iscoroutinefunction(tool_method):
                        result = await tool_method(**tool_input)
                    else:
                        result = tool_method(**tool_input)

                results.append({"tool_use_id": tool_call["id"], "content": str(result)})

            except Exception as e:
                results.append(
                    {
                        "tool_use_id": tool_call["id"],
                        "content": str({"success": False, "error": str(e)}),
                    }
                )

        return results

    def _build_system_prompt(self) -> str:
        """Build system prompt with tools and context"""
        # Get tool descriptions
        available_tools = self.tools.get_available_tools()
        tool_desc = get_tool_descriptions(available_tools)

        # Build base prompt
        prompt = AGENT_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)

        # Add conversation context
        context_info = build_conversation_context_prompt(self.context)
        if context_info:
            prompt += "\n\n" + context_info

        return prompt

    def _get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for Claude API"""
        return [
            {
                "name": "generate_posts",
                "description": "Generate social media posts from a client brief. Returns project_id and quality score.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "description": "Client company name"},
                        "brief_path": {
                            "type": "string",
                            "description": "Path to client brief file",
                        },
                        "num_posts": {
                            "type": "integer",
                            "description": "Number of posts to generate (default 30)",
                        },
                        "platform": {
                            "type": "string",
                            "description": "Platform: linkedin, twitter, facebook, blog (default linkedin)",
                        },
                    },
                    "required": ["client_name", "brief_path"],
                },
            },
            {
                "name": "list_projects",
                "description": "List all projects, optionally filtered by client",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Filter by client name (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max number of projects to return (default 10)",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_project_status",
                "description": "Get detailed status and statistics for a specific project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID to query"}
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "list_clients",
                "description": "Get list of all clients in the system",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_client_history",
                "description": "Get a client's complete project history and statistics",
                "input_schema": {
                    "type": "object",
                    "properties": {"client_name": {"type": "string", "description": "Client name"}},
                    "required": ["client_name"],
                },
            },
            {
                "name": "read_file",
                "description": "Read content from a file (brief, feedback, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to read"}
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "search_files",
                "description": "Search for files matching a pattern in a directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "File pattern to search for (e.g., *.txt, *brief*)",
                        },
                        "directory": {
                            "type": "string",
                            "description": "Directory to search in (default: data)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "show_dashboard",
                "description": "Show analytics dashboard with metrics and charts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Filter by client name (optional)",
                        }
                    },
                    "required": [],
                },
            },
        ]

    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Claude response"""
        text_parts = []
        for content_block in response.content:
            if hasattr(content_block, "text"):
                text_parts.append(content_block.text)

        return "\n".join(text_parts)

    def reset_conversation(self):
        """Reset conversation history (keeps context)"""
        self.messages = []

    def start_new_session(self) -> str:
        """Start a completely new session"""
        session_id = str(uuid.uuid4())
        self.context = ConversationContext(session_id=session_id)
        self.messages = []
        return session_id

    def get_session_id(self) -> str:
        """Get current session ID"""
        return self.context.session_id

    def update_context(self, **kwargs):
        """Update conversation context"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

        self.context.update_activity()
        self.context_manager.save_context(self.context)
