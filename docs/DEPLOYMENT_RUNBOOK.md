# Deployment Runbook

**Version:** 1.0
**Last Updated:** 2025-12-29
**Target Environment:** Production (Render.com / Docker)

This runbook provides step-by-step procedures for deploying, monitoring, and troubleshooting the Content Jumpstart application in production.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Post-Deployment Verification](#post-deployment-verification)
4. [Rollback Procedures](#rollback-procedures)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Contacts](#emergency-contacts)

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All tests passing (`pytest` in project/)
- [ ] E2E tests passing (`playwright test` in tests/e2e/)
- [ ] Code coverage ≥ 80%
- [ ] No critical security vulnerabilities (run `bandit`, `safety`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Code formatted (`black src/`)

### Configuration

- [ ] Environment variables configured in Render dashboard
  - [ ] `ANTHROPIC_API_KEY` (required)
  - [ ] `SECRET_KEY` (32+ chars, generated securely)
  - [ ] `DATABASE_URL` (PostgreSQL connection string)
  - [ ] `CORS_ORIGINS` (production domain only)
  - [ ] `DEBUG_MODE=false`
  - [ ] `RATE_LIMIT_REQUESTS_PER_MINUTE=2800`
  - [ ] `RATE_LIMIT_TOKENS_PER_MINUTE=280000`

- [ ] Database migrations ready
  - [ ] Migration scripts tested in staging
  - [ ] Backup plan for database rollback

- [ ] Frontend build completed
  - [ ] `cd operator-dashboard && npm run build`
  - [ ] Build artifacts in `dist/` directory
  - [ ] No build warnings or errors

### Documentation

- [ ] CHANGELOG.md updated with release notes
- [ ] API documentation updated (if API changes)
- [ ] README.md reflects current version

### Dependencies

- [ ] All dependencies pinned to specific versions (`requirements.txt`)
- [ ] No known vulnerabilities in dependencies
  - [ ] `safety check` (Python)
  - [ ] `npm audit` (Frontend)

---

## Deployment Procedures

### Deployment Strategy: Blue-Green with Docker

**Timeline:** ~15 minutes total
**Downtime:** 0 minutes (blue-green deployment)

### Step 1: Prepare New Version (Green)

```bash
# 1. Pull latest code
git pull origin main

# 2. Verify version tag
git tag -a v1.x.x -m "Production release v1.x.x"
git push origin v1.x.x

# 3. Build Docker image
docker build -t content-jumpstart:v1.x.x -f Dockerfile .

# 4. Tag for deployment
docker tag content-jumpstart:v1.x.x registry.render.com/content-jumpstart:latest
```

### Step 2: Deploy to Render.com

**Option A: Automatic Deployment (Git-based)**

```bash
# Push to deployment branch
git push render main
```

Render automatically:
1. Detects push to deployment branch
2. Builds Docker image
3. Runs health checks
4. Switches traffic to new version

**Option B: Manual Deployment (Docker Registry)**

```bash
# 1. Push image to Render registry
docker push registry.render.com/content-jumpstart:latest

# 2. Trigger deployment via Render dashboard
# Navigate to: Dashboard → Services → content-jumpstart → Manual Deploy
```

### Step 3: Database Migrations (if needed)

```bash
# Run migrations before deploying new app version
docker exec -it content-jumpstart-api alembic upgrade head
```

**⚠️ CRITICAL:** Always run migrations BEFORE deploying code that depends on schema changes.

### Step 4: Health Check Verification

```bash
# Check health endpoint
curl https://your-app.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "version": "1.x.x",
  "debug_mode": false,
  "rate_limits": { ... }
}
```

### Step 5: Switch Traffic (Blue-Green)

Render.com handles this automatically:
- New version (Green) deployed alongside old version (Blue)
- Health checks pass on Green
- Traffic gradually shifted to Green (0% → 50% → 100%)
- Blue version kept for 10 minutes, then removed

**Manual traffic control (if needed):**
```bash
# Render CLI
render services deploy <service-id> --image content-jumpstart:v1.x.x
```

---

## Post-Deployment Verification

### Automated Checks (First 5 Minutes)

```bash
# 1. Health endpoint
curl https://your-app.onrender.com/health
# Expected: HTTP 200, "status": "healthy"

# 2. API docs accessible
curl https://your-app.onrender.com/docs
# Expected: HTTP 200, Swagger UI

# 3. Frontend loads
curl https://your-app.onrender.com/
# Expected: HTTP 200, React app HTML

# 4. Authentication works
curl -X POST https://your-app.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'
# Expected: HTTP 200, access_token

# 5. Database connection
curl https://your-app.onrender.com/api/health/db
# Expected: HTTP 200, "database": "connected"
```

### Manual Checks (First 15 Minutes)

- [ ] Login to operator dashboard
- [ ] Create new project via wizard (end-to-end test)
- [ ] Generate 30 posts (verify performance < 90s)
- [ ] Review content (QA flags working)
- [ ] Export deliverable (DOCX download)
- [ ] Check error logs (no unexpected errors)

### Performance Benchmarks

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **API Response Time** | < 200ms (p95) | > 500ms |
| **Page Load Time** | < 2s (dashboard) | > 5s |
| **Generation Time** | < 90s (30 posts) | > 120s |
| **Error Rate** | < 0.1% | > 1% |
| **Database Queries** | < 50ms (p95) | > 200ms |

---

## Rollback Procedures

### Immediate Rollback (< 5 Minutes)

**Trigger Conditions:**
- Critical errors in logs (500 errors > 10%)
- Health checks failing
- Database connection failures
- Authentication broken
- Frontend not loading

**Procedure:**

1. **Stop new deployments**
   ```bash
   # Render Dashboard: Disable Auto-Deploy
   # Or via CLI:
   render services update <service-id> --auto-deploy=false
   ```

2. **Revert to previous version**
   ```bash
   # Option A: Via Git (if git-based deploy)
   git revert HEAD
   git push render main

   # Option B: Via Docker image tag
   render services deploy <service-id> --image content-jumpstart:v1.x.x-previous
   ```

3. **Verify rollback successful**
   ```bash
   curl https://your-app.onrender.com/health
   # Check version matches previous
   ```

4. **Database rollback (if migrations were run)**
   ```bash
   # Downgrade database to previous version
   docker exec -it content-jumpstart-api alembic downgrade -1

   # For multiple versions:
   docker exec -it content-jumpstart-api alembic downgrade <revision-id>
   ```

5. **Notify stakeholders**
   ```bash
   # Post to Slack/Discord/Email
   "🚨 ROLLBACK: Deployment v1.x.x rolled back due to [reason].
    System restored to v1.x.x-previous. Investigating root cause."
   ```

### Database Rollback Considerations

**⚠️ Data Loss Risk:** Database rollbacks may cause data loss if:
- New rows were inserted with new schema
- Columns were dropped in migration
- Data transformations were applied

**Mitigation:**
1. **Always backup before migration**
   ```bash
   pg_dump $DATABASE_URL > backup_pre_migration_v1.x.x.sql
   ```

2. **Test rollback in staging first**
3. **Consider forward-fixes instead of rollbacks**

---

## Monitoring & Alerts

### Key Metrics to Monitor

**Application Performance:**
- API response times (p50, p95, p99)
- Error rates (4xx, 5xx)
- Request throughput (req/min)
- Generation success rate

**Infrastructure:**
- CPU usage (% of limit)
- Memory usage (% of limit)
- Database connections (active/idle)
- Disk space (database)

**Business Metrics:**
- Posts generated per hour
- Active projects
- Failed generations (%)
- User logins

### Alert Thresholds

| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| **API 5xx errors** | Critical | > 10 in 5 min | Immediate rollback consideration |
| **High latency** | Warning | p95 > 500ms | Investigate performance |
| **Low memory** | Warning | > 85% used | Scale up or optimize |
| **Database slow** | Warning | p95 > 200ms | Check queries/indexes |
| **Failed health check** | Critical | 3 consecutive failures | Rollback |
| **High error rate** | Critical | > 1% of requests | Investigate logs |

### Monitoring Tools

**Render.com Built-in:**
- Dashboard metrics (CPU, memory, requests)
- Logs (stdout/stderr)
- Health check status

**External (Recommended):**
- **Sentry** - Error tracking & alerting
- **Datadog** - APM & infrastructure monitoring
- **LogDNA/Papertrail** - Log aggregation
- **UptimeRobot** - Uptime monitoring

---

## Troubleshooting

### Common Issues & Solutions

#### 1. "Service Unavailable" (503 Error)

**Symptoms:**
- Health endpoint returns 503
- Frontend not loading
- API requests timeout

**Diagnosis:**
```bash
# Check service status
render services status <service-id>

# Check logs
render services logs <service-id> --tail 100
```

**Solutions:**
- **If out of memory:** Upgrade plan or optimize memory usage
- **If database connection failed:** Check DATABASE_URL, verify database is running
- **If startup timeout:** Increase startup time limit, optimize initialization code

#### 2. Database Connection Errors

**Symptoms:**
- "could not connect to server" errors
- Timeouts on database queries
- Connection pool exhausted

**Diagnosis:**
```bash
# Test database connectivity
docker exec -it content-jumpstart-api python -c "from database import engine; engine.connect()"

# Check connection pool stats
curl https://your-app.onrender.com/api/health/db
```

**Solutions:**
- Verify DATABASE_URL is correct
- Check database is running (`render services status`)
- Increase connection pool size (`DB_POOL_SIZE`)
- Check for connection leaks (unclosed sessions)

#### 3. Frontend Not Loading

**Symptoms:**
- Blank page
- "Failed to load resource" errors
- Chunk loading failures

**Diagnosis:**
```bash
# Check if frontend files exist
curl https://your-app.onrender.com/assets/index.js
# Expected: HTTP 200, JavaScript code

# Check CSP headers
curl -I https://your-app.onrender.com/
# Look for Content-Security-Policy header
```

**Solutions:**
- Verify frontend was built (`npm run build`)
- Check `dist/` directory contains assets
- Clear browser cache
- Check CSP headers allow assets

#### 4. Slow API Performance

**Symptoms:**
- p95 latency > 500ms
- Timeout errors
- Slow page loads

**Diagnosis:**
```bash
# Check for N+1 queries (look for many similar queries)
render services logs <service-id> | grep "SELECT"

# Check rate limit queue
curl https://your-app.onrender.com/health
# Check rate_limits.queue_length

# Profile a slow endpoint
time curl -X POST https://your-app.onrender.com/api/generator/generate-all ...
```

**Solutions:**
- Add database indexes
- Use `.joinedload()` for relationships
- Increase `MAX_CONCURRENT_API_CALLS`
- Optimize prompt caching

#### 5. Authentication Failures

**Symptoms:**
- "Invalid token" errors
- Users logged out unexpectedly
- 401 Unauthorized on all requests

**Diagnosis:**
```bash
# Verify SECRET_KEY hasn't changed
render services env <service-id> | grep SECRET_KEY

# Test token generation
curl -X POST https://your-app.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'
```

**Solutions:**
- Verify SECRET_KEY is consistent across deployments
- Check token expiry times (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- Clear frontend localStorage/cookies
- Regenerate tokens

---

## Emergency Contacts

| Role | Name | Contact | Timezone |
|------|------|---------|----------|
| **Primary On-Call** | TBD | TBD | UTC-X |
| **Secondary On-Call** | TBD | TBD | UTC-X |
| **Database Admin** | TBD | TBD | UTC-X |
| **DevOps Lead** | TBD | TBD | UTC-X |

### Escalation Path

1. **Level 1** (0-15 min): On-call engineer investigates
2. **Level 2** (15-30 min): Escalate to senior engineer if not resolved
3. **Level 3** (30+ min): Escalate to DevOps lead + engineering manager
4. **Critical** (any time): For data loss or security breaches, immediately escalate to CTO

### Incident Communication

**Slack Channel:** #incidents-content-jumpstart
**Status Page:** https://status.your-app.com (if applicable)
**Incident Template:**
```
🚨 INCIDENT: [Brief description]
Severity: [Critical/High/Medium/Low]
Impact: [What's affected]
Started: [Timestamp]
Current Status: [Investigating/Identified/Monitoring/Resolved]
ETA: [Expected resolution time]
Updates: [Thread below]
```

---

## Appendix

### A. Environment Variables Reference

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-...` | Yes |
| `SECRET_KEY` | JWT signing key | `32+ char random` | Yes |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://user:pass@host/db` | Yes |
| `CORS_ORIGINS` | Allowed origins | `https://app.example.com` | Yes |
| `DEBUG_MODE` | Debug flag | `false` | Yes |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | API rate limit | `2800` | No |
| `RATE_LIMIT_TOKENS_PER_MINUTE` | Token limit | `280000` | No |

### B. Database Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### C. Useful Curl Commands

```bash
# Health check
curl https://your-app.onrender.com/health

# Login
curl -X POST https://your-app.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}'

# Generate content (with token)
curl -X POST https://your-app.onrender.com/api/generator/generate-all \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"xxx","client_id":"yyy"}'
```

---

**Document Control:**
- **Version:** 1.0
- **Last Review:** 2025-12-29
- **Next Review:** 2026-03-29 (quarterly)
- **Owner:** DevOps Team
