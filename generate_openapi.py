"""Generate clean OpenAPI schema without debug output"""
import sys
import os
import json
import secrets
import logging

# OpenAPI generation imports the FastAPI app but never connects to the database
# (app.openapi() inspects routes/models; init_db only runs in the lifespan startup,
# which is not triggered here). Force the in-memory SQLite URL that config.py
# explicitly allows for non-production, so the PostgreSQL-only validation doesn't
# block schema generation locally or in CI. A fresh random SECRET_KEY satisfies the
# strength validator; none of these values are used during schema generation.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(32))
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-api03-openapi-generation-only-key")

# Suppress all logging
logging.disable(logging.CRITICAL)

# Suppress stdout/stderr temporarily
devnull = open(os.devnull, "w")
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = devnull
sys.stderr = devnull

try:
    from backend.main import app
finally:
    # Restore stdout/stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    devnull.close()

# Now print the clean JSON
print(json.dumps(app.openapi(), indent=2))
