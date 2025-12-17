# Multi-stage build for optimized full-system deployment
# Includes: Agent system, CLI tools, Backend API, Template library
FROM python:3.11-slim as builder

# Set working directory
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

# Production stage
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
COPY --from=builder /root/.local /home/appuser/.local

# Copy ENTIRE project (agents, backend, CLI, templates)
COPY --chown=appuser:appuser . .

# Copy template library from parent directory
# Note: This will be handled by docker-compose build context
# COPY --chown=appuser:appuser ../02_POST_TEMPLATE_LIBRARY.md ./02_POST_TEMPLATE_LIBRARY.md

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

# Expose backend API port
EXPOSE 8000

# Health check (backend API)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend API (which can call run_jumpstart.py and agents)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
