# Docker Quick Start Guide

## TL;DR - Get Running in 2 Minutes

```bash
cd project/backend

# 1. Copy environment file
cp .env.docker.example .env

# 2. Edit .env and set:
#    - SECRET_KEY (generate: openssl rand -hex 32)
#    - ANTHROPIC_API_KEY

# 3. Start (development with SQLite)
docker-compose --profile dev up -d

# 4. Check health
curl http://localhost:8000/health

# 5. View API docs
open http://localhost:8000/docs
```

**That's it!** Your backend is running at http://localhost:8000

---

## What You Get

✅ FastAPI backend running in Docker
✅ Automatic reload on code changes (dev mode)
✅ SQLite database (persisted in ./data)
✅ API documentation at /docs
✅ Health check endpoint at /health
✅ Logs in ./logs directory

---

## Common Commands

### Development Mode (SQLite)

```bash
# Start
docker-compose --profile dev up -d

# View logs
docker-compose logs -f api-dev

# Restart
docker-compose restart api-dev

# Stop
docker-compose --profile dev down

# Rebuild after dependency changes
docker-compose --profile dev up -d --build
```

### Production Mode (PostgreSQL)

```bash
# Start both API and database
docker-compose --profile prod up -d

# View logs
docker-compose logs -f api

# Check database status
docker-compose exec db psql -U postgres -d content_jumpstart -c "SELECT version();"

# Run migrations (if using Alembic)
docker-compose exec api alembic upgrade head

# Stop everything
docker-compose --profile prod down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose --profile prod down -v
```

### Debugging

```bash
# Shell into container
docker-compose exec api bash

# Check environment variables
docker-compose exec api env

# Test database connection
docker-compose exec api python -c "from database import engine; print(engine.url)"

# View container stats
docker stats
```

---

## Environment Variables

### Minimal Setup (Development)

```env
SECRET_KEY=your-secret-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Full Setup (Production)

```env
# Required
SECRET_KEY=<openssl rand -hex 32>
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_PASSWORD=secure-password-here

# Optional
DEBUG_MODE=false
CORS_ORIGINS=https://your-frontend.netlify.app
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
PARALLEL_GENERATION=true
MAX_CONCURRENT_API_CALLS=5
```

---

## Test the API

### Health Check
```bash
curl http://localhost:8000/health
# {"status":"healthy","timestamp":1234567890}
```

### API Documentation
Visit: http://localhost:8000/docs

### Create User (Example)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword",
    "full_name": "Test User"
  }'
```

---

## Troubleshooting

### Port Already in Use
```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Container Won't Start
```bash
# Check logs
docker-compose logs api-dev

# Common issues:
# - Missing .env file → copy .env.docker.example
# - Invalid SECRET_KEY → generate new one
# - Missing ANTHROPIC_API_KEY → add to .env
```

### Database Connection Failed (Production)
```bash
# Check database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Verify DATABASE_URL format
docker-compose exec api env | grep DATABASE_URL
```

### Code Changes Not Reflected
```bash
# Development mode auto-reloads, but if it doesn't:
docker-compose restart api-dev

# Or rebuild:
docker-compose --profile dev up -d --build
```

---

## Next Steps

1. **Local development:** Use dev profile (SQLite)
2. **Test production setup:** Use prod profile (PostgreSQL)
3. **Deploy to cloud:** See CONTAINER_DEPLOYMENT_PLAN.md
4. **Connect frontend:** Update Netlify env vars

---

## File Structure

```
backend/
├── Dockerfile                      # Container build instructions
├── docker-compose.yml              # Local orchestration
├── .dockerignore                   # Files to exclude from build
├── .env.docker.example             # Environment template
├── .env                            # Your environment (gitignored)
│
├── deploy/                         # Platform-specific configs
│   ├── railway.json
│   ├── render.yaml
│   ├── fly.toml
│   └── cloudrun.yaml
│
├── data/                           # Database & uploads (volume)
├── logs/                           # Application logs (volume)
│
└── CONTAINER_DEPLOYMENT_PLAN.md    # Full deployment guide
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start dev | `docker-compose --profile dev up -d` |
| Start prod | `docker-compose --profile prod up -d` |
| View logs | `docker-compose logs -f` |
| Restart | `docker-compose restart api-dev` |
| Stop | `docker-compose down` |
| Rebuild | `docker-compose up -d --build` |
| Shell | `docker-compose exec api bash` |

---

**Ready to deploy?** See `CONTAINER_DEPLOYMENT_PLAN.md` for cloud deployment options.
