"""
Unit tests for backend security and request-tracing middleware.
"""

from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.middleware.csrf_protection import (
    CSRFProtectionMiddleware,
    STATE_CHANGING_METHODS,
    generate_csrf_token,
    is_same_origin,
    verify_csrf_token,
)
from backend.middleware.request_id import RequestIDMiddleware, get_request_id
from backend.middleware.security_headers import add_security_headers_middleware


def build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    @app.get("/ping")
    def plain_ping():
        return {"ok": True}

    @app.post("/api/update")
    def update():
        return {"updated": True}

    @app.post("/api/auth/login")
    def login():
        return {"logged_in": True}

    return app


class TestSecurityHeadersMiddleware:
    def test_api_routes_get_security_headers(self, monkeypatch):
        from backend.middleware import security_headers

        monkeypatch.setattr(security_headers.settings, "DEBUG_MODE", False, raising=False)

        app = build_app()
        add_security_headers_middleware(app)

        with TestClient(app) as client:
            response = client.get("/api/ping")

        assert response.status_code == 200
        assert (
            response.headers["Strict-Transport-Security"]
            == "max-age=31536000; includeSubDomains; preload"
        )
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert (
            response.headers["Permissions-Policy"]
            == "geolocation=(), camera=(), microphone=(), payment=()"
        )
        assert (
            response.headers["Content-Security-Policy"]
            == "default-src 'none'; frame-ancestors 'none'"
        )

    def test_frontend_routes_skip_csp_and_debug_mode_skips_hsts(self, monkeypatch):
        from backend.middleware import security_headers

        monkeypatch.setattr(security_headers.settings, "DEBUG_MODE", True, raising=False)

        app = build_app()
        add_security_headers_middleware(app)

        with TestClient(app) as client:
            response = client.get("/ping")

        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
        assert "Content-Security-Policy" not in response.headers


class TestRequestIDMiddleware:
    def test_request_id_header_and_state(self):
        app = build_app()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/trace")
        def trace(request: Request):
            return {"request_id": request.state.request_id}

        with TestClient(app) as client:
            response = client.get("/trace")

        assert response.status_code == 200
        assert response.headers["X-Request-ID"]
        assert response.json()["request_id"] == response.headers["X-Request-ID"]

    def test_get_request_id_fallback(self):
        request = SimpleNamespace(state=SimpleNamespace())

        assert get_request_id(request) == "unknown"


class TestCSRFHelpers:
    def test_same_origin_matching(self):
        assert is_same_origin("http://localhost:5173", {"http://localhost:5173"}) is True
        assert is_same_origin("http://localhost:5173/path", {"http://localhost:5173"}) is True
        assert is_same_origin("http://localhost:5174", {"http://localhost:5173"}) is False
        assert is_same_origin("http://example.com", {"*"}) is True

    def test_token_helpers(self):
        token = generate_csrf_token()

        assert len(token) >= 32
        assert verify_csrf_token("token-a", "token-a") is True
        assert verify_csrf_token("token-a", "token-b") is False

    def test_validate_origin_referer_with_allowed_origin(self):
        app = build_app()
        app.add_middleware(CSRFProtectionMiddleware)

        with TestClient(app) as client:
            response = client.post("/api/update", headers={"Origin": "http://localhost:5173"})

        assert response.status_code == 200
        assert response.json()["updated"] is True

    def test_validate_origin_referer_blocks_invalid_origin(self):
        app = build_app()
        app.add_middleware(CSRFProtectionMiddleware)

        with TestClient(app) as client:
            response = client.post("/api/update", headers={"Origin": "http://evil.example"})

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

    def test_exempt_login_path_skips_validation(self):
        app = build_app()
        app.add_middleware(CSRFProtectionMiddleware)

        with TestClient(app) as client:
            response = client.post("/api/auth/login", headers={"Origin": "http://evil.example"})

        assert response.status_code == 200
        assert response.json()["logged_in"] is True

    def test_state_changing_methods_constant(self):
        assert STATE_CHANGING_METHODS == {"POST", "PUT", "PATCH", "DELETE"}
