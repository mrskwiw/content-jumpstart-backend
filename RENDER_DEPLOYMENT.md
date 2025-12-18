# Render Single-Service Deployment Guide

## Overview

This deployment architecture eliminates CORS issues by serving both the React frontend and FastAPI backend from a single Render service. The backend serves the frontend static files, so all requests go to the same origin.

**Benefits:**
- ✅ No CORS configuration needed
- ✅ Single service to manage (simpler, cheaper)
- ✅ Faster deployment
- ✅ Frontend and backend always in sync

## Architecture

```
Client Browser
    ↓
https://your-app.onrender.com/
    ↓
Render Service (Single)
    ├── FastAPI Backend (Python)
    │   ├── /api/* → API endpoints
    │   ├── /assets/* → Static files (JS, CSS)
    │   └── /* → React app (index.html)
    └── React Frontend (built to /dist)
```

## Prerequisites

1. GitHub repository with your code
2. Render account (free tier works)
3. Python 3.12+ and Node.js 18+ installed locally (for testing)

## Step 1: Prepare Your Repository

### Required Files

Ensure these files are in your repository:

#### `build.sh` (Root of project)
```bash
#!/bin/bash
# Unified build script for Render deployment

set -e  # Exit on error

echo "=== Content Jumpstart Unified Build ==="
echo ""

# Step 1: Install backend dependencies
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt
echo "✅ Python dependencies installed"
echo ""

# Step 2: Build frontend
echo "🎨 Building React frontend..."
cd operator-dashboard

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm ci --prefer-offline --no-audit
echo "✅ Node dependencies installed"

# Build for production
echo "🏗️  Building frontend for production..."
npm run build
echo "✅ Frontend built successfully"

cd ..
echo ""

# Step 3: Verify build output
if [ -d "operator-dashboard/dist" ]; then
    echo "✅ Frontend build output verified: operator-dashboard/dist"
    echo "   Files:"
    ls -lh operator-dashboard/dist/ | head -10
else
    echo "❌ ERROR: Frontend build failed - dist directory not found"
    exit 1
fi

echo ""
echo "=== Build Complete ==="
echo "Backend will serve frontend from operator-dashboard/dist"
echo "No CORS configuration needed (same origin)"
```

Make it executable:
```bash
chmod +x build.sh
```

#### `operator-dashboard/.env.production`
```bash
# Production Environment Variables
# Single-service deployment - frontend served by FastAPI backend

# IMPORTANT: Leave VITE_API_URL empty to use relative URLs
# This eliminates CORS since requests go to the same origin
# VITE_API_URL=

# Disable mocks in production
VITE_USE_MOCKS=false

# Debug mode (set to false in production)
VITE_DEBUG_MODE=false
```

### Verify Backend Configuration

Ensure `backend/main.py` includes static file serving:

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ... after app initialization and router includes ...

# Static file serving for React frontend
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "operator-dashboard" / "dist"

if FRONTEND_BUILD_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"), name="assets")

    # Root route: serve React app
    @app.get("/")
    async def serve_root():
        """Serve React app at root URL"""
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

    # Catch-all route: serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # If path looks like a file, try to serve it
        if "." in full_path.split("/")[-1]:
            file_path = FRONTEND_BUILD_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)

        # Otherwise, serve index.html (React Router)
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")
```

Verify `operator-dashboard/src/utils/env.ts` uses relative URLs in production:

```typescript
export function getApiBaseUrl(): string {
  const value = readEnvVar('VITE_API_URL');
  const mode = readEnvVar('MODE') || 'development';

  if (!value) {
    if (mode === 'production') {
      return '';  // Relative URLs eliminate CORS
    } else {
      return 'http://localhost:8000';  // Development
    }
  }
  // ... rest of function
}
```

## Step 2: Create Render Service

### Via Render Dashboard

1. **Go to:** https://dashboard.render.com
2. **Click:** "New +" → "Web Service"
3. **Connect:** Your GitHub repository

### Configuration

**General Settings:**
- **Name:** `content-jumpstart` (or your preferred name)
- **Region:** Oregon (US West) - or closest to your users
- **Branch:** `main` (or `master`)
- **Root Directory:** Leave empty (root of repo)

**Build & Deploy:**
- **Runtime:** Python 3
- **Build Command:** `./build.sh`
- **Start Command:** `cd backend && python main.py`

**Instance Type:**
- Free tier: Works for testing
- Starter ($7/month): Recommended for production (512MB RAM, 0.5 CPU)

## Step 3: Environment Variables

Go to: Render Dashboard → Your Service → Environment

### Required Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG_MODE=false

# Database (Render provides this if you add Postgres)
DATABASE_URL=<provided-by-render-if-using-postgres>

# Security - CRITICAL!
SECRET_KEY=<generate-with-command-below>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Anthropic API (if using AI features)
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000

# CORS - NO LONGER NEEDED (but keep for backward compatibility)
# CORS_ORIGINS can be empty or omitted since everything is same-origin
CORS_ORIGINS=

# Cache Configuration
CACHE_TTL_SHORT=300
CACHE_TTL_MEDIUM=600
CACHE_TTL_LONG=3600
```

### Generate SECRET_KEY

Run locally:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste into `SECRET_KEY` on Render.

## Step 4: Deploy

### Automatic Deployment

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Configure single-service deployment"
   git push origin main
   ```

2. **Render auto-deploys** when you push to the configured branch

3. **Monitor deployment:**
   - Go to Render Dashboard → Your Service → Events
   - Watch build logs in real-time
   - Build takes ~3-5 minutes (installs Python + Node deps, builds frontend)

### Manual Deployment

If auto-deploy is disabled:
1. Go to Render Dashboard → Your Service
2. Click "Manual Deploy" → "Deploy latest commit"

## Step 5: Verify Deployment

### Check Deployment Logs

Look for these success messages:

```
📦 Installing Python dependencies...
✅ Python dependencies installed

🎨 Building React frontend...
✅ Frontend built successfully

✅ Frontend build output verified: operator-dashboard/dist

=== Build Complete ===
Backend will serve frontend from operator-dashboard/dist
```

### Test Endpoints

```bash
# Replace with your Render URL
RENDER_URL="https://your-app.onrender.com"

# Test health endpoint
curl $RENDER_URL/api/health

# Should return:
# {"status":"healthy","service":"Content Jumpstart API","version":"1.0.0"}

# Test frontend (should return HTML)
curl $RENDER_URL/ | grep "<!doctype html>"

# Test static assets
curl -I $RENDER_URL/assets/index-[hash].js
# Should return: HTTP/1.1 200 OK
```

### Browser Test

1. Open `https://your-app.onrender.com` in browser
2. Open DevTools (F12) → Network tab
3. Verify:
   - Root request loads `index.html`
   - Assets load from `/assets/*`
   - API calls go to `/api/*`
   - **NO CORS errors** in console

## Step 6: DNS & Custom Domain (Optional)

### Add Custom Domain

1. **Go to:** Render Dashboard → Your Service → Settings → Custom Domains
2. **Click:** "Add Custom Domain"
3. **Enter:** `yourdomain.com`
4. **Configure DNS** at your domain registrar:
   ```
   Type: CNAME
   Name: @ (or www)
   Value: <your-app>.onrender.com
   TTL: 3600
   ```

5. **Wait** for DNS propagation (5-60 minutes)
6. **SSL Certificate** - Render auto-provisions via Let's Encrypt

## Troubleshooting

### Build Fails: "npm: command not found"

**Issue:** Node.js not available in build environment
**Fix:** Render should auto-detect Node.js from `package.json`. If not, contact Render support.

### Build Fails: "Permission denied: ./build.sh"

**Issue:** Build script not executable
**Fix:**
```bash
chmod +x build.sh
git add build.sh
git commit -m "Make build.sh executable"
git push
```

### Frontend Serves but API Returns 404

**Issue:** Wrong start command or backend not running
**Fix:** Verify start command is `cd backend && python main.py`

### Assets Load but Login Doesn't Work

**Issue:** Database not initialized or SECRET_KEY not set
**Fix:**
1. Check logs for database connection errors
2. Verify `SECRET_KEY` is set in environment variables
3. If using Postgres, verify `DATABASE_URL` is configured

### Static Assets Return 404

**Issue:** Frontend build directory not found
**Fix:**
1. Check build logs: "Frontend build output verified"
2. Verify `operator-dashboard/dist` exists after build
3. Check `backend/main.py` path to dist directory

### API Works but Frontend Shows Blank Page

**Issue:** JavaScript errors or wrong base URL
**Fix:**
1. Open browser console (F12)
2. Look for JavaScript errors
3. Verify `VITE_API_URL` is NOT set (should use relative URLs)
4. Check Network tab: assets should load from same domain

## Performance Optimization

### Enable Gzip Compression

Add to `backend/main.py`:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Add Response Caching Headers

Modify static file serving:

```python
from fastapi.responses import FileResponse

@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    file = FRONTEND_BUILD_DIR / "assets" / file_path
    if file.is_file():
        return FileResponse(
            file,
            headers={"Cache-Control": "public, max-age=31536000"}  # 1 year
        )
    return {"error": "Not found"}
```

## Monitoring & Logging

### View Logs

```bash
# Via Render Dashboard
# Go to: Your Service → Logs (live tail)

# Via CLI (if you have Render CLI installed)
render logs <service-id>
```

### Set Up Alerts

1. Go to: Render Dashboard → Your Service → Settings → Notifications
2. Add webhook or email for:
   - Deploy failures
   - Service crashes
   - High CPU/memory usage

## Cost Estimate

**Free Tier:**
- 750 hours/month free
- Service sleeps after 15 minutes of inactivity
- ~30 second cold start

**Starter ($7/month):**
- Always running
- 512 MB RAM, 0.5 CPU
- Recommended for production

**Standard ($25/month):**
- 2 GB RAM, 1 CPU
- For higher traffic

## Migration from Netlify + Render

If you were previously using Netlify (frontend) + Render (backend):

### Steps

1. **Deploy new single-service** following this guide
2. **Test thoroughly** at new URL
3. **Update DNS** to point to new service
4. **Deactivate Netlify site** after confirming
5. **Delete old Render backend service** if separate

### Considerations

- SSL certificate provision may take 5-10 minutes
- Update any third-party integrations (webhooks, OAuth redirects) to new URL
- Monitor logs for 24 hours after migration

## Rollback Plan

If deployment fails:

1. **Revert code changes:**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Manually trigger deploy** of previous commit:
   - Go to Render Dashboard → Your Service → Events
   - Find last successful deploy
   - Click "Redeploy"

3. **Emergency:** If service is down, redeploy from Render dashboard:
   - Click "Manual Deploy" → "Clear build cache & deploy"

## Next Steps

After successful deployment:

1. **Create first user** via `/api/auth/register`
2. **Test login** and core workflows
3. **Monitor logs** for first 24 hours
4. **Set up backups** if using database
5. **Configure domain** if using custom domain
6. **Add monitoring** (Sentry, LogRocket, etc.)

## Support

- **Render Docs:** https://render.com/docs
- **Render Community:** https://community.render.com
- **GitHub Issues:** [Your repo]/issues
