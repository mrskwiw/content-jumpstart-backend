"""
HTTP Rate Limiting (TR-004)

Protects API endpoints from abuse and DoS attacks by limiting request rates.

Rate Limits (from TRA report):
- /api/research/*: 5 requests/hour per IP+user (expensive AI operations $400-600/call)
- /api/auth/login: 10 requests/hour per IP (prevent brute force)
- /api/auth/register: 3 requests/hour per IP (prevent spam accounts)
- /api/assistant/*: 50 requests/hour per IP+user (Claude API chat)
- /api/generator/*: 10 requests/hour per IP+user (expensive operations)
- /api/projects/*: 100 requests/hour per user (standard operations)
- /api/briefs/*: 100 requests/hour per user (standard operations)
- /api/clients/*: 100 requests/hour per user (standard operations)
- /api/deliverables/*: 100 requests/hour per user (standard operations)
- /api/posts/*: 1000 requests/hour per user (cheap read operations)
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


def get_composite_key(request: Request) -> str:
    """
    Combine IP + user ID to prevent VPN bypass.

    This is more secure than IP-only or user-only limiting because:
    - Prevents single user from bypassing limits via VPN/proxies
    - Prevents single IP from creating multiple accounts to bypass limits
    - Provides defense-in-depth for critical operations
    """
    ip = get_remote_address(request)
    user = getattr(request.state, "user", None)

    if user and hasattr(user, "id"):
        return f"{ip}:user-{user.id}"

    return f"{ip}:anonymous"


# Create limiter instance (default for all endpoints)
limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["60/minute"],  # Default limit for all endpoints
    storage_uri="memory://",  # In-memory storage (use Redis for production clustering)
    strategy="fixed-window",  # Fixed time window
)


# Strict limiter for expensive operations (research, generation)
# Uses composite key (IP + user ID) to prevent VPN bypass
strict_limiter = Limiter(
    key_func=get_composite_key,
    default_limits=[],  # No default - explicitly set per endpoint
    storage_uri="memory://",
    strategy="fixed-window",
)


# Standard limiter for normal operations (projects, clients, briefs)
standard_limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["100/hour"],  # Standard limit for authenticated operations
    storage_uri="memory://",
    strategy="fixed-window",
)


# Lenient limiter for cheap read operations (posts, health checks)
lenient_limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["1000/hour"],  # High limit for cheap operations
    storage_uri="memory://",
    strategy="fixed-window",
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
