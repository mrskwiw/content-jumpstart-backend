"""
Pytest configuration for backend integration tests.

Sets up test environment before imports to avoid configuration conflicts.
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set minimal environment variables for testing
# This prevents Settings validation errors from conflicting .env files
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-integration-tests")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Prevent loading .env files during tests
os.environ["ENV_FILE"] = ".env.test.nonexistent"
