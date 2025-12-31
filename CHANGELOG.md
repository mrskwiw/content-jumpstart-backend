# Changelog

All notable changes to the Content Jumpstart project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- E2E tests with Playwright for critical user workflows
- Security scanning CI/CD pipeline (Bandit, Safety, CodeQL, TruffleHog)
- Comprehensive deployment runbook with rollback procedures
- Performance baselines document for regression detection
- API versioning system with changelog tracking
- Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
- Environment-aware CORS configuration (strict in production)

### Changed
- Pinned all dependency versions for production stability
- Reduced API key logging from 7 to 4 characters for security
- Hardened CORS configuration with explicit allow-lists in production
- Fixed undefined variables in coordinator.py auto_fix path

### Security
- Added comprehensive security headers to all API responses
- Implemented environment-aware CORS (permissive dev, restrictive prod)
- Reduced API key exposure in logs
- Added automated security scanning to CI/CD

---

## [1.0.0] - 2025-01-15

### Added
- **Core Features**
  - Complete content generation workflow (brief → 30 posts → QA → deliverables)
  - 14 specialized AI agents for content operations
  - Multi-platform support (LinkedIn, Twitter, Facebook, Blog, Email)
  - Async parallel generation (5 concurrent API calls, 4x speedup)
  - 6 quality validators (hooks, CTAs, length, headlines, keywords, security)
  - Enhanced voice analysis with brand archetypes
  - Template quantity system with per-template pricing

- **Operator Dashboard**
  - React + TypeScript web UI for internal operators
  - 5-step project wizard (client → brief → templates → generate → review)
  - Quality assurance workflow with flag management
  - Deliverable export (TXT, JSON, DOCX, CSV, iCal)
  - Real-time progress updates via SSE

- **Backend API**
  - FastAPI REST API with 11 router groups
  - JWT authentication with access + refresh tokens
  - Rate limiting at 70% of Anthropic API limits
  - SQLAlchemy ORM with PostgreSQL/SQLite support
  - Connection pooling for production (20 pool, 40 overflow)
  - Server-Sent Events for progress tracking

- **Research Modules**
  - 8 specialized research agents (audience, competitive, content gap, etc.)
  - SEO keyword research with difficulty scoring
  - Market trends analysis
  - Platform strategy recommendations

- **Interactive Agent**
  - Conversational CLI with workflow planning
  - Proactive suggestions and error recovery
  - Task scheduling (once, daily, weekly)
  - Email notification system
  - Conversation history with search

- **Testing & Quality**
  - 50+ test files with 12,304 lines of test code
  - Unit, integration, and research test coverage
  - pytest-asyncio for async test support
  - Pre-commit hooks (Black, Ruff, MyPy)

- **Documentation**
  - Comprehensive CLAUDE.md guides (root + project)
  - README files for each major component
  - Implementation plan with 9 phases
  - Phase completion documentation (Phases 1-9A)
  - Operator dashboard guide
  - Agent user guide

### Changed
- Migrated from sync to async content generation (Phase 2)
- Enhanced voice analysis with readability metrics (Phase 4)
- Improved template selection with client type classification
- Optimized prompt caching for token savings (~40% reduction)

### Fixed
- Windows UTF-8 encoding issues in console output
- Template path resolution for parent directory access
- Async semaphore limits to prevent rate limiting
- Connection pool configuration for production PostgreSQL

### Security
- Prompt injection defense system (OWASP LLM01 compliance)
- Input sanitization with 3-tier pattern detection
- Output validation for system prompt leakage detection
- JWT authentication with secure token handling
- Environment variable validation (API keys, secrets)

---

## Version History

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Release Schedule

- **Major releases:** Quarterly (Q1, Q2, Q3, Q4)
- **Minor releases:** Monthly (feature additions)
- **Patch releases:** As needed (bug fixes, security patches)

### Migration Guides

For breaking changes requiring migration:
- See `docs/migrations/v1-to-v2.md` (when v2.0.0 is released)

---

## API Version History

### v1 API (Current)

**Base URL:** `/api/v1/*` (aliased to `/api/*` for backwards compatibility)

**Endpoints:**
- `/api/auth/*` - Authentication
- `/api/clients/*` - Client management
- `/api/projects/*` - Project management
- `/api/briefs/*` - Brief handling
- `/api/posts/*` - Post CRUD
- `/api/runs/*` - Generation run tracking
- `/api/deliverables/*` - Deliverable management
- `/api/generator/*` - Content generation
- `/api/research/*` - Research modules
- `/api/pricing/*` - Pricing calculations
- `/api/health` - System health

**Breaking Changes from v0 (Beta):**
- N/A (first stable release)

**Deprecations:**
- None

**Sunset Date:**
- None (current stable version)

---

## Upgrade Guide

### From Beta to v1.0.0

No breaking changes. Beta installations can upgrade directly:

```bash
# 1. Backup database
pg_dump $DATABASE_URL > backup_pre_v1.sql

# 2. Pull latest code
git pull origin main

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
alembic upgrade head

# 5. Restart services
docker-compose restart
```

---

## Contributing

When adding entries to this changelog:

1. **Add to [Unreleased] section** for work-in-progress
2. **Categorize changes:**
   - `Added` - new features
   - `Changed` - changes to existing functionality
   - `Deprecated` - soon-to-be-removed features
   - `Removed` - removed features
   - `Fixed` - bug fixes
   - `Security` - security fixes
3. **Link to issues/PRs** when applicable: `(#123)`
4. **Be specific:** "Added JWT authentication" not "Improved auth"
5. **Use imperative mood:** "Add feature" not "Added feature"

Example:
```markdown
### Added
- JWT authentication with refresh tokens (#45)
- Rate limiting middleware at 70% of API limits (#47)

### Fixed
- Database connection pool exhaustion under load (#52)
```

---

## Support

- **Issues:** https://github.com/your-org/content-jumpstart/issues
- **Discussions:** https://github.com/your-org/content-jumpstart/discussions
- **Security:** security@your-org.com

---

**Document Control:**
- **Format:** Keep a Changelog 1.0.0
- **Versioning:** Semantic Versioning 2.0.0
- **Owner:** Engineering Team
- **Review Frequency:** Every release
