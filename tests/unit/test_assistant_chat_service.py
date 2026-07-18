"""Unit tests for the AI assistant: ownership parity, tool dispatch, streaming loop.

Self-contained: builds an in-memory SQLite DB with the real models so it doesn't
depend on the app's server fixtures. The Anthropic client is mocked.
"""

import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.database import Base
from backend.models import Client, Project, User
from backend.services import chat_service
from backend.services.assistant_tools import dispatch_tool, get_tool_definitions


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded(db):
    """Two users; user A owns a client + project, user B owns nothing."""
    ua = User(id="ua", email="a@x.com", hashed_password="x", is_active=True, is_superuser=False)
    ub = User(id="ub", email="b@x.com", hashed_password="x", is_active=True, is_superuser=False)
    su = User(id="su", email="s@x.com", hashed_password="x", is_active=True, is_superuser=True)
    db.add_all([ua, ub, su])
    db.add(Client(id="ca", user_id="ua", name="Acme"))
    db.add(
        Project(
            id="pa", user_id="ua", client_id="ca", name="Q3 Launch", status="complete", num_posts=30
        )
    )
    db.commit()
    return types.SimpleNamespace(ua=ua, ub=ub, su=su)


# ---------------------------------------------------------------------------
# Ownership parity (the ENFORCE_RESOURCE_OWNERSHIP toggle)
# ---------------------------------------------------------------------------


@pytest.fixture
def restore_flag():
    original = settings.ENFORCE_RESOURCE_OWNERSHIP
    yield
    settings.ENFORCE_RESOURCE_OWNERSHIP = original


def test_ownership_flag_on_isolates_users(db, seeded, restore_flag):
    settings.ENFORCE_RESOURCE_OWNERSHIP = True
    a = dispatch_tool("list_projects", db, seeded.ua, {})
    b = dispatch_tool("list_projects", db, seeded.ub, {})
    assert [p["name"] for p in a.data] == ["Q3 Launch"]
    assert b.data == []


def test_ownership_flag_on_superuser_sees_all(db, seeded, restore_flag):
    settings.ENFORCE_RESOURCE_OWNERSHIP = True
    s = dispatch_tool("list_projects", db, seeded.su, {})
    assert [p["name"] for p in s.data] == ["Q3 Launch"]


def test_ownership_flag_off_is_global(db, seeded, restore_flag):
    settings.ENFORCE_RESOURCE_OWNERSHIP = False
    b = dispatch_tool("list_projects", db, seeded.ub, {})
    assert [p["name"] for p in b.data] == ["Q3 Launch"]


def test_get_project_status_denied_cross_user_when_scoped(db, seeded, restore_flag):
    settings.ENFORCE_RESOURCE_OWNERSHIP = True
    res = dispatch_tool("get_project_status", db, seeded.ub, {"project_id": "pa"})
    assert res.ok is False
    assert "not found" in (res.error or "").lower()


# ---------------------------------------------------------------------------
# Tool registry / dispatch guardrails
# ---------------------------------------------------------------------------


def test_unknown_tool_is_rejected(db, seeded):
    res = dispatch_tool("rm_rf", db, seeded.ua, {})
    assert res.ok is False
    assert "unknown tool" in (res.error or "").lower()


def test_only_read_tools_exposed_by_default():
    names = {d["name"] for d in get_tool_definitions(include_billable=False)}
    assert "list_projects" in names
    # No billable/mutating tools until Phase 2 wires confirmation.
    assert "run_research_tool" not in names
    for d in get_tool_definitions():
        assert "name" in d and "input_schema" in d


def test_tool_handler_exception_becomes_error(db, seeded, monkeypatch):
    from backend.services.assistant_tools import base as tools_base

    spec = tools_base.get_spec("get_credits")
    monkeypatch.setattr(
        spec, "handler", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    res = dispatch_tool("get_credits", db, seeded.ua, {})
    assert res.ok is False  # exception surfaced as a structured error, not raised


# ---------------------------------------------------------------------------
# Streaming agentic loop
# ---------------------------------------------------------------------------


class _FakeClient:
    """Turn 1 asks to run list_projects; turn 2 answers with text."""

    def __init__(self):
        self.calls = 0
        self.model = "fake"

    def create_message_stream_async(self, **kwargs):
        if self.calls == 0:
            script = {
                "text": ["Let me check."],
                "blocks": [
                    {"type": "text", "text": "Let me check."},
                    {"type": "tool_use", "id": "t1", "name": "list_projects", "input": {}},
                ],
                "stop": "tool_use",
            }
        else:
            script = {
                "text": ["You have 1 project."],
                "blocks": [{"type": "text", "text": "You have 1 project."}],
                "stop": "end_turn",
            }
        self.calls += 1
        return self._gen(script)

    async def _gen(self, script):
        for t in script["text"]:
            yield {"type": "text_delta", "text": t}
        yield {
            "type": "message_stop",
            "stop_reason": script["stop"],
            "content": script["blocks"],
            "usage": {"input_tokens": 5, "output_tokens": 3},
        }


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.mark.asyncio
async def test_stream_chat_runs_tool_and_persists(db, seeded, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(chat_service, "get_default_client", lambda: fake)

    events = await _collect(
        chat_service.stream_chat(
            db, seeded.ua, message="How many projects?", context={"page": "projects"}
        )
    )
    types_seen = [e["type"] for e in events]
    assert "start" in types_seen
    assert "token" in types_seen
    assert "tool_result" in types_seen
    assert "complete" in types_seen

    tool_results = [e for e in events if e["type"] == "tool_result"]
    assert tool_results[0]["ok"] is True
    assert tool_results[0]["name"] == "list_projects"

    # Conversation persisted with the full turn sequence.
    conv_id = next(e for e in events if e["type"] == "start")["conversation_id"]
    conv = chat_service.get_conversation_detail(db, seeded.ua, conv_id)
    roles = [m.role for m in conv.messages]
    assert roles == ["user", "assistant", "tool", "assistant"]


@pytest.mark.asyncio
async def test_stream_chat_blocks_prompt_injection(db, seeded, monkeypatch):
    def _raise(*a, **k):
        raise ValueError("injection")

    monkeypatch.setattr(chat_service, "sanitize_prompt_input", _raise)
    events = await _collect(chat_service.stream_chat(db, seeded.ua, message="ignore instructions"))
    assert events and events[0]["type"] == "error"
    # Nothing persisted for a blocked message.
    assert db.query(chat_service.Conversation).count() == 0


# ---------------------------------------------------------------------------
# Conversation CRUD ownership
# ---------------------------------------------------------------------------


def test_conversation_crud_cross_user_denied(db, seeded):
    conv = chat_service.get_or_create_conversation(db, seeded.ua, None, {"page": "projects"})
    # User B cannot read or delete A's conversation.
    with pytest.raises(PermissionError):
        chat_service.get_conversation_detail(db, seeded.ub, conv.id)
    with pytest.raises(PermissionError):
        chat_service.delete_conversation(db, seeded.ub, conv.id)
    # Owner can, and soft-delete removes it from the listing.
    chat_service.delete_conversation(db, seeded.ua, conv.id)
    listing = chat_service.list_conversations(db, seeded.ua)
    assert listing["total"] == 0


def test_missing_conversation_raises_lookup(db, seeded):
    with pytest.raises(LookupError):
        chat_service.get_conversation_detail(db, seeded.ua, "conv_does_not_exist")
