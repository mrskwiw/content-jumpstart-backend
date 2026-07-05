from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.middleware import auth_dependency as auth_dep
from backend.middleware import csrf_protection as csrf_mod
from backend.middleware import metrics as metrics_mod
from backend.middleware import request_id as request_id_mod
from backend.middleware.auth_dependency import HTTPBearerWith401
from backend.middleware.csrf_protection import (
    CSRFProtectionMiddleware,
    is_same_origin,
    validate_origin_referer,
)
from backend.middleware.metrics import MetricsMiddleware
from backend.middleware.request_id import RequestIDMiddleware
from backend.schemas.deliverable import (
    DeliverableCreate,
    DeliverableDetailResponse,
    DeliverableResponse,
    DeliverableUpdate,
    MarkDeliveredRequest,
    PostSummary,
    QASummary,
    ResearchResultSummary,
)
from backend.schemas.audit import AuditLogResponse, ComplianceStatsResponse
from backend.schemas.story import StoryResponse
from backend.utils import auth as auth_utils
from src.config.settings import Settings


def make_request(headers=None, method="GET", path="/"):
    headers = headers or {}
    header_items = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": header_items,
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class TestAuthDependencyPriority:
    @pytest.mark.asyncio
    async def test_http_bearer_with401_converts_forbidden_to_unauthorized(self, monkeypatch):
        async def fake_super_call(self, request):
            raise HTTPException(status_code=403, detail="Not authenticated")

        monkeypatch.setattr(auth_dep.HTTPBearer, "__call__", fake_super_call, raising=True)

        bearer = HTTPBearerWith401()
        with pytest.raises(HTTPException) as exc:
            await bearer(make_request())

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_http_bearer_with401_handles_none_return(self, monkeypatch):
        async def fake_super_call(self, request):
            return None

        monkeypatch.setattr(auth_dep.HTTPBearer, "__call__", fake_super_call, raising=True)

        bearer = HTTPBearerWith401()
        with pytest.raises(HTTPException) as exc:
            await bearer(make_request())

        assert exc.value.status_code == 401


class TestCsrfPriority:
    def test_is_same_origin_false_for_empty_origin(self):
        assert is_same_origin("", {"http://localhost"}) is False

    def test_validate_origin_referer_invalid_referer(self, monkeypatch):
        monkeypatch.setattr(
            csrf_mod.settings, "CORS_ORIGINS", "http://localhost:3000", raising=False
        )
        request = make_request(headers={"referer": "http://evil.example/path"})
        assert validate_origin_referer(request) is False

    def test_middleware_allows_exempt_prefix(self, monkeypatch):
        monkeypatch.setattr(
            csrf_mod.settings, "CORS_ORIGINS", "http://localhost:3000", raising=False
        )
        app = FastAPI()
        app.add_middleware(CSRFProtectionMiddleware)

        @app.post("/api/auth/login/extra")
        def login_extra():
            return {"ok": True}

        client = TestClient(app)
        response = client.post("/api/auth/login/extra")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestRequestIdPriority:
    def test_middleware_logs_and_reraises_on_error(self, monkeypatch):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        seen = {}

        @app.get("/boom")
        def boom():
            raise RuntimeError("boom")

        def fake_error(msg, *args, **kwargs):
            seen["message"] = msg
            seen["extra"] = kwargs.get("extra")

        monkeypatch.setattr(request_id_mod.logger, "error", fake_error)

        client = TestClient(app)
        with pytest.raises(RuntimeError):
            client.get("/boom")

        assert "Request" in seen["message"]
        assert "request_id" in seen["extra"]


class TestStorySchemaPriority:
    def test_story_response_serializer_handles_none_and_timezones(self):
        story = StoryResponse(
            id="story-1",
            client_id="client-1",
            project_id=None,
            user_id="user-1",
            story_type="success",
            title="Story",
            summary="Summary",
            full_story={"context": "ctx"},
            key_metrics={"growth": "20%"},
            emotional_hook="hook",
            source="interview",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        )

        assert story.serialize_datetime(None, None) is None
        payload = story.model_dump()
        assert payload["created_at"].endswith("+00:00")
        assert payload["updated_at"].endswith("+00:00")


class TestSettingsPriority:
    def test_validate_api_key_branches(self):
        assert Settings.validate_api_key(None) is None

        with pytest.raises(ValueError):
            Settings.validate_api_key("sk-ant-placeholder")

        with pytest.raises(ValueError):
            Settings.validate_api_key("short")

        value = "notpref-" + "x" * 20
        assert Settings.validate_api_key(value) == value


class FakeSecretManagerForPriority:
    def __init__(self, primary_secret=None, active_secrets=None):
        self.primary_secret = primary_secret
        self.active_secrets = active_secrets or []

    def get_primary_secret(self):
        return self.primary_secret

    def get_active_secrets(self):
        return list(self.active_secrets)


class FakeMetricsRecorder:
    def __init__(self):
        self.records = []

    def record_request(self, **kwargs):
        self.records.append(kwargs)


class TestAuthUtilsPriority:
    def test_get_secret_manager_logs_once_when_no_secrets(self, monkeypatch):
        created = []

        class FakeSecretManager:
            def __init__(self):
                created.append(self)
                self._active_secrets = []

            def get_active_secrets(self):
                return []

        monkeypatch.setattr(auth_utils, "SecretManager", FakeSecretManager)
        monkeypatch.setattr(auth_utils, "_secret_manager", None, raising=False)
        monkeypatch.setattr(auth_utils, "_fallback_warned", False, raising=False)

        seen = []
        monkeypatch.setattr(auth_utils.logger, "info", lambda message: seen.append(message))

        first = auth_utils.get_secret_manager()
        second = auth_utils.get_secret_manager()

        assert first is second
        assert len(created) == 1
        assert len(seen) == 1
        assert "using settings.SECRET_KEY" in seen[0]

    def test_create_tokens_use_settings_fallback_when_primary_missing(self, monkeypatch):
        fake_manager = FakeSecretManagerForPriority(primary_secret=None, active_secrets=[])
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)
        monkeypatch.setattr(
            auth_utils.settings, "SECRET_KEY", "fallback-secret-1234567890123456", raising=False
        )

        access = auth_utils.create_access_token(
            {"sub": "user-10"}, expires_delta=timedelta(minutes=5)
        )
        refresh = auth_utils.create_refresh_token({"sub": "user-11"})

        access_payload = auth_utils.jwt.decode(
            access, auth_utils.settings.SECRET_KEY, algorithms=[auth_utils.settings.ALGORITHM]
        )
        refresh_payload = auth_utils.jwt.decode(
            refresh, auth_utils.settings.SECRET_KEY, algorithms=[auth_utils.settings.ALGORITHM]
        )

        assert access_payload["sub"] == "user-10"
        assert access_payload["type"] == "access"
        assert refresh_payload["sub"] == "user-11"
        assert refresh_payload["type"] == "refresh"

    def test_decode_token_falls_back_when_no_active_secrets(self, monkeypatch):
        fake_manager = FakeSecretManagerForPriority(active_secrets=[])
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)
        token = auth_utils.jwt.encode(
            {"sub": "user-12", "type": "access"},
            auth_utils.settings.SECRET_KEY,
            algorithm=auth_utils.settings.ALGORITHM,
        )

        payload = auth_utils.decode_token(token)
        assert payload["sub"] == "user-12"


class TestAuditSchemaPriority:
    def test_from_orm_entry_handles_naive_timestamp_and_missing_name(self):
        entry = SimpleNamespace(
            id="audit-1",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            user_id=None,
            user_name=None,
            user_email="user@example.com",
            action="create",
            action_type="post.create",
            resource_type="client",
            resource_name="Acme Corp",
            details=None,
            ip_address=None,
            status=None,
            extra_metadata={"source": "api"},
        )

        response = AuditLogResponse.from_orm_entry(entry)
        payload = response.model_dump_api()

        assert response.timestamp.endswith("+00:00")
        assert response.resource == "Client: Acme Corp"
        assert response.user.name == "user@example.com"
        assert payload["actionType"] == "post.create"
        assert payload["ipAddress"] == ""
        assert payload["metadata"] == {"source": "api"}

    def test_from_orm_entry_handles_aware_timestamp_without_resource_name(self):
        entry = SimpleNamespace(
            id="audit-2",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            user_id="user-2",
            user_name="Jordan",
            user_email="jordan@example.com",
            action="update",
            action_type="post.update",
            resource_type="project",
            resource_name="",
            details="Updated",
            ip_address="127.0.0.1",
            status="success",
            extra_metadata=None,
        )

        response = AuditLogResponse.from_orm_entry(entry)

        assert response.resource == "Project"
        assert response.user.id == "user-2"
        assert response.user.name == "Jordan"
        assert response.status == "success"

    def test_compliance_stats_model_dump_uses_aliases(self):
        stats = ComplianceStatsResponse(
            total_events=5,
            today_events=2,
            failed_actions=1,
            security_events=3,
            avg_events_per_day=1.5,
        )

        payload = stats.model_dump(by_alias=True)
        assert payload["totalEvents"] == 5
        assert payload["retentionDays"] == 90


class TestMetricsMiddlewarePriority:
    def _build_app(self, response_factory):
        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/ok")
        async def ok():
            return response_factory()

        @app.get("/boom")
        async def boom():
            raise RuntimeError("boom")

        return app

    def test_metrics_skips_static_paths(self, monkeypatch):
        recorder = FakeMetricsRecorder()
        monkeypatch.setattr(metrics_mod, "get_metrics", lambda: recorder)

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/favicon.ico")
        async def favicon():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/favicon.ico")

        assert response.status_code == 200
        assert recorder.records == []

    def test_metrics_records_success_and_header(self, monkeypatch):
        recorder = FakeMetricsRecorder()
        monkeypatch.setattr(metrics_mod, "get_metrics", lambda: recorder)
        client = TestClient(self._build_app(lambda: {"ok": True}))

        response = client.get("/ok")

        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert recorder.records[0]["path"] == "/ok"
        assert recorder.records[0]["status_code"] == 200

    def test_metrics_records_failure_and_reraises(self, monkeypatch):
        recorder = FakeMetricsRecorder()
        monkeypatch.setattr(metrics_mod, "get_metrics", lambda: recorder)
        client = TestClient(self._build_app(lambda: {"ok": True}))

        with pytest.raises(RuntimeError):
            client.get("/boom")

        assert recorder.records[-1]["path"] == "/boom"
        assert recorder.records[-1]["status_code"] == 500


class TestDeliverableSchemaPriority:
    def test_create_update_and_mark_delivered_aliases(self):
        create = DeliverableCreate(
            format="docx",
            projectId="project-1",
            runId="run-1",
        )
        update = DeliverableUpdate(status="delivered")
        mark = MarkDeliveredRequest(
            deliveredAt=datetime(2026, 1, 2, 10, 30, 0),
            proofUrl="https://example.com/proof",
            proofNotes="Shared in Drive",
        )

        assert create.project_id == "project-1"
        assert create.run_id == "run-1"
        assert update.status == "delivered"
        assert mark.proof_url == "https://example.com/proof"
        assert mark.proof_notes == "Shared in Drive"

        with pytest.raises(Exception):
            DeliverableCreate(format="txt", projectId="project-1", runId="run-1", status="bad")

        with pytest.raises(Exception):
            DeliverableUpdate(status="delivered", extra_field=True)

    def test_deliverable_response_serializers_cover_naive_and_aware_values(self):
        response = DeliverableResponse(
            id="deliverable-1",
            format="docx",
            project_id="project-1",
            client_id="client-1",
            run_id="run-1",
            path="/tmp/output.docx",
            status="ready",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="abc123",
            file_size_bytes=2048,
        )

        assert response.serialize_datetime(None, None) is None
        payload = response.model_dump(mode="json", by_alias=True)
        assert payload["createdAt"].endswith("Z")
        assert payload["deliveredAt"] is None
        assert payload["projectId"] == "project-1"

        aware = DeliverableResponse(
            id="deliverable-2",
            format="pdf",
            project_id="project-1",
            client_id="client-1",
            run_id=None,
            path="/tmp/output.pdf",
            status="delivered",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            delivered_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        )
        aware_payload = aware.model_dump(mode="json", by_alias=True)
        assert aware_payload["createdAt"].endswith("Z")
        assert aware_payload["deliveredAt"].endswith("Z")

    def test_detail_response_and_nested_serializers(self):
        detail = DeliverableDetailResponse(
            id="deliverable-3",
            format="txt",
            project_id="project-1",
            client_id="client-1",
            run_id=None,
            path="/tmp/output.txt",
            status="delivered",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            delivered_at=datetime(2026, 1, 2, 12, 0, 0),
            file_preview="First preview",
            file_preview_truncated=True,
            posts=[
                PostSummary(
                    id="post-1",
                    template_name="Problem Recognition",
                    word_count=220,
                    readability_score=8.1,
                    status="approved",
                    flags=["cta"],
                    content="Post content",
                    content_preview="Post content preview",
                )
            ],
            qa_summary=QASummary(
                avg_readability=8.2,
                avg_word_count=215,
                total_posts=30,
                flagged_count=2,
                approved_count=28,
                cta_percentage=80.0,
                common_flags=["cta"],
            ),
            file_modified_at=datetime(2026, 1, 3, 12, 0, 0),
            research_results=[
                ResearchResultSummary(
                    id="research-1",
                    user_id="user-1",
                    client_id="client-1",
                    project_id="project-1",
                    tool_name="audience_research",
                    tool_label="Audience Research",
                    tool_price=500.0,
                    actual_cost_usd=125.0,
                    summary="Useful findings",
                    status="complete",
                    error_message=None,
                    duration_seconds=42.5,
                    created_at=datetime(2026, 1, 4, 12, 0, 0),
                )
            ],
        )

        payload = detail.model_dump(mode="json", by_alias=True)
        assert payload["filePreview"] == "First preview"
        assert payload["filePreviewTruncated"] is True
        assert payload["posts"][0]["templateName"] == "Problem Recognition"
        assert payload["qaSummary"]["totalPosts"] == 30
        assert payload["researchResults"][0]["createdAt"].endswith("Z")
