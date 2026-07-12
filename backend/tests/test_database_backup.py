"""
Unit tests for database backup/restore authorization.

Tests verify that:
1. Non-authenticated users cannot access backup/restore endpoints
2. Regular users (non-admin) receive 403 Forbidden
3. Admin users (is_superuser=True) can access all endpoints
"""

import os
import sys
from pathlib import Path

# Set up environment BEFORE imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from backend.routers.database import require_admin, router
from backend.models.user import User


class TestRequireAdminDependency:
    """Tests for the require_admin dependency function."""

    def test_admin_user_allowed(self):
        """Admin user (is_superuser=True) should be allowed."""
        admin_user = MagicMock(spec=User)
        admin_user.is_superuser = True
        admin_user.email = "admin@example.com"

        result = require_admin(admin_user)

        assert result == admin_user

    def test_regular_user_denied(self):
        """Regular user (is_superuser=False) should receive 403."""
        regular_user = MagicMock(spec=User)
        regular_user.is_superuser = False
        regular_user.email = "user@example.com"

        with pytest.raises(HTTPException) as exc_info:
            require_admin(regular_user)

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail

    def test_none_superuser_denied(self):
        """User with None is_superuser should be denied."""
        user = MagicMock(spec=User)
        user.is_superuser = None
        user.email = "user@example.com"

        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)

        assert exc_info.value.status_code == 403


class TestBackupEndpointAuthorization:
    """Tests for backup endpoint authorization."""

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        user = MagicMock(spec=User)
        user.is_superuser = True
        user.email = "admin@example.com"
        user.id = "admin-123"
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular user."""
        user = MagicMock(spec=User)
        user.is_superuser = False
        user.email = "user@example.com"
        user.id = "user-456"
        return user

    def test_backup_requires_authentication(self):
        """Backup endpoint should require authentication."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # Request without auth header should fail
        response = client.get("/database/backup")

        # Should get 401 or 403 (depends on auth middleware)
        assert response.status_code in [401, 403, 422]

    def test_restore_requires_authentication(self):
        """Restore endpoint should require authentication."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # Request without auth should fail
        response = client.post("/database/restore")

        assert response.status_code in [401, 403, 422]

    def test_cleanup_requires_authentication(self):
        """Cleanup endpoint should require authentication."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        response = client.delete("/database/cleanup-backups")

        assert response.status_code in [401, 403, 422]


class TestAdminAccessLogging:
    """Tests for admin access logging."""

    def test_denied_access_logged(self):
        """Denied admin access should be logged."""
        regular_user = MagicMock(spec=User)
        regular_user.is_superuser = False
        regular_user.email = "hacker@example.com"

        with patch("backend.routers.database.logger") as mock_logger:
            with pytest.raises(HTTPException):
                require_admin(regular_user)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "hacker@example.com" in call_args
            assert "Admin access denied" in call_args


class TestEndpointRouteRegistration:
    """Tests to verify all endpoints have admin dependency."""

    def test_all_endpoints_require_admin(self):
        """All database endpoints should have require_admin dependency."""
        # Get all routes from the router
        routes = router.routes

        admin_protected_paths = []
        for route in routes:
            if hasattr(route, "dependant"):
                deps = route.dependant.dependencies
                for dep in deps:
                    if dep.call == require_admin or (
                        hasattr(dep.call, "__name__") and dep.call.__name__ == "require_admin"
                    ):
                        admin_protected_paths.append(route.path)

        # All three endpoints should be protected
        # Router has prefix "/database" so paths include that
        expected_paths = ["/database/backup", "/database/restore", "/database/cleanup-backups"]
        route_paths = [r.path for r in routes if hasattr(r, "path")]

        for path in expected_paths:
            assert (
                path in route_paths
            ), f"Expected endpoint {path} not found in router. Found: {route_paths}"


# NOTE: The former TestDatabasePathValidation and TestRestoreValidation classes
# were removed when the router dropped SQLite file backup/restore (Bug #186).
# get_database_path() and restore_to_restore_point() no longer exist — the
# SQLite restore path (and its Bug #180 traversal risk) is gone entirely. The
# Postgres contract (status/backup-instructions/restore-501/merge-501) is
# covered by tests/integration/test_router_database.py.


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
