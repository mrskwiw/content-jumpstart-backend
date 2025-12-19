# Single-Service Deployment Guide

## Architecture Overview

This deployment strategy packages **frontend + backend + agents** into a **single Docker container** running on **port 8000**.

### What Gets Served on Port 8000

```
http://localhost:8000/
├── /                    → React frontend (index.html)
├── /assets/*            → Frontend static files (JS, CSS, images)
├── /api/*               → Backend API endpoints
├── /health              → Health check endpoint
├── /docs                → API documentation (Swagger UI)
└── /*                   → React Router (client-side routing)
```

**Key Benefit:** No CORS issues - frontend and backend share the same origin.

## How It Works

### Multi-Stage Dockerfile

The `Dockerfile` has 3 stages:

1. **Stage 1: Build React Frontend** (Node.js 20)
   - Installs npm dependencies
   - Runs `npm run build`
   - Outputs to `/frontend/dist`

2. **Stage 2: Build Python Dependencies** (Python 3.11)
   - Installs Python packages
   - Compiles native extensions
   - Outputs to `/root/.local`

3. **Stage 3: Production Image** (Python 3.11 slim)
   - Copies Python dependencies from Stage 2
   - Copies entire Python codebase
   - **Copies built frontend from Stage 1** to `/app/operator-dashboard/dist`
   - Runs FastAPI with uvicorn

### Backend Static File Serving

The backend (`backend/main.py:172-209`) automatically serves the frontend:

```python
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "operator-dashboard" / "dist"

if FRONTEND_BUILD_DIR.exists():
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"))

    # Root route: serve React app
    @app.get("/")
    async def serve_root():
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

    # Catch-all: serve index.html for React Router
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")
```

### Frontend API Configuration

The frontend (`operator-dashboard/src/utils/env.ts:48-71`) automatically uses relative URLs in production:

```typescript
export function getApiBaseUrl(): string {
  const mode = readEnvVar('MODE') || 'development';

  if (mode === 'production') {
    return '';  // Relative URLs - no CORS!
  } else {
    return 'http://localhost:8000';  // Dev mode
  }
}
```

## Building for Production

### Local Build & Test

```bash
# 1. Build the Docker image
docker-compose build api

# 2. Start the container
docker-compose up api

# 3. Access the application
# Frontend: http://localhost:8000
# API docs: http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

### Render Deployment

#### Option 1: Web Service (Recommended)

1. **Create Web Service** on Render dashboard
2. **Connect repository**
3. **Configure build settings:**
   ```
   Build Command:    docker build -t content-jumpstart .
   Start Command:    docker run -p 8000:8000 content-jumpstart
   ```
4. **Set environment variables:**
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   SECRET_KEY=<generate-random-string>
   POSTGRES_PASSWORD=<generate-random-string>
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-app.onrender.com
   ```

#### Option 2: Docker Deployment

1. **Use `render.yaml`** (see below)
2. **Push to GitHub**
3. **Render auto-deploys** on push to main branch

### render.yaml Configuration

```yaml
services:
  - type: web
    name: content-jumpstart
    env: docker
    dockerfilePath: ./Dockerfile
    dockerContext: .
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: POSTGRES_PASSWORD
        generateValue: true
      - key: ENVIRONMENT
        value: production
      - key: CORS_ORIGINS
        value: https://content-jumpstart.onrender.com

  - type: pserv
    name: content-jumpstart-db
    env: docker
    plan: free
    dockerfilePath: ./Dockerfile.postgres
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-...` |
| `SECRET_KEY` | JWT signing key | Random 32-char string |
| `POSTGRES_PASSWORD` | Database password | Random string |
| `DATABASE_URL` | Postgres connection string | `postgresql://user:pass@host/db` |

### Optional (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Deployment environment |
| `DEBUG_MODE` | `false` | Enable debug logging |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `PARALLEL_GENERATION` | `true` | Enable async generation |
| `MAX_CONCURRENT_API_CALLS` | `5` | Anthropic API concurrency |

## Testing the Build

### 1. Verify Frontend Build

```bash
# Build image
docker-compose build api

# Check if frontend files exist in container
docker run --rm content-jumpstart-api ls -la /app/operator-dashboard/dist

# Expected output:
# index.html
# assets/
#   ├── index-abc123.js
#   ├── index-def456.css
#   └── ...
```

### 2. Test Endpoints

```bash
# Start container
docker-compose up -d api

# Test health endpoint (API)
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"1.0.0",...}

# Test root endpoint (Frontend)
curl http://localhost:8000/

# Expected: HTML content with <div id="root"></div>

# Test API endpoint
curl http://localhost:8000/api/health

# Expected: {"status":"healthy",...}
```

### 3. Test in Browser

```bash
# 1. Open browser
http://localhost:8000

# 2. You should see the Operator Dashboard UI
# 3. Check browser console for errors
# 4. Test API calls (should work without CORS errors)
```

## Troubleshooting

### Issue: "Frontend not found" warning

**Symptom:** Container logs show:
```
>> WARNING: Frontend build directory not found: /app/operator-dashboard/dist
>> Run 'cd operator-dashboard && npm run build' to build frontend
```

**Solution:** The frontend build stage failed. Check:
1. Is `operator-dashboard/package.json` present?
2. Did `npm ci` succeed?
3. Did `npm run build` succeed?

**Debug:**
```bash
# Build with verbose output
docker build -t content-jumpstart . --progress=plain

# Check build logs for errors
```

### Issue: "Received HTML instead of API response"

**Symptom:** Browser console error when making API calls.

**Cause:** Frontend is calling `/health` instead of `/api/health`

**Solution:** All API endpoints must have `/api` prefix:
```typescript
// ❌ Wrong
axios.get('/health')

// ✅ Correct
axios.get('/api/health')
```

### Issue: CORS errors in production

**Symptom:** Browser shows CORS errors even though same origin.

**Cause:** `VITE_API_URL` environment variable set during build.

**Solution:** **Don't set `VITE_API_URL`** in production build. The frontend automatically uses relative URLs when this is unset.

```bash
# ❌ Wrong - causes CORS
VITE_API_URL=http://api:8000 npm run build

# ✅ Correct - uses relative URLs
npm run build
```

### Issue: React Router 404 errors

**Symptom:** Refreshing page shows 404 error.

**Cause:** Backend not serving `index.html` for all routes.

**Solution:** The catch-all route in `backend/main.py:186-203` should handle this. Verify it exists.

## Build Optimization

### Reduce Image Size

Current image size: ~800MB

**Optimization opportunities:**
1. **Multi-stage build** ✅ Already implemented
2. **Slim Python base** ✅ Already using `python:3.11-slim`
3. **Alpine Node** ✅ Already using `node:20-alpine`
4. **Production deps only** ❌ Currently installing all deps

**To optimize further:**
```dockerfile
# In frontend-builder stage
RUN npm ci --production
```

### Speed Up Builds

**Use build cache:**
```bash
# Cache Python packages
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1 api
```

**Parallel builds:**
```bash
# Build stages run in parallel automatically
docker-compose build --parallel
```

## Monitoring in Production

### Health Checks

Render automatically monitors `/health` endpoint (configured in Dockerfile).

**Health check configuration:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### Logging

**View logs:**
```bash
# Render dashboard: Logs tab
# Or via CLI:
render logs -s content-jumpstart
```

### Metrics

Access metrics at:
- **Health endpoint:** `https://your-app.onrender.com/health`
- **Render dashboard:** Metrics tab
- **API rate limits:** Included in health response

## Development vs Production

### Development (Separate Services)

```bash
# Backend (terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# Frontend (terminal 2)
cd operator-dashboard
npm run dev  # Port 5173
```

**Benefits:**
- Fast hot reload
- Independent debugging
- Better dev experience

### Production (Single Service)

```bash
docker-compose up api
```

**Benefits:**
- Single deployment unit
- No CORS issues
- Simplified infrastructure
- Cheaper hosting (1 service vs 2)

## Cost Comparison

### Separate Services (Old)
- **Backend web service:** $7/month (Starter)
- **Frontend static site:** $0 (free tier)
- **PostgreSQL:** $7/month (Basic)
- **Total:** $14/month

### Single Service (New)
- **Combined web service:** $7/month (Starter)
- **PostgreSQL:** $7/month (Basic)
- **Total:** $14/month

**Same cost, but simpler architecture and no CORS.**

## Next Steps

1. ✅ **Build locally** - Verify the build works
2. ✅ **Test locally** - Access http://localhost:8000
3. ⬜ **Push to GitHub** - Trigger Render deployment
4. ⬜ **Configure Render** - Set environment variables
5. ⬜ **Monitor deployment** - Check logs and health endpoint
6. ⬜ **Test production** - Verify frontend and API work

## References

- **Dockerfile:** `Dockerfile`
- **Docker Compose:** `docker-compose.yml`
- **Backend Config:** `backend/main.py`
- **Frontend Config:** `operator-dashboard/src/utils/env.ts`
- **Render Docs:** https://render.com/docs/docker
