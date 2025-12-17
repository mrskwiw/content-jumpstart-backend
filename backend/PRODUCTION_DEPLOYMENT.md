# Production Deployment Guide

## Overview

This guide covers production deployment of the Content Jumpstart API backend with Week 3 performance optimizations (connection pooling, caching, query profiling).

**Last Updated:** December 15, 2025

---

## Quick Start

### 1. Copy Production Environment File

```bash
cp .env.production.example .env
```

### 2. Generate Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and set as `SECRET_KEY` in `.env`

### 3. Configure Database

**Option A: PostgreSQL (Recommended)**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/content_jumpstart
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

**Option B: SQLite (Development Only)**
```env
DATABASE_URL=sqlite:///./data/operator.db
```

### 4. Set Anthropic API Key

```env
ANTHROPIC_API_KEY=sk-ant-your-production-key-here
```

### 5. **⚠️ CRITICAL: Purge Demo Data**

**BEFORE deploying to production, you MUST purge all demo/seed data from the database!**

The development database contains demo data for testing purposes. This data includes:
- 15 sample clients
- 27 sample projects
- 10 sample runs
- 10 sample posts
- 15 sample deliverables

**To purge demo data:**

```bash
# Option 1: Drop and recreate database (RECOMMENDED)
# PostgreSQL
dropdb content_jumpstart
createdb content_jumpstart
python -c "from database import init_db; init_db()"

# SQLite
rm data/operator.db
python -c "from database import init_db; init_db()"

# Option 2: Clear data only (keeps schema)
python seed_demo_data.py --clear-only
```

**Verification:**
```bash
# PostgreSQL
psql -d content_jumpstart -c "SELECT COUNT(*) FROM clients;"
# Should return 0

# SQLite
sqlite3 data/operator.db "SELECT COUNT(*) FROM clients;"
# Should return 0
```

**❌ DO NOT skip this step!** Demo data in production will cause:
- Incorrect client information displayed
- Invalid project data
- Confusion for real users
- Potential data integrity issues

### 6. Deploy

```bash
# Using uvicorn (development/testing)
uvicorn main:app --host 0.0.0.0 --port 8000

# Using gunicorn (production)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Environment Configuration

### Critical Settings

#### SECRET_KEY
**NEVER use default value in production!**

Generate a strong secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set in `.env`:
```env
SECRET_KEY=your-generated-secret-here
```

#### DEBUG_MODE
**MUST be False in production for security:**
```env
DEBUG_MODE=False
```

Debug mode exposes internal stack traces and error details.

#### CORS_ORIGINS
Set to your production frontend domains:
```env
CORS_ORIGINS=https://dashboard.yourdomain.com,https://app.yourdomain.com
```

Never use wildcards (`*`) in production!

---

## Database Configuration

### PostgreSQL (Recommended)

#### Connection String Format
```
postgresql://[username]:[password]@[host]:[port]/[database]
```

#### Example Configurations

**Local PostgreSQL:**
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/content_jumpstart
```

**AWS RDS:**
```env
DATABASE_URL=postgresql://admin:password@mydb.abc123.us-east-1.rds.amazonaws.com:5432/content_jumpstart
```

**Heroku Postgres:**
```env
DATABASE_URL=postgres://user:password@ec2-host.compute-1.amazonaws.com:5432/database
```

**Google Cloud SQL:**
```env
DATABASE_URL=postgresql://user:password@/dbname?host=/cloudsql/project:region:instance
```

#### Connection Pool Settings

**Small Traffic (< 100 users):**
```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True
```

**Medium Traffic (100-1000 users):**
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True
```

**High Traffic (1000+ users):**
```env
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=True
```

**Connection Pool Monitoring:**
Monitor pool health at: `GET /api/health/database`

---

## Cache Configuration

### Cache TTL Tiers

#### Short Tier (5 minutes default)
**Use for:** Frequently changing data
- Active project lists
- Recent deliverables
- User session data

```env
CACHE_TTL_SHORT=300  # 5 minutes
```

#### Medium Tier (10 minutes default)
**Use for:** Moderately stable data
- Client lists
- Project details
- Template selections

```env
CACHE_TTL_MEDIUM=600  # 10 minutes
```

#### Long Tier (1 hour default)
**Use for:** Rarely changing data
- Template library
- System configuration
- Brand archetypes

```env
CACHE_TTL_LONG=3600  # 1 hour
```

### Cache Size Limits

**Recommendation based on available memory:**

**Small Instance (512 MB - 1 GB RAM):**
```env
CACHE_MAX_SIZE_SHORT=500
CACHE_MAX_SIZE_MEDIUM=500
CACHE_MAX_SIZE_LONG=500
```

**Medium Instance (2-4 GB RAM):**
```env
CACHE_MAX_SIZE_SHORT=1000
CACHE_MAX_SIZE_MEDIUM=1000
CACHE_MAX_SIZE_LONG=1000
```

**Large Instance (8+ GB RAM):**
```env
CACHE_MAX_SIZE_SHORT=5000
CACHE_MAX_SIZE_MEDIUM=5000
CACHE_MAX_SIZE_LONG=5000
```

**Cache Monitoring:**
Monitor cache health at: `GET /api/health/cache`

---

## Query Profiling Configuration

### Slow Query Thresholds

**Aggressive Monitoring (Optimize for Speed):**
```env
QUERY_PROFILING_SLOW_THRESHOLD_MS=50
QUERY_PROFILING_VERY_SLOW_THRESHOLD_MS=200
```

**Standard Monitoring (Recommended):**
```env
QUERY_PROFILING_SLOW_THRESHOLD_MS=100
QUERY_PROFILING_VERY_SLOW_THRESHOLD_MS=500
```

**Relaxed Monitoring (Large Scale):**
```env
QUERY_PROFILING_SLOW_THRESHOLD_MS=200
QUERY_PROFILING_VERY_SLOW_THRESHOLD_MS=1000
```

### Profiling Retention

**Short Retention (Active Debugging):**
```env
QUERY_PROFILING_RETENTION_SECONDS=3600  # 1 hour
```

**Standard Retention (Recommended):**
```env
QUERY_PROFILING_RETENTION_SECONDS=86400  # 24 hours
```

**Long Retention (Historical Analysis):**
```env
QUERY_PROFILING_RETENTION_SECONDS=604800  # 7 days
```

**Query Profiling Monitoring:**
Monitor query performance at: `GET /api/health/profiling`

---

## Rate Limiting Configuration

### Anthropic API Tier Limits

**Tier 1 (Default):**
- 50 RPM (requests per minute)
- 40,000 TPM (tokens per minute)

**Tier 2:**
- 4,000 RPM
- 400,000 TPM

**Tier 3:**
- 4,000 RPM
- 400,000 TPM

**Tier 4:**
- 10,000 RPM
- 2,000,000 TPM

### Recommended Settings (70% of Limit)

**Tier 1:**
```env
RATE_LIMIT_REQUESTS_PER_MINUTE=35
RATE_LIMIT_TOKENS_PER_MINUTE=28000
```

**Tier 2 (Recommended):**
```env
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000
```

**Tier 3:**
```env
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000
```

**Tier 4:**
```env
RATE_LIMIT_REQUESTS_PER_MINUTE=7000
RATE_LIMIT_TOKENS_PER_MINUTE=1400000
```

**Why 70%?** Leaves headroom for:
- Retry logic on failures
- Traffic spikes
- Multiple concurrent users
- Background jobs

---

## Content Generation Configuration

### Parallel Generation

**Enabled (Recommended):**
```env
PARALLEL_GENERATION=True
MAX_CONCURRENT_API_CALLS=5
```

**Benefits:**
- 4x faster generation (62s vs 240s for 30 posts)
- Better resource utilization
- Improved UX

**Disabled (Debugging Only):**
```env
PARALLEL_GENERATION=False
MAX_CONCURRENT_API_CALLS=1
```

### Concurrency Tuning

**Conservative (Tier 1):**
```env
MAX_CONCURRENT_API_CALLS=2
```

**Standard (Tier 2 - Recommended):**
```env
MAX_CONCURRENT_API_CALLS=5
```

**Aggressive (Tier 3+):**
```env
MAX_CONCURRENT_API_CALLS=10
```

**Warning:** Higher concurrency increases rate limit risk.

### Timeout Configuration

**Standard:**
```env
GENERATION_TIMEOUT_SECONDS=300  # 5 minutes total
POST_GENERATION_TIMEOUT_SECONDS=30  # 30 seconds per post
```

**Aggressive (Fast Network):**
```env
GENERATION_TIMEOUT_SECONDS=180  # 3 minutes total
POST_GENERATION_TIMEOUT_SECONDS=20  # 20 seconds per post
```

**Conservative (Slow Network):**
```env
GENERATION_TIMEOUT_SECONDS=600  # 10 minutes total
POST_GENERATION_TIMEOUT_SECONDS=60  # 60 seconds per post
```

---

## Health Check Configuration

### Health Check Intervals

**Aggressive Monitoring:**
```env
HEALTH_CHECK_INTERVAL_SECONDS=30
HEALTH_CHECK_TIMEOUT_SECONDS=5
```

**Standard Monitoring (Recommended):**
```env
HEALTH_CHECK_INTERVAL_SECONDS=60
HEALTH_CHECK_TIMEOUT_SECONDS=10
```

**Relaxed Monitoring:**
```env
HEALTH_CHECK_INTERVAL_SECONDS=300
HEALTH_CHECK_TIMEOUT_SECONDS=30
```

### Alert Thresholds

**Cache Hit Rate:**
```env
CACHE_HIT_RATE_WARNING_THRESHOLD=50
CACHE_HIT_RATE_CRITICAL_THRESHOLD=30
```

**Database Pool Utilization:**
```env
DB_POOL_UTILIZATION_WARNING_THRESHOLD=70
DB_POOL_UTILIZATION_CRITICAL_THRESHOLD=90
```

**Slow Query Percentage:**
```env
QUERY_SLOW_PERCENTAGE_WARNING_THRESHOLD=10
QUERY_SLOW_PERCENTAGE_CRITICAL_THRESHOLD=25
```

### Health Check Endpoints

1. **Basic Health:** `GET /health`
   - API status
   - Rate limit statistics
   - Version info

2. **Database Health:** `GET /api/health/database`
   - Pool status
   - Connection utilization
   - Database type

3. **Cache Health:** `GET /api/health/cache`
   - Hit/miss rates
   - Tier statistics
   - Recommendations

4. **Profiling Health:** `GET /api/health/profiling`
   - Slow query detection
   - Performance metrics
   - Recommendations

5. **Full Health:** `GET /api/health/full`
   - All subsystems
   - Aggregated status
   - Component health

---

## Deployment Options

### Option 1: Uvicorn (Development/Testing)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Pros:**
- Simple setup
- Fast reload

**Cons:**
- Single worker (no horizontal scaling)
- Not production-grade

### Option 2: Gunicorn + Uvicorn Workers (Production)

```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --keepalive 5
```

**Pros:**
- Multiple workers
- Process management
- Graceful restarts

**Worker Count Formula:**
```
workers = (2 x CPU cores) + 1
```

### Option 3: Docker Deployment (Recommended)

**Full System Docker Deployment** includes backend API + agent system + content generation CLI tools.

**Quick Start:**

1. **Copy environment template:**
   ```bash
   cd .. # Go to Project root
   cp .env.docker.example .env
   ```

2. **Configure environment variables:**
   Edit `.env` and set:
   - `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
   - `POSTGRES_PASSWORD` (strong password for database)
   - `ANTHROPIC_API_KEY` (your production API key)
   - `CORS_ORIGINS` (your production frontend URLs)

3. **Build and start services:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check API health
   curl http://localhost:8000/health

   # Check database health
   curl http://localhost:8000/api/health/database

   # View logs
   docker-compose logs -f api
   ```

**Architecture:**

The Docker deployment includes two services:

1. **api** - Full Content Jumpstart System
   - Backend FastAPI application
   - Agent system (`src/agents/`, `agent/`)
   - CLI tools (`run_jumpstart.py`)
   - Template library
   - Multi-stage build for optimized image size
   - Non-root user for security
   - Health checks enabled

2. **db** - PostgreSQL 16 Database
   - Persistent volume for data
   - Health checks with `pg_isready`
   - Configurable port (default: 5432)

**Persistent Volumes:**
- `postgres-data` - Database files
- `api-data` - Application data (briefs, outputs)
- `api-logs` - Application logs

**Environment Variables:**

All settings are configurable via `.env` file:

```env
# Security (REQUIRED)
SECRET_KEY=your-generated-secret-key
POSTGRES_PASSWORD=your-secure-password
ANTHROPIC_API_KEY=sk-ant-your-production-key

# Application
ENVIRONMENT=production
DEBUG_MODE=false
CORS_ORIGINS=https://dashboard.yourdomain.com

# Database Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Anthropic API
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000

# Content Generation
PARALLEL_GENERATION=true
MAX_CONCURRENT_API_CALLS=5

# Cache
CACHE_TTL_SHORT=300
CACHE_TTL_MEDIUM=600
CACHE_TTL_LONG=3600
```

**Docker Commands:**

```bash
# Build images
docker-compose build

# Start services (detached)
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f db

# Check service status
docker-compose ps

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (⚠️ deletes data)
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build

# Execute commands inside container
docker-compose exec api python --version
docker-compose exec db psql -U postgres -d content_jumpstart
```

**Production Considerations:**

1. **⚠️ CRITICAL: Purge demo data before deploying:**
   ```bash
   # Option 1: Drop and recreate database (recommended)
   docker-compose down -v
   docker-compose up -d

   # Option 2: Clear data only (preserves schema)
   docker-compose exec api python backend/seed_demo_data.py --clear-only
   ```

2. **Security:**
   - Never use default SECRET_KEY
   - Use strong POSTGRES_PASSWORD
   - Restrict CORS_ORIGINS to production domains
   - Set DEBUG_MODE=false

3. **Resource Allocation:**
   ```yaml
   # Add to docker-compose.yml under api service
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
       reservations:
         cpus: '1'
         memory: 2G
   ```

4. **Scaling:**
   ```bash
   # Scale API workers (NOT recommended for stateful service)
   docker-compose up -d --scale api=3

   # Better: Use load balancer + multiple instances
   ```

5. **Backup Volumes:**
   ```bash
   # Backup database volume
   docker run --rm -v content-jumpstart_postgres-data:/data \
     -v $(pwd):/backup alpine \
     tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data

   # Restore database volume
   docker run --rm -v content-jumpstart_postgres-data:/data \
     -v $(pwd):/backup alpine \
     tar xzf /backup/postgres-backup-20251217.tar.gz -C /
   ```

**Files:**
- **`Dockerfile`** - Multi-stage build at Project root
- **`docker-compose.yml`** - Service orchestration at Project root
- **`.env.docker.example`** - Environment template at Project root
- **`.dockerignore`** - Build exclusions at Project root

### Option 4: Cloud Deployment

#### AWS Elastic Beanstalk
```bash
eb init -p python-3.12 content-jumpstart-api
eb create production-env
eb deploy
```

#### Heroku
```bash
heroku create content-jumpstart-api
git push heroku main
heroku config:set SECRET_KEY=your-secret-here
```

#### Google Cloud Run
```bash
gcloud run deploy content-jumpstart-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Monitoring & Observability

### Health Check Integration

**Load Balancer Health Check:**
```nginx
upstream backend {
    server 127.0.0.1:8000;
}

location /health {
    proxy_pass http://backend/health;
    access_log off;
}
```

**Kubernetes Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Kubernetes Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /api/health/full
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Metrics Export

**Prometheus Metrics (Optional):**
Install `prometheus-fastapi-instrumentator`:
```bash
pip install prometheus-fastapi-instrumentator
```

Add to `main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Metrics available at: `GET /metrics`

### Logging

**JSON Logging (Recommended for Production):**
```env
LOG_FORMAT=json
LOG_LEVEL=INFO
```

**Structured Log Output:**
```json
{
  "timestamp": "2025-12-15T10:30:45Z",
  "level": "INFO",
  "message": "Post generation completed",
  "client": "Acme Corp",
  "posts_generated": 30,
  "duration_seconds": 62.3
}
```

**Log Aggregation:**
- **Elasticsearch + Kibana:** Full-text search and visualization
- **Datadog:** Application performance monitoring
- **New Relic:** APM and error tracking
- **Sentry:** Error tracking and alerting

---

## Security Best Practices

### 1. Environment Variables

**NEVER commit `.env` to version control:**
```bash
# Add to .gitignore
.env
.env.production
.env.local
```

**Use secret management services:**
- AWS Secrets Manager
- Google Cloud Secret Manager
- HashiCorp Vault
- Kubernetes Secrets

### 2. HTTPS Only

**Nginx SSL Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Force HTTPS redirect:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. Security Headers

Enable in `.env`:
```env
ENABLE_HSTS=True
HSTS_MAX_AGE=31536000
ENABLE_CSP=True
X_FRAME_OPTIONS=DENY
X_CONTENT_TYPE_OPTIONS=nosniff
```

### 4. Rate Limiting

**Application-level rate limiting** is already configured via Anthropic API limits.

**Add nginx rate limiting** for DDoS protection:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

### 5. Database Security

**Use SSL for database connections:**
```env
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

**Restrict database access:**
- Firewall rules (only allow API server IP)
- VPC/private subnet (AWS, GCP)
- IP whitelisting (managed databases)

---

## Backup & Disaster Recovery

### Database Backups

**Automated Daily Backups:**
```env
DB_BACKUP_ENABLED=True
DB_BACKUP_SCHEDULE=0 2 * * *  # 2 AM daily
DB_BACKUP_RETENTION_DAYS=30
DB_BACKUP_PATH=/var/backups/content-jumpstart
```

**Manual Backup (PostgreSQL):**
```bash
pg_dump -U postgres -h localhost content_jumpstart > backup_$(date +%Y%m%d).sql
```

**Restore from Backup:**
```bash
psql -U postgres -h localhost content_jumpstart < backup_20251215.sql
```

### File System Backups

**Backup directories:**
- `/var/www/content-jumpstart/data/briefs`
- `/var/www/content-jumpstart/data/outputs`
- `/var/www/content-jumpstart/logs`

**Automated backup script:**
```bash
#!/bin/bash
tar -czf backup_$(date +%Y%m%d).tar.gz \
  /var/www/content-jumpstart/data \
  /var/www/content-jumpstart/logs

aws s3 cp backup_$(date +%Y%m%d).tar.gz s3://backups/content-jumpstart/
```

---

## Performance Tuning

### Database Optimization

**PostgreSQL Settings (postgresql.conf):**
```ini
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB
```

**Create Indexes:**
```sql
-- Projects table
CREATE INDEX idx_projects_client_id ON projects(client_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- Posts table
CREATE INDEX idx_posts_project_id ON posts(project_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);

-- Cursor pagination indexes
CREATE INDEX idx_projects_cursor ON projects(created_at DESC, id);
CREATE INDEX idx_posts_cursor ON posts(created_at DESC, id);
```

### Cache Tuning

**Monitor cache hit rates:**
```bash
curl http://localhost:8000/api/health/cache
```

**Adjust TTLs based on hit rates:**
- Hit rate < 50%: Increase TTL
- Hit rate > 90%: Data might be stale, reduce TTL

### Query Profiling

**Monitor slow queries:**
```bash
curl http://localhost:8000/api/health/profiling
```

**Identify N+1 queries:**
- Look for repeated similar queries
- Add eager loading with `.options(joinedload())`

---

## Troubleshooting

### Issue: High Database Pool Utilization

**Symptoms:**
- Pool utilization > 90%
- Connection timeouts
- Slow response times

**Solutions:**
1. Increase pool size:
   ```env
   DB_POOL_SIZE=50
   DB_MAX_OVERFLOW=100
   ```

2. Reduce connection lifecycle:
   ```env
   DB_POOL_RECYCLE=1800  # 30 minutes
   ```

3. Enable connection pre-ping:
   ```env
   DB_POOL_PRE_PING=True
   ```

### Issue: Low Cache Hit Rate

**Symptoms:**
- Cache hit rate < 50%
- Slow API response times
- High database load

**Solutions:**
1. Increase cache TTLs:
   ```env
   CACHE_TTL_SHORT=600
   CACHE_TTL_MEDIUM=1200
   CACHE_TTL_LONG=7200
   ```

2. Increase cache size:
   ```env
   CACHE_MAX_SIZE_SHORT=5000
   ```

3. Review cache key generation (avoid unique keys)

### Issue: Rate Limit Errors

**Symptoms:**
- 429 errors from Anthropic API
- Generation failures
- Queue buildup

**Solutions:**
1. Reduce concurrency:
   ```env
   MAX_CONCURRENT_API_CALLS=3
   ```

2. Lower rate limits:
   ```env
   RATE_LIMIT_REQUESTS_PER_MINUTE=2000
   ```

3. Add retry backoff:
   ```env
   MAX_GENERATION_RETRIES=5
   RETRY_INITIAL_DELAY_SECONDS=2
   ```

### Issue: Slow Query Performance

**Symptoms:**
- Slow query percentage > 25%
- API response times > 1 second
- Database CPU high

**Solutions:**
1. Add database indexes (see Performance Tuning)
2. Enable query caching:
   ```env
   CACHE_TTL_MEDIUM=600
   ```
3. Review query patterns in `/api/health/profiling`

---

## Deployment Checklist

### Pre-Deployment

- [ ] **⚠️ CRITICAL: Purge all demo/seed data from database**
- [ ] **Verify database is empty (0 clients, 0 projects)**
- [ ] Generate secure `SECRET_KEY`
- [ ] Set `DEBUG_MODE=False`
- [ ] Configure production `DATABASE_URL`
- [ ] Set production `CORS_ORIGINS`
- [ ] Configure `ANTHROPIC_API_KEY` (production tier)
- [ ] Review rate limiting settings
- [ ] Set up SSL/HTTPS
- [ ] Configure health check endpoints
- [ ] Set up logging and monitoring
- [ ] Configure database backups

### Deployment

- [ ] Run database migrations
- [ ] Test health check endpoints
- [ ] Verify CORS configuration
- [ ] Test JWT authentication
- [ ] Load test with expected traffic
- [ ] Verify cache functionality
- [ ] Test content generation
- [ ] Check query profiling

### Post-Deployment

- [ ] Monitor health check endpoints
- [ ] Review error logs
- [ ] Monitor cache hit rates
- [ ] Check database pool utilization
- [ ] Review slow query reports
- [ ] Set up alerts for critical thresholds
- [ ] Schedule backup verification
- [ ] Document any production-specific issues

---

## Support & Resources

### Documentation
- Week 3 Task 4: Unit Tests Complete
- Week 3 Task 5: Integration Tests Complete
- Backend API Documentation: `/docs` (Swagger UI)
- Health Monitoring: `/api/health/*` endpoints

### Monitoring Endpoints
- Basic Health: `GET /health`
- Database: `GET /api/health/database`
- Cache: `GET /api/health/cache`
- Profiling: `GET /api/health/profiling`
- Full Health: `GET /api/health/full`

### Contact
- Technical Issues: [Your Support Email]
- Emergency Escalation: [On-Call Contact]
- Documentation: [Wiki/Docs URL]

---

**Last Updated:** December 15, 2025
**Version:** 1.0.0
