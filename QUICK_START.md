# Quick Start - Single-Service Deployment

## Current Status: ✅ Working Locally

Your container is **running right now** at: http://localhost:8000

## Access Your Application

### Frontend (Operator Dashboard)
```
http://localhost:8000
```

### Backend API
```
Health:      http://localhost:8000/health
API Docs:    http://localhost:8000/docs
All APIs:    http://localhost:8000/api/*
```

## Quick Commands

### Start/Stop Container
```bash
# Start
cd "C:\git\project\CONTENT MARKETING\30 Day Content Jumpstart\Project"
docker-compose up -d api

# Stop
docker-compose down

# View logs (live)
docker logs content-jumpstart-api -f

# Restart after changes
docker-compose build api && docker-compose up -d api
```

### Test Endpoints
```bash
# Test health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:8000/

# Test API
curl http://localhost:8000/api/health
```

### Check Status
```bash
# Container status
docker ps | findstr content-jumpstart

# Container logs
docker logs content-jumpstart-api --tail 50

# Frontend files in container
docker exec content-jumpstart-api ls //app//operator-dashboard//dist
```

## What's Serving on Port 8000?

```
Port 8000
├── / ────────────────────→ React Frontend (Operator Dashboard)
│   ├── /projects ────────→ Projects page
│   ├── /clients ─────────→ Clients page
│   ├── /deliverables ───→ Deliverables page
│   └── /settings ────────→ Settings page
│
├── /api/* ───────────────→ Backend API
│   ├── /api/health ─────→ Health check
│   ├── /api/clients ────→ Clients CRUD
│   ├── /api/projects ───→ Projects CRUD
│   ├── /api/generator ──→ Content generation
│   └── /api/auth ───────→ Authentication
│
├── /health ──────────────→ Health check (alias)
└── /docs ────────────────→ Swagger API documentation
```

## Architecture

**One container = Frontend + Backend + Agents**

```
┌─────────────────────────────────────┐
│  Docker Container (Port 8000)       │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  FastAPI Backend            │   │
│  │  - Serves API at /api/*     │   │
│  │  - Serves frontend at /     │   │
│  │  - Calls agents internally  │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  React Frontend (Built)     │   │
│  │  /operator-dashboard/dist   │   │
│  │  - index.html               │   │
│  │  - assets/*.js, *.css       │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Content Generation Agents  │   │
│  │  - BriefParser              │   │
│  │  - ContentGenerator         │   │
│  │  - QAValidator              │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Next Steps

### 1. Test in Browser ⬜
```
Open: http://localhost:8000
Expected: Operator Dashboard UI loads
```

### 2. Test API ⬜
```
Open: http://localhost:8000/docs
Expected: Swagger UI with API documentation
```

### 3. Test Content Generation ⬜
```
Use dashboard to:
1. Create a client
2. Upload a brief
3. Generate posts
4. Review quality
5. Export deliverable
```

### 4. Push to GitHub ⬜
```bash
git add Dockerfile docker-compose.yml SINGLE_SERVICE_DEPLOYMENT.md
git commit -m "Add single-service deployment"
git push origin main
```

### 5. Deploy to Render ⬜
```
1. Create Web Service on Render
2. Connect repository
3. Set environment variables (see below)
4. Deploy
5. Test at https://your-app.onrender.com
```

## Environment Variables for Render

**Required:**
```
ANTHROPIC_API_KEY=sk-ant-api-... (your Claude API key)
SECRET_KEY=<random-32-character-string>
POSTGRES_PASSWORD=<random-password>
DATABASE_URL=postgresql://user:pass@host:5432/content_jumpstart
```

**Optional (with good defaults):**
```
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.onrender.com
PARALLEL_GENERATION=true
MAX_CONCURRENT_API_CALLS=5
DEBUG_MODE=false
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs content-jumpstart-api

# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process using port 8000
taskkill /PID <pid> /F
```

### Frontend not loading
```bash
# Verify frontend files exist
docker exec content-jumpstart-api ls //app//operator-dashboard//dist

# Expected:
# index.html
# assets/

# If missing, rebuild
docker-compose build api --no-cache
```

### API calls fail
```bash
# Check backend is running
curl http://localhost:8000/health

# Check API endpoint
curl http://localhost:8000/api/health

# Check CORS (should be empty in prod)
docker exec content-jumpstart-api env | grep CORS
```

### Database connection fails
```bash
# Check database is running
docker ps | findstr content-jumpstart-db

# Check connection
docker exec content-jumpstart-db psql -U postgres -c "SELECT 1"

# Check DATABASE_URL
docker exec content-jumpstart-api env | grep DATABASE_URL
```

## Documentation

- **This file** - Quick commands
- **DEPLOYMENT_SUCCESS.md** - Verification results
- **SINGLE_SERVICE_DEPLOYMENT.md** - Complete guide
- **docker-compose.yml** - Service configuration
- **Dockerfile** - Multi-stage build

## Support

**Issue?** Check logs first:
```bash
docker logs content-jumpstart-api -f
```

**Still stuck?** See `SINGLE_SERVICE_DEPLOYMENT.md` for detailed troubleshooting.

## Success! 🎉

Your deployment is **working locally**. When you hit port 8000, you should now see:
- **Frontend UI** at the root
- **API responses** at /api/* endpoints
- **No CORS errors**

Ready to deploy to production? Follow the "Next Steps" above.
