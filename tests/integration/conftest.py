"""
Configuration for integration tests.

Sets up Python path to allow backend imports to work correctly.
"""
import sys
from pathlib import Path

# Add backend directory to Python path so relative imports work
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
