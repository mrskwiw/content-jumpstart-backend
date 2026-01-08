# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **agent implementation** for the 30-Day Content Jumpstart system - an AI-powered content generator that creates 30 professional social media posts from client briefs using Claude 3.5 Sonnet. This directory contains the working Python codebase, while business templates and documentation are in the parent directory.

**Key Constraint:** All paths to business templates (01_CLIENT_BRIEF_TEMPLATE.md, 02_POST_TEMPLATE_LIBRARY.md) are relative to parent directory (`../`). These files must never be moved into this directory.

**New:** Strategic service packaging and pricing reference lives in `../STRATEGY_SERVICE.md`.

## Development Workflow

**IMPORTANT: Repository Structure and Usage**

- **This is the only development machine** - All development work happens on this local machine
- **Remote repository is deployment-only** - The remote repo exists solely for deployment to production servers
- **Exclude non-application files** - Only files required to run the application should be committed to the remote repository

**What to exclude from remote repo:**
- Documentation files (*.md except README.md)
- Test results and reports
- Development notes and planning documents
- Analysis files and completion reports
- Local configuration and IDE files
- Generated output files (data/outputs/*)
- Development artifacts not needed in production

**What to include in remote repo:**
- Source code (src/, backend/, operator-dashboard/src/)
- Configuration files (.env.example, requirements.txt, pyproject.toml, package.json)
- Docker configuration (Dockerfile, docker-compose.yml)
- Tests (tests/)
- Essential documentation (README.md only)
- Template files needed by the application

**Use .gitignore to enforce this separation.** Development documentation should remain local or in a separate docs repository.

## Development Commands

**IMPORTANT: Special Characters and Path Separators in Bash**

When running commands with file paths or strings containing spaces, parentheses, or special characters, use double quotes to escape them properly.

**Windows Path Separators:**
On Windows, use backslashes (`\\`) in paths, NOT forward slashes (`/`). Forward slashes will cause "file not found" errors.

```bash
# ✅ Correct - Windows paths with backslashes and quotes
cd "C:\\git\\project\\CONTENT MARKETING\\30 Day Content Jumpstart\\Project"
python "C:\\git\\project\\script.py"

# ❌ Incorrect - forward slashes (Unix-style)
cd "C:/git/project/CONTENT MARKETING/30 Day Content Jumpstart/Project"

# ❌ Incorrect - no quotes with spaces
cd C:\\git\\project\\CONTENT MARKETING\\30 Day Content Jumpstart\\Project

# ✅ Correct - special characters in strings quoted
git commit -m "Fixed bug #7 (import error)"

# ❌ Incorrect - parentheses will be interpreted
git commit -m Fixed bug #7 (import error)
```

**Note:** Git Bash on Windows accepts both `/` and `\\`, but most Windows programs require `\\` for file paths.

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### Running the System

**RECOMMENDED: Coordinator Interface**
```bash
# Run with existing brief
python run_jumpstart.py tests/fixtures/sample_brief.txt

# Interactive brief builder
python run_jumpstart.py --interactive

# With voice samples for tone analysis
python run_jumpstart.py brief.txt --voice-samples sample1.txt sample2.txt

# Generate with specific template quantities (NEW - recommended)
python run_jumpstart.py brief.txt --template-quantities '{"1": 3, "2": 5, "9": 2}'

# Platform-specific generation
python run_jumpstart.py brief.txt --platform twitter --num-posts 20

# Set posting schedule start date
python run_jumpstart.py brief.txt --start-date 2025-12-01
```

**Template Quantities System (NEW):**
The system now supports flexible per-template quantity selection:
- Use `--template-quantities` with JSON dict: `'{"1": 3, "2": 5, "9": 2}'`
- Template IDs are numeric strings (1-15 for standard templates)
- Quantities are integers (0-100 per template)
- Total posts auto-calculated from quantities
- Pricing: Flat $40/post (all templates same price)
- See `python run_jumpstart.py --help` for examples

**LEGACY: Direct CLI** - `python 03_post_generator.py generate brief.txt -c "ClientName"` with optional flags: `--platform`, `--templates`, `-n`, `--no-randomize`. See `python 03_post_generator.py --help` for full options.

### Testing
`pytest` (all tests), `pytest tests/unit/` (unit only), `pytest --cov=src --cov-report=html` (with coverage).

### Code Quality
```bash
# Format all code (required before commits)
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/

# Run all quality checks
black src/ tests/ && ruff check src/ tests/ && mypy src/
```

### Bug Tracking

**IMPORTANT:** When you encounter a bug that is not immediately resolved:

1. **Document it in BUGS.md** - Add the bug to `BUGS.md` in the project root
2. **Include key details:**
   - Description of the bug
   - Steps to reproduce
   - Expected vs. actual behavior
   - Affected component/file
   - Potential causes
   - Workarounds (if any)
3. **Track status** - Mark bugs as "Open" or "Resolved"
4. **Reference in commits** - When fixing a bug, reference it in the commit message

**Example:**
```markdown
### 1. Wizard fails to create project after creating client

**Status:** Open
**Severity:** High
**Component:** Wizard (operator-dashboard)
**Location:** `operator-dashboard/src/pages/Wizard.tsx`

**Description:**
Client is created successfully but project creation fails with "Failed to create project" error.
```

See `BUGS.md` for the bug tracking template and active bugs list.

### UI/UX Revisions Tracking

**Location:** `../docs/todo.md` (parent directory)

This file tracks operator dashboard UI/UX improvements and bug fixes organized by page:
- Wizard page improvements
- Review Content page fixes
- Projects page enhancements
- Settings page issues
- Global/cross-page issues (theme, client ID display, etc.)

**When completing a revision:**
1. Mark the item as ✅ **COMPLETE** with completion date
2. Add brief description of the fix
3. Reference the commit or PR if applicable

**Example:**
```markdown
## Review content
- ✅ **COMPLETE** - Fixed QA status filter (December 22, 2025)
```

See `../docs/todo.md` for the current revision list.

### Backend API (FastAPI)

**Dev:** `uvicorn backend.main:app --reload --port 8000` (docs at http://localhost:8000/docs)
**Production:** `docker-compose up -d api` (serves frontend + backend at http://localhost:8000)

### Operator Dashboard (React)

**Dev:** `cd operator-dashboard && npm install && npm run dev` (http://localhost:5173)
**Production:** Dashboard built during Docker build, served by FastAPI. See Docker deployment section.

### Interactive Agent
`python agent_cli_enhanced.py chat` (start/resume). Other commands: `sessions`, `pending`, `export`, `search`. See AGENT_USER_GUIDE.md.

### Docker Deployment (Single-Service)

`docker-compose up -d api` - Runs single container with frontend + backend. Access at http://localhost:8000 (frontend), /api/* (API), /docs (Swagger).

**Architecture:** Multi-stage build (Node.js → React build → Python + FastAPI serves everything). Login: mrskwiw@gmail.com / Random!1Pass. See SINGLE_SERVICE_DEPLOYMENT.md.

## Architecture Overview

### Agent Pipeline

The system uses a **6-agent pipeline** for content generation:

```
BriefParserAgent → ClientClassifier → TemplateLoader → ContentGeneratorAgent → QAAgent → OutputFormatter
```

**Critical Flow:**
1. **BriefParserAgent** extracts structured JSON from free-form text via Claude API
2. **ClientClassifier** categorizes client (B2B SaaS, Agency, Coach, Creator) using keyword scoring
3. **TemplateLoader** selects 15 templates from the parent directory's 02_POST_TEMPLATE_LIBRARY.md
4. **ContentGeneratorAgent** generates posts in **async parallel** (5 concurrent API calls, ~60s for 30 posts)
5. **QAAgent** validates posts across 5 dimensions (hooks, CTAs, length, headlines, keywords)
6. **OutputFormatter** packages deliverables (posts, brand voice guide, QA report, keyword strategy)

### Async Architecture

**Default mode is ASYNC** (`settings.PARALLEL_GENERATION = True`):
- Uses `asyncio.gather()` for parallel execution
- `asyncio.Semaphore(5)` limits concurrent API calls to prevent rate limiting
- Speedup: **~4x faster** than synchronous (62s vs 240s for 30 posts)
- Configured in `src/config/settings.py`

**When to use sync:**
- Debugging individual posts
- Network issues causing async race conditions
- Set `PARALLEL_GENERATION=False` in .env

### Multi-Platform Content Generation

**Supported Platforms:** LinkedIn (200-300w), Twitter (12-18w), Facebook (10-15w), Blog (1500-2000w), Email (150-250w). Platform specs defined in `src/config/platform_specs.py`. Generator adjusts prompts, length, tone per platform. Validators use platform-specific rules.

### Cross-Platform Blog Linking

Generates blog posts (1500-2000w) + social teasers (Twitter/Facebook) with link placeholders `[BLOG_LINK_X]`. Post model includes `target_platform`, `related_blog_post_id`, `blog_link_placeholder`. See `generate_multi_platform_with_blog_links_async()` in content_generator.py.

### Enhanced Voice Analysis & Brand Frameworks

**Voice Metrics** (`src/utils/voice_metrics.py`): Flesch Reading Ease (0-100 readability), voice dimensions (formality/tone/perspective), sentence variety analysis.

**Brand Archetypes** (`src/config/brand_frameworks.py`): Expert, Friend, Innovator, Guide, Motivator. Inferred from client type or voice dimensions. Guides writing with action verbs, positive descriptors, outcome language.

**Integration:** VoiceAnalyzer adds metrics to EnhancedVoiceGuide. ContentGenerator injects archetype guidance into prompts. All fields optional for backward compatibility. Tests: 96% coverage, <5s for 30 posts.

### Anthropic API Wrapper

**Critical component:** `src/utils/anthropic_client.py`

All API calls go through `AnthropicClient` which provides:
- **Automatic retry logic** (3 attempts with exponential backoff)
- **Sync and async methods** (`create_message` vs `create_message_async`)
- **Token optimization** via `_format_context_optimized()` (excludes empty fields, limits list items to 5)
- **Error handling** for `RateLimitError`, `APIConnectionError`, `APIError`

**Never call Anthropic API directly** - always use `AnthropicClient` methods.

### Template Selection Logic

Keyword-based classification into client types (B2B_SAAS, AGENCY, COACH_CONSULTANT, CREATOR_FOUNDER, UNKNOWN). Min 15% confidence required. Each type has preferred/avoided templates. Manual override via `--templates` flag. See `src/config/template_rules.py`.

### Quality Validation System

5 validators (all sync, <1s total): **HookValidator** (80% similarity threshold), **CTAValidator** (40% variety min), **LengthValidator** (platform-aware specs), **HeadlineValidator** (min 3 engagement elements), **KeywordValidator** (optional). Quality score = avg of validators. Target: 85-90%.

### Data Models (Pydantic)

**ClientBrief**: Required fields (company_name, business_description, ideal_customer, main_problem_solved), unlimited customer_pain_points. **Post**: Auto-calc word_count/has_cta, quality flags, optional keywords. **Template**: Type/difficulty enums, structure with [BRACKETS]. **QAReport**: Aggregated validator results with overall_passed/quality_score.

### Configuration System

Environment config in `src/config/settings.py`: ANTHROPIC_API_KEY (required), ANTHROPIC_MODEL (default: claude-3-5-sonnet-latest), PARALLEL_GENERATION (True), MAX_CONCURRENT_API_CALLS (5). Quality thresholds: 75-350 words. Override via .env file.

### File Organization

**Source code:**
- `src/agents/` - AI agent implementations (6 agents)
- `src/models/` - Pydantic data models (5 models)
- `src/validators/` - Quality validators (5 validators)
- `src/utils/` - Utilities (anthropic_client, template_loader, output_formatter, logger)
- `src/config/` - Configuration (settings, template_rules)

**Runtime data (gitignored):**
- `data/briefs/` - Working client briefs during generation
- `data/outputs/{ClientName}/` - Generated deliverables with timestamps
- `data/projects/` - Completed client deliverables archive
- `logs/` - Application logs

**Tests:**
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - End-to-end workflow tests
- `tests/fixtures/sample_brief.txt` - Test client brief

## Important Implementation Details

**UTF-8 Encoding (Windows):** Lines 13-15 of 03_post_generator.py force UTF-8 (never remove - fixes Windows console errors).

**Template Paths:** Loaded from parent dir (`../02_POST_TEMPLATE_LIBRARY.md`). Update if structure changes.

**Prompt Caching:** System prompt cached once per run (~10K token savings).

**Temperature:** Brief parsing 0.3 (accuracy), post generation 0.7 (creativity). Never >0.3 for parsing.

**Error Recovery:** Failed posts create placeholders to maintain batch count.

**Classification:** Min 15% keyword confidence required, else UNKNOWN type with safe templates.

## Common Development Patterns

See git history or ask Claude for: adding validators, template types, client types. Use `pytest-asyncio` for async tests.

## Debugging Tips

**Logging:** Set `DEBUG_MODE=True` and `LOG_LEVEL=DEBUG` in .env. Check `logs/content_jumpstart.log` for API calls.

**Templates:** `python 03_post_generator.py list-templates` should show 15. If not, verify `../02_POST_TEMPLATE_LIBRARY.md` path.

**Output:** Check `data/outputs/{ClientName}/` for deliverable.md, brand_voice.md, qa_report.md, keyword_strategy.md.

**UI/UX Testing Best Practices:**
When testing or debugging multi-step UI flows (wizard, forms, navigation):
1. **Walk through ALL steps one at a time** - Don't skip ahead
2. **Take screenshots at each step** - Use Playwright's screenshot feature or browser devtools
3. **Examine each page load carefully** - Verify the page loaded correctly before proceeding
4. **Check for error messages** - Look for validation errors, network errors, console errors
5. **Verify state changes** - Confirm data persisted, mutations succeeded, navigation occurred
6. **Read error context snapshots** - Playwright generates `error-context.md` files with page structure
7. **Check backend logs** - Look for API errors, validation failures, database issues

**Common UI debugging patterns:**
- Form won't submit → Check validation schema, required fields, mutation errors
- Navigation fails silently → Check route configuration, authentication guards, error handling
- Data not persisting → Check mutation functions, API endpoints, backend validation
- Page shows wrong content → Check URL routing, component rendering conditions, data loading state

## Performance Considerations

**Token Usage:** ~500 (parsing) + 9K (generation) + 6K (output) = ~15.5K tokens/client. **Cost: $0.40-0.60/client**. Context filtering excludes empty fields, limits lists to 5 items. System prompt cached (~40% savings).

**Rate Limiting:** Semaphore limits to 5 concurrent requests. Reduce `MAX_CONCURRENT_API_CALLS` if hitting limits.

## Business Logic Constraints

**Revisions:** Max 5 per contract. Variant system marks revisions (variant+100), not for auto-correction (cost control).

**Templates:** Manually maintained in `../02_POST_TEMPLATE_LIBRARY.md`. TemplateLoader auto-detects changes. Add to TEMPLATE_PREFERENCES for new templates.

**Output:** Timestamp-based versioning prevents overwriting (`ClientName_TIMESTAMP_deliverable.md`).

## Related Documentation

**Parent directory documentation:**
- `../CLAUDE.md` - Repository guide (business context, workflow, pricing)
- `../README.md` - Business system overview
- `../IMPLEMENTATION_PLAN.md` - Phased development plan
- `../PHASE_1_DETAILED_PLAN.md` - Phase 1 specifications
- `../PHASE_2_COMPLETION.md` - Async generation implementation
- `../PHASE_2_PROGRESS_SUMMARY.md` - Multi-platform implementation progress
- `../PHASE_3_COMPLETION.md` - QA validation implementation
- `PHASE_5_COMPLETION.md` - TypeScript/React code quality improvements (Jan 2026)
- `PHASE_5_CODE_QUALITY_PLAN.md` - Phase 5 implementation plan
- `../CROSS_PLATFORM_BLOG_LINKING_COMPLETE.md` - Cross-platform feature documentation
- `../01_CLIENT_BRIEF_TEMPLATE.md` - Discovery form template
- `../02_POST_TEMPLATE_LIBRARY.md` - 15 post templates
- `../04_PROJECT_CHECKLIST.md` - Business workflow checklist

**Technical documentation:**
- `../SYSTEM_CAPABILITIES_REPORT.md` - Comprehensive system analysis
- `SECURITY.md` - Security guidelines and threat model
- `SECURITY_FIXES_2026-01-07.md` - Recent security improvements
- `docs/platform_length_specifications_2025.md` - Platform length research
- This directory's `README.md` - Quick start guide

## Key Architecture Principles

1. **Agent-based design** - Each major function is a separate agent (separation of concerns)
2. **Async-first** - Default to async for performance, fallback to sync for debugging
3. **Pydantic validation** - All data models validated at runtime
4. **Fail gracefully** - Generate placeholder posts on error to maintain batch integrity
5. **Token optimization** - Filter context, cache prompts, limit list items
6. **Type safety** - Full type hints with mypy checking
7. **Business template separation** - Templates live in parent directory, code never modifies them

## Known Issues & Limitations

**Deep-Link Routing (Dashboard):** Refreshing on deep routes returns 404. Catch-all route removed to fix API routing. Use navigation menu instead of browser refresh. Future fix: middleware-based SPA routing. See DASHBOARD_FIX_SUMMARY.md.

---

# Operator Dashboard (Internal Web UI)

React + TypeScript web UI in `operator-dashboard/` for internal operator workflow. **Tech:** Vite, Tailwind, shadcn/ui, React Query, Zustand.

**Features:** 5-step project wizard (profile → templates → generation → QA → export), automated quality flags, deliverable management with audit logging.

**Dev:** `cd operator-dashboard && npm install && npm run dev` (http://localhost:5173). **API:** Integrates via REST (`/api/generator/*`, `/api/qa/*`, `/api/projects/*`).

**Docs:** See OPERATOR_DASHBOARD.md, IMPLEMENTATION_PLAN.md.

---

# Internal CLI Agent System (Phase 9A)

Conversational agent for content workflows with workflow planning, proactive suggestions, error recovery, conversation history. **Version:** 2.0

**Usage:** `python agent_cli_enhanced.py chat` (start/resume). **Commands:** sessions, scheduled, pending, export, search, summary. **In-chat:** help, pending, scheduled, reset, new, exit.

## Agent Architecture

**Components:** core_enhanced.py (orchestrator), context.py (sessions), tools.py (16 tools), planner.py (workflows), suggestions.py (proactive), error_recovery.py (retry), scheduler.py (tasks), email_system.py (emails).

**Tools:** 14 core (generate_posts, list_projects, get_project_status, collect_feedback, process_revision, etc.) + 2 special (schedule_task, send_email).

**Flow:** User input → Claude analysis → function calling → tool execution → results → response. See tools.py and AGENT_USER_GUIDE.md.

## Intelligence Features

**Workflow Planning:** Multi-step operations (onboarding, batch ops) with dependencies. **Proactive Suggestions:** Auto-detects missing feedback, overdue invoices, pending deliverables. **Error Recovery:** Exponential backoff retry (0s → 1s → 2s → 4s). **Scheduling:** Future tasks with ONCE/DAILY/WEEKLY frequencies. **Email:** Template-based (deliverable, reminders, invoices).

## Polish Features

**Conversation History:** SQLite database (`data/agent_sessions.db`) with sessions/messages tables. Methods: save, load, export, search, summary.

**Rich Output:** Syntax highlighting (Monokai), tree visualization, enhanced progress bars, panel messages, color coding. See agent_cli_enhanced.py.

## Testing

`pytest tests/agent/` (40 tests: 24 Week 2 + 16 Week 3). `python test_tool_execution.py` verifies tool discovery.

## Database Schema

**sessions:** session_id, user_id, context_data (JSON), timestamps.
**conversation_messages:** message_id, session_id, role, content, timestamp, metadata (JSON). Indexed on session_id/timestamp.
**scheduled_tasks:** task_id, description, tool_name, tool_params (JSON), scheduled_for, frequency, status.

## Agent Configuration

**Env:** ANTHROPIC_API_KEY (required), model (claude-3-5-sonnet-20241022), PARALLEL_GENERATION (True), DEBUG_MODE (False).

**Settings:** Temperature 0.7, max_tokens 4096, RetryConfig (max 3, exponential backoff with jitter). See agent/core_enhanced.py.

## Debugging

**Logging:** Set DEBUG_MODE=True, check logs/content_jumpstart.log.

**Database:** Use sqlite3 to query agent_sessions.db (sessions, messages, tasks).

See AGENT_USER_GUIDE.md for patterns and examples.

## Agent Documentation

**Docs:** AGENT_USER_GUIDE.md (user guide), PHASE_9A_WEEK{1,2,3}_COMPLETION.md (implementation).

**Features:** Week 2 (planning, suggestions, error recovery, scheduling, email), Week 3 (history, rich output, tests). **Tests:** 40 total, 100% passing.
