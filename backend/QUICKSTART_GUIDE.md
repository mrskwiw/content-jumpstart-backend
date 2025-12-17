# Backend Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Install Dependencies (1 minute)

```bash
# Navigate to backend directory
cd "C:\git\project\CONTENT MARKETING\30 Day Content Jumpstart\project\backend"

# Activate virtual environment
..\..\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Generate Secret Key (30 seconds)

```bash
# Generate a secure secret key
python generate_secret_key.py

# Copy the output (looks like: KwL8P9zT...)
```

### Step 3: Configure Environment (30 seconds)

```bash
# Copy template
copy .env.example .env

# Edit .env file and replace this line:
SECRET_KEY=your-secret-key-here-replace-in-production

# With your generated key:
SECRET_KEY=KwL8P9zT...  (paste what you copied)
```

### Step 4: Start Backend (10 seconds)

```bash
# Start the server
python main.py
```

**Expected output:**
```
🚀 Starting Content Jumpstart API...
📊 Rate Limits: 2800 req/min, 280000 tokens/min
✅ Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 5: Test It Works (2 minutes)

**Option A: Open browser**
1. Go to http://localhost:8000/health
2. Should see: `{"status":"healthy",...}`

**Option B: Run automated tests**
```bash
# Open NEW terminal
cd "C:\git\project\CONTENT MARKETING\30 Day Content Jumpstart\project\backend"
..\..\venv\Scripts\activate

# Run tests
python test_api_endpoints.py
```

**Expected output:**
```
✅ Health check passed
✅ User registration successful
✅ Login successful
... (15 more tests)
✅ All API tests passed successfully!
```

**Option C: Try interactive API docs**
1. Go to http://localhost:8000/docs
2. Click "Authorize" button
3. Register a user: `POST /api/auth/register`
4. Copy `access_token` from response
5. Click "Authorize" again, paste: `Bearer <token>`
6. Try any protected endpoint!

## 📚 What You Just Built

**24 API Endpoints:**
- `/api/auth/*` - Authentication (register, login, refresh)
- `/api/clients/*` - Client management
- `/api/projects/*` - Project CRUD
- `/api/briefs/*` - Brief upload/paste
- `/api/posts/*` - Post listing
- `/api/deliverables/*` - Deliverable management

**Features:**
- ✅ JWT authentication with 30-min expiry
- ✅ Rate limiting at 70% of API limits
- ✅ File upload for briefs (.txt, .md)
- ✅ SQLite database with 7 tables
- ✅ Interactive API documentation

## 🔥 Common Commands

**Start backend:**
```bash
python main.py
```

**Run tests:**
```bash
python test_api_endpoints.py
```

**View API docs:**
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

**Check health:**
```bash
curl http://localhost:8000/health
```

**Register user:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"SecurePass123!\",\"full_name\":\"Test User\"}"
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"SecurePass123!\"}"
```

## 🐛 Troubleshooting

**Error: "ModuleNotFoundError: No module named 'fastapi'"**
- Fix: `pip install -r requirements.txt`

**Error: "SECRET_KEY is required"**
- Fix: Run `python generate_secret_key.py` and add to .env

**Error: "Address already in use"**
- Fix: Port 8000 is occupied. Change `API_PORT=8001` in .env

**Error: "401 Unauthorized"**
- Fix: Login again, token expired (30 min expiry)

**Tests fail: "Connection refused"**
- Fix: Make sure backend is running: `python main.py`

## 📖 Next Steps

1. **Read full documentation:** `BACKEND_SETUP.md`
2. **Phase 2 completion summary:** `PHASE_2_COMPLETION.md`
3. **Integrate with frontend:** See `operator-dashboard/` directory
4. **Phase 3:** Agent-powered endpoints with SSE

## 🎯 Quick Test Flow

```bash
# Terminal 1: Start backend
python main.py

# Terminal 2: Run tests
python test_api_endpoints.py

# Terminal 3: Try manual request
curl http://localhost:8000/health

# Browser: Interactive docs
http://localhost:8000/docs
```

## ✨ You're All Set!

The backend is now running with all Direct API endpoints ready for:
- Frontend integration (React Operator Dashboard)
- Agent-powered content generation (Phase 3)
- Production deployment (with PostgreSQL, Redis, etc.)

**Questions?** See `BACKEND_SETUP.md` for detailed documentation.
