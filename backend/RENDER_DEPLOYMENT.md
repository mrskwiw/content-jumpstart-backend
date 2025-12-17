# Render Deployment Guide - Content Jumpstart API

Complete guide for deploying the Content Jumpstart FastAPI backend with PostgreSQL 18 on Render.

## Prerequisites

- GitHub account with this repository
- Render account (free tier available)
- Anthropic API key

## 🚀 Quick Deploy (Using Blueprint)

### Option 1: Deploy via render.yaml (Recommended)

1. **Push latest code to GitHub:**
   ```bash
   git add .
   git commit -m "Add PostgreSQL support and Render deployment config"
   git push origin main
   ```

2. **Create Blueprint in Render:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `backend/deploy/render.yaml`
   - Click "Apply" to create both services

3. **Set Required Environment Variables:**
   After blueprint deployment, add to the web service:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key (sk-ant-...)

   The following are auto-configured by render.yaml:
   - ✅ `DATABASE_URL`: Auto-linked from PostgreSQL service
   - ✅ `SECRET_KEY`: Auto-generated secure value
   - ✅ `ANTHROPIC_MODEL`: claude-3-5-sonnet-20241022
   - ✅ `DEBUG_MODE`: false
   - ✅ `CORS_ORIGINS`: Update this to your frontend URL

4. **Update CORS_ORIGINS:**
   - In web service settings, update `CORS_ORIGINS` to your frontend URL
   - Example: `https://your-app.netlify.app,https://your-app.vercel.app`

5. **Deploy:**
   - Render automatically builds and deploys
   - Monitor deployment in "Events" tab
   - Check logs in "Logs" tab

## 📋 Manual Setup (Alternative)

If you prefer manual setup instead of Blueprint:

### Step 1: Create PostgreSQL Database

1. Dashboard → "New +" → "PostgreSQL"
2. Configure:
   - **Name:** content-jumpstart-db
   - **Database:** content_jumpstart
   - **User:** content_jumpstart_user (auto-generated)
   - **Region:** Oregon (or your preferred region)
   - **PostgreSQL Version:** 18
   - **Plan:** Starter (free tier or paid)
3. Click "Create Database"
4. **Copy Internal Database URL** (starts with `postgresql://`)

### Step 2: Create Web Service

1. Dashboard → "New +" → "Web Service"
2. Connect GitHub repository
3. Configure:
   - **Name:** content-jumpstart-api
   - **Region:** Oregon (same as database)
   - **Branch:** main
   - **Root Directory:** backend
   - **Environment:** Docker
   - **Dockerfile Path:** ./Dockerfile
   - **Plan:** Starter (free tier or paid)

4. **Add Environment Variables:**
   ```
   DATABASE_URL=<paste-internal-database-url-here>
   SECRET_KEY=<generate-random-secret>
   ANTHROPIC_API_KEY=<your-anthropic-key>
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
   DEBUG_MODE=false
   CORS_ORIGINS=https://your-frontend-url.com
   PARALLEL_GENERATION=true
   MAX_CONCURRENT_API_CALLS=5
   ```

5. **Health Check Path:** `/health`

6. Click "Create Web Service"

## ✅ Verify Deployment

### 1. Check Health Endpoint

Visit: `https://your-app.onrender.com/health`

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "debug_mode": false,
  "rate_limits": { ... }
}
```

### 2. Check API Documentation

Visit: `https://your-app.onrender.com/docs`

Should show FastAPI Swagger UI with all endpoints.

### 3. Check Database Tables

In Render PostgreSQL dashboard:
- Click "Connect" → "External Connection"
- Use provided credentials with psql or TablePlus
- Verify tables exist:
  ```sql
  \dt
  ```
  Expected tables: users, clients, projects, briefs, runs, posts, deliverables

### 4. Check Logs

In web service dashboard:
- Go to "Logs" tab
- Look for:
  ```
  >> Starting Content Jumpstart API...
  >> Database initialized
  INFO:     Started server process
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.
  ```

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'psycopg2'"

**Cause:** Missing PostgreSQL driver in requirements.txt

**Fix:** Verify `requirements.txt` includes:
```
psycopg2-binary==2.9.9
```

### Issue: "SQLSTATE[42P01]: undefined table"

**Cause:** Database tables not created

**Solution 1 - Auto-create on startup (current approach):**
The app automatically creates tables via `init_db()` in `main.py:39`

**Solution 2 - Manual creation:**
```bash
# SSH into Render service (paid plans only)
python init_db.py
```

**Solution 3 - Use Alembic migrations:**
```bash
# Install Alembic (already in requirements.txt)
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Issue: "Connection refused" to database

**Causes:**
1. Wrong `DATABASE_URL` format
2. Database not in same region as web service
3. Database not yet ready (startup delay)

**Fixes:**
1. Use **Internal Database URL** (not External)
   - Format: `postgresql://user:pass@internal-host:5432/dbname`
2. Ensure both services in same region (Oregon)
3. Wait 2-3 minutes after database creation

### Issue: "SECRET_KEY not set"

**Cause:** Missing environment variable

**Fix:** In web service settings, add:
```
SECRET_KEY=<generate-random-256-bit-base64-string>
```

Or use Render's auto-generation (already in render.yaml):
```yaml
- key: SECRET_KEY
  generateValue: true
```

### Issue: CORS errors from frontend

**Cause:** Frontend URL not in CORS_ORIGINS

**Fix:** Update environment variable:
```
CORS_ORIGINS=https://frontend.netlify.app,https://frontend.vercel.app
```

Restart service after updating.

### Issue: 502 Bad Gateway on deployment

**Causes:**
1. App not binding to correct PORT
2. Health check failing
3. Build failure

**Fixes:**
1. Dockerfile already binds to 0.0.0.0:8000 ✅
2. Check `/health` endpoint works locally
3. Review build logs in "Events" tab

## 🔐 Security Best Practices

### Environment Variables

**Never commit these to GitHub:**
- ❌ `ANTHROPIC_API_KEY`
- ❌ `SECRET_KEY`
- ❌ `DATABASE_URL`

**Use Render's environment variable management:**
- Set `sync: false` for secrets in render.yaml
- Use `generateValue: true` for auto-generated secrets
- Manually add API keys in Render dashboard

### Database Access

**Use Internal URLs for app-to-database:**
- ✅ Internal: `postgresql://...@dpg-internal.../dbname`
- ❌ External: `postgresql://...@oregon-postgres.../dbname` (slower, costs egress)

**Backup Strategy:**
- Render free tier: Daily backups, 7-day retention
- Paid plans: Continuous PITR (Point-in-Time Recovery)

## 📊 Monitoring & Logs

### View Real-Time Logs

In web service dashboard → "Logs" tab:
```
2025-12-13 10:30:52 - API call: claude-3-5-sonnet-20241022
2025-12-13 10:30:54 - Post generated: #1 "Problem Recognition"
```

### Health Monitoring

Render automatically monitors `/health` endpoint:
- Green: Service healthy
- Yellow: Degraded (slow responses)
- Red: Down (health check failing)

### Rate Limiting

Monitor via `/health` endpoint:
```json
{
  "rate_limits": {
    "requests_per_minute": {
      "current": 120,
      "limit": 2800,
      "utilization_pct": 4.3
    },
    "tokens_per_minute": {
      "current": 15000,
      "limit": 280000,
      "utilization_pct": 5.4
    }
  }
}
```

## 🚦 Deployment Workflow

### Continuous Deployment (Auto-deploy enabled)

1. Push code to GitHub main branch
2. Render detects changes automatically
3. Builds new Docker image
4. Runs health check
5. Switches traffic to new deployment (zero-downtime)

### Manual Deployment

1. Dashboard → Web Service → "Manual Deploy"
2. Select branch
3. Click "Deploy latest commit"

### Rollback

1. Dashboard → "Events" tab
2. Find previous successful deployment
3. Click "Rollback to this version"

## 💰 Cost Optimization

### Free Tier Limits

**PostgreSQL:**
- 256 MB storage
- 90-day expiration (upgrade to persist)
- Shared CPU

**Web Service:**
- Spins down after 15 min inactivity
- 750 hours/month free
- Slow cold starts (10-30 seconds)

### Upgrade Considerations

**When to upgrade:**
- Frequent usage (avoid cold starts) → **Starter plan ($7/month)**
- >256 MB data → **PostgreSQL Starter ($7/month)**
- >100 users → **Standard plan ($25/month)**
- Need 99.9% uptime → **Pro plan ($85/month)**

## 📚 Additional Resources

- [Render PostgreSQL Docs](https://render.com/docs/postgresql)
- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [FastAPI Production Best Practices](https://render.com/articles/fastapi-production-deployment-best-practices)
- [How to Deploy FastAPI + PostgreSQL on Render](https://www.freecodecamp.org/news/deploy-fastapi-postgresql-app-on-render/)

## 🆘 Support

**Render Issues:**
- Dashboard → "Help" → "Contact Support"
- [Render Community](https://community.render.com)

**App Issues:**
- Check logs in Render dashboard
- Test locally with PostgreSQL first
- Review this guide's troubleshooting section

---

**Last Updated:** 2025-12-13
**PostgreSQL Version:** 18
**Python Version:** 3.11
**FastAPI Version:** 0.109.0
