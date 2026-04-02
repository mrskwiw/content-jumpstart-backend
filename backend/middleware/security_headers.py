"""
Security Headers Middleware - TR-011

Adds security headers to all HTTP responses to protect against common attacks.

Headers Added:
- Strict-Transport-Security (HSTS): Enforce HTTPS
- X-Content-Type-Options: Prevent MIME sniffing
- X-Frame-Options: Prevent clickjacking
- X-XSS-Protection: Enable browser XSS filter
- Referrer-Policy: Control referrer information
- Permissions-Policy: Restrict browser features

ALE Prevented: $3,000/year
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import settings
from backend.utils.logger import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # HSTS (HTTP Strict Transport Security) - TR-011
        # Tells browsers to only connect via HTTPS for the next 1 year
        # includeSubDomains: Apply to all subdomains
        # preload: Allow inclusion in browser HSTS preload lists
        if not settings.DEBUG_MODE:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent MIME sniffing attacks
        # Browsers must respect declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        # Page cannot be embedded in any <iframe>, <frame>, etc.
        response.headers["X-Frame-Options"] = "DENY"

        # Enable browser XSS protection
        # Deprecated in modern browsers but harmless to include
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        # Only send origin for same-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features (Privacy-focused)
        # Disable geolocation, camera, microphone, etc.
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=()"
        )

        # Content Security Policy (CSP) - Only for API endpoints
        # Frontend routes need permissive policy for React app
        if request.url.path.startswith("/api"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        # Don't set CSP for frontend routes - let React handle it

        return response


def add_security_headers_middleware(app):
    """Add security headers middleware to FastAPI app"""
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware enabled (TR-011)")


def enforce_https_redirect(app):
    """
    HTTPS redirect is intentionally disabled.

    Render (and most PaaS providers) terminate TLS at the edge and forward
    requests to the app as plain HTTP internally. Adding HTTPSRedirectMiddleware
    causes an infinite redirect loop: Render sends HTTP → app redirects to
    HTTPS → Render forwards as HTTP → repeat.

    HTTPS is enforced at the Render layer. HSTS headers are set by
    SecurityHeadersMiddleware to instruct browsers to use HTTPS directly.
    """
    logger.info("HTTPS redirect skipped — handled by Render edge (TR-011)")
