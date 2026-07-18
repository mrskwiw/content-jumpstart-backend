"""
Core types for the AI assistant tool registry.

Tools are user-scoped platform actions the assistant may invoke. Each tool
pairs an Anthropic tool *definition* (name/description/JSON schema) with a
*handler* that runs server-side against the request-bound DB session and the
authenticated user. Read-only tools (Tier A) run automatically; billable or
mutating tools (Tier B, Phase 2) set ``requires_confirmation=True``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import User

# A handler takes (db, current_user, validated_input) and returns a ToolResult.
ToolHandler = Callable[[Session, User, Dict[str, Any]], "ToolResult"]
# A cost estimator returns an estimated USD cost for a proposed invocation.
CostEstimator = Callable[[Session, User, Dict[str, Any]], float]


@dataclass
class ToolResult:
    """Outcome of a tool execution, serialized back to the model."""

    ok: bool
    data: Any = None
    error: Optional[str] = None
    # Short human-readable line surfaced in the UI (SSE tool_result.summary).
    summary: str = ""

    def to_content(self) -> str:
        """Render the result as the string content of an Anthropic tool_result."""
        if not self.ok:
            return json.dumps({"error": self.error or "Tool execution failed"})
        try:
            return json.dumps({"result": self.data}, default=str)
        except (TypeError, ValueError):
            return json.dumps({"result": str(self.data)})


@dataclass
class ToolSpec:
    """A registered assistant tool."""

    name: str
    definition: Dict[str, Any]
    handler: ToolHandler
    requires_confirmation: bool = False
    cost_estimator: Optional[CostEstimator] = None


# Name -> ToolSpec. Populated by the tool modules at import time.
_REGISTRY: Dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    """Add a tool to the registry (last registration wins for a given name)."""
    _REGISTRY[spec.name] = spec


def get_spec(name: str) -> Optional[ToolSpec]:
    return _REGISTRY.get(name)


def get_tool_definitions(include_billable: bool = False) -> List[Dict[str, Any]]:
    """Return Anthropic tool definitions the assistant is allowed to use.

    Args:
        include_billable: When False (Phase 1 default), only auto-run read-only
            tools are exposed. Billable/mutating tools are gated behind the
            confirmation flow and excluded until Phase 2 wires it.
    """
    defs: List[Dict[str, Any]] = []
    for spec in _REGISTRY.values():
        if spec.requires_confirmation and not include_billable:
            continue
        defs.append(spec.definition)
    return defs
