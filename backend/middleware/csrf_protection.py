"""
CSRF Protection Middleware (TR-009)

Provides Cross-Site Request Forgery protection for state-changing operations.

Current auth model uses JWT tokens in Authorization headers, which provides
implicit CSRF protection. This middleware adds additional protection via
Origin/Referer validation for defense in depth.

For cookie-based auth migration, enable CSRF_TOKEN_REQUIRED in settings.
"""

import logging
import secrets
from typing import Set
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings

logger = logging.getLogger(__name__)

# Methods that change state and need CSRF protection
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that are exempt from CSRF protection (public endpoints)
CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/stripe/webhook",
    "/api/ops/render-webhook",  # Render webhook — Standard Webhooks signature is the auth (BUGS #239)
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def is_same_origin(request_origin: str, allowed_origins: Set[str]) -> bool:
    """
    Check if the request origin matches allowed origins.

    Args:
        request_origin: Origin header from request
        allowed_origins: Set of allowed origin URLs

    Returns:
        True if origin is allowed
    """
    if not request_origin:
        return False

    # Parse the origin
    parsed = urlparse(request_origin)
    origin_base = f"{parsed.scheme}://{parsed.netloc}"

    # Check against allowed origins
    for allowed in allowed_origins:
        if allowed == "*":
            return True
        if origin_base == allowed or request_origin == allowed:
            return True

    return False


def validate_origin_referer(request: Request) -> bool:
    """
    Validate Origin or Referer header matches allowed origins.

    Args:
        request: The incoming request

    Returns:
        True if origin/referer is valid
    """
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    allowed_origins = set(settings.cors_origins_list)

    # Check Origin header first
    if origin:
        if is_same_origin(origin, allowed_origins):
            return True
        logger.warning(f"CSRF: Invalid Origin header: {origin}")
        return False

    # Fall back to Referer header
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
        if is_same_origin(referer_origin, allowed_origins):
            return True
        logger.warning(f"CSRF: Invalid Referer header: {referer}")
        return False

    # No Origin or Referer - could be same-origin request
    # In strict mode, we'd reject this, but for compatibility we allow it
    # when using Authorization header (JWT) which provides CSRF protection
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # JWT auth provides implicit CSRF protection
        return True

    # Log but allow for backwards compatibility
    logger.debug("CSRF: No Origin/Referer header, but allowing due to compatibility mode")
    return True


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware.

    Validates Origin/Referer headers for state-changing requests.
    Provides defense in depth alongside JWT authentication.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)

        # Skip CSRF check for exempt paths
        path = request.url.path
        if path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Skip for paths under exempt prefixes
        for exempt in CSRF_EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        # Validate Origin/Referer
        if not validate_origin_referer(request):
            logger.warning(
                f"CSRF validation failed: {request.method} {path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "Request origin validation failed",
                    },
                },
            )

        return await call_next(request)


def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token.

    Returns:
        A cryptographically secure token string
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """
    Verify a CSRF token using constant-time comparison.

    Args:
        token: Token from request
        expected: Expected token from session

    Returns:
        True if tokens match
    """
    return secrets.compare_digest(token, expected)
