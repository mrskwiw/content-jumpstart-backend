"""
Pytest configuration for backend integration tests.

Sets up test environment before imports to avoid configuration conflicts.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Add both project root and backend directory so legacy imports continue working.
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / "backend"
for path in (project_root, backend_dir):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Set minimal environment variables for testing
# This prevents Settings validation errors from conflicting .env files
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-integration-tests")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# GAP-AUTH-02: production defaults REQUIRE_EMAIL_VERIFICATION=True, which gates every
# authenticated request. Test fixtures create users straight through the ORM (unverified
# by column default) and then log in for real, so the gate is off by default here and the
# tests that are ABOUT the gate turn it on explicitly (see test_email_verification_api.py).
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "false")

# Keep pytest temp files inside a pre-created repo directory so Windows ACLs do not block tmp_path.
temp_root = project_root / "backend" / "data" / ".pytest-temp"
temp_root.mkdir(exist_ok=True)
for key in ("TMP", "TEMP", "TMPDIR"):
    os.environ[key] = str(temp_root)
tempfile.tempdir = str(temp_root)

# Prevent loading .env files during tests
os.environ["ENV_FILE"] = ".env.test.nonexistent"


@pytest.fixture
def client():
    """Create a TestClient for backend test modules that expect a shared client fixture."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as test_client:
        yield test_client


@pytest.fixture
def tmp_path():
    """Provide a stable repo-local temporary path for tests that need filesystem writes."""

    yield temp_root
