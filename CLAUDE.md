# CLAUDE.md - Technical Implementation Guide

## Project Overview

Agent implementation for 30-Day Content Jumpstart - AI content generator using Claude 3.5 Sonnet. Business templates are in parent directory (`../templates/`).

## Development Workflow

**Repository Structure:**
- This is the development machine; remote repo is deployment-only
- Exclude: *.md (except README), docs, reports, analysis files, data/outputs/*
- Include: src/, backend/, operator-dashboard/src/, tests/, config files, Docker files

## Development Commands

**Windows paths:** Use backslashes (`\\`) and quotes for spaces. Example: `cd "C:\\path\\with spaces"`

### Setup
```bash
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
cp .env.example .env  # Set ANTHROPIC_API_KEY
```

### Running
```bash
# Recommended CLI
python run_jumpstart.py tests/fixtures/sample_brief.txt
python run_jumpstart.py --interactive  # Brief builder
python run_jumpstart.py brief.txt --template-quantities '{"1": 3, "2": 5, "9": 2}'

# Backend API
uvicorn backend.main:app --reload --port 8000  # http://localhost:8000/docs

# Dashboard
cd operator-dashboard && npm install && npm run dev  # http://localhost:5173

# Interactive Agent
python agent_cli_enhanced.py chat
```

### Testing & Quality
```bash
# IMPORTANT: Run tests FROM project/ directory, targeting ../tests/
cd project

pytest ../tests                  # All tests (4,743 tests, 95% coverage)
pytest ../tests/unit/            # Unit tests only
pytest ../tests/integration/     # Integration tests only
pytest ../tests -q               # Quick run without verbose output
pytest --cov=src --cov=backend --cov-report=html --cov-report=term  # With detailed coverage

# Quality checks
black src/ backend/ && ruff check src/ backend/ && mypy src/
```

**View coverage report:** Open `htmlcov/index.html` in browser after running coverage tests

### Docker Deployment
```bash
docker-compose up -d api  # Frontend + backend at http://localhost:8000
```

## Architecture

### Agent Pipeline
```
BriefParserAgent → ClientClassifier → TemplateLoader → ContentGeneratorAgent → QAAgent → OutputFormatter
```

**Key behaviors:**
- **Async parallel generation:** 5 concurrent API calls (~60s for 30 posts)
- **Quality validation:** 8 validators (hooks, CTAs, length, headlines, keywords, SEO, prompt injection, research inputs)
- **Target quality:** 85-90% pass rate on first generation
- **Template selection:** Automatic selection by client type (B2B_SAAS, AGENCY, COACH, CREATOR)
- **Error recovery:** Automatic retry (3 attempts with exponential backoff), placeholder posts on failure
- **Research integration:** Context builder injects research findings into generation prompts

### File Organization
```
src/agents/       # 14 AI agents
src/models/       # Pydantic models
src/validators/   # 5 QA validators
src/utils/        # Utilities (anthropic_client, logger)
src/config/       # Settings, template rules

backend/routers/  # API endpoints (/auth, /clients, /projects, /briefs, /generator, /posts)
backend/services/ # Business logic (generator, crud, export, research, trends)
backend/models/   # SQLAlchemy models

operator-dashboard/src/  # React + TypeScript UI

agent/            # Interactive agent (core_enhanced.py, tools.py - 58 tools)

# Parent directory (../)
../templates/     # Business templates (client brief, post library, checklists)
../docs/          # Documentation and archives
```

### API Routes
- `/api/auth/*` - JWT authentication (login, register, refresh tokens)
- `/api/clients/*` - Client management (CRUD, profile fields)
- `/api/projects/*` - Project management (CRUD, workflow states)
- `/api/briefs/*` - Brief upload/parse (AI extraction with confidence scores)
- `/api/generator/*` - Content generation (batch generation, template selection)
- `/api/posts/*` - Post management (CRUD, QA validation, regeneration)
- `/api/deliverables/*` - Export management (DOCX/PDF/TXT, delivery tracking)
- `/api/research/*` - Research tools (12 tools, $300-$600 each, dependency validation)
- `/api/trends/*` - Google Trends integration (30/hour rate limit)
- `/api/costs/*` - Cost tracking and analytics
- `/api/settings/*` - User settings (API keys, web search providers)
- `/api/admin/users/*` - Admin panel (user management)

## Configuration

**Environment (`.env`):**
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL` (default: claude-3-5-sonnet-latest)
- `PARALLEL_GENERATION` (True)
- `MAX_CONCURRENT_API_CALLS` (5)
- `DEBUG_MODE`, `LOG_LEVEL`

**Temperature:** 0.3 for parsing, 0.7 for generation.

## Implementation Details

**Token Optimization:** ~15.5K tokens/client ($0.40-0.60). Context filtering excludes empty fields, limits lists to 5 items, caches system prompt.

**Rate Limiting:** Semaphore limits 5 concurrent requests. Reduce `MAX_CONCURRENT_API_CALLS` if hitting limits.

**UTF-8 (Windows):** Lines 13-15 of 03_post_generator.py force UTF-8 - never remove.

**Template Paths:** Loaded from `../templates/02_POST_TEMPLATE_LIBRARY.md`.

**Error Recovery:** Failed posts create placeholders to maintain batch count.

**Research Tools Integration:**
- 12 tools available: Voice Analysis, Brand Archetype, SEO Keywords, Competitive Analysis, Content Gap, Market Trends, Content Audit, Platform Strategy, Content Calendar, Audience Research, ICP Workshop, Story Mining
- Tools follow base class pattern in `src/research/base.py`
- Results stored in `backend/models/research_result.py` with JSON metadata
- Prerequisites enforced via `backend/services/research_prerequisites.py`
- Context injection via `backend/services/research_context_builder.py` (builds prompts for generation)
- Export formatting in `backend/services/export_service.py`

**Test Path Warning:**
- Tests are in `../tests/` (parent directory), NOT `project/tests/`
- `pyproject.toml` shows `testpaths = ["tests"]` but this is INCORRECT
- ALWAYS run `pytest ../tests` from `project/` directory
- conftest.py handles path setup automatically

## Common Pitfalls

**1. Test Path Confusion**
- ❌ WRONG: `pytest tests/` (won't work - tests aren't in project/tests/)
- ✅ CORRECT: `pytest ../tests/` (from project/ directory)

**2. Missing API Key**
- Error: "ANTHROPIC_API_KEY not found"
- Fix: Copy `.env.example` to `.env` and add your API key

**3. Import Errors**
- Backend imports use absolute paths: `from backend.models import User`
- Research tools use relative: `from ..utils.anthropic_client import get_default_client`

**4. Null Safety in Frontend**
- Pattern: `(value?.property ?? 0).toFixed(2)` (use optional chaining + nullish coalescing)
- Common error: `Cannot read properties of undefined (reading 'toFixed')`

**5. Research Tool Prerequisites**
- Some tools REQUIRE others (e.g., Content Calendar needs SEO + Platform Strategy)
- Check `backend/services/research_prerequisites.py` for dependency tree

## Debugging

```bash
# Enable debug logging
DEBUG_MODE=True LOG_LEVEL=DEBUG

# Check logs
logs/content_jumpstart.log

# Verify templates (loads from ../templates/02_POST_TEMPLATE_LIBRARY.md)
python 03_post_generator.py list-templates  # Should show 15

# Check outputs
data/outputs/{ClientName}/  # deliverable.md, brand_voice.md, qa_report.md

# Test single file
pytest ../tests/unit/test_specific.py -v

# Frontend build issues
cd operator-dashboard && npm run build && npm run preview
```

**UI debugging:** Walk through all steps, take screenshots, check console errors, verify state changes, read error-context.md files.

## Bug Tracking

Document unresolved bugs in `BUGS.md` with: description, steps to reproduce, expected vs actual, component, severity, status.

UI/UX revisions tracked in `../docs/todo.md`.

## Key Patterns

- **Agent-based design:** Each function is a separate agent
- **Async-first:** Default async, sync for debugging
- **Pydantic validation:** All data models validated
- **Fail gracefully:** Placeholder posts on error
- **Business template separation:** Templates in `../templates/`, never modify

## Known Issues

**Deep-Link Routing:** ~~Dashboard refresh on deep routes returns 404.~~ **FIXED** - SPA routing middleware in backend/main.py now handles deep-links correctly. Works when:
- Running production build from FastAPI (serves operator-dashboard/dist)
- Running Vite dev server (automatic SPA fallback)

If issues persist, ensure the frontend is built (`cd operator-dashboard && npm run build`).

## Recent Fixes (February 2, 2026)

**Template Path Issue:** ~~24 coordinator tests failing with FileNotFoundError.~~ **FIXED**
- Root cause: `.env` file had `TEMPLATE_LIBRARY_PATH=../02_POST_TEMPLATE_LIBRARY.md`
- Solution: Updated to `TEMPLATE_LIBRARY_PATH=02_POST_TEMPLATE_LIBRARY.md`
- Template file exists at `Project/02_POST_TEMPLATE_LIBRARY.md`
- All 25 coordinator tests now pass ✅

**Test Organization:** Agent tests moved to correct locations
- Moved 4 tests from `tests/unit/` to `tests/unit/agents/`
- Improved test directory consistency

**Integration Test Coverage:** Added 67 new router integration tests
- `test_router_research.py` - 20 tests (P0 priority, $300-600 features)
- `test_router_trends.py` - 29 tests (Google Trends integration)
- `test_router_assistant.py` - 18 tests (AI assistant chat)

**Test Suite Status:** 4,743 passing tests, **95% coverage achieved** ✅ (target: 90%)

## Operator Dashboard

React + TypeScript + Vite + Tailwind + shadcn/ui + React Query + Zustand

```bash
cd operator-dashboard
npm run dev        # Development
npm run build      # Production
npm run lint:fix   # ESLint
npm run typecheck  # TypeScript
```

## Interactive Agent

58 tools: content generation, project/client management, research, Google Trends, backend API wrappers.

**Commands:** `chat`, `sessions`, `pending`, `export`, `search`, `summary`
**In-chat:** `help`, `pending`, `scheduled`, `reset`, `new`, `exit`

**Database:** SQLite `data/agent_sessions.db` (sessions, messages, scheduled_tasks)
