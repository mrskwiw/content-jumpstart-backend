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
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from routers import auth, briefs, clients, deliverables, generator, health, posts, projects, research, runs

# Import models so SQLAlchemy can create tables
import models  # noqa: F401
from config import settings
from database import init_db
from utils.rate_limiter import rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Runs on startup and shutdown.
    """
    # Startup
    print(">> Starting Content Jumpstart API...")
    print(
        f">> Rate Limits: {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min, {settings.RATE_LIMIT_TOKENS_PER_MINUTE} tokens/min"
    )
    print(f">> CORS Origins: {settings.cors_origins_list}")
    print(f">> DEBUG: CORS_ORIGINS env var = '{settings.CORS_ORIGINS}'")

    # Initialize database
    init_db()
    print(">> Database initialized")

    # Auto-seed users if database is empty
    from database import SessionLocal
    from models.user import User
    from utils.auth import get_password_hash
    import uuid

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            print(">> No users found - creating default users...")
            users_to_create = [
                {
                    "email": "mrskwiw@gmail.com",
                    "full_name": "Primary User",
                },
                {
                    "email": "michele.vanhy@gmail.com",
                    "full_name": "Secondary User",
                }
            ]

            for user_data in users_to_create:
                user = User(
                    id=f"user-{uuid.uuid4().hex[:12]}",
                    email=user_data["email"],
                    hashed_password=get_password_hash("Random!1Pass"),
                    full_name=user_data["full_name"],
                    is_active=True
                )
                db.add(user)

            db.commit()
            print(f">> Created {len(users_to_create)} default users")
            print(">> Default password: Random!1Pass")
        else:
            print(f">> Found {user_count} existing users")
    finally:
        db.close()

    yield  # Application runs here

    # Shutdown
    print(">> Shutting down Content Jumpstart API...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Backend API for 30-Day Content Jumpstart Operator Dashboard",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
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


# SPA routing middleware (handles frontend routes without breaking API)
@app.middleware("http")
async def spa_routing_middleware(request: Request, call_next):
    """
    Serve index.html for 404s on non-API routes (enables React Router deep-links).

    This allows:
    - API routes to return JSON 404s properly
    - Frontend routes (/login, /dashboard, etc.) to load the React app
    - No interference with API routing
    """
    response = await call_next(request)

    # If 404 and not an API/docs/health route, serve index.html
    if response.status_code == 404 and not request.url.path.startswith("/api"):
        if request.url.path not in ["/docs", "/redoc", "/openapi.json", "/health"]:
            frontend_build_dir = Path(__file__).parent.parent / "operator-dashboard" / "dist"
            if frontend_build_dir.exists():
                return FileResponse(frontend_build_dir / "index.html")

    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns API status and rate limit statistics.
    """
    usage_stats = rate_limiter.get_usage_stats()
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "debug_mode": settings.DEBUG_MODE,
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


# Root endpoint - COMMENTED OUT to allow frontend serving at /
# API information available at /health and /docs
# @app.get("/", tags=["Root"])
# async def root():
#     """Root endpoint with API information"""
#     return {
#         "message": "Content Jumpstart API",
#         "version": settings.API_VERSION,
#         "docs": "/docs",
#         "health": "/health",
#     }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    if settings.DEBUG_MODE:
        # In debug mode, return full error details
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            },
        )
    else:
        # In production, return generic error
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )


# Static file serving for React frontend (defined BEFORE including routers)
# This eliminates CORS issues by serving frontend from same origin as API
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "operator-dashboard" / "dist"

if FRONTEND_BUILD_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"), name="assets")

    # Root route: serve React app
    @app.get("/")
    async def serve_root():
        """Serve React app at root URL"""
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

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
app.include_router(health.router, prefix="/api", tags=["Health & Monitoring"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(briefs.router, prefix="/api/briefs", tags=["Briefs"])
app.include_router(runs.router, prefix="/api/runs", tags=["Runs"])
app.include_router(deliverables.router, prefix="/api/deliverables", tags=["Deliverables"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(generator.router, prefix="/api/generator", tags=["Generator"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG_MODE,
        log_level="debug" if settings.DEBUG_MODE else "info",
    )
