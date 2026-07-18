"""
AI assistant tool registry.

Importing this package registers all built-in tools. Public surface:

- ``get_tool_definitions(include_billable=False)`` — Anthropic tool defs to send.
- ``dispatch_tool(name, db, user, input)`` — run a tool with allow-list enforcement.
- ``get_spec(name)`` — inspect a registered tool.
"""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.models import User
from backend.services.assistant_tools.base import (
    ToolResult,
    ToolSpec,
    get_spec,
    get_tool_definitions,
    register,
)

# Import tool modules for their registration side effects.
from backend.services.assistant_tools import read_tools  # noqa: F401,E402

__all__ = [
    "ToolResult",
    "ToolSpec",
    "register",
    "get_spec",
    "get_tool_definitions",
    "dispatch_tool",
]


def dispatch_tool(
    name: str, db: Session, current_user: User, tool_input: Dict[str, Any]
) -> ToolResult:
    """Execute a registered tool by name.

    Enforces the allow-list (only registered tools run) and never raises: handler
    failures are converted to a structured error ToolResult the model can recover
    from, so a bad tool call can't 500 the stream.
    """
    spec = get_spec(name)
    if spec is None:
        return ToolResult(ok=False, error=f"Unknown tool: {name}")

    if not isinstance(tool_input, dict):
        tool_input = {}

    try:
        return spec.handler(db, current_user, tool_input)
    except Exception as exc:  # noqa: BLE001 - deliberate: surface as tool error
        from backend.utils.logger import logger

        logger.error(f"Assistant tool '{name}' failed: {exc}", exc_info=True)
        return ToolResult(ok=False, error="The tool failed to run. Please try again.")
