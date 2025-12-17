"""
FastAPI main application entry point.

This module creates and configures the FastAPI application with:
- CORS middleware for frontend integration
- API routers for authentication and other endpoints
- Database initialization
- Exception handlers
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError

from .api import (
    auth_router,
    briefs_router,
    deliverables_router,
    posts_router,
    projects_router,
    uploads_router,
)
from .config import settings
from .db.database import init_db

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Client self-service portal for content generation projects",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(JWTError)
async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT-related errors."""
    return JSONResponse(
        status_code=401,
        content={"detail": "Invalid authentication credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    print(f"[OK] {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"[DB] Database: {settings.DATABASE_URL}")
    print(f"[CORS] CORS enabled for: {', '.join(settings.ALLOWED_ORIGINS)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    print(f"[SHUTDOWN] {settings.APP_NAME} shutting down")


# Include API routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(briefs_router)
app.include_router(uploads_router)
app.include_router(deliverables_router)
app.include_router(posts_router)


# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns basic application info and status.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": "development" if settings.DEBUG else "production",
    }


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """API-specific health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Add actual DB health check
    }
