"""
Tier-A read-only assistant tools.

These run automatically (no confirmation) and let the assistant answer questions
grounded in the instance's data. Every query is scoped through
``assistant_scope_query`` / ``assistant_can_access`` so visibility follows the
``ENFORCE_RESOURCE_OWNERSHIP`` toggle: global by default, per-user when enabled
(superusers always unrestricted).
"""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.middleware.authorization import (
    assistant_can_access,
    assistant_scope_query,
)
from backend.models import Client, Post, Project, ResearchResult, User
from backend.services.assistant_tools.base import ToolResult, ToolSpec, register

# Clamp list sizes so a tool can't dump an unbounded result set into the prompt.
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


def _limit(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    return max(1, min(n, _MAX_LIMIT))


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


def _list_projects(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    q = assistant_scope_query(db.query(Project), Project, user).filter(
        Project.is_deleted.is_(False)
    )
    status = inp.get("status")
    if status:
        q = q.filter(Project.status == status)
    rows = q.order_by(Project.created_at.desc()).limit(_limit(inp.get("limit"))).all()
    data = [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "client_id": p.client_id,
            "num_posts": p.num_posts,
            "created_at": p.created_at,
        }
        for p in rows
    ]
    return ToolResult(ok=True, data=data, summary=f"Found {len(data)} project(s)")


register(
    ToolSpec(
        name="list_projects",
        handler=_list_projects,
        definition={
            "name": "list_projects",
            "description": (
                "List content projects the current user can see. Optionally filter "
                "by status. Use this to answer questions about the user's projects."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Optional status filter (e.g. draft, generating, complete).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Max rows (1-{_MAX_LIMIT}, default {_DEFAULT_LIMIT}).",
                    },
                },
            },
        },
    )
)


# ---------------------------------------------------------------------------
# get_project_status
# ---------------------------------------------------------------------------


def _get_project_status(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    project_id = inp.get("project_id")
    if not project_id:
        return ToolResult(ok=False, error="project_id is required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.is_deleted:
        return ToolResult(ok=False, error="Project not found")
    if not assistant_can_access(project, user):
        return ToolResult(ok=False, error="Project not found")
    post_count = (
        db.query(Post).filter(Post.project_id == project.id, Post.is_deleted.is_(False)).count()
    )
    data = {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "client_id": project.client_id,
        "num_posts": project.num_posts,
        "posts_generated": post_count,
        "target_platform": project.target_platform,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }
    return ToolResult(ok=True, data=data, summary=f"Project '{project.name}' is {project.status}")


register(
    ToolSpec(
        name="get_project_status",
        handler=_get_project_status,
        definition={
            "name": "get_project_status",
            "description": "Get detailed status and post counts for a single project by id.",
            "input_schema": {
                "type": "object",
                "properties": {"project_id": {"type": "string", "description": "The project id."}},
                "required": ["project_id"],
            },
        },
    )
)


# ---------------------------------------------------------------------------
# list_clients
# ---------------------------------------------------------------------------


def _list_clients(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    q = assistant_scope_query(db.query(Client), Client, user).filter(Client.is_deleted.is_(False))
    rows = q.order_by(Client.created_at.desc()).limit(_limit(inp.get("limit"))).all()
    data = [
        {"id": c.id, "name": c.name, "industry": c.industry, "created_at": c.created_at}
        for c in rows
    ]
    return ToolResult(ok=True, data=data, summary=f"Found {len(data)} client(s)")


register(
    ToolSpec(
        name="list_clients",
        handler=_list_clients,
        definition={
            "name": "list_clients",
            "description": "List clients the current user can see.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": f"Max rows (1-{_MAX_LIMIT}, default {_DEFAULT_LIMIT}).",
                    }
                },
            },
        },
    )
)


# ---------------------------------------------------------------------------
# get_client_history
# ---------------------------------------------------------------------------


def _get_client_history(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    client_id = inp.get("client_id")
    if not client_id:
        return ToolResult(ok=False, error="client_id is required")
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client or client.is_deleted:
        return ToolResult(ok=False, error="Client not found")
    if not assistant_can_access(client, user):
        return ToolResult(ok=False, error="Client not found")
    projects = (
        db.query(Project)
        .filter(Project.client_id == client.id, Project.is_deleted.is_(False))
        .order_by(Project.created_at.desc())
        .limit(_MAX_LIMIT)
        .all()
    )
    data = {
        "id": client.id,
        "name": client.name,
        "industry": client.industry,
        "business_description": client.business_description,
        "projects": [
            {"id": p.id, "name": p.name, "status": p.status, "num_posts": p.num_posts}
            for p in projects
        ],
    }
    return ToolResult(ok=True, data=data, summary=f"{client.name}: {len(projects)} project(s)")


register(
    ToolSpec(
        name="get_client_history",
        handler=_get_client_history,
        definition={
            "name": "get_client_history",
            "description": "Get a client's profile and their projects by client id.",
            "input_schema": {
                "type": "object",
                "properties": {"client_id": {"type": "string", "description": "The client id."}},
                "required": ["client_id"],
            },
        },
    )
)


# ---------------------------------------------------------------------------
# list_posts
# ---------------------------------------------------------------------------


def _list_posts(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    project_id = inp.get("project_id")
    if not project_id:
        return ToolResult(ok=False, error="project_id is required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.is_deleted:
        return ToolResult(ok=False, error="Project not found")
    if not assistant_can_access(project, user):
        return ToolResult(ok=False, error="Project not found")
    q = db.query(Post).filter(Post.project_id == project_id, Post.is_deleted.is_(False))
    status = inp.get("status")
    if status:
        q = q.filter(Post.status == status)
    rows = q.order_by(Post.created_at.desc()).limit(_limit(inp.get("limit"))).all()
    data = [
        {
            "id": p.id,
            "status": p.status,
            "target_platform": p.target_platform,
            "word_count": p.word_count,
            "template_name": p.template_name,
            "preview": (p.content or "")[:160],
        }
        for p in rows
    ]
    return ToolResult(ok=True, data=data, summary=f"Found {len(data)} post(s)")


register(
    ToolSpec(
        name="list_posts",
        handler=_list_posts,
        definition={
            "name": "list_posts",
            "description": "List generated posts for a project (with a short content preview).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project id."},
                    "status": {
                        "type": "string",
                        "description": "Optional status filter (e.g. approved, flagged).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Max rows (1-{_MAX_LIMIT}, default {_DEFAULT_LIMIT}).",
                    },
                },
                "required": ["project_id"],
            },
        },
    )
)


# ---------------------------------------------------------------------------
# get_credits
# ---------------------------------------------------------------------------


def _get_credits(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    # Live lot sum, not the cached column — excludes expired credits (S-01.4b-ii review).
    from backend.services import credit_service

    balance = credit_service.live_balance(db, user.id)
    data = {
        "credit_balance": balance,
        "total_credits_purchased": user.total_credits_purchased,
        "total_credits_used": user.total_credits_used,
    }
    return ToolResult(ok=True, data=data, summary=f"{balance} credits remaining")


register(
    ToolSpec(
        name="get_credits",
        handler=_get_credits,
        definition={
            "name": "get_credits",
            "description": "Get the current user's credit balance and usage.",
            "input_schema": {"type": "object", "properties": {}},
        },
    )
)


# ---------------------------------------------------------------------------
# list_research_results
# ---------------------------------------------------------------------------


def _list_research_results(db: Session, user: User, inp: Dict[str, Any]) -> ToolResult:
    q = assistant_scope_query(db.query(ResearchResult), ResearchResult, user)
    client_id = inp.get("client_id")
    if client_id:
        q = q.filter(ResearchResult.client_id == client_id)
    rows = q.order_by(ResearchResult.created_at.desc()).limit(_limit(inp.get("limit"))).all()
    data = [
        {
            "id": r.id,
            "tool_name": r.tool_name,
            "tool_label": getattr(r, "tool_label", None),
            "client_id": r.client_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return ToolResult(ok=True, data=data, summary=f"Found {len(data)} research result(s)")


register(
    ToolSpec(
        name="list_research_results",
        handler=_list_research_results,
        definition={
            "name": "list_research_results",
            "description": (
                "List completed research tool results the user can see, optionally "
                "filtered by client id."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "client_id": {
                        "type": "string",
                        "description": "Optional client id filter.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Max rows (1-{_MAX_LIMIT}, default {_DEFAULT_LIMIT}).",
                    },
                },
            },
        },
    )
)
