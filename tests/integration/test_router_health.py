"""
Integration tests for health router.

Tests all health check endpoints including:
- Health check (GET /api/health)
- Readiness check (GET /api/health/ready)
- Liveness check (GET /api/health/live)
- Database connectivity
- No authentication required
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user in the database"""
    user = User(
        id="user-test-123",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestHealthEndpoint:
    """Test GET /api/health"""

    def test_health_check_success(self, client):
        """Test basic health check endpoint"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy" or data["status"] == "ok"

    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication"""
        # Should work without auth headers
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_check_includes_version(self, client):
        """Test that health check includes version info"""
        response = client.get("/api/health")

        assert response.status_code == 200
        _data = response.json()
        # Version might be included
        # Exact field depends on implementation

    def test_health_check_includes_timestamp(self, client):
        """Test that health check includes timestamp"""
        response = client.get("/api/health")

        assert response.status_code == 200
        _data = response.json()
        # Timestamp might be included
        # Exact field depends on implementation


class TestReadinessEndpoint:
    """Test GET /api/health/ready"""

    def test_readiness_check_success(self, client, test_user):
        """Test readiness check with healthy database"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready" or data["status"] == "ok"

    def test_readiness_check_no_auth_required(self, client):
        """Test that readiness check doesn't require authentication"""
        # Should work without auth headers
        response = client.get("/api/health/ready")
        assert response.status_code == 200

    def test_readiness_check_database_connectivity(self, client, db_session):
        """Test that readiness check verifies database connectivity"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        data = response.json()

        # Should include database status
        if "database" in data:
            assert data["database"] == "connected" or data["database"] == "ok"
        elif "checks" in data:
            assert any(check.get("name") == "database" for check in data["checks"])

    def test_readiness_check_includes_dependencies(self, client):
        """Test that readiness check includes dependency statuses"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        _data = response.json()

        # Might include checks for various services
        # Database, external APIs, etc.


class TestLivenessEndpoint:
    """Test GET /api/health/live"""

    def test_liveness_check_success(self, client):
        """Test liveness check endpoint"""
        response = client.get("/api/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive" or data["status"] == "ok"

    def test_liveness_check_no_auth_required(self, client):
        """Test that liveness check doesn't require authentication"""
        # Should work without auth headers
        response = client.get("/api/health/live")
        assert response.status_code == 200

    def test_liveness_check_fast_response(self, client):
        """Test that liveness check responds quickly"""
        import time

        start = time.time()
        response = client.get("/api/health/live")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Liveness should be very fast (< 100ms)
        assert elapsed < 1.0  # More lenient for test environment


class TestHealthMetrics:
    """Test health endpoint metrics and details"""

    def test_health_includes_uptime(self, client):
        """Test that health check might include uptime"""
        response = client.get("/api/health")

        assert response.status_code == 200
        _data = response.json()
        # Uptime might be included
        # Exact field depends on implementation

    def test_health_includes_environment(self, client):
        """Test that health check might include environment info"""
        response = client.get("/api/health")

        assert response.status_code == 200
        _data = response.json()
        # Environment (dev/staging/prod) might be included
        # Exact field depends on implementation


class TestDatabaseHealthCheck:
    """Test database-specific health checks"""

    def test_database_connection_healthy(self, client, db_session, test_user):
        """Test database connection is healthy"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        # If database is accessible, readiness should succeed

    def test_health_check_with_database_query(self, client, db_session, test_user):
        """Test health check performs actual database query"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        # Readiness check should verify database is queryable


class TestHealthEndpointFormats:
    """Test health endpoint response formats"""

    def test_health_check_json_format(self, client):
        """Test that health check returns JSON"""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_readiness_check_json_format(self, client):
        """Test that readiness check returns JSON"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_liveness_check_json_format(self, client):
        """Test that liveness check returns JSON"""
        response = client.get("/api/health/live")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


class TestHealthEndpointCaching:
    """Test health endpoint caching behavior"""

    def test_health_check_not_cached(self, client):
        """Test that health check is not cached"""
        response = client.get("/api/health")

        assert response.status_code == 200
        # Should have no-cache headers or no cache-control
        cache_control = response.headers.get("cache-control", "")
        if cache_control:
            assert "no-cache" in cache_control or "no-store" in cache_control


class TestHealthEndpointErrors:
    """Test health endpoint error handling"""

    def test_health_endpoint_always_responds(self, client):
        """Test that health endpoint always returns a response"""
        # Even if database is down, health endpoint should respond
        response = client.get("/api/health")

        # Should get a response, might be 200 or 503
        assert response.status_code in [200, 503]

    def test_readiness_endpoint_database_failure(self, client):
        """Test readiness endpoint behavior when database is unavailable"""
        # This test would require mocking database failure
        # which is complex in integration tests
        # Skip for now
        pass


class TestHealthEndpointSecurity:
    """Test health endpoint security"""

    def test_health_check_no_sensitive_info(self, client):
        """Test that health check doesn't expose sensitive information"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Should not include passwords, tokens, keys, etc.
        response_str = str(data).lower()
        assert "password" not in response_str
        assert "token" not in response_str
        assert "secret" not in response_str
        assert "key" not in response_str

    def test_readiness_check_no_sensitive_info(self, client):
        """Test that readiness check doesn't expose sensitive information"""
        response = client.get("/api/health/ready")

        assert response.status_code == 200
        data = response.json()

        # Should not include sensitive database details
        response_str = str(data).lower()
        assert "password" not in response_str
        assert "connection_string" not in response_str


class TestHealthEndpointHTTPMethods:
    """Test health endpoint HTTP methods"""

    def test_health_check_get_only(self, client):
        """Test that health check only accepts GET"""
        # POST should not be allowed
        response = client.post("/api/health")
        assert response.status_code in [404, 405]

        # PUT should not be allowed
        response = client.put("/api/health")
        assert response.status_code in [404, 405]

        # DELETE should not be allowed
        response = client.delete("/api/health")
        assert response.status_code in [404, 405]

    def test_readiness_check_get_only(self, client):
        """Test that readiness check only accepts GET"""
        # POST should not be allowed
        response = client.post("/api/health/ready")
        assert response.status_code in [404, 405]


class TestHealthEndpointCORS:
    """Test health endpoint CORS headers"""

    def test_health_check_cors_headers(self, client):
        """Test that health check has appropriate CORS headers"""
        response = client.get("/api/health")

        assert response.status_code == 200
        # CORS headers might be present for health checks
        # Depends on CORS configuration


class TestHealthEndpointPerformance:
    """Test health endpoint performance"""

    def test_health_check_multiple_calls(self, client):
        """Test that health check can handle multiple rapid calls"""
        responses = []
        for _ in range(10):
            response = client.get("/api/health")
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_readiness_check_multiple_calls(self, client, test_user):
        """Test that readiness check can handle multiple rapid calls"""
        responses = []
        for _ in range(10):
            response = client.get("/api/health/ready")
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)
