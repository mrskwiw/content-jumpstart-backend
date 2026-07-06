import os
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20)

import backend.main as main_mod


class _EmailField:
    def __eq__(self, other):
        return other


class _FakeQuery:
    def __init__(self, session):
        self._session = session
        self._email = None

    def count(self):
        return self._session.user_count

    def filter(self, criterion):
        self._email = criterion
        return self

    def first(self):
        return self._session.existing_users.get(self._email)


class _FakeSession:
    def __init__(self, user_count=0, existing_users=None):
        self.user_count = user_count
        self.existing_users = existing_users or {}
        self.added = []
        self.committed = False
        self.closed = False

    def query(self, model):
        self.model = model
        return _FakeQuery(self)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class _FakeUser:
    email = _EmailField()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_health_endpoints_return_stats(monkeypatch):
    monkeypatch.setattr(
        main_mod.rate_limiter,
        "get_usage_stats",
        lambda: {
            "requests": 3,
            "requests_limit": 60,
            "requests_available": 57,
            "requests_utilization": 5.0,
            "tokens": 100,
            "tokens_limit": 1000,
            "tokens_available": 900,
            "tokens_utilization": 10.0,
            "queue_length": 2,
        },
    )

    client = TestClient(main_mod.app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["rate_limits"]["requests_per_minute"]["current"] == 3


def test_health_head_and_root_routes():
    client = TestClient(main_mod.app)

    head_response = client.head("/health")
    assert head_response.status_code == 200

    root_response = client.get("/")
    assert root_response.status_code in {200, 404}
    if root_response.status_code == 200:
        assert "text/html" in root_response.headers.get("content-type", "")

    favicon_response = client.get("/favicon.ico")
    assert favicon_response.status_code in {200, 404}
    if favicon_response.status_code == 200:
        assert favicon_response.headers.get("content-type") == "image/svg+xml"


def test_limit_request_size_branches(monkeypatch):
    monkeypatch.setattr(main_mod, "MAX_CONTENT_LENGTH", 0)
    monkeypatch.setattr(main_mod, "MAX_CONTENT_LENGTH_BRIEFS", 0)
    monkeypatch.setattr(main_mod, "MAX_CONTENT_LENGTH_VOICE", 0)

    client = TestClient(main_mod.app)

    response_default = client.post("/api/other", data="x")
    response_brief = client.post("/api/briefs/test", data="x")
    response_voice = client.post("/api/voice/test", data="x")

    assert response_default.status_code == 413
    assert response_brief.status_code == 413
    assert response_voice.status_code == 413

    response_export = client.post(
        "/api/deliverables/export",
        content=b"x",
        headers={"content-length": "60000000"},
    )
    assert response_export.status_code == 413
    assert response_export.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_spa_fallback_and_global_exception_handler(monkeypatch):
    client = TestClient(main_mod.app)

    response = client.get("/dashboard")
    assert response.status_code in {200, 404}

    monkeypatch.setattr(main_mod, "get_request_id", lambda request: "req-1")
    monkeypatch.setattr(
        "backend.utils.error_sanitizer.create_safe_error_response",
        lambda exc, status_code=500, request_id=None: {
            "error": "safe",
            "request_id": request_id,
        },
    )

    class DummyRequest:
        pass

    payload = asyncio.run(main_mod.global_exception_handler(DummyRequest(), RuntimeError("boom")))
    assert payload.status_code == 500


def test_lifespan_seeds_admin_users(monkeypatch):
    calls = []
    session = _FakeSession(user_count=0)

    monkeypatch.delenv("DEFAULT_USER_PASSWORD", raising=False)
    monkeypatch.delenv("FORCE_ADMIN_SEED", raising=False)
    monkeypatch.delenv("ADMIN_USER_1_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_USER_2_EMAIL", raising=False)
    # Drive the PRIMARY/SECONDARY_ADMIN_EMAIL fallback with explicit test values so
    # this is hermetic — previously it silently relied on the developer's local
    # .env (which isn't present in CI, so seeding produced 0 users there).
    monkeypatch.setenv("PRIMARY_ADMIN_EMAIL", "primary-admin@test.local")
    monkeypatch.setenv("SECONDARY_ADMIN_EMAIL", "secondary-admin@test.local")
    monkeypatch.setattr(main_mod.secrets, "token_urlsafe", lambda size: "generated-password")
    monkeypatch.setattr(main_mod, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr("backend.utils.auth.get_password_hash", lambda password: f"hash:{password}")
    monkeypatch.setattr(
        "backend.migrations.add_run_qa_score.run_migration",
        lambda: calls.append("migrate_qa_score"),
    )
    monkeypatch.setattr(
        "backend.migrations.add_deletion_audit_log.run",
        lambda: calls.append("migrate_deletion_audit_log"),
    )
    monkeypatch.setattr("backend.database.SessionLocal", lambda: session)
    monkeypatch.setattr("backend.models.user.User", _FakeUser)
    monkeypatch.setattr(
        main_mod.app_settings,
        "DEBUG_MODE",
        True,
    )
    monkeypatch.setattr(main_mod.app_settings, "DEBUG_CREDITS", 4242)

    async def _run_lifespan():
        async with main_mod.lifespan(main_mod.app):
            return None

    asyncio.run(_run_lifespan())

    assert calls == ["init_db", "migrate_qa_score", "migrate_deletion_audit_log"]
    assert session.committed is True
    assert session.closed is True
    assert len(session.added) == 2
    assert {user.email for user in session.added} == {
        "primary-admin@test.local",
        "secondary-admin@test.local",
    }
    assert all(user.hashed_password for user in session.added)
    assert all(user.credit_balance == 4242 for user in session.added)


def test_lifespan_updates_existing_admin_users(monkeypatch):
    calls = []
    existing_admin = SimpleNamespace(
        hashed_password="old-hash",
        is_superuser=True,
        is_active=False,
    )
    session = _FakeSession(
        user_count=1,
        existing_users={"admin@example.com": existing_admin},
    )

    monkeypatch.setenv("DEFAULT_USER_PASSWORD", "env-password")
    monkeypatch.setenv("FORCE_ADMIN_SEED", "true")
    monkeypatch.setenv("ADMIN_USER_1_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_USER_1_NAME", "Admin One")
    monkeypatch.setenv("ADMIN_USER_1_IS_SUPERUSER", "false")
    monkeypatch.setattr(main_mod.secrets, "token_urlsafe", lambda size: "should-not-be-used")
    monkeypatch.setattr(main_mod, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr("backend.utils.auth.get_password_hash", lambda password: f"hash:{password}")
    monkeypatch.setattr(
        "backend.migrations.add_run_qa_score.run_migration",
        lambda: calls.append("migrate_qa_score"),
    )
    monkeypatch.setattr(
        "backend.migrations.add_deletion_audit_log.run",
        lambda: calls.append("migrate_deletion_audit_log"),
    )
    monkeypatch.setattr("backend.database.SessionLocal", lambda: session)
    monkeypatch.setattr("backend.models.user.User", _FakeUser)
    monkeypatch.setattr(main_mod.app_settings, "DEBUG_MODE", False)

    async def _run_lifespan():
        async with main_mod.lifespan(main_mod.app):
            return None

    asyncio.run(_run_lifespan())

    assert calls == ["init_db", "migrate_qa_score", "migrate_deletion_audit_log"]
    assert session.committed is True
    assert session.closed is True
    assert session.added == []
    assert existing_admin.hashed_password != "old-hash"
    assert existing_admin.is_superuser is False
    assert existing_admin.is_active is True


def test_lifespan_skips_seed_when_users_exist(monkeypatch):
    calls = []
    session = _FakeSession(user_count=2)

    monkeypatch.delenv("DEFAULT_USER_PASSWORD", raising=False)
    monkeypatch.delenv("FORCE_ADMIN_SEED", raising=False)
    monkeypatch.setattr(main_mod.secrets, "token_urlsafe", lambda size: "generated-password")
    monkeypatch.setattr(main_mod, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr("backend.utils.auth.get_password_hash", lambda password: f"hash:{password}")
    monkeypatch.setattr(
        "backend.migrations.add_run_qa_score.run_migration",
        lambda: calls.append("migrate_qa_score"),
    )
    monkeypatch.setattr(
        "backend.migrations.add_deletion_audit_log.run",
        lambda: calls.append("migrate_deletion_audit_log"),
    )
    monkeypatch.setattr("backend.database.SessionLocal", lambda: session)
    monkeypatch.setattr("backend.models.user.User", _FakeUser)

    async def _run_lifespan():
        async with main_mod.lifespan(main_mod.app):
            return None

    asyncio.run(_run_lifespan())

    assert calls == ["init_db", "migrate_qa_score", "migrate_deletion_audit_log"]
    assert session.committed is False
    assert session.closed is True
    assert session.added == []
