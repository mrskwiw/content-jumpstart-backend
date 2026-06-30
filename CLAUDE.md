# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This directory

`project/` is the deployable application. Tests live at `../tests/`, docs at `../docs/`, task tracking at `../TODO.md`. Never put tests, docs, or planning files here.

## Deployment model — multi-instance (one database per customer)

Each customer runs as an isolated Render web service pointing at their own Supabase PostgreSQL project. Platform-level keys (Anthropic, Stripe) are shared across all instances via environment variables set at provisioning time.

**Database:** Supabase PostgreSQL (us-west-1). Connection string uses Transaction Pooler (port 6543, not 5432).
**No SQLite.** The app requires `DATABASE_URL=postgresql://...` — it will refuse to start with a SQLite URL.

### Provisioning a new customer

From the project root (`../`), not from inside `project/`:

```bash
python ../provision_customer.py
```

The script is fully interactive — no CLI arguments, no environment variables.

**First run:** a setup wizard collects platform-level API keys (Render, Supabase, Anthropic, Stripe) and saves them to `platform-config.json`. This file is gitignored and contains secrets — never commit it.

**Every subsequent run:** loads `platform-config.json` automatically, then prompts for customer-specific details:
- Customer name and slug
- Admin email
- App domain (CORS origin)
- Temp password and DB password (auto-generated, accept or override)
- Whether to skip Supabase creation (if a database already exists)

The script creates a Supabase project, applies `../scripts/schema.sql`, creates the Render service with all env vars, and appends a record to `../customers.json` (also gitignored).

**To re-run the platform setup wizard:** delete `platform-config.json` and run the script again.

### Render API — what's available

Full REST API at `https://api.render.com/v1`. Key endpoints used by the provisioning script:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/services` | POST | Create a service with all env vars in one call |
| `/services/{id}/env-vars` | PUT | Replace all env vars (⚠ deletes any not included) |
| `/services/{id}/env-vars/{key}` | PUT | Add/update a single var safely |
| `/services/{id}/deploys` | POST | Trigger deploy (env var changes don't auto-deploy) |

`SECRET_KEY` uses `"generateValue": true` — Render auto-generates a unique strong secret per service.

### Schema changes

When the schema changes, update `../scripts/schema.sql` and apply to existing customer databases via:
```bash
# Supabase dashboard → SQL editor, or:
psql $DATABASE_URL < ../scripts/schema.sql
```

New customer instances automatically get the current schema via `provision_customer.py`.

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
pytest ../tests                             # full suite (~6,180 test functions, ~83.6% coverage)
pytest backend/tests                        # backend-local tests (22 files)
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

**`pyproject.toml` sets `testpaths = ["../tests", "backend/tests"]`** — the main suite lives at `../tests/`, *outside* this git repo. Always run pytest from `project/`; `conftest.py` adds `project/` to `sys.path` automatically.

> **Decision (2026-06-30): Python tests run LOCALLY, not in CI.** The suite at `../tests/` is intentionally never pushed (it lives outside the `project/` git repo), so GitHub CI cannot run it. `quality-gates.yml` therefore runs only lint (`black`/`ruff` on `src backend`), the frontend build, and a backend import check — **no `pytest`**. Python tests are enforced before commit via pre-commit, Codex adversarial review, and the Stop hooks. **You are responsible for running `pytest ../tests` locally before pushing.** If the suite is later moved into the repo, re-add the `python-tests`/`test-coverage` jobs and make them blocking. Decision record + re-enablement steps: `../TODO.md` → OPS-02.

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

29 routers, ~200 endpoints. Middleware stack in `backend/main.py` (order matters):

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

~14 tools, $300–$600 per run. All extend `src/research/base.py:ResearchTool`.

**Dependency system:** each tool declares `ToolPrerequisite` entries typed `REQUIRED | RECOMMENDED | OPTIONAL`. `get_parallel_groups()` in `research_prerequisites.py` builds topological execution batches — currently **only REQUIRED edges** are wired into the sort. Running `competitive_analysis` in the same batch as `determine_competitors` causes HTTP 400. The original P0 batch-research bugs are fixed; tightening RECOMMENDED-edge ordering is a low-priority/optional item (`../TODO.md`).

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
- Types: `src/types/domain.ts` (Zod) is the **canonical** TypeScript model source. The generated `src/types/api-schema.ts` is reference only (openapi-typescript output)
- **API type parity:** the backend contract is `operator-dashboard/openapi.json`, generated from the FastAPI app via `npm run generate:openapi` (atomic + loud — `scripts/generate-openapi.mjs`; writes only on full success, never clobbers/masks on failure). `prebuild` runs two gates: `check:openapi-fresh` (regenerates and diffs vs the committed contract to catch a stale `openapi.json`; honestly SKIPs when the backend isn't importable, e.g. a frontend-only CI box) and `check:parity` (fails if `domain.ts` misses any field the backend serializes; hard-fails on a missing/empty/invalid contract). **After changing a backend response model: `npm run generate:api`, add new fields to `domain.ts`, and commit both.** Core models checked: Client/Project/Run (extend `CASES` in `scripts/check-api-parity.mjs`). Local jest mirror: `src/types/__tests__/api-parity.test.ts`. Note: where the backend can't be imported, freshness can't be verified — keeping the committed contract current is a commit-time responsibility

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

- **Test path**: run `pytest ../tests/` from `project/` — the suite is outside the repo (CI sees only `tests/unit/`, see OPS-02)
- **Template path**: `.env` must have `TEMPLATE_LIBRARY_PATH=02_POST_TEMPLATE_LIBRARY.md` (not `../02_...`)
- **Deep-link 404**: only works with a production build (`npm run build`) or Vite dev server
- **Research race condition**: `competitive_analysis` must run after `determine_competitors` (optional sequencing item in `../TODO.md`)
- **Google Trends rate limit**: 30 req/hour; circuit-breaker stops after 3 consecutive failures; DataForSEO fallback configured via `DATAFORSEO_LOGIN`

## Coverage gaps (overall ~83.6% as of coverage.json 2026-06-18)

Worst offenders are revenue/orchestration-critical, not the periphery:
`stripe_service.py` ~23%, `stripe_checkout.py` ~31%, `generator_service.py` ~24%, `research.py` (router) ~69%.
Several modules sit at 0% and may be dead scripts (`temp_db_query.py`, `benchmark_queries.py`, `apply_*_indexes.py`, `database_merger.py`) — see `../TODO.md` → TEST-01/OPS-03. Full analysis: `../docs/TESTING_GAP_ANALYSIS.md` (note: that doc's headline % is stale).
