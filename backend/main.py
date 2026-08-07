"""
Content Jumpstart API - Main FastAPI Application

This is the backend API for the Operator Dashboard, providing:
- Direct CRUD endpoints for simple operations
- Agent-powered endpoints for complex workflows
- JWT authentication
- Rate limiting (70% of Anthropic API limits)
- Server-Sent Events for progress updates
- Static file serving for React frontend (eliminates CORS)
"""

import asyncio
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import (
    strict_limiter,
    standard_limiter,
    lenient_limiter,
)
from backend.routers import (
    admin_users,
    assistant,
    audit,
    metrics,
    cache,
    auth,
    briefs,
    client_research,
    clients,
    communications,
    costs,
    credits,
    database,
    deliverables,
    distribution,
    engagement,
    generator,
    health,
    media,
    posts,
    privacy,
    pricing,
    projects,
    research,
    runs,
    settings,
    stories,
    trends,
    stripe_checkout,
    client_keywords,
    teams,
    comments,
    approvals,
)
from slowapi.errors import RateLimitExceeded
from backend.utils.http_rate_limiter import (
    rate_limit_exceeded_handler as _rate_limit_exceeded_handler,
)

# Import models so SQLAlchemy can create tables
import backend.models  # noqa: F401
from backend.config import settings as app_settings
from backend.database import init_db
from backend.middleware.metrics import MetricsMiddleware
from backend.middleware.compression import add_compression_middleware
from backend.middleware.security_headers import (
    add_security_headers_middleware,
    enforce_https_redirect,
)
from backend.middleware.csrf_protection import CSRFProtectionMiddleware
from backend.middleware.request_id import RequestIDMiddleware, get_request_id
from backend.utils.rate_limiter import rate_limiter
from backend.utils.http_rate_limiter import limiter

# Load .env file to make variables available to os.getenv() for admin seeding
# On Render: .env file won't exist, variables come from Render dashboard
env_file_path = Path(__file__).parent / ".env"
if env_file_path.exists():
    load_dotenv(env_file_path)
    print(f">> Loaded environment from: {env_file_path}")
else:
    print(f">> No .env file found at {env_file_path}, using system environment variables")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Runs on startup and shutdown.
    """
    # Startup
    print(">> Starting Content Jumpstart API...")
    print(
        f">> Rate Limits: {app_settings.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min, {app_settings.RATE_LIMIT_TOKENS_PER_MINUTE} tokens/min"
    )
    print(f">> CORS Origins: {app_settings.cors_origins_list}")
    print(f">> DEBUG: CORS_ORIGINS env var = '{app_settings.CORS_ORIGINS}'")

    # Log database connection info
    from backend.database import engine

    db_url = str(engine.url)

    # Debug: Show DATABASE_URL from settings (helps diagnose Render env var issues)

    raw_db_url = os.getenv("DATABASE_URL", "NOT_SET")
    if raw_db_url != "NOT_SET" and "@" in raw_db_url:
        # Mask password for security
        raw_db_display = raw_db_url.split("@")[0].split(":")[0] + ":***@" + raw_db_url.split("@")[1]
    else:
        raw_db_display = raw_db_url[:50] if raw_db_url != "NOT_SET" else "NOT_SET"
    print(f">> DEBUG: DATABASE_URL env var = '{raw_db_display}'")
    print(f">> DEBUG: app_settings.DATABASE_URL = '{app_settings.DATABASE_URL[:80]}...'")

    # Mask password in URL for security
    if "@" in db_url:
        db_display = db_url.split("@")[1] if "@" in db_url else db_url
        print(f">> Database: PostgreSQL ({db_display})")
    else:
        print(">> Database: SQLite (local)")

    # Initialize database
    init_db()
    print(">> Database initialized")

    # Run pending migrations (idempotent — safe to run on every startup)
    from backend.migrations.add_run_qa_score import run_migration as migrate_qa_score
    from backend.migrations.add_deletion_audit_log import (
        run as migrate_deletion_audit_log,
    )

    migrate_qa_score()
    migrate_deletion_audit_log()

    # Auto-seed admin users if database is empty or forced reset
    from backend.database import SessionLocal
    from backend.models.user import User
    from backend.utils.auth import get_password_hash
    import uuid

    db = SessionLocal()
    try:
        user_count = db.query(User).count()

        # Check if admin seeding is forced (useful for password reset)
        force_admin_seed = os.getenv("FORCE_ADMIN_SEED", "false").lower() == "true"

        # Debug: Show seeding decision factors
        print(">> Admin seeding check:")
        print(f">>   - User count in DB: {user_count}")
        print(f">>   - FORCE_ADMIN_SEED: {os.getenv('FORCE_ADMIN_SEED', 'not set')}")
        print(f">>   - PRIMARY_ADMIN_EMAIL: {os.getenv('PRIMARY_ADMIN_EMAIL', 'not set')}")
        print(
            f">>   - DEFAULT_USER_PASSWORD: {'set' if os.getenv('DEFAULT_USER_PASSWORD') else 'not set'}"
        )
        print(f">>   - Will seed: {user_count == 0 or force_admin_seed}")

        if user_count == 0 or force_admin_seed:
            if force_admin_seed and user_count > 0:
                print(">> FORCE_ADMIN_SEED=true - Updating admin accounts...")
            else:
                print(">> No users found - creating admin users...")

            # Load admin credentials from environment
            # Format: ADMIN_USER_1_EMAIL, ADMIN_USER_1_NAME, ADMIN_USER_1_IS_SUPERUSER
            # Or use default users if not specified
            admin_users_config = []

            # Check for configured admin users (ADMIN_USER_1, ADMIN_USER_2, etc.)
            for i in range(1, 10):  # Support up to 9 admin users
                email = os.getenv(f"ADMIN_USER_{i}_EMAIL")
                if email:
                    admin_users_config.append(
                        {
                            "email": email,
                            "full_name": os.getenv(f"ADMIN_USER_{i}_NAME", f"Admin User {i}"),
                            "is_superuser": os.getenv(
                                f"ADMIN_USER_{i}_IS_SUPERUSER", "true"
                            ).lower()
                            == "true",
                        }
                    )

            # Use defaults if no admin users configured in env
            if not admin_users_config:
                primary_email = os.getenv("PRIMARY_ADMIN_EMAIL")
                secondary_email = os.getenv("SECONDARY_ADMIN_EMAIL")
                if not primary_email:
                    print(
                        ">> WARNING: No ADMIN_USER_* or PRIMARY_ADMIN_EMAIL set — skipping admin seed"
                    )
                    print(
                        ">> Set PRIMARY_ADMIN_EMAIL (and optionally SECONDARY_ADMIN_EMAIL) to seed admin accounts"
                    )
                else:
                    admin_users_config = [
                        {
                            "email": primary_email,
                            "full_name": os.getenv("PRIMARY_ADMIN_NAME", "Primary Admin"),
                            "is_superuser": True,
                        },
                    ]
                    if secondary_email:
                        admin_users_config.append(
                            {
                                "email": secondary_email,
                                "full_name": os.getenv("SECONDARY_ADMIN_NAME", "Secondary Admin"),
                                "is_superuser": True,
                            }
                        )

            # SECURITY FIX: Use environment variable for default password (TR-018)
            default_password = os.getenv("DEFAULT_USER_PASSWORD")

            if not default_password:
                # Generate secure random password if not provided
                default_password = secrets.token_urlsafe(16)
                print(">> " + "=" * 60)
                print(">> WARNING: DEFAULT_USER_PASSWORD not set in environment!")
                print(">> Generated secure random password for admin users")
                print(">> IMPORTANT: Use /api/auth/forgot-password to reset admin password")
                print(">> ")
                print(">> FOR PRODUCTION: Set DEFAULT_USER_PASSWORD in environment")
                print(">> " + "=" * 60)
            else:
                print(">> Using DEFAULT_USER_PASSWORD from environment")

            from datetime import datetime, timezone

            created_count = 0
            updated_count = 0
            for user_data in admin_users_config:
                # Check if user already exists (for force_admin_seed mode)
                existing_user = db.query(User).filter(User.email == user_data["email"]).first()

                if existing_user:
                    # Update existing user's password and superuser status
                    existing_user.hashed_password = get_password_hash(default_password)
                    # Revoke pre-existing sessions when the admin password is reset.
                    existing_user.password_changed_at = datetime.now(timezone.utc)
                    existing_user.is_superuser = user_data["is_superuser"]
                    existing_user.is_active = True
                    # GAP-AUTH-02: a force-reseed is the operator's break-glass recovery
                    # path, so it must also clear the verification gate — otherwise an
                    # unverified admin stays locked out no matter how often it runs.
                    if not existing_user.email_verified:
                        existing_user.email_verified = True
                        existing_user.email_verified_at = datetime.now(timezone.utc)
                    updated_count += 1
                    print(
                        f">> Updated admin: {user_data['email']} (superuser={user_data['is_superuser']})"
                    )
                else:
                    # Create new user; grant debug credits in dev/debug mode.
                    # GAP-AUTH-02: seeded admins are operator-provisioned (the address
                    # comes from instance env vars, not a signup form) and no verification
                    # email is sent on this path, so they start verified — otherwise a
                    # fresh instance would have no account able to log in at all.
                    user = User(
                        id=f"user-{uuid.uuid4().hex[:12]}",
                        email=user_data["email"],
                        hashed_password=get_password_hash(default_password),
                        full_name=user_data["full_name"],
                        is_active=True,
                        is_superuser=user_data["is_superuser"],
                        email_verified=True,
                        email_verified_at=datetime.now(timezone.utc),
                        credit_balance=(
                            app_settings.DEBUG_CREDITS if app_settings.DEBUG_MODE else 1000
                        ),
                    )
                    db.add(user)
                    created_count += 1
                    print(
                        f">> Created admin: {user_data['email']} (superuser={user_data['is_superuser']})"
                    )

            db.commit()

            if created_count > 0:
                print(f">> Created {created_count} admin user(s)")
            if updated_count > 0:
                print(f">> Updated {updated_count} admin user(s)")

            # Clear force flag reminder
            if force_admin_seed:
                print(">> NOTE: Set FORCE_ADMIN_SEED=false after admin accounts are configured")
        else:
            print(f">> Found {user_count} existing users")
    finally:
        db.close()

    # Optional in-process distribution scheduler (Phase 10). Enabled by
    # RUN_SCHEDULER=true; publishes due posts every SCHEDULER_INTERVAL_SECONDS.
    from backend.services.distribution import scheduler as distribution_scheduler

    scheduler_stop: Optional[asyncio.Event] = None
    scheduler_task = None
    if distribution_scheduler.enabled():
        scheduler_stop = asyncio.Event()
        scheduler_task = asyncio.create_task(distribution_scheduler.scheduler_loop(scheduler_stop))
        print(">> Distribution scheduler: ENABLED")
    else:
        print(">> Distribution scheduler: disabled (set RUN_SCHEDULER=true to enable)")

    # Optional in-process media scheduler (Phase 12). Shares RUN_SCHEDULER; polls
    # in-flight media renders every MEDIA_SCHEDULER_INTERVAL_SECONDS.
    from backend.services.media import scheduler as media_scheduler

    media_scheduler_stop: Optional[asyncio.Event] = None
    media_scheduler_task = None
    if media_scheduler.enabled():
        media_scheduler_stop = asyncio.Event()
        media_scheduler_task = asyncio.create_task(
            media_scheduler.scheduler_loop(media_scheduler_stop)
        )
        print(">> Media scheduler: ENABLED")
    else:
        print(">> Media scheduler: disabled (set RUN_SCHEDULER=true to enable)")

    yield  # Application runs here

    # Shutdown
    print(">> Shutting down Content Jumpstart API...")
    for stop_event, task in (
        (scheduler_stop, scheduler_task),
        (media_scheduler_stop, media_scheduler_task),
    ):
        if task is not None and stop_event is not None:
            stop_event.set()
            try:
                await asyncio.wait_for(task, timeout=10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()


# Create FastAPI app
app = FastAPI(
    title=app_settings.API_TITLE,
    version=app_settings.API_VERSION,
    description="Backend API for 30-Day Content Jumpstart Operator Dashboard",
    lifespan=lifespan,
)

# Add rate limiters to app state (TR-004: Multiple tiers for different operation costs)
app.state.limiter = limiter  # Default limiter
app.state.strict_limiter = strict_limiter  # For expensive operations (research, generation)
app.state.standard_limiter = standard_limiter  # For normal operations (projects, clients)
app.state.lenient_limiter = lenient_limiter  # For cheap operations (posts, health)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# TR-009: CSRF Protection middleware (validates Origin/Referer headers)
app.add_middleware(CSRFProtectionMiddleware)
# Request ID tracking middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)

# Add response compression (gzip)
add_compression_middleware(app)

# TR-011: Security headers (HSTS, X-Frame-Options, etc.)
add_security_headers_middleware(app)
enforce_https_redirect(app)


# CORS middleware
# Production: Restrict to specific origins, methods, and headers
# Development: More permissive for ease of development
if app_settings.DEBUG_MODE:
    # Development mode - permissive CORS for easier testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
else:
    # Production mode - restrictive CORS for security
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,  # Only whitelisted origins
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
        ],  # Explicit methods only
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],  # Only necessary headers
        expose_headers=[
            "X-Process-Time",
            "X-Total-Count",
            "Content-Disposition",
        ],  # Content-Disposition needed for file downloads
        max_age=3600,
    )


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 3))
    return response


# TR-011: Request body size limit middleware
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB default limit
MAX_CONTENT_LENGTH_BRIEFS = 1 * 1024 * 1024  # 1MB for brief uploads
MAX_CONTENT_LENGTH_VOICE = 5 * 1024 * 1024  # 5MB for voice samples


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    TR-011: Limit request body size to prevent DoS attacks.

    Limits:
    - Default: 10MB
    - Brief uploads: 1MB
    - Voice samples: 5MB
    - File uploads: 50MB (for DOCX exports)

    Returns 413 Payload Too Large if exceeded.
    """
    content_length = request.headers.get("content-length")

    if content_length:
        content_length = int(content_length)

        # Determine limit based on endpoint
        path = request.url.path
        if "/briefs" in path:
            max_size = MAX_CONTENT_LENGTH_BRIEFS
        elif "/voice" in path or "/samples" in path:
            max_size = MAX_CONTENT_LENGTH_VOICE
        elif "/deliverables" in path or "/export" in path:
            max_size = 50 * 1024 * 1024  # 50MB for exports
        else:
            max_size = MAX_CONTENT_LENGTH

        if content_length > max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds maximum size of {max_size // (1024 * 1024)}MB",
                    },
                },
            )

    return await call_next(request)


# SPA routing middleware (handles frontend routes without breaking API)
@app.middleware("http")
async def spa_routing_middleware(request: Request, call_next):
    """
    Serve index.html for 404s on non-API routes (enables React Router deep-links).

    This allows:
    - API routes to return JSON 404s properly
    - Frontend routes (/login, /dashboard, etc.) to load the React app
    - No interference with API routing

    Known frontend routes that should serve index.html:
    - /login, /dashboard, /dashboard/*, /wizard, etc.
    """
    path = request.url.path

    # List of paths that should NOT trigger SPA fallback
    excluded_prefixes = [
        "/api",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/assets",
        "/favicon.ico",
    ]

    # Check if this is a known frontend route BEFORE processing
    # This handles deep-links that would otherwise 404
    is_frontend_route = not any(
        path.startswith(prefix) for prefix in excluded_prefixes
    ) and not path.endswith(
        (
            ".js",
            ".css",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".json",
            ".map",
        )
    )

    try:
        response = await call_next(request)
    except RuntimeError as e:
        # Starlette raises RuntimeError("No response returned.") when its routing
        # finds no handler and nothing sends a response.  For SPA frontend routes
        # that is expected — serve index.html so React Router can handle the path.
        # All other RuntimeErrors (and all other exception types) still propagate
        # as 500s so real server failures are never silently masked.
        if "No response returned" in str(e) and is_frontend_route:
            frontend_build_dir = Path(__file__).parent.parent / "operator-dashboard" / "dist"
            index_file = frontend_build_dir / "index.html"
            if index_file.exists():
                spa_response = FileResponse(index_file)
                spa_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                spa_response.headers["Pragma"] = "no-cache"
                spa_response.headers["Expires"] = "0"
                return spa_response
        logger.error(
            f"Middleware error in spa_routing_middleware: {str(e)} [{request.method} {path}]"
        )
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": "Internal Server Error"},
            status_code=500,
        )
    except Exception as e:
        logger.error(
            f"Middleware error in spa_routing_middleware: {str(e)} [{request.method} {path}]"
        )
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": "Internal Server Error"},
            status_code=500,
        )

    if response is None:
        logger.error(
            f"SPA routing middleware received None response from call_next "
            f"[{request.method} {path}]"
        )
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": "Internal Server Error"},
            status_code=500,
        )

    # If 404 and looks like a frontend route, serve index.html
    if response.status_code == 404 and is_frontend_route:
        frontend_build_dir = Path(__file__).parent.parent / "operator-dashboard" / "dist"
        index_file = frontend_build_dir / "index.html"
        if index_file.exists():
            spa_response = FileResponse(index_file)
            # Prevent HTML caching to avoid chunk loading errors
            spa_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            spa_response.headers["Pragma"] = "no-cache"
            spa_response.headers["Expires"] = "0"
            return spa_response

    return response


# Health check endpoint
@app.get("/health", tags=["Health"], operation_id="health_check_get")
async def health_check_get(request: Request):
    """
    Health check endpoint (GET).

    Returns API status and rate limit statistics.
    """
    usage_stats = rate_limiter.get_usage_stats()
    return {
        "status": "healthy",
        "version": app_settings.API_VERSION,
        "debug_mode": app_settings.DEBUG_MODE,
        "rate_limits": {
            "requests_per_minute": {
                "current": usage_stats["requests"],
                "limit": usage_stats["requests_limit"],
                "available": usage_stats["requests_available"],
                "utilization_pct": usage_stats["requests_utilization"],
            },
            "tokens_per_minute": {
                "current": usage_stats["tokens"],
                "limit": usage_stats["tokens_limit"],
                "available": usage_stats["tokens_available"],
                "utilization_pct": usage_stats["tokens_utilization"],
            },
            "queue_length": usage_stats["queue_length"],
        },
    }


@app.head(
    "/health",
    tags=["Health"],
    operation_id="health_check_head",
    include_in_schema=False,
)
async def health_check_head():
    """Health check endpoint (HEAD) for monitoring tools."""
    return Response(status_code=200)


# Root endpoint - COMMENTED OUT to allow frontend serving at /
# API information available at /health and /docs
# @app.get("/", tags=["Root"])
# async def root():
#     """Root endpoint with API information"""
#     return {
#         "message": "Content Jumpstart API",
#         "version": app_settings.API_VERSION,
#         "docs": "/docs",
#         "health": "/health",
#     }


# Global exception handler (TR-010: Error sanitization)
from backend.services.account_state import AccountSuspendedError  # noqa: E402


@app.exception_handler(AccountSuspendedError)
async def account_suspended_handler(request: Request, exc: AccountSuspendedError):
    """Past-due / suspended account attempted a spend → 402 (S-01.4d).

    Reads are never routed here (only spends raise this), so viewing/exporting
    content stays available while billing is resolved.
    """
    return JSONResponse(
        status_code=402,
        content={
            "detail": (
                "Your subscription is past due or suspended. Update billing to "
                "resume generating — your existing content stays accessible."
            ),
            "account_state": exc.state,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions with error sanitization.

    TR-010: Prevents internal error details from leaking to clients.
    Full error details are logged server-side for debugging.
    """
    from backend.utils.error_sanitizer import create_safe_error_response

    # Get request ID for tracing
    request_id = get_request_id(request)

    # Create sanitized response (handles debug vs production mode internally)
    error_response = create_safe_error_response(exc, status_code=500, request_id=request_id)

    return JSONResponse(status_code=500, content=error_response)


# Static file serving for React frontend (defined BEFORE including routers)
# This eliminates CORS issues by serving frontend from same origin as API
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "operator-dashboard" / "dist"

if FRONTEND_BUILD_DIR.exists():
    # Serve static assets (JS, CSS, images) with long cache duration
    # These files have content hashes, so they can be cached indefinitely
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"), name="assets")

    # Root route: serve React app with no-cache headers
    @app.get("/", operation_id="serve_root_get")
    async def serve_root_get():
        """
        Serve React app at root URL with cache prevention.

        Critical: HTML file must not be cached to ensure users get
        the latest version and correct chunk references after deployments.
        """
        response = FileResponse(FRONTEND_BUILD_DIR / "index.html")
        # Prevent HTML caching to avoid chunk loading errors
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.head("/", operation_id="serve_root_head", include_in_schema=False)
    async def serve_root_head():
        """HEAD request for Render health checks."""
        return Response(status_code=200)

    # Favicon route: serve vite.svg as favicon
    @app.get("/favicon.ico")
    async def serve_favicon():
        """Serve favicon (uses vite.svg)"""
        favicon_path = FRONTEND_BUILD_DIR / "vite.svg"
        if favicon_path.exists():
            return FileResponse(favicon_path, media_type="image/svg+xml")
        return JSONResponse({"error": "Favicon not found"}, status_code=404)

    # Catch-all route removed - causes issues with API routing
    # Instead, we'll mount frontend as static files and handle SPA routing differently

    print(f">> Frontend static files enabled: {FRONTEND_BUILD_DIR}")
else:
    print(f">> WARNING: Frontend build directory not found: {FRONTEND_BUILD_DIR}")
    print(">> Run 'cd operator-dashboard && npm run build' to build frontend")


# Include API routers
# These MUST be registered before any catch-all routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin_users.router, prefix="/api/admin", tags=["Admin - User Management"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(comments.router, prefix="/api", tags=["Comments"])
app.include_router(approvals.router, prefix="/api", tags=["Approvals"])
app.include_router(
    health.router, prefix="/api", tags=["Health & Monitoring"]
)  # Routes at /api/health/...
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(client_keywords.router, prefix="/api/clients", tags=["Client Keywords"])
app.include_router(communications.router, prefix="/api", tags=["Communications"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(briefs.router, prefix="/api/briefs", tags=["Briefs"])
app.include_router(runs.router, prefix="/api/runs", tags=["Runs"])
app.include_router(deliverables.router, prefix="/api/deliverables", tags=["Deliverables"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(privacy.router, tags=["Privacy & GDPR"])
app.include_router(distribution.router, tags=["Distribution"])
app.include_router(engagement.router, tags=["Analytics & Engagement"])
app.include_router(media.router, tags=["Media Generation"])
app.include_router(stories.router, prefix="/api/stories", tags=["Stories"])
app.include_router(generator.router, prefix="/api/generator", tags=["Generator"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(client_research.router, prefix="/api/client-research", tags=["Client Research"])
app.include_router(trends.router, prefix="/api/trends", tags=["Google Trends"])
app.include_router(pricing.router, prefix="/api/pricing", tags=["Pricing"])
app.include_router(credits.router, prefix="/api", tags=["Credits"])  # Prefix included in router
app.include_router(costs.router, tags=["Costs"])  # Prefix included in router
app.include_router(assistant.router, prefix="/api/assistant", tags=["AI Assistant"])
app.include_router(settings.router, tags=["Settings"])  # Prefix included in router
app.include_router(database.router, prefix="/api", tags=["Database"])
app.include_router(cache.router, prefix="/api/cache", tags=["Cache Management"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics & Monitoring"])
app.include_router(stripe_checkout.router, prefix="/api/stripe", tags=["Payments"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Trail"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=app_settings.API_HOST,
        port=app_settings.API_PORT,
        reload=app_settings.DEBUG_MODE,
        log_level="debug" if app_settings.DEBUG_MODE else "info",
    )
