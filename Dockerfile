# ============================================================
# STAGE 1: Build React Frontend
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY operator-dashboard/package.json operator-dashboard/package-lock.json ./

# Install dependencies
RUN npm ci --production=false

# Copy frontend source code
COPY operator-dashboard/ ./

# Build frontend for production with environment variables
# VITE_API_URL="" uses relative URLs (same origin as backend)
# This eliminates CORS issues in single-service deployment
ENV VITE_API_URL="" \
    VITE_USE_MOCKS=false \
    VITE_DEBUG_MODE=false

# Output will be in /frontend/dist
RUN npm run build


# ============================================================
# STAGE 2: Build Python Backend Dependencies
# ============================================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy all requirements files
COPY requirements.txt .
COPY backend/requirements.txt backend/requirements.txt

# Install Python dependencies (project root + backend)
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user -r backend/requirements.txt


# ============================================================
# STAGE 3: Production Image
# ============================================================
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /root/.local /home/appuser/.local

# Copy ENTIRE project (agents, backend, CLI, templates)
COPY --chown=appuser:appuser . .

# Copy built frontend from frontend-builder stage
# This is the key step that was missing!
COPY --from=frontend-builder --chown=appuser:appuser /frontend/dist /app/operator-dashboard/dist

# Create directories for data, logs, and outputs
RUN mkdir -p /app/data /app/logs /app/data/outputs /app/data/briefs && \
    chown -R appuser:appuser /app/data /app/logs

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/backend

# Switch to non-root user
USER appuser

# Expose backend API port (serves both API and frontend)
EXPOSE 8000

# Health check (backend API)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend API (which serves frontend static files)
# Single port 8000 serves:
#   - Frontend at /
#   - API at /api/*
#   - Health at /health
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
