# Content Jumpstart Backend API

FastAPI backend for the Operator Dashboard with hybrid agent integration.

## Features

- **JWT Authentication** - Secure API access
- **Rate Limiting** - 70% of Anthropic API limits (2,800 req/min, 280K tokens/min)
- **Direct CRUD API** - Fast operations for projects, deliverables, posts
- **Agent-Powered API** - Complex workflows via Internal CLI Agent
- **Server-Sent Events** - Real-time progress updates
- **File Uploads** - Brief upload or paste support

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment (local vs remote)

- Local dev (SQLite): use `.env.local` (created in repo). Adjust `ANTHROPIC_API_KEY` and `SECRET_KEY` as needed.
- Remote/Render DB: `.env` currently points to the Render Postgres instance.
- To switch which file is loaded at runtime, set `ENV_FILE`:
  ```bash
  # Local
  ENV_FILE=.env.local uvicorn main:app --reload --host 0.0.0.0 --port 8000
  # Remote/Render DB
  ENV_FILE=.env uvicorn main:app --host 0.0.0.0 --port 8000
  ```

### 3. Run Server

```bash
ENV_FILE=.env.local uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Project Structure

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py               # Settings from environment
├── database.py             # SQLAlchemy setup
├── models/                 # Database models
├── schemas/                # Pydantic schemas
├── routers/                # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── projects.py        # Projects CRUD
│   ├── deliverables.py    # Deliverables CRUD
│   ├── briefs.py          # Brief upload/paste
│   └── agent.py           # Agent-powered endpoints
├── services/               # Business logic
│   ├── agent_service.py   # Agent integration
│   └── crud.py            # Database operations
├── middleware/             # Custom middleware
├── utils/                  # Utilities
│   ├── auth.py            # JWT utilities
│   └── rate_limiter.py    # Rate limiting tracker
└── requirements.txt
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with credentials
- `POST /api/auth/refresh` - Refresh access token

### Direct API (CRUD)
- `GET/POST /api/projects` - List/create projects
- `GET/PUT/DELETE /api/projects/{id}` - Project operations
- `GET /api/deliverables` - List deliverables
- `GET /api/posts` - List posts

### Briefs
- `POST /api/briefs/upload` - Upload brief file
- `POST /api/briefs/create` - Create from pasted text

### Agent-Powered
- `POST /api/agent/generate-all` - Generate 30 posts (SSE)
- `POST /api/agent/regenerate` - Regenerate specific posts
- `POST /api/agent/export-deliverable` - Create deliverable package
- `POST /api/agent/message` - Natural language commands

## Development

### Run Tests
```bash
pytest
```

### Check Rate Limits
```bash
curl http://localhost:8000/health
```

### Generate Secret Key
```bash
openssl rand -hex 32
```

## Configuration

Key environment variables:

- `SECRET_KEY` - JWT secret (required)
- `ANTHROPIC_API_KEY` - Anthropic API key (required)
- `DATABASE_URL` - SQLite database path
- `RATE_LIMIT_REQUESTS_PER_MINUTE` - Request rate limit (default: 2800)
- `RATE_LIMIT_TOKENS_PER_MINUTE` - Token rate limit (default: 280000)

See `.env.example` for all options.
