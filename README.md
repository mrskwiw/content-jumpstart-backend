# 30-Day Content Jumpstart - Implementation

AI-powered content generation system that creates 30 professional social media posts from client briefs using Claude 3.5 Sonnet.

## 📖 **Start Here: [CLAUDE.md](CLAUDE.md)**

For complete development documentation, commands, architecture details, and implementation guidance, see **[CLAUDE.md](CLAUDE.md)**.

This README provides a quick-start overview only.

## Quick Start

### Option 1: Docker Deployment (Recommended for Production)

**Complete system (backend + agents + database) in Docker:**

```bash
# 1. Create a .env file (env files are NOT committed — see CLAUDE.md § Environment
#    variables for the full annotated list of every key + defaults). Set at least:
#    - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
#    - SETTINGS_ENCRYPTION_KEY — REQUIRED here: docker-compose defaults DEBUG_MODE=false,
#      and the app refuses to boot without it. Generate:
#        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#    - POSTGRES_PASSWORD
#    - ANTHROPIC_API_KEY
#    - CORS_ORIGINS

# 3. Build and start
docker-compose build
docker-compose up -d

# 4. Verify deployment
curl http://localhost:8000/health
docker-compose logs -f api
```

**See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for complete Docker guide.**

### Option 2: Local Development

**Local Python setup for development:**

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
# Create a .env with your keys — env files aren't committed (see CLAUDE.md
# § Environment variables for the full list). At minimum set ANTHROPIC_API_KEY
# and SECRET_KEY; DATABASE_URL is optional locally (defaults to a SQLite file).

# Generate content (recommended)
python run_jumpstart.py tests/fixtures/sample_brief.txt

# Interactive agent
python agent_cli_enhanced.py chat

# Run tests
pytest

# Start backend API
uvicorn backend.main:app --reload --port 8000

# Start operator dashboard
cd operator-dashboard && npm run dev
```

## Project Structure

```
project/
├── CLAUDE.md                 # ⭐ COMPLETE TECHNICAL DOCUMENTATION
├── src/                      # Python source code
│   ├── agents/              # AI agent implementations
│   ├── models/              # Pydantic data models
│   ├── validators/          # Quality validators
│   ├── utils/               # Utilities
│   └── config/              # Configuration
├── backend/                 # FastAPI REST API
├── operator-dashboard/      # React operator UI
├── agent/                   # Interactive agent system
├── tests/                   # Test suite
└── data/                    # Runtime data (gitignored)
```

## Key Entry Points

- **`run_jumpstart.py`** - Main CLI (recommended)
- **`agent_cli_enhanced.py`** - Interactive conversational agent
- **`03_post_generator.py`** - Legacy CLI (still supported)

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete development guide ⭐
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker deployment guide 🐳
- **[OPERATOR_DASHBOARD.md](OPERATOR_DASHBOARD.md)** - Operator dashboard docs
- **[AGENT_USER_GUIDE.md](AGENT_USER_GUIDE.md)** - Interactive agent guide
- **[backend/PRODUCTION_DEPLOYMENT.md](backend/PRODUCTION_DEPLOYMENT.md)** - Production deployment options
- **[../CLAUDE.md](../CLAUDE.md)** - Repository navigation & business context
- **[../README.md](../README.md)** - Business system overview

## Critical Constraints

1. **Template paths** - All business templates are in parent directory (`../`)
2. **Async by default** - `PARALLEL_GENERATION=True` for 4x speedup
3. **UTF-8 encoding** - Windows encoding fix in `03_post_generator.py:13-15` must never be removed
4. **Temperature settings** - Never use >0.3 for parsing (causes JSON errors)

For detailed explanation of these constraints and all other implementation details, see **[CLAUDE.md](CLAUDE.md)**.
