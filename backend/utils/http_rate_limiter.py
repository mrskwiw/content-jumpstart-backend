"""
HTTP Rate Limiting (TR-004)

Protects API endpoints from abuse and DoS attacks by limiting request rates.

Rate Limits (from TRA report):
- /api/generator/*: 10 requests/hour per IP
- /api/projects/*: 100 requests/hour per user
- /api/pricing/*: 1000 requests/hour global
- Default: 60 requests/minute per IP

OWASP Top 10 2021: API4:2023 - Unrestricted Resource Consumption
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limit key - user ID if authenticated, otherwise IP address.

    This allows per-user rate limiting for authenticated endpoints
    and per-IP limiting for public endpoints.
    """
    # Check if user is authenticated (from auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["60/minute"],  # Default limit for all endpoints
    storage_uri="memory://",  # In-memory storage (use Redis for production clustering)
    strategy="fixed-window",  # Fixed time window
)


# Custom rate limit error message
def rate_limit_exceeded_handler(request: Request, exc):
    """Custom handler for rate limit exceeded errors"""
    return {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail,  # Seconds until reset
        }
    }
