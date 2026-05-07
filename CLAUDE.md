# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This directory

`project/` is the deployable application. Tests live at `../tests/`, docs at `../docs/`, task tracking at `../TODO.md`. Never put tests, docs, or planning files here.

## Commands

```bash
# Setup
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY

# Run
uvicorn backend.main:app --reload --port 8000   # API + Swagger at :8000/docs
python run_jumpstart.py --interactive            # CLI brief builder
python run_jumpstart.py brief.txt --template-quantities '{"1": 3, "2": 5}'
python agent_cli_enhanced.py chat               # interactive agent

# Tests — must run from project/ targeting ../tests/
pytest ../tests                             # all 4,743 tests
pytest ../tests/unit/                       # unit only
pytest ../tests/integration/               # integration only
pytest ../tests/unit/path/to/test_foo.py -v
pytest --cov=src --cov=backend --cov-report=html --cov-report=term

# Quality (run before every commit)
black src/ backend/
ruff check src/ backend/
mypy src/

# Frontend
cd operator-dashboard
npm run dev           # http://localhost:5173
npm run build         # production build (FastAPI serves from dist/)
npm run lint:fix
npm run typecheck     # tsc --noEmit
npx jest              # unit tests
npx playwright test   # e2e tests
```

**`pyproject.toml` says `testpaths = ["tests"]` — this is wrong.** Always use `../tests/` from this directory. `conftest.py` adds `project/` to `sys.path` automatically.

**Windows UTF-8:** `src/agents/03_post_generator.py` lines 13–15 force UTF-8 output. Never remove them.

## Architecture

### Agent pipeline (src/)

```
BriefParserAgent → ClientClassifier → TemplateLoader → ContentGeneratorAgent → QAAgent → OutputFormatter
```

Entry point: `src/agents/coordinator.py` → `CoordinatorAgent.run_complete_workflow()`.

- **ContentGeneratorAgent** (`src/agents/content_generator.py`): asyncio semaphore limits 5 concurrent Anthropic calls; ~60s for 30 posts. Reduce `MAX_CONCURRENT_API_CALLS` if rate-limited.
- **QAAgent** runs 5 validators: hook similarity (MinHash/LSH dedup), CTA presence, platform length, SEO, headline quality.
- **ClientClassifier** emits one of: `B2B_SAAS | AGENCY | COACH | CREATOR`. Template selection depends on this.
- **Error recovery**: 3 retries with exponential backoff; failed posts become placeholder entries to keep the batch count intact.

Token budget: ~15.5K tokens/client (~$0.40–0.60). `research_context_builder.py` injects research findings and limits injected lists to 5 items to stay within budget.

Temperature: 0.3 for parsing agents, 0.7 for generation.

### FastAPI backend (backend/)

27 routers, ~200 endpoints. Middleware stack in `backend/main.py` (order matters):

```
RequestIDMiddleware → MetricsMiddleware → CSRFProtectionMiddleware
→ security_headers → gzip_compression → rate_limiters (slowapi, 3 tiers)
```

SPA fallback in `backend/main.py` catches unmatched routes and serves `operator-dashboard/dist/index.html` — deep-link routing only works with a production build or the Vite dev server.

Key services:
- `backend/services/generator_service.py` — orchestrates agents from the API layer
- `backend/services/export_service.py` — DOCX/PDF/TXT deliverable assembly
- `backend/services/research_context_builder.py` — injects research JSON into generation prompts
- `backend/services/crud.py` — shared SQLAlchemy CRUD layer

### Research tools (src/research/ + backend/services/research_prerequisites.py)

12 tools, $300–$600 per run. All extend `src/research/base.py:ResearchTool`.

**Dependency system:** each tool declares `ToolPrerequisite` entries typed `REQUIRED | RECOMMENDED | OPTIONAL`. `get_parallel_groups()` in `research_prerequisites.py` builds topological execution batches — currently **only REQUIRED edges** are wired into the sort. Running `competitive_analysis` in the same batch as `determine_competitors` causes HTTP 400 (active P0 — see `../TODO.md`).

Adding a new research tool touches 10 files in order:
1. `src/models/[tool]_models.py` — Pydantic output schema
2. `src/research/[tool].py` — extends `ResearchTool`, implements `validate_inputs` + `run_analysis`
3. `backend/schemas/research_schemas.py` — request schema
4. `backend/routers/research.py` — add to `RESEARCH_TOOLS` + `VALIDATION_SCHEMAS`
5. `backend/services/research_service.py` — add to `RESEARCH_TOOL_MAP`
6. `backend/services/research_prerequisites.py` — declare tier + prerequisites
7. `backend/services/export_service.py` — section formatter
8. `backend/services/research_context_builder.py` — prompt injection
9. `operator-dashboard/src/components/wizard/ResearchPanel.tsx` — tool card + TOOL_PREREQUISITES mirror
10. `operator-dashboard/src/components/wizard/ResearchDataCollectionPanel.tsx` — input form fields
    + tests: `../tests/research/` + `../tests/integration/`

### Frontend (operator-dashboard/src/)

Stack: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + React Query 5 + Zustand 5.

- Data fetching: `useQuery` / `useMutation` (React Query)
- Global state: `useAuthStore`, `useProjectStore` (Zustand)
- **Null safety:** always `(value?.prop ?? fallback).toFixed(n)` — missing optional chaining is the #1 runtime error source
- Dark mode: `className="bg-white dark:bg-neutral-900"`
- API clients: `src/api/` — one module per domain, all use shared Axios instance with auth interceptor
- Types: `src/types/domain.ts` is the canonical TypeScript model source

Adding a new endpoint: schema → router → service → `src/api/[domain].ts` → `domain.ts` types → integration test.

### Interactive agent (agent/)

58 tools in `agent/tools.py`. Entry: `python agent_cli_enhanced.py chat`.
SQLite session store at `data/agent_sessions.db`. In-chat commands: `help`, `pending`, `scheduled`, `reset`, `new`, `exit`.

## Configuration

```
ANTHROPIC_API_KEY          required
ANTHROPIC_MODEL            default: claude-3-5-sonnet-latest
MAX_CONCURRENT_API_CALLS   default: 5
PARALLEL_GENERATION        True
DEBUG_MODE / LOG_LEVEL
DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD   optional — Google Trends fallback
```

## Import conventions

- Backend: absolute — `from backend.models import User`
- Research/src: relative — `from ..utils.anthropic_client import get_default_client`

## Known pitfalls

- **Test path**: `pyproject.toml` is wrong — use `pytest ../tests/` always
- **Template path**: `.env` must have `TEMPLATE_LIBRARY_PATH=02_POST_TEMPLATE_LIBRARY.md` (not `../02_...`)
- **Deep-link 404**: only works with a production build (`npm run build`) or Vite dev server
- **Research race condition**: `competitive_analysis` must run after `determine_competitors` — see P0 in `../TODO.md`
- **Google Trends rate limit**: 30 req/hour; circuit-breaker stops after 3 consecutive failures; DataForSEO fallback configured via `DATAFORSEO_LOGIN`

## Coverage gaps (as of 2026-03-19)

Lowest coverage files: `export_service.py` 75%, `market_trends_research.py` 70%, `seo_keyword_research.py` 75%, `content_generator.py` 85%. Full gap analysis: `../docs/TESTING_GAP_ANALYSIS.md`.
