# Backend Setup and Testing Guide

## Phase 2 Direct API Implementation - Complete! ✅

All 6 routers have been implemented and wired into the FastAPI application:

- ✅ Authentication (`/api/auth`)
- ✅ Clients (`/api/clients`)
- ✅ Projects (`/api/projects`)
- ✅ Briefs (`/api/briefs`)
- ✅ Deliverables (`/api/deliverables`)
- ✅ Posts (`/api/posts`)

## Quick Start

### 1. Install Dependencies

```bash
# From project/backend directory
cd "C:\git\project\CONTENT MARKETING\30 Day Content Jumpstart\project\backend"

# Create virtual environment (if not already done)
python -m venv ../../venv

# Activate virtual environment
../../venv/Scripts/activate  # Windows
source ../../venv/bin/activate  # macOS/Linux

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux

# Edit .env and set:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - ANTHROPIC_API_KEY (if you have one, optional for Direct API testing)
```

### 3. Initialize Database

The database will be created automatically on first run. It will be located at:
```
project/data/operator.db
```

### 4. Start the Backend Server

```bash
# Start the server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --port 8000
```

The server will start on `http://localhost:8000`

**Console output should show:**
```
🚀 Starting Content Jumpstart API...
📊 Rate Limits: 2800 req/min, 280000 tokens/min
✅ Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Test the API

#### Option 1: Run Automated Test Script

```bash
# In a NEW terminal (keep server running in first terminal)
cd "C:\git\project\CONTENT MARKETING\30 Day Content Jumpstart\project\backend"

# Activate venv
../../venv/Scripts/activate

# Run test script
python test_api_endpoints.py
```

This will test all endpoints in sequence:
- ✅ Health check
- ✅ User registration
- ✅ Login (JWT authentication)
- ✅ Client CRUD operations
- ✅ Project CRUD operations
- ✅ Brief creation (paste text)
- ✅ Posts listing
- ✅ Deliverables listing
- ✅ Project deletion

#### Option 2: Interactive API Documentation

FastAPI provides automatic interactive API docs:

1. **Swagger UI:** http://localhost:8000/docs
2. **ReDoc:** http://localhost:8000/redoc

**Testing with Swagger UI:**
1. Open http://localhost:8000/docs
2. Click "Authorize" button (top right)
3. Register a user via POST `/api/auth/register`
4. Copy the `access_token` from response
5. Paste into "Authorize" dialog as: `Bearer <token>`
6. Now you can test all protected endpoints

#### Option 3: Manual Testing with cURL

```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'

# Save the access_token from login response, then:
export TOKEN="<your-access-token>"

# List clients (requires auth)
curl http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN"

# Create client
curl -X POST http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Client","industry":"Technology","website":"https://example.com"}'
```

## API Endpoints Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login and get tokens | No |
| POST | `/api/auth/refresh` | Refresh access token | No (requires refresh token) |

### Client Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/clients/` | List all clients | Yes |
| POST | `/api/clients/` | Create new client | Yes |
| GET | `/api/clients/{client_id}` | Get client by ID | Yes |

### Project Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/projects/` | List all projects | Yes |
| POST | `/api/projects/` | Create new project | Yes |
| GET | `/api/projects/{project_id}` | Get project by ID | Yes |
| PUT | `/api/projects/{project_id}` | Update project | Yes |
| DELETE | `/api/projects/{project_id}` | Delete project | Yes |

### Brief Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/briefs/create` | Create brief from pasted text | Yes |
| POST | `/api/briefs/upload` | Upload brief file | Yes |
| GET | `/api/briefs/{brief_id}` | Get brief by ID | Yes |

### Post Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/posts/` | List all posts | Yes |
| GET | `/api/posts/{post_id}` | Get post by ID | Yes |

### Deliverable Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/deliverables/` | List all deliverables | Yes |
| GET | `/api/deliverables/{deliverable_id}` | Get deliverable by ID | Yes |
| PATCH | `/api/deliverables/{deliverable_id}/mark-delivered` | Mark deliverable as delivered | Yes |

## Database Schema

The system uses SQLite with the following main tables:

- **users** - User accounts
- **clients** - Client companies
- **projects** - Content generation projects
- **briefs** - Client briefs (linked to projects)
- **runs** - Generation runs
- **posts** - Generated social media posts
- **deliverables** - Final deliverable packages

All tables have proper foreign key relationships and cascading deletes.

## Troubleshooting

### Server won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`
- **Fix:** Make sure you've installed dependencies: `pip install -r requirements.txt`

**Error:** `SECRET_KEY is required`
- **Fix:** Copy `.env.example` to `.env` and set SECRET_KEY

### Database errors

**Error:** `sqlite3.OperationalError: no such table: users`
- **Fix:** Delete `project/data/operator.db` and restart server (will recreate tables)

### Authentication errors

**Error:** `401 Unauthorized`
- **Fix:** Make sure you're passing the token correctly: `Authorization: Bearer <token>`

**Error:** `Invalid authentication credentials`
- **Fix:** Token may have expired (30 min). Login again to get new token.

### Test script fails

**Error:** `Connection refused`
- **Fix:** Make sure backend server is running on http://localhost:8000

**Error:** `User already registered`
- **Fix:** This is expected if running tests multiple times. Test will continue.

## Next Steps

After verifying all endpoints work:

1. **Phase 3:** Implement Agent-powered endpoints with SSE
   - `/api/agent/generate` - Intelligent content generation
   - `/api/agent/regenerate` - Context-aware regeneration
   - `/api/agent/analyze` - Brief analysis and recommendations

2. **Phase 4:** Frontend integration with React Operator Dashboard
   - Connect dashboard to Direct API endpoints
   - Implement JWT authentication flow
   - Wire up wizard to backend

3. **Phase 5:** End-to-end testing
   - Integration tests across full stack
   - Performance testing under load
   - User acceptance testing

## Project Structure

```
backend/
├── main.py                      # FastAPI app entry point
├── config.py                    # Configuration from .env
├── database.py                  # Database connection & session
├── requirements.txt             # Python dependencies
├── test_api_endpoints.py        # Automated API tests
├── .env.example                 # Environment template
├── .env                         # Environment variables (gitignored)
│
├── models/                      # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py                  # User model
│   ├── client.py                # Client model
│   ├── project.py               # Project model
│   ├── brief.py                 # Brief model
│   ├── run.py                   # Run model
│   ├── post.py                  # Post model
│   └── deliverable.py           # Deliverable model
│
├── schemas/                     # Pydantic schemas
│   ├── __init__.py
│   ├── auth.py                  # Auth request/response schemas
│   ├── client.py                # Client schemas
│   ├── project.py               # Project schemas
│   ├── brief.py                 # Brief schemas
│   ├── post.py                  # Post schemas
│   └── deliverable.py           # Deliverable schemas
│
├── routers/                     # API route handlers
│   ├── __init__.py
│   ├── auth.py                  # Authentication endpoints
│   ├── clients.py               # Client endpoints
│   ├── projects.py              # Project endpoints
│   ├── briefs.py                # Brief endpoints
│   ├── posts.py                 # Post endpoints
│   └── deliverables.py          # Deliverable endpoints
│
├── services/                    # Business logic
│   ├── __init__.py
│   └── crud.py                  # CRUD operations
│
├── middleware/                  # Middleware
│   ├── __init__.py
│   └── auth_dependency.py       # JWT auth dependency
│
└── utils/                       # Utilities
    ├── __init__.py
    ├── auth.py                  # JWT token creation/verification
    └── rate_limiter.py          # Rate limiting tracker
```

## Development Notes

- **Database:** SQLite with WAL mode for better concurrency
- **Authentication:** JWT tokens with 30-minute expiry
- **Rate Limiting:** In-memory tracker at 70% of Anthropic API limits
- **CORS:** Configured for frontend on localhost:5173 and localhost:3000
- **Logging:** All requests logged to console (can be configured)

## Support

If you encounter issues:

1. Check the console output for error messages
2. Verify .env configuration is correct
3. Ensure all dependencies are installed
4. Check database file exists and is writable
5. Review API documentation at http://localhost:8000/docs
