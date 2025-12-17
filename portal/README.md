# Client Self-Service Portal

A full-stack web portal for the 30-Day Content Jumpstart system, enabling clients to manage projects, submit briefs, download deliverables, and track analytics independently.

## Overview

**Version:** 1.0.0 (Week 1 - Foundation Complete)
**Status:** In Development (Week 1 of 8)
**Tech Stack:** FastAPI (backend) + React (frontend - coming Week 3)

---

## Features

### ✅ Implemented (Week 1)

- User registration with email/password
- JWT authentication (access + refresh tokens)
- Secure password hashing (bcrypt)
- Role-based access control (client, admin, agency)
- Database models for all entities
- Multi-tenant architecture (white-label ready)
- CORS-enabled API
- Auto-generated API documentation

### 🚧 Coming Soon

- **Week 2:** Brief submission, file uploads, project creation
- **Week 3:** Project dashboard, status tracking, deliverable downloads
- **Week 4:** Revision management, feedback system
- **Week 5:** Stripe payment integration, invoicing
- **Week 6:** Analytics dashboard (Phase 11 integration)
- **Week 7:** White-label branding, multi-tenant UI
- **Week 8:** Testing, security audit, production deployment

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip
- (Optional) PostgreSQL for production

### Installation

```bash
# Navigate to backend directory
cd portal/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY to a random 32+ character string
```

### Running the Server

```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Server will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Redoc: http://localhost:8000/redoc
```

### Database Initialization

The database is automatically initialized on first startup. You can also manually initialize:

```bash
python -c "from app.db.database import init_db; init_db(); print('Database initialized')"
```

---

## API Documentation

### Authentication Endpoints

#### Register New User

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "full_name": "John Doe",
  "company_name": "Acme Corp"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "abc123",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "client",
    "is_active": true
  }
}
```

#### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:** Same as register

#### Refresh Access Token

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** New access token (same refresh token returned)

### Protected Endpoints

All other endpoints require authentication. Include the access token in the Authorization header:

```http
Authorization: Bearer {access_token}
```

#### Project Management

**List Projects:**
```http
GET /api/projects/?status_filter=processing&skip=0&limit=100
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total": 5,
  "projects": [
    {
      "project_id": "abc123",
      "user_id": "user456",
      "client_name": "Acme Corp",
      "status": "processing",
      "package_tier": "Professional",
      "package_price": 1800.00,
      "posts_count": 30,
      "revision_limit": 2,
      "revisions_used": 0,
      "submitted_at": "2025-12-08T10:00:00",
      "processing_started_at": "2025-12-08T10:05:00",
      "completed_at": null,
      "delivered_at": null
    }
  ]
}
```

**Get Project Details:**
```http
GET /api/projects/{project_id}
Authorization: Bearer {access_token}
```

**Create New Project:**
```http
POST /api/projects/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "client_name": "Acme Corp",
  "package_tier": "Professional",
  "package_price": 1800.00,
  "posts_count": 30,
  "revision_limit": 2
}
```

**Update Project Status:**
```http
PATCH /api/projects/{project_id}/status
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "status": "delivered"
}
```

Valid statuses: `brief_submitted`, `processing`, `qa_review`, `ready_for_delivery`, `delivered`, `completed`

---

## Database Schema

### Tables

1. **users** - User accounts
2. **tenants** - White-label organizations
3. **projects** - Content generation requests
4. **briefs** - Client requirements
5. **file_uploads** - Uploaded files
6. **revisions** - Change requests
7. **payments** - Payment transactions
8. **deliverables** - Generated content
9. **activity_log** - Audit trail

### Relationships

- User → Projects (1:many)
- Project → Brief (1:1)
- Project → Revisions (1:many)
- Project → Deliverables (1:many)
- Project → FileUploads (1:many)
- Tenant → Users (1:many)

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Application
APP_NAME=Content Jumpstart Portal
DEBUG=True

# Database
DATABASE_URL=sqlite:///./portal.db

# Security (REQUIRED - Change in production!)
SECRET_KEY=your-secret-key-min-32-chars-change-in-production

# Stripe (for Week 5)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## Security

### Authentication Flow

1. User registers or logs in
2. Server returns JWT access token (30 min expiry) + refresh token (7 days)
3. Client includes access token in Authorization header
4. When access token expires, use refresh token to get new access token

### Password Security

- Passwords hashed with bcrypt
- Minimum 8 characters required
- Never stored in plaintext
- Hash includes automatic salt

### Access Control

- Users can only access their own projects
- Admin role required for administrative endpoints
- Inactive accounts cannot authenticate
- Token expiry enforced

---

## Development

### Project Structure

```
portal/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Security & auth
│   │   ├── db/            # Database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic (coming Week 2)
│   │   ├── config.py      # Configuration
│   │   └── main.py        # FastAPI app
│   ├── tests/             # Tests (coming Week 8)
│   └── requirements.txt
└── frontend/              # React app (coming Week 3)
```

### Adding New Endpoints

1. Create schema in `app/schemas/`
2. Create route in `app/api/`
3. Register router in `app/main.py`
4. Add business logic in `app/services/`

Example:

```python
# app/api/example.py
from fastapi import APIRouter, Depends
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/example", tags=["Example"])

@router.get("/")
async def example_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": "Hello, " + current_user.full_name}
```

```python
# app/main.py
from .api import auth_router, example_router

app.include_router(auth_router)
app.include_router(example_router)
```

---

## Testing

### Manual Testing

Use the interactive API docs at `http://localhost:8000/docs`:

1. Expand `/api/auth/register`
2. Click "Try it out"
3. Fill in example data
4. Click "Execute"
5. Copy the `access_token` from response
6. Click "Authorize" button (top right)
7. Paste token, click "Authorize"
8. Now you can test protected endpoints

### Using cURL

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Access protected endpoint
curl -H "Authorization: Bearer {your_access_token}" \
  http://localhost:8000/api/projects/
```

---

## Deployment (Coming Week 8)

### Production Checklist

- [ ] Change SECRET_KEY to secure random value
- [ ] Set DEBUG=False
- [ ] Configure PostgreSQL database
- [ ] Enable HTTPS
- [ ] Set up domain & SSL certificate
- [ ] Configure production CORS origins
- [ ] Add rate limiting
- [ ] Set up logging & monitoring
- [ ] Run security audit
- [ ] Configure backup strategy

---

## Troubleshooting

### Common Issues

**Issue:** "Could not validate credentials"
**Solution:** Check that your access token hasn't expired (30 min). Use refresh token to get new access token.

**Issue:** "Email already registered"
**Solution:** Email must be unique. Use different email or login with existing account.

**Issue:** Database not initialized
**Solution:** Run `python -c "from app.db.database import init_db; init_db()"`

**Issue:** Import errors
**Solution:** Make sure you're in the `portal/backend` directory and virtual environment is activated.

---

## Support

For issues or questions:
- Check `/docs` endpoint for API documentation
- Review completion doc: `../../PHASE_12_WEEK1_COMPLETION.md`
- Check main project docs: `../../PHASE_12_PORTAL_PLAN.md`

---

## License

Part of the 30-Day Content Jumpstart system.

---

**Current Status:** Week 1 Complete - Foundation & Authentication ✅
**Next Milestone:** Week 2 - Client Onboarding Flow
