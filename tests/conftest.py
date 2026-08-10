import pytest
import os
import sys
from pathlib import Path

# MUST be set before any backend imports to prevent FileHandler creation
# during pytest collection (fixes ValueError: I/O operation on closed file)
os.environ["TESTING"] = "1"


def pytest_ignore_collect(collection_path, config):
    """Skip Windows reserved device names (NUL, CON, PRN, etc.) during collection."""
    reserved = {"NUL", "CON", "PRN", "AUX"}
    if collection_path.name.upper() in reserved:
        return True
    # Skip COM1-COM9 and LPT1-LPT9
    if len(collection_path.name) == 4 and collection_path.name[:3].upper() in {"COM", "LPT"}:
        return True
    return None


# Add project directory to Python path for imports.
# Tests now live INSIDE the repo at project/tests/, so the project root is the
# parent of this file's parent (project/tests/conftest.py -> project/).
# (Was `.parent.parent / "project"` when tests lived at ../tests, outside the repo.)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set up test environment before any imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-anthropic-for-testing-only")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")
# GAP-AUTH-02: production defaults REQUIRE_EMAIL_VERIFICATION=True, which gates every
# authenticated request. Test fixtures create users straight through the ORM (unverified
# by column default) and then log in for real, so the gate is off by default here and the
# tests that are ABOUT the gate turn it on explicitly (see test_email_verification_api.py).
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "false")


@pytest.fixture(autouse=True)
def _clear_instance_config_cache():
    """Reset the instance-config read cache between tests (AUDIT-01 / P1).

    That cache is module-level and keyed by config key alone, which is correct in
    production — one process serves exactly one instance database. Tests violate
    that assumption: each test builds a fresh DB while the cache persists, so a
    value written by one test would be read by the next. Autouse, because the
    failure mode is a confusing cross-test leak rather than an obvious error.
    """
    from backend.services.settings_service import invalidate_instance_config_cache

    invalidate_instance_config_cache()
    yield
    invalidate_instance_config_cache()
