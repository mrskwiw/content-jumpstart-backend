# Docker Deployment Guide

## Overview

This guide provides quick start instructions for deploying the complete Content Jumpstart system using Docker. The Docker deployment includes:

- ✅ Backend FastAPI API
- ✅ Agent system (content generation)
- ✅ CLI tools (`run_jumpstart.py`)
- ✅ PostgreSQL 16 database
- ✅ Persistent volumes for data and logs
- ✅ Health checks and monitoring

**Architecture:** Monolithic deployment with all components in a single container.

---

## Quick Start

### 1. Prerequisites

**Required:**
- Docker 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 1.29+ (included with Docker Desktop)

**Optional:**
- Make (for convenience commands)

### 2. Environment Setup

```bash
# Copy environment template
cp .env.docker.example .env
```

**Edit `.env` and configure these REQUIRED variables:**

```env
# Generate secret key:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-generated-secret-key-here

# Strong password for PostgreSQL
POSTGRES_PASSWORD=your-secure-postgres-password

# Your Anthropic API key for content generation
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Production frontend URLs (comma-separated)
CORS_ORIGINS=https://dashboard.yourdomain.com
```

### 3. Build and Deploy

```bash
# Build Docker images
docker-compose build

# Start services in background
docker-compose up -d

# View logs (follow mode)
docker-compose logs -f api
```

### 4. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Expected output:
# {
#   "status": "healthy",
#   "timestamp": "2025-12-17T10:30:00Z",
#   "version": "1.0.0"
# }

# Check database health
curl http://localhost:8000/api/health/database

# View running services
docker-compose ps
```

**Access Points:**
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Database:** localhost:5432 (PostgreSQL)

---

## Docker Services

### Service: `api` (Full Content Jumpstart System)

**Container:** `content-jumpstart-api`

**Includes:**
- Backend FastAPI application
- Agent system (`src/agents/`, `agent/`)
- CLI tools (`run_jumpstart.py`)
- Template library
- All Python dependencies

**Ports:**
- 8000:8000 (HTTP API)

**Volumes:**
- `api-data` → `/app/data` (briefs, outputs)
- `api-logs` → `/app/logs` (application logs)

**Health Check:**
- Endpoint: `http://localhost:8000/health`
- Interval: 30s
- Timeout: 10s
- Retries: 3

### Service: `db` (PostgreSQL Database)

**Container:** `content-jumpstart-db`

**Image:** `postgres:16-alpine`

**Ports:**
- 5432:5432 (PostgreSQL)

**Volumes:**
- `postgres-data` → `/var/lib/postgresql/data`

**Health Check:**
- Command: `pg_isready -U postgres`
- Interval: 10s
- Timeout: 5s
- Retries: 5

---

## Common Commands

### Start/Stop Services

```bash
# Start services (detached)
docker-compose up -d

# Stop services (keeps containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (⚠️ DELETES ALL DATA)
docker-compose down -v
```

### View Logs

```bash
# Follow all logs
docker-compose logs -f

# Follow API logs only
docker-compose logs -f api

# Follow database logs only
docker-compose logs -f db

# View last 100 lines
docker-compose logs --tail=100 api
```

### Execute Commands

```bash
# Python version in container
docker-compose exec api python --version

# Database shell
docker-compose exec db psql -U postgres -d content_jumpstart

# Run migrations (if needed)
docker-compose exec api alembic upgrade head

# Seed demo data (DEVELOPMENT ONLY)
docker-compose exec api python backend/seed_demo_data.py

# Clear demo data (REQUIRED before production)
docker-compose exec api python backend/seed_demo_data.py --clear-only
```

### Rebuild and Update

```bash
# Rebuild images after code changes
docker-compose build

# Rebuild without cache (clean build)
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build

# Pull latest base images
docker-compose pull
```

---

## Environment Variables

### Security (REQUIRED)

```env
SECRET_KEY=your-generated-secret-key
POSTGRES_PASSWORD=your-secure-password
ANTHROPIC_API_KEY=sk-ant-your-production-key
```

### Application Settings

```env
ENVIRONMENT=production          # production, staging, development
DEBUG_MODE=false                # MUST be false in production
CORS_ORIGINS=https://dashboard.yourdomain.com
```

### Database Configuration

```env
POSTGRES_PORT=5432
DB_POOL_SIZE=20                 # Connection pool size
DB_MAX_OVERFLOW=40              # Max overflow connections
DB_POOL_RECYCLE=3600            # Recycle connections after 1 hour
DB_POOL_PRE_PING=true           # Test connections before use
```

### Anthropic API Settings

```env
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
RATE_LIMIT_REQUESTS_PER_MINUTE=2800    # 70% of Tier 2 limit
RATE_LIMIT_TOKENS_PER_MINUTE=280000
```

### Content Generation

```env
PARALLEL_GENERATION=true        # Enable async generation (4x faster)
MAX_CONCURRENT_API_CALLS=5      # Concurrent API requests
```

### Cache Settings

```env
CACHE_TTL_SHORT=300             # 5 minutes
CACHE_TTL_MEDIUM=600            # 10 minutes
CACHE_TTL_LONG=3600             # 1 hour
CACHE_MAX_SIZE_SHORT=1000
CACHE_MAX_SIZE_MEDIUM=1000
CACHE_MAX_SIZE_LONG=1000
```

**See `.env.docker.example` for complete list with explanations.**

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] **⚠️ CRITICAL: Purge all demo data from database**
- [ ] Generate secure `SECRET_KEY`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure production `ANTHROPIC_API_KEY`
- [ ] Set production `CORS_ORIGINS` (no wildcards!)
- [ ] Set `DEBUG_MODE=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Review rate limiting settings for your Anthropic tier
- [ ] Configure backup strategy for volumes
- [ ] Set up monitoring and alerting

### Purge Demo Data (CRITICAL)

**Option 1: Drop and recreate database (RECOMMENDED)**
```bash
# Stop services, remove volumes, restart
docker-compose down -v
docker-compose up -d
```

**Option 2: Clear data only (preserves schema)**
```bash
docker-compose exec api python backend/seed_demo_data.py --clear-only
```

**Verify database is empty:**
```bash
# Should return 0
docker-compose exec db psql -U postgres -d content_jumpstart -c "SELECT COUNT(*) FROM clients;"
```

### Security Best Practices

1. **Never use default values in production:**
   - Generate unique `SECRET_KEY`
   - Use strong `POSTGRES_PASSWORD` (16+ characters)

2. **Restrict CORS origins:**
   ```env
   # ✅ Good
   CORS_ORIGINS=https://dashboard.yourdomain.com,https://app.yourdomain.com

   # ❌ Bad - allows all origins
   CORS_ORIGINS=*
   ```

3. **Disable debug mode:**
   ```env
   DEBUG_MODE=false
   ```

4. **Use HTTPS in production:**
   - Deploy behind reverse proxy (nginx, Traefik, Caddy)
   - Configure SSL certificates
   - Force HTTPS redirects

5. **Secure database access:**
   - Don't expose port 5432 externally (remove from `docker-compose.yml`)
   - Use strong password
   - Consider database encryption

### Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## Monitoring & Health Checks

### Health Check Endpoints

```bash
# Basic health
curl http://localhost:8000/health

# Database health (pool, connections)
curl http://localhost:8000/api/health/database

# Cache health (hit rates, performance)
curl http://localhost:8000/api/health/cache

# Query profiling (slow queries)
curl http://localhost:8000/api/health/profiling

# Full health check (all subsystems)
curl http://localhost:8000/api/health/full
```

### View Service Status

```bash
# Container status
docker-compose ps

# Resource usage
docker stats content-jumpstart-api content-jumpstart-db

# Container health
docker inspect content-jumpstart-api | grep Health -A 10
```

---

## Data Persistence & Backups

### Persistent Volumes

Docker creates three volumes:

1. **`postgres-data`** - PostgreSQL database files
2. **`api-data`** - Application data (briefs, outputs)
3. **`api-logs`** - Application logs

**List volumes:**
```bash
docker volume ls | grep content-jumpstart
```

**Inspect volume:**
```bash
docker volume inspect content-jumpstart_postgres-data
```

### Backup Volumes

**Backup database volume:**
```bash
docker run --rm \
  -v content-jumpstart_postgres-data:/data \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data
```

**Backup application data:**
```bash
docker run --rm \
  -v content-jumpstart_api-data:/data \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/api-data-backup-$(date +%Y%m%d).tar.gz /data
```

**Restore volume:**
```bash
docker run --rm \
  -v content-jumpstart_postgres-data:/data \
  -v $(pwd):/backup \
  alpine \
  tar xzf /backup/postgres-backup-20251217.tar.gz -C /
```

### Database Dumps

**Create SQL dump:**
```bash
docker-compose exec db pg_dump -U postgres content_jumpstart > backup_$(date +%Y%m%d).sql
```

**Restore from SQL dump:**
```bash
cat backup_20251217.sql | docker-compose exec -T db psql -U postgres content_jumpstart
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs api
docker-compose logs db
```

**Common issues:**
- Missing environment variables → Check `.env` file
- Port conflicts → Change ports in `docker-compose.yml`
- Permission errors → Check volume permissions

### Database Connection Errors

**Symptoms:**
- API can't connect to database
- Health check fails

**Solutions:**
```bash
# Check database is running
docker-compose ps db

# Check database health
docker-compose exec db pg_isready -U postgres

# Restart database
docker-compose restart db

# Check connection from API container
docker-compose exec api ping db
```

### High Memory Usage

**Check resource usage:**
```bash
docker stats
```

**Solutions:**
- Reduce `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
- Reduce cache sizes (`CACHE_MAX_SIZE_*`)
- Add resource limits to `docker-compose.yml`

### Slow Performance

**Symptoms:**
- API response times > 1 second
- High database CPU

**Solutions:**
```bash
# Check query profiling
curl http://localhost:8000/api/health/profiling

# Increase cache TTLs
# Edit .env:
CACHE_TTL_MEDIUM=1200
CACHE_TTL_LONG=7200

# Restart services
docker-compose restart
```

### Volume Cleanup

**Remove stopped containers:**
```bash
docker-compose down
```

**Remove volumes (⚠️ DELETES ALL DATA):**
```bash
docker-compose down -v
```

**Remove unused images:**
```bash
docker image prune -a
```

---

## Advanced Configuration

### Custom Network

The deployment uses a custom bridge network `content-jumpstart` for service communication.

**Inspect network:**
```bash
docker network inspect content-jumpstart
```

### Multi-Container Scaling

**Note:** API service is stateful (uses local file system). Scaling requires:
- Shared volume for data
- Load balancer with sticky sessions
- OR move to stateless architecture

```bash
# NOT recommended without changes
docker-compose up -d --scale api=3
```

### Optional: Operator Dashboard

Uncomment dashboard service in `docker-compose.yml`:

```yaml
dashboard:
  build:
    context: ./operator-dashboard
    dockerfile: Dockerfile
  container_name: content-jumpstart-dashboard
  ports:
    - "80:80"
  environment:
    - VITE_API_URL=http://api:8000
  depends_on:
    - api
  restart: unless-stopped
  networks:
    - content-jumpstart
```

---

## Files Reference

All Docker deployment files are in the Project root:

- **`Dockerfile`** - Multi-stage build definition
- **`docker-compose.yml`** - Service orchestration
- **`.env.docker.example`** - Environment variable template
- **`.dockerignore`** - Build exclusion rules

---

## Additional Resources

### Documentation

- **Production Deployment:** `backend/PRODUCTION_DEPLOYMENT.md`
- **Backend Setup:** `backend/README.md`
- **Operator Dashboard:** `OPERATOR_DASHBOARD.md`
- **Project Overview:** `CLAUDE.md`

### Support

- **Issues:** Check logs with `docker-compose logs`
- **Health Checks:** Monitor endpoints at `/api/health/*`
- **API Docs:** http://localhost:8000/docs

---

**Last Updated:** December 17, 2025
**Version:** 1.0.0
