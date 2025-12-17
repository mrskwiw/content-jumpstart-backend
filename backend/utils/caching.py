"""
Response caching utilities for FastAPI.

Provides:
- ETag generation and validation
- Cache-Control header management
- Conditional response handling (304 Not Modified)
"""
import hashlib
import json
from typing import Any, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse


class CacheConfig:
    """Cache configuration for different resource types"""

    # Static resources (rarely change)
    TEMPLATES = {
        "max_age": 3600,  # 1 hour
        "stale_while_revalidate": 86400,  # 1 day
    }

    # Dynamic resources (change frequently)
    POSTS = {
        "max_age": 300,  # 5 minutes
        "stale_while_revalidate": 600,  # 10 minutes
    }

    PROJECTS = {
        "max_age": 300,  # 5 minutes
        "stale_while_revalidate": 600,  # 10 minutes
    }

    CLIENTS = {
        "max_age": 600,  # 10 minutes
        "stale_while_revalidate": 1800,  # 30 minutes
    }

    # User-specific resources (no shared cache)
    USER_DATA = {
        "max_age": 0,
        "private": True,
    }

    # Real-time resources (no cache)
    REAL_TIME = {
        "no_cache": True,
        "no_store": True,
    }


def generate_etag(data: Any) -> str:
    """
    Generate ETag from response data.

    Args:
        data: Response data (dict, list, or any JSON-serializable object)

    Returns:
        ETag string (MD5 hash of JSON representation)

    Example:
        etag = generate_etag({"id": "123", "name": "Test"})
        # Returns: "a3f5c8d2e1b4..."
    """
    # Convert to stable JSON representation
    json_str = json.dumps(data, sort_keys=True, default=str)

    # Generate MD5 hash
    hash_obj = hashlib.md5(json_str.encode())
    etag = hash_obj.hexdigest()

    return f'"{etag}"'  # ETags should be quoted


def build_cache_control_header(config: Dict[str, Any]) -> str:
    """
    Build Cache-Control header from config dict.

    Args:
        config: Cache configuration with keys like max_age, private, no_cache, etc.

    Returns:
        Cache-Control header string

    Example:
        header = build_cache_control_header({"max_age": 300, "stale_while_revalidate": 600})
        # Returns: "max-age=300, stale-while-revalidate=600"
    """
    directives = []

    # No-cache directives
    if config.get("no_cache"):
        directives.append("no-cache")

    if config.get("no_store"):
        directives.append("no-store")

    if config.get("must_revalidate"):
        directives.append("must-revalidate")

    # Visibility directives
    if config.get("private"):
        directives.append("private")
    elif config.get("public"):
        directives.append("public")

    # Age directives
    if "max_age" in config:
        directives.append(f"max-age={config['max_age']}")

    if "s_maxage" in config:
        directives.append(f"s-maxage={config['s_maxage']}")

    if "stale_while_revalidate" in config:
        directives.append(f"stale-while-revalidate={config['stale_while_revalidate']}")

    if "stale_if_error" in config:
        directives.append(f"stale-if-error={config['stale_if_error']}")

    return ", ".join(directives)


def check_etag_match(request: Request, etag: str) -> bool:
    """
    Check if request's If-None-Match header matches the given ETag.

    Args:
        request: FastAPI request object
        etag: ETag to compare against

    Returns:
        True if ETags match (resource unchanged), False otherwise
    """
    if_none_match = request.headers.get("If-None-Match")

    if not if_none_match:
        return False

    # Handle multiple ETags in If-None-Match
    client_etags = [tag.strip() for tag in if_none_match.split(",")]

    return etag in client_etags


def add_cache_headers(
    response: Response,
    cache_config: Dict[str, Any],
    etag: Optional[str] = None,
) -> Response:
    """
    Add caching headers to response.

    Args:
        response: FastAPI response object
        cache_config: Cache configuration dict
        etag: Optional ETag to include

    Returns:
        Response with added headers
    """
    # Add Cache-Control header
    cache_control = build_cache_control_header(cache_config)
    if cache_control:
        response.headers["Cache-Control"] = cache_control

    # Add ETag header
    if etag:
        response.headers["ETag"] = etag

    # Add Vary header for content negotiation
    response.headers["Vary"] = "Accept-Encoding, Authorization"

    return response


def create_cacheable_response(
    data: Any,
    cache_config: Dict[str, Any],
    request: Request,
    status_code: int = 200,
) -> Response:
    """
    Create a cacheable JSON response with ETag support.

    If the client's If-None-Match header matches the ETag,
    returns 304 Not Modified instead of the full response.

    Args:
        data: Response data (will be JSON-encoded)
        cache_config: Cache configuration dict
        request: FastAPI request object
        status_code: HTTP status code (default 200)

    Returns:
        JSONResponse with caching headers, or 304 if ETag matches

    Example:
        return create_cacheable_response(
            data=posts,
            cache_config=CacheConfig.POSTS,
            request=request
        )
    """
    # Generate ETag from data
    etag = generate_etag(data)

    # Check if client has cached version
    if check_etag_match(request, etag):
        # Return 304 Not Modified (no body)
        response = Response(status_code=304)
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = build_cache_control_header(cache_config)
        return response

    # Create full JSON response
    response = JSONResponse(content=data, status_code=status_code)

    # Add caching headers
    add_cache_headers(response, cache_config, etag)

    return response


# Cache invalidation helpers
class CacheInvalidator:
    """
    Helper class for cache invalidation patterns.

    In a real production system, this would integrate with Redis or similar
    to track and invalidate cached resources.
    """

    @staticmethod
    def get_invalidation_header(resource_types: list[str]) -> Dict[str, str]:
        """
        Get headers to signal cache invalidation for specific resource types.

        Args:
            resource_types: List of resource types to invalidate (e.g., ["posts", "projects"])

        Returns:
            Dict of headers to add to response

        Example:
            headers = CacheInvalidator.get_invalidation_header(["posts"])
            # Client can use this to invalidate local caches
        """
        return {
            "X-Cache-Invalidate": ",".join(resource_types),
            "X-Cache-Timestamp": str(int(hashlib.md5(str(resource_types).encode()).hexdigest()[:8], 16))
        }


# Common cache configurations
def get_cache_config_for_resource(resource_type: str) -> Dict[str, Any]:
    """
    Get appropriate cache configuration for a resource type.

    Args:
        resource_type: Type of resource (posts, projects, clients, etc.)

    Returns:
        Cache configuration dict
    """
    configs = {
        "posts": CacheConfig.POSTS,
        "projects": CacheConfig.PROJECTS,
        "clients": CacheConfig.CLIENTS,
        "templates": CacheConfig.TEMPLATES,
        "user": CacheConfig.USER_DATA,
        "realtime": CacheConfig.REAL_TIME,
    }

    return configs.get(resource_type, CacheConfig.POSTS)  # Default to POSTS config
