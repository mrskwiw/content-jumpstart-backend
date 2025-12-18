# Netlify + Render Deployment Checklist

## Prerequisites

- ✅ Backend code pushed to GitHub
- ✅ Frontend code pushed to GitHub
- ✅ Render service created and connected to backend repo
- ✅ Netlify site created and connected to frontend repo
- ✅ PostgreSQL database provisioned on Render

## Step 1: Configure Render Backend

### Environment Variables (Render Dashboard)

Go to: Render Dashboard → Your Service → Environment

**Required variables:**

```bash
# API Configuration
DEBUG_MODE=false
API_TITLE=Content Jumpstart API
API_VERSION=1.0.0

# Database (automatically set if using Render Postgres)
DATABASE_URL=<provided-by-render-postgres>

# Security - CRITICAL!
SECRET_KEY=<generate-with-command-below>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - ADD YOUR NETLIFY URL HERE!
CORS_ORIGINS=https://your-app-name.netlify.app,http://localhost:5173,http://localhost:3000

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000

# Paths (use absolute paths in Docker)
BRIEFS_DIR=/app/data/briefs
OUTPUTS_DIR=/app/data/outputs
LOGS_DIR=/app/logs

# Cache Configuration
CACHE_TTL_SHORT=300
CACHE_TTL_MEDIUM=600
CACHE_TTL_LONG=3600
CACHE_MAX_SIZE_SHORT=500
CACHE_MAX_SIZE_MEDIUM=200
CACHE_MAX_SIZE_LONG=100

# Celery + Redis (if using background jobs)
CELERY_BROKER_URL=redis://your-redis-url:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-url:6379/0
CELERY_TASK_TRACK_STARTED=true
CELERY_TASK_SEND_SENT_EVENT=true
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=540
REDIS_URL=redis://your-redis-url:6379/0
REDIS_MAX_CONNECTIONS=50
```

### Generate SECRET_KEY

Run this command locally and copy the output:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `xK9mP4vN2wQ7hR1tY8jL3nM6bV5cX0zA1sD4fG7hJ9kP2qW5eR8t`

Paste this value into the `SECRET_KEY` variable on Render.

### Get Your Netlify URL

1. Go to Netlify Dashboard → Your site
2. Look for the URL (e.g., `https://keen-mahavira-abc123.netlify.app`)
3. Add this to `CORS_ORIGINS` on Render:
   ```
   CORS_ORIGINS=https://keen-mahavira-abc123.netlify.app,http://localhost:5173
   ```

**CRITICAL:** The CORS_ORIGINS value must be comma-separated with NO SPACES.

### Verify Backend Deployment

```bash
# Test health endpoint
curl https://your-backend.onrender.com/health

# Expected response:
{"status":"healthy","timestamp":"2025-12-18T..."}
```

## Step 2: Configure Netlify Frontend

### Environment Variables (Netlify Dashboard)

Go to: Netlify Dashboard → Your site → Site settings → Environment variables

**Required variables:**

```bash
# Backend API URL (use your actual Render URL)
VITE_API_URL=https://your-backend.onrender.com

# Disable mocks in production
VITE_USE_MOCKS=false
```

### Get Your Render Backend URL

1. Go to Render Dashboard → Your service
2. Look for the URL at the top (e.g., `https://content-backend-flmx.onrender.com`)
3. Use this EXACT URL (including `https://`) in `VITE_API_URL`

### Deploy Changes

**IMPORTANT:** After adding environment variables:

1. Go to: Deploys → Trigger deploy
2. Choose: **"Clear cache and deploy site"**
3. Wait for deployment to finish (~2 minutes)

**Why clear cache?** Vite embeds environment variables at build time. Cached builds won't have the new values.

## Step 3: Verify Connection

### Browser Console Test

1. Open your Netlify site in browser
2. Open Developer Tools (F12)
3. Go to Console tab
4. Try to login
5. Check for errors:

**❌ Bad - CORS error:**
```
Access to XMLHttpRequest at 'https://backend.onrender.com/api/auth/login'
from origin 'https://your-app.netlify.app' has been blocked by CORS policy
```
→ Fix: Add Netlify URL to CORS_ORIGINS on Render

**❌ Bad - Wrong URL:**
```
POST http://localhost:8000/api/auth/login 404 (Not Found)
```
→ Fix: Set VITE_API_URL on Netlify and redeploy

**✅ Good - Auth error (means connection works):**
```
401 Unauthorized: Incorrect email or password
```
→ Connection is working! Create a user or use correct credentials.

### Network Tab Test

1. Open Developer Tools (F12) → Network tab
2. Try to login
3. Find the `/api/auth/login` request
4. Verify:
   - Request URL: `https://your-backend.onrender.com/api/auth/login` ✅
   - Status: 401 (or 200 if credentials correct) ✅
   - Response headers include: `access-control-allow-origin` ✅

## Step 4: Create Test User

If backend is running but you don't have a user:

### Option A: Use Backend API Docs

1. Go to: `https://your-backend.onrender.com/docs`
2. Find: `POST /api/auth/register`
3. Click "Try it out"
4. Fill in:
   ```json
   {
     "email": "admin@example.com",
     "password": "SecurePassword123!",
     "full_name": "Admin User"
   }
   ```
5. Click "Execute"

### Option B: Use curl

```bash
curl -X POST https://your-backend.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "full_name": "Admin User"
  }'
```

## Common Issues

### Issue 1: "Cannot reach server"
- **Cause:** VITE_API_URL not set or wrong
- **Fix:** Set `VITE_API_URL=https://your-backend.onrender.com` on Netlify
- **Verify:** Clear cache and redeploy Netlify

### Issue 2: "CORS policy blocked"
- **Cause:** Netlify URL not in CORS_ORIGINS
- **Fix:** Add your Netlify URL to `CORS_ORIGINS` on Render
- **Verify:** Render auto-restarts after environment variable change

### Issue 3: "401 Unauthorized" on login
- **Cause:** Wrong credentials (but connection works!)
- **Fix:** Create user or use correct credentials
- **Verify:** Use /api/auth/register endpoint

### Issue 4: Backend shows "SECRET_KEY validation failed"
- **Cause:** SECRET_KEY not set or too weak
- **Fix:** Generate new key and add to Render:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

### Issue 5: Render service sleeping (free tier)
- **Symptom:** First request takes 30+ seconds
- **Cause:** Free tier services sleep after 15 minutes of inactivity
- **Solution:** Upgrade to paid tier or accept the delay

## Verification Commands

Run these from your terminal:

```bash
# 1. Test backend health
curl https://your-backend.onrender.com/health

# 2. Test auth endpoint (401 = working)
curl -X POST https://your-backend.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}'

# 3. Check CORS headers
curl -I https://your-backend.onrender.com/health | grep -i access-control

# 4. Run verification script
bash verify-deployment.sh
```

## Success Criteria

✅ Backend health endpoint returns 200
✅ CORS headers include your Netlify URL
✅ Auth endpoint returns 401 (or 200 with valid credentials)
✅ Browser console shows no CORS errors
✅ Login request goes to correct backend URL
✅ Can successfully login with valid credentials

## Support Resources

- **Backend logs:** Render Dashboard → Your service → Logs
- **Frontend build logs:** Netlify Dashboard → Deploys → Latest deploy → Build logs
- **Detailed diagnostics:** See `DEPLOYMENT_DIAGNOSTICS.md`
- **Verification script:** Run `bash verify-deployment.sh`
