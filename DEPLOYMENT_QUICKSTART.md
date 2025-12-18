# Render Deployment Quickstart

## Pre-Deployment Checklist

- [ ] Code pushed to GitHub (`main` or `master` branch)
- [ ] `build.sh` exists and is executable (`chmod +x build.sh`)
- [ ] `operator-dashboard/.env.production` exists with empty `VITE_API_URL`
- [ ] `backend/main.py` includes static file serving code
- [ ] All dependencies in `backend/requirements.txt` and `operator-dashboard/package.json`

## Render Service Creation

### 1. Create Service

Dashboard → New + → Web Service → Connect GitHub repo

### 2. Configure Service

| Setting | Value |
|---------|-------|
| **Name** | `content-jumpstart` |
| **Region** | Oregon (US West) |
| **Branch** | `main` |
| **Runtime** | Python 3 |
| **Build Command** | `./build.sh` |
| **Start Command** | `cd backend && python main.py` |
| **Instance Type** | Starter ($7/month recommended) |

### 3. Environment Variables

**Required:**
```bash
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(32))">
DEBUG_MODE=false
API_HOST=0.0.0.0
API_PORT=8000
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Optional (defaults work):**
```bash
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
RATE_LIMIT_REQUESTS_PER_MINUTE=2800
RATE_LIMIT_TOKENS_PER_MINUTE=280000
```

**Not needed:**
```bash
# CORS_ORIGINS - no longer needed (same origin)
# VITE_API_URL - set via .env.production
```

### 4. Deploy

Click "Create Web Service" → Auto-deploys

Build time: ~3-5 minutes

## Verification Steps

### 1. Check Build Logs

Look for:
```
✅ Python dependencies installed
✅ Frontend built successfully
✅ Frontend build output verified
=== Build Complete ===
```

### 2. Test Endpoints

```bash
# Replace with your actual URL
URL="https://your-app.onrender.com"

# Health check
curl $URL/api/health

# Frontend (should return HTML)
curl $URL/ | grep "<!doctype"

# Assets (should return 200)
curl -I $URL/assets/index-*.js
```

### 3. Browser Test

1. Open `https://your-app.onrender.com`
2. F12 → Console: **No CORS errors**
3. F12 → Network: Assets load from same domain

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "npm: command not found" | Render should auto-detect Node.js from `package.json` |
| "Permission denied: build.sh" | `chmod +x build.sh`, commit, push |
| API returns 404 | Verify start command: `cd backend && python main.py` |
| Assets return 404 | Check build logs for "Frontend build output verified" |
| Blank page, no errors | Check `VITE_API_URL` is NOT set in environment |

## Quick Commands

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Make build.sh executable
chmod +x build.sh

# Test build locally
./build.sh
cd backend && python main.py
# Open http://localhost:8000

# Commit and deploy
git add .
git commit -m "Configure single-service deployment"
git push origin main
```

## What This Architecture Does

✅ **Eliminates CORS** - Frontend and API on same origin
✅ **Single service** - Simpler, cheaper
✅ **Automatic sync** - Frontend and backend always match
✅ **Faster** - No cross-origin preflight requests

## File Structure

```
project/
├── build.sh                          # Unified build script
├── backend/
│   ├── main.py                       # Serves API + frontend
│   ├── requirements.txt
│   └── ...
└── operator-dashboard/
    ├── .env.production                # Empty VITE_API_URL
    ├── package.json
    ├── dist/                          # Built by build.sh
    └── src/
        └── utils/
            └── env.ts                 # Returns '' for production
```

## Success Criteria

✅ Build completes without errors
✅ `curl $URL/api/health` returns JSON
✅ `curl $URL/` returns HTML with React app
✅ `curl $URL/assets/index-*.js` returns 200
✅ Browser loads app with no CORS errors
✅ Login works (if database configured)

## Next Steps After Deployment

1. Create first user: `POST /api/auth/register`
2. Test core workflows
3. Configure custom domain (optional)
4. Set up monitoring/alerts
5. Backup database (if using Postgres)

---

**Full Guide:** See `RENDER_DEPLOYMENT.md`
**Previous Approach:** See `DEPLOYMENT_CHECKLIST.md` (Netlify + Render)
