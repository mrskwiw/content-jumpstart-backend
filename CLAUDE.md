# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **agent implementation** for the 30-Day Content Jumpstart system - an AI-powered content generator that creates 30 professional social media posts from client briefs using Claude 3.5 Sonnet. This directory contains the working Python codebase, while business templates and documentation are in the parent directory.

**Key Constraint:** All paths to business templates (01_CLIENT_BRIEF_TEMPLATE.md, 02_POST_TEMPLATE_LIBRARY.md) are relative to parent directory (`../`). These files must never be moved into this directory.

**New:** Strategic service packaging and pricing reference lives in `../STRATEGY_SERVICE.md`.

## Development Commands

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

# Platform-specific generation
python run_jumpstart.py brief.txt --platform twitter --num-posts 20

# Set posting schedule start date
python run_jumpstart.py brief.txt --start-date 2025-12-01
```

**LEGACY: Direct CLI**
```bash
# Basic generation (30 LinkedIn posts - default)
python 03_post_generator.py generate tests/fixtures/sample_brief.txt -c "ClientName"

# Platform-specific generation
python 03_post_generator.py generate brief.txt -c "ClientName" --platform twitter
python 03_post_generator.py generate brief.txt -c "ClientName" --platform facebook
python 03_post_generator.py generate brief.txt -c "ClientName" --platform blog

# Multi-platform blog linking (generates blogs + social teasers)
python 03_post_generator.py generate-multi-platform brief.txt -c "ClientName" -b 5
# Output: 5 blog posts + 5 Twitter teasers + 5 Facebook teasers (15 total)

# Custom post count
python 03_post_generator.py generate brief.txt -c "ClientName" -n 10

# Manual template selection (override intelligent selection)
python 03_post_generator.py generate brief.txt -c "ClientName" --templates "1,3,5,7,9"

# Disable post randomization
python 03_post_generator.py generate brief.txt -c "ClientName" --no-randomize

# Parse brief only (no generation)
python 03_post_generator.py parse-brief tests/fixtures/sample_brief.txt

# List all available templates
python 03_post_generator.py list-templates
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_brief_parser.py

# Run specific test
pytest tests/unit/test_brief_parser.py::test_parse_brief

# Run with coverage report
pytest --cov=src --cov-report=html

# Run integration tests only
pytest tests/integration/

# Run async tests
pytest tests/integration/test_async_generation.py -v
```

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

### Backend API (FastAPI)

**Development (Standalone):**
```bash
# Start API server only (for backend-only development)
uvicorn backend.main:app --reload --port 8000

# With specific host
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Check API docs
# Navigate to http://localhost:8000/docs (Swagger UI)
```

**Production (Docker - Recommended):**
```bash
# Run full stack (frontend + backend in one container)
docker-compose up -d api

# Access at http://localhost:8000
# - Frontend: http://localhost:8000
# - API: http://localhost:8000/api/*
# - Docs: http://localhost:8000/docs
```

**Note:** In production, FastAPI serves both API and frontend static files. See [Docker Deployment](#docker-deployment-single-service) section above.

### Operator Dashboard (React)

**Development (Standalone):**
```bash
# Navigate to dashboard directory
cd operator-dashboard

# Install dependencies
npm install

# Start dev server (separate from backend)
npm run dev
# Available at http://localhost:5173

# Run tests
npm run test
```

**Production (Docker - Recommended):**
```bash
# Build is automated in Dockerfile (multi-stage build)
# Dashboard served by FastAPI at http://localhost:8000
docker-compose up -d api
```

**Build for Production:**
```bash
cd operator-dashboard
npm run build
# Output: dist/ directory (served by FastAPI in production)

# Preview production build locally
npm run preview
```

**Note:** In production, the dashboard is built during Docker image creation (Node.js build stage) and served by FastAPI from `/operator-dashboard/dist`. See [Docker Deployment](#docker-deployment-single-service) section above.

### Interactive Agent
```bash
# Start conversational agent
python agent_cli_enhanced.py chat

# Resume previous session
python agent_cli_enhanced.py chat --session <session_id>

# List recent sessions
python agent_cli_enhanced.py sessions

# Show pending tasks
python agent_cli_enhanced.py pending

# Export conversation to markdown
python agent_cli_enhanced.py export -s <session_id>

# Search conversation history
python agent_cli_enhanced.py search -s <session_id> "query"

# See AGENT_USER_GUIDE.md for complete documentation
```

### Docker Deployment (Single-Service)

**PRODUCTION: Single Container with Frontend + Backend**

```bash
# Build and start
docker-compose up -d api

# View logs
docker logs content-jumpstart-api -f

# Rebuild after changes
docker-compose build api && docker-compose up -d api

# Access application
# Frontend: http://localhost:8000
# API: http://localhost:8000/api/*
# Docs: http://localhost:8000/docs
```

**Architecture:**
- One Docker container runs both frontend (React) and backend (FastAPI)
- FastAPI serves frontend static files from `/operator-dashboard/dist`
- Eliminates CORS issues (same origin)
- Port 8000 exposed for all traffic

**Files:**
- `Dockerfile` - Multi-stage build (Node.js for frontend + Python for backend)
- `docker-compose.yml` - Service configuration
- See `QUICK_START.md` for quick reference
- See `SINGLE_SERVICE_DEPLOYMENT.md` for complete guide

**Development vs Production:**
```yaml
# Development: Volume mount for hot-reload
volumes:
  - .:/app

# Production: Comment out volume mount
# volumes:
#   - .:/app
```

**Login Credentials:**
```
Email: mrskwiw@gmail.com
Password: Random!1Pass

See LOGIN_CREDENTIALS.md for user management
```

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

**NEW FEATURE (Nov 2025):** The system now supports generating content for multiple platforms with platform-specific optimization.

**Supported Platforms:**
- **LinkedIn** (default): 200-300 words, professional tone, first 140 chars critical
- **Twitter**: 12-18 words, ultra-concise, max 280 chars
- **Facebook**: 10-15 words, ultra-short captions for visuals
- **Blog**: 1,500-2,000 words, SEO-optimized long-form
- **Email**: 150-250 words, personal and valuable

**Platform Specifications** (`src/config/platform_specs.py`):
- Each platform has min/max/optimal word and character counts
- Platform-specific writing guidelines injected into prompts
- Hook requirements vary by platform (e.g., LinkedIn's 140-char mobile cutoff)

**Platform-Aware Generation:**
```python
# Generator automatically adjusts:
# 1. System prompt with platform-specific guidance
# 2. Target length in prompt
# 3. Tone and structure requirements
# 4. Post.target_platform field for validation

posts = await generator.generate_posts_async(
    client_brief=brief,
    num_posts=30,
    platform=Platform.TWITTER  # Generates 12-18 word tweets
)
```

**Platform-Aware Validation:**
- `LengthValidator` detects platform from `Post.target_platform`
- Uses platform-specific specs instead of hard-coded LinkedIn rules
- Error messages include platform context

### Cross-Platform Blog Linking

**NEW FEATURE (Nov 2025):** Generate coordinated blog + social media ecosystems.

**Architecture:**
1. **Blog posts generated first** (1,500-2,000 words) as anchor content
2. **Metadata extracted**: Title, slug, summary from each blog
3. **Social teasers generated**: Twitter and Facebook posts linking to blogs
4. **Link placeholders**: `[BLOG_LINK_1]`, `[BLOG_LINK_2]` for URL replacement

**Usage:**
```python
content = await generator.generate_multi_platform_with_blog_links_async(
    client_brief=brief,
    num_blog_posts=5,
    social_teasers_per_blog=2  # 1 Twitter + 1 Facebook per blog
)
# Returns: {"blog": [5 posts], "twitter": [5 teasers], "facebook": [5 teasers]}
```

**Post Model Enhancement:**
```python
class Post(BaseModel):
    # ... existing fields ...
    target_platform: Optional[str]  # Platform this post is for
    related_blog_post_id: Optional[int]  # Links teaser to blog
    blog_link_placeholder: Optional[str]  # e.g., "[BLOG_LINK_1]"
    blog_title: Optional[str]  # Title of related blog
```

**Key Methods** (`src/agents/content_generator.py`):
- `generate_multi_platform_with_blog_links_async()` - Main orchestration (lines 653-744)
- `_extract_blog_title()` - Extracts title from blog content (lines 746-761)
- `_create_slug()` - Creates URL-friendly slug (lines 763-771)
- `_generate_blog_teaser_async()` - Generates social teasers with links (lines 783-869)

**Output Files:**
- `{client}_{timestamp}_blog_posts.txt` - Full blog articles
- `{client}_{timestamp}_twitter_teasers.txt` - Twitter posts with `[BLOG_LINK_X]`
- `{client}_{timestamp}_facebook_teasers.txt` - Facebook posts with `[BLOG_LINK_X]`

### Enhanced Voice Analysis & Brand Frameworks

**NEW FEATURE (Nov 2025 - Phase 6):** Advanced voice metrics and professional copywriting frameworks integrated from content-creator Claude skill.

**Overview:**
The voice analysis system now goes beyond pattern detection to provide objective, measurable insights about content quality and brand voice consistency. Brand frameworks guide content generation with proven copywriting principles.

#### Voice Metrics System (`src/utils/voice_metrics.py`)

**VoiceMetrics** class provides four core analyses:

1. **Readability Scoring** - Flesch Reading Ease (0-100)
   ```python
   score = voice_metrics.calculate_readability(text)
   # 90-100: Very easy (5th grade)
   # 80-89: Easy (6th grade)
   # 70-79: Fairly easy (7th grade)
   # 60-69: Standard (8th-9th grade)
   # 50-59: Fairly difficult (high school)
   # 30-49: Difficult (college)
   ```

2. **Voice Dimension Analysis** - Keyword-based detection
   - **Formality**: formal → professional → conversational → casual
   - **Tone**: authoritative, friendly, innovative, educational
   - **Perspective**: authoritative, collaborative, conversational
   ```python
   dimensions = voice_metrics.analyze_voice_dimensions(text)
   # Returns: {'formality': {'dominant': 'professional', 'scores': {...}}, ...}
   ```

3. **Sentence Variety** - Structure diversity analysis
   ```python
   analysis = voice_metrics.analyze_sentence_variety(text)
   # Returns: {'variety': 'medium', 'average_length': 15.3, 'count': 10, ...}
   ```

4. **Complete Analysis** - All metrics in one call
   ```python
   results = voice_metrics.analyze_all(text)
   # Includes: readability, dimensions, sentence analysis, recommendations
   ```

#### Brand Archetype Framework (`src/config/brand_frameworks.py`)

**Five Brand Archetypes** based on proven voice frameworks:

1. **Expert** - Knowledgeable, data-driven, authoritative
   - Best for: B2B SaaS, consulting, professional services
   - Tone: "Our research shows that 87% of businesses..."

2. **Friend** - Warm, supportive, conversational
   - Best for: Consumer brands, coaching, community-focused
   - Tone: "We get it - marketing can be overwhelming..."

3. **Innovator** - Visionary, bold, forward-thinking
   - Best for: Startups, tech companies, disruptive products
   - Tone: "The future of marketing is here..."

4. **Guide** - Wise, patient, instructive
   - Best for: Education, training, how-to content
   - Tone: "Let's walk through this together..."

5. **Motivator** - Energetic, positive, inspiring
   - Best for: Coaches, self-improvement, transformation services
   - Tone: "You have the power to transform your business..."

**Archetype Inference:**
```python
# From voice dimensions (primary method)
archetype = infer_archetype_from_voice_dimensions(formality, tone, perspective)

# From client type (fallback method)
archetype = get_archetype_from_client_type("B2B_SAAS")  # Returns "Expert"
```

**Writing Principles Included:**
- Action verbs: transform, accelerate, optimize, unlock, elevate
- Positive descriptors: seamless, powerful, intuitive, strategic
- Outcome-focused language: results, growth, success, impact, ROI
- Words to avoid: synergy, leverage, very, really, just

#### Integration Points

**1. VoiceAnalyzer Enhancement** (`src/agents/voice_analyzer.py`)

Enhanced `analyze_voice_patterns()` now includes:
```python
# NEW: Calculate advanced voice metrics
readability_score = self.voice_metrics.calculate_readability(all_text)
voice_dimensions = self.voice_metrics.analyze_voice_dimensions(all_text)
sentence_analysis = self.voice_metrics.analyze_sentence_variety(all_text)

# NEW: Determine brand archetype
archetype = self._determine_archetype(voice_dimensions, client_brief)

# NEW: Add readability recommendations to dos/donts
if readability_score < 50:
    donts.append("DON'T: Use overly complex sentences")
```

Returns `EnhancedVoiceGuide` with new optional fields:
- `average_readability_score: Optional[float]`
- `voice_dimensions: Optional[Dict]`
- `sentence_variety: Optional[str]`
- `voice_archetype: Optional[str]`

**2. ContentGenerator Enhancement** (`src/agents/content_generator.py`)

Enhanced `_build_system_prompt()` injects brand frameworks:
```python
# NEW: Add brand archetype guidance
archetype = self._infer_archetype(client_brief)
archetype_guidance = get_archetype_guidance(archetype)
prompt += archetype_guidance

# NEW: Add professional writing principles
writing_principles = get_writing_principles_guidance()
prompt += writing_principles
```

Archetype inference uses:
1. Client type from classifier (if available)
2. Keyword-based inference from business description (fallback)
3. Default to "Guide" archetype (safe, versatile)

**3. EnhancedVoiceGuide Markdown Output** (`src/models/voice_guide.py`)

New **Voice Metrics** section in markdown deliverable:
```markdown
### Voice Metrics

**Brand Archetype:** Expert

**Readability Score:** 72.3/100 (Fairly Easy - 7th grade)

**Sentence Variety:** Medium 📊

**Voice Dimensions:**
- Formality: Professional
- Tone: Authoritative
- Perspective: Collaborative
```

#### Performance & Testing

**Unit Tests** (`tests/unit/test_voice_metrics.py`):
- 29 tests covering all VoiceMetrics methods
- Edge cases: empty text, special characters, unicode, very long text
- Coverage: 96% for VoiceMetrics class

**Integration Tests** (`tests/integration/test_voice_analysis_integration.py`):
- 11 tests verifying end-to-end voice analysis pipeline
- Archetype detection for B2B SaaS, conversational, professional content
- Markdown output validation
- Backward compatibility verification
- Performance test: <5 seconds for 30 posts

**Coverage:**
- VoiceAnalyzer: 95%
- VoiceGuide: 93%
- VoiceMetrics: 96% (unit tests)
- brand_frameworks: 47% (helper functions)

**Backward Compatibility:**
All new fields in `EnhancedVoiceGuide` are Optional. Existing code works unchanged:
```python
# Works without new metrics
voice_guide = EnhancedVoiceGuide(
    company_name="Test",
    generated_from_posts=5,
    # ... other required fields ...
    # New fields automatically default to None
)
```

#### Key Architecture Decisions

1. **Additive Integration** - All changes are optional/additive to maintain backward compatibility
2. **No External Dependencies** - Extracted algorithms from skill, adapted to Pydantic models
3. **Voice Dimensions as Primary Signal** - More reliable than simple keyword matching
4. **Flesch Reading Ease** - Industry-standard readability metric
5. **Brand Archetypes** - Based on proven content marketing frameworks
6. **Performance-Conscious** - All metrics calculated synchronously, <1 second overhead

### Anthropic API Wrapper

**Critical component:** `src/utils/anthropic_client.py`

All API calls go through `AnthropicClient` which provides:
- **Automatic retry logic** (3 attempts with exponential backoff)
- **Sync and async methods** (`create_message` vs `create_message_async`)
- **Token optimization** via `_format_context_optimized()` (excludes empty fields, limits list items to 5)
- **Error handling** for `RateLimitError`, `APIConnectionError`, `APIError`

**Never call Anthropic API directly** - always use `AnthropicClient` methods.

### Template Selection Logic

Templates are selected by **client type** using keyword-based classification:

**Client Types** (defined in `src/config/template_rules.py`):
- `B2B_SAAS`: Prefers Problem, Statistic, Contrarian, How-To; avoids Story
- `AGENCY`: Prefers Evolution, Comparison, Q&A, Milestone; avoids Future
- `COACH_CONSULTANT`: Prefers Story, Myth Busting, Future; avoids Statistic
- `CREATOR_FOUNDER`: Prefers Story, Q&A, Behind Scenes, Milestone; avoids Statistic
- `UNKNOWN`: Default safe set (7 templates: Problem, Stat, Contrarian, Evolution, Question, How-To, Comparison)

**Classification process:**
1. Extract keywords from `business_description` and `ideal_customer` fields
2. Score each client type by keyword matches
3. Require minimum 15% confidence, otherwise use `UNKNOWN`
4. Select templates from `TEMPLATE_PREFERENCES[client_type]`

**Manual override:** Use `--templates "1,3,5"` CLI flag to bypass classification.

### Quality Validation System

**QAAgent** orchestrates 5 independent validators (all synchronous, <1 second total):

1. **HookValidator** (`src/validators/hook_validator.py`)
   - Uses `difflib.SequenceMatcher` for fuzzy matching
   - Default threshold: 80% similarity = duplicate
   - Returns uniqueness score (0.0-1.0)

2. **CTAValidator** (`src/validators/cta_validator.py`)
   - Detects CTAs via pattern matching (questions, invitations, offers)
   - Classifies CTA types (question, engagement, direct)
   - Minimum variety threshold: 40%

3. **LengthValidator** (`src/validators/length_validator.py`)
   - **Platform-aware (Nov 2025)**: Detects platform from `Post.target_platform`
   - Uses platform-specific specs from `platform_specs.py`
   - LinkedIn: 200-300 words optimal
   - Twitter: 12-18 words optimal
   - Facebook: 10-15 words optimal
   - Blog: 1,500-2,000 words optimal
   - Returns distribution and optimal ratio with platform context

4. **HeadlineValidator** (`src/validators/headline_validator.py`)
   - Counts engagement elements (questions, numbers, power words)
   - Minimum 3 elements for strong hooks
   - Returns below-threshold count

5. **KeywordValidator** (`src/validators/keyword_validator.py`) - **Optional**
   - Only runs if `KeywordStrategy` provided
   - Validates primary/secondary keyword usage
   - Checks keyword density and stuffing

**Quality score** = average of all validator scores. Typical production score: 85-90%.

### Data Models (Pydantic)

All models in `src/models/` use Pydantic for validation:

**ClientBrief** - Structured client information
- Required: `company_name`, `business_description`, `ideal_customer`, `main_problem_solved`
- Enums: `TonePreference`, `Platform`, `DataUsagePreference`
- Method: `to_context_dict()` converts to template rendering format
- **NEW (Nov 2025):** `customer_pain_points` field accepts unlimited entries (no 5-item limit)
- `customer_questions` still limited to 10 items (reasonable constraint)

**Post** - Generated post with metadata
- Auto-calculated: `word_count`, `has_cta`
- Quality flags: `needs_review`, `review_reasons`
- SEO: `keywords_used` (optional)

**Template** - Template structure
- Enums: `TemplateType`, `TemplateDifficulty`
- Flags: `requires_story`, `requires_data`
- `structure` field contains template text with [BRACKETS]

**QAReport** - Validation results
- Aggregates all validator outputs
- `overall_passed` boolean
- `quality_score` float (0.0-1.0)
- `all_issues` list for reporting

### Configuration System

**Environment-based config** via `src/config/settings.py`:

```python
# Critical settings
ANTHROPIC_API_KEY: str          # Required
ANTHROPIC_MODEL: str            # Default: "claude-3-5-sonnet-latest"
PARALLEL_GENERATION: bool       # Default: True (async mode)
MAX_CONCURRENT_API_CALLS: int   # Default: 5 (semaphore limit)

# Quality thresholds
MIN_POST_WORD_COUNT: int        # 75 words
OPTIMAL_POST_MIN_WORDS: int     # 150 words
OPTIMAL_POST_MAX_WORDS: int     # 250 words
MAX_POST_WORD_COUNT: int        # 350 words

# Paths (relative to /project/ directory)
TEMPLATE_LIBRARY_PATH: str      # "../02_POST_TEMPLATE_LIBRARY.md"
CLIENT_BRIEF_TEMPLATE_PATH: str # "../01_CLIENT_BRIEF_TEMPLATE.md"
DEFAULT_OUTPUT_DIR: str         # "data/outputs"
```

**Override via .env file:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
PARALLEL_GENERATION=False
MAX_CONCURRENT_API_CALLS=3
DEBUG_MODE=True
```

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

### UTF-8 Encoding Fix (Windows)

**Lines 13-15 of 03_post_generator.py** force UTF-8 encoding:
```python
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```
**Never remove this** - Windows console defaults cause encoding errors with special characters.

### Template Path Resolution

Templates are loaded from **parent directory**:
```python
# src/config/settings.py
TEMPLATE_LIBRARY_PATH: str = "../02_POST_TEMPLATE_LIBRARY.md"
CLIENT_BRIEF_TEMPLATE_PATH: str = "../01_CLIENT_BRIEF_TEMPLATE.md"
```

Paths are resolved relative to `project/` directory. If you change directory structure, update these paths.

### Prompt Caching Strategy

**ContentGeneratorAgent** caches prompts to reduce token usage:
```python
# Built once, reused for all 30 posts
cached_system_prompt = self._build_system_prompt(client_brief)
base_context = client_brief.to_context_dict()

# Passed to each post generation
post = self._generate_single_post(
    ...,
    cached_system_prompt=cached_system_prompt,
    base_context=base_context
)
```

**Performance impact:** Saves ~10,000 tokens per generation run.

### Temperature Settings

Different temperatures for different agent tasks:
```python
# Brief parsing (accuracy matters)
BRIEF_PARSING_TEMPERATURE: float = 0.3

# Post generation (creativity matters)
POST_GENERATION_TEMPERATURE: float = 0.7
```

**Never use temperature > 0.3 for parsing** - causes JSON parsing errors.

### Error Recovery in Content Generation

If post generation fails, system creates **placeholder post** to maintain count:
```python
# src/agents/content_generator.py:354-362
post = Post(
    content=f"[ERROR: Failed to generate post - {str(e)}]",
    template_id=template.template_id,
    template_name=template.name,
    variant=variant,
    client_name=client_brief.company_name,
)
post.flag_for_review(f"Generation failed: {str(e)}")
```

**This prevents entire batch failure** if 1-2 posts have API issues.

### Client Type Confidence Threshold

Classification requires **minimum 15% keyword match**:
```python
# src/agents/client_classifier.py:66
if confidence < 0.15:
    return ClientType.UNKNOWN, confidence
```

**Rationale:** Low-confidence classifications lead to poor template selection. Better to use safe default set.

## Common Development Patterns

### Adding a New Validator

1. Create validator in `src/validators/new_validator.py`:
```python
class NewValidator:
    def validate(self, posts: List[Post]) -> Dict:
        return {
            "passed": bool,
            "score": float,
            "issues": List[str]
        }
```

2. Register in `QAAgent.__init__()`:
```python
self.new_validator = NewValidator()
```

3. Call in `QAAgent.validate_posts()`:
```python
new_results = self.new_validator.validate(posts)
all_issues.extend(new_results.get("issues", []))
scores.append(new_results.get("score", 1.0))
```

4. Add results to QAReport model

### Adding a New Template Type

1. Add enum to `src/models/template.py`:
```python
class TemplateType(str, Enum):
    NEW_TYPE = "new_type"
```

2. Add to template library (`../02_POST_TEMPLATE_LIBRARY.md`)

3. Update `src/config/template_rules.py`:
```python
TEMPLATE_PREFERENCES[ClientType.X]["preferred"].append(TemplateType.NEW_TYPE)
```

4. Template loader auto-detects from markdown - no code changes needed

### Adding a New Client Type

1. Add enum to `src/config/template_rules.py`:
```python
class ClientType(Enum):
    NEW_TYPE = "new_type"
```

2. Add keyword mappings:
```python
CLIENT_TYPE_KEYWORDS[ClientType.NEW_TYPE] = {
    "business_description": ["keyword1", "keyword2"],
    "ideal_customer": ["keyword3", "keyword4"]
}
```

3. Add template preferences:
```python
TEMPLATE_PREFERENCES[ClientType.NEW_TYPE] = {
    "preferred": [TemplateType.X, TemplateType.Y],
    "avoid": [TemplateType.Z]
}
```

Classification is automatic via `ClientClassifier`.

### Testing Async Functions

Use `pytest-asyncio` for async tests:
```python
import pytest

@pytest.mark.asyncio
async def test_async_generation():
    generator = ContentGeneratorAgent()
    posts = await generator.generate_posts_async(
        client_brief=sample_brief,
        num_posts=10
    )
    assert len(posts) == 10
```

Run with: `pytest tests/integration/test_async_generation.py -v`

## Debugging Tips

### Enable Debug Logging
```bash
# In .env
DEBUG_MODE=True
LOG_LEVEL=DEBUG
```

### Check API Calls
All API calls are logged in `logs/content_jumpstart.log`:
```
2025-11-23 14:30:52 - API call: claude-3-5-sonnet-latest (~500 tokens)
2025-11-23 14:30:54 - Post generated: #1 "Problem Recognition" (208 words)
```

### Test Individual Agents
```python
# Test brief parser
from src.agents.brief_parser import BriefParserAgent

parser = BriefParserAgent()
brief_text = Path("tests/fixtures/sample_brief.txt").read_text()
client_brief = parser.parse_brief(brief_text)
print(client_brief.company_name)
```

### Validate Template Loading
```bash
python 03_post_generator.py list-templates
```
Should show 15 templates. If not, check `../02_POST_TEMPLATE_LIBRARY.md` path.

### Check Output Files
Generated files in `data/outputs/{ClientName}/`:
```
ClientName_20251123_143052_deliverable.md      # 30 posts
ClientName_20251123_143052_brand_voice.md      # Voice guide
ClientName_20251123_143052_qa_report.md        # Quality report
ClientName_20251123_143052_keyword_strategy.md # SEO keywords (optional)
```

If files missing, check `OutputFormatter` logs for errors.

## Performance Considerations

### Token Usage Optimization

**Context filtering** (src/utils/anthropic_client.py:335-378):
- Priority fields always included: company_name, ideal_customer, problem_solved, brand_voice
- Empty lists/dicts excluded
- Lists limited to first 5 items
- Template metadata excluded (already in structure)

**Typical token usage per client:**
- Brief parsing: ~500 input tokens
- Post generation: ~300 tokens/post × 30 = 9,000 input tokens
- Total output: ~6,000 tokens (30 posts × 200 words avg)
- **Cost: ~$0.40-0.60 per client** (Claude 3.5 Sonnet pricing)

### API Rate Limiting

**Semaphore prevents rate limits:**
```python
# Max 5 concurrent requests
semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_API_CALLS)
```

If you hit rate limits, reduce `MAX_CONCURRENT_API_CALLS` in .env.

### Caching Strategy

**System prompt caching** saves ~40% tokens:
```python
# Built once per generation run
cached_system_prompt = self._build_system_prompt(client_brief)

# Reused for all 30 posts (saves 10,000 tokens)
```

**Base context caching** saves dictionary rebuilding:
```python
base_context = client_brief.to_context_dict()  # Once
# Copied for each variant (not rebuilt)
```

## Business Logic Constraints

### Scope Limits (Revenue Protection)

**Revision variant system** (not auto-correction):
```python
def generate_variant(
    original_post: Post,
    client_brief: ClientBrief,
    feedback: str
) -> Post
```

- Used for **client revision requests** (max 5 per contract)
- Marks revised posts with `variant + 100` (e.g., variant 101 = revision of variant 1)
- **Not** for automatic quality fixes (that would add unbounded API costs)

### Template Library Sync

Business templates (`../02_POST_TEMPLATE_LIBRARY.md`) are **manually maintained**.

**TemplateLoader** parses markdown dynamically, so template changes are automatically picked up. But adding new templates requires:
1. Update markdown file (business team)
2. Optionally add to `TEMPLATE_PREFERENCES` (engineering team)

No code changes needed for template content edits.

### Output Directory Structure

Deliverables saved with **timestamp-based versioning**:
```
data/outputs/
  ├── ClientName/
  │   ├── ClientName_20251123_143052_deliverable.md
  │   └── ClientName_20251123_150000_deliverable.md  # Second run
```

**Never overwrite** - timestamps prevent data loss during re-runs.

## Related Documentation

**Parent directory documentation:**
- `../CLAUDE.md` - Repository guide (business context, workflow, pricing)
- `../README.md` - Business system overview
- `../IMPLEMENTATION_PLAN.md` - Phased development plan
- `../PHASE_1_DETAILED_PLAN.md` - Phase 1 specifications
- `../PHASE_2_COMPLETION.md` - Async generation implementation
- `../PHASE_2_PROGRESS_SUMMARY.md` - Multi-platform implementation progress
- `../PHASE_3_COMPLETION.md` - QA validation implementation
- `../CROSS_PLATFORM_BLOG_LINKING_COMPLETE.md` - Cross-platform feature documentation
- `../01_CLIENT_BRIEF_TEMPLATE.md` - Discovery form template
- `../02_POST_TEMPLATE_LIBRARY.md` - 15 post templates
- `../04_PROJECT_CHECKLIST.md` - Business workflow checklist

**Technical documentation:**
- `../SYSTEM_CAPABILITIES_REPORT.md` - Comprehensive system analysis
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

### Deep-Link Routing (Dashboard)

**Issue:** Refreshing on deep routes (e.g., `/dashboard/projects`) returns 404.

**Cause:** The catch-all route that served `index.html` for all paths was interfering with API routing. When frontend made API requests, the catch-all route was matching `/api/*` paths BEFORE the API routers could handle them, causing the API to return HTML instead of JSON. This caused errors like "x.filter is not a function" in the React dashboard.

**Solution:** Removed the catch-all route entirely. This fixed API routing but broke deep-link support as a trade-off.

**Workaround:** Use the navigation menu instead of browser refresh when on deep routes.

**Future Fix:** Implement middleware-based SPA routing (does not interfere with API routes):
```python
@app.middleware("http")
async def spa_middleware(request: Request, call_next):
    response = await call_next(request)

    # If 404 and not an API route, serve index.html
    if response.status_code == 404 and not request.url.path.startswith("/api"):
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

    return response
```

This approach:
- Lets API routes handle their 404s properly (returns JSON)
- Serves `index.html` for non-API 404s (enables React Router deep-links)
- Doesn't interfere with API routing

**Documentation:** See `DASHBOARD_FIX_SUMMARY.md` for complete fix history and technical details.

---

# Operator Dashboard (Internal Web UI)

## Overview

The **Operator Dashboard** is the internal web UI for managing the 30-Day Content Jumpstart content generation workflow. Located in `operator-dashboard/`, it provides a comprehensive React-based interface for operators to manage projects, execute generation workflows, perform quality assurance, and deliver completed content.

**Primary Use:** Internal operator workflow management
**Location:** `operator-dashboard/`
**Documentation:** `OPERATOR_DASHBOARD.md`

## Key Distinction: Operator Dashboard vs. Client Portal

| Feature | Operator Dashboard | Client Portal |
|---------|-------------------|---------------|
| **Purpose** | Internal workflow management | Client self-service |
| **Users** | Internal operators | External clients |
| **Directory** | `operator-dashboard/` | `portal/` |
| **Status** | **Active Development (Primary)** | On hold |

**Use the Operator Dashboard for all internal workflow needs.**

## Tech Stack

- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- React Query (server state) + Zustand (local state)
- React Router v6 (nested routes)
- Axios with JWT authentication

## Core Features

### 1. Project Management Dashboard
- Client search with typeahead
- Project filters (status, client, date)
- Projects table with status indicators
- Deliverables grouped by client

### 2. Project Wizard (5-Step)
1. **Client Profile** - Zod-validated form for client details
2. **Template Selection** - Choose from 15 templates
3. **Generation** - "Generate All" with progress tracking
4. **Quality Gate** - Automated flagging (length, readability, CTAs)
5. **Export** - Format selection (TXT/DOCX) + audit logging

### 3. Quality Assurance System
- Automated flags:
  - Post length (too short/too long)
  - Readability score (Flesch Reading Ease)
  - Missing CTAs
  - Platform-specific requirements
- Bulk or targeted regeneration
- Export blocking for unresolved flags

### 4. Deliverable Management
- List view with filters
- Detail drawer (file path, run ID, status)
- "Mark Delivered" with audit logging
- Delivery proof URL + notes

### 5. Research Tools Panel (Optional)
- Display available research tools
- Run research add-ons
- Attach outputs to briefs

## Quick Start

```bash
# Navigate to dashboard
cd operator-dashboard

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Start dev server
npm run dev
# Available at http://localhost:5173
```

## Integration with Python Backend

The dashboard integrates with the Python content generation system via REST API:

**Expected API Endpoints:**
- `POST /api/generator/generate-all` - Generate posts
- `POST /api/generator/regenerate` - Regenerate specific posts
- `POST /api/qa/validate` - Validate quality
- `GET /api/projects` - List projects
- `GET /api/deliverables` - List deliverables

**Or integrate directly with CLI:**
```typescript
// Trigger 03_post_generator.py from dashboard
await client.post('/api/cli/generate', {
  command: `python 03_post_generator.py generate ${briefPath} -c "${clientName}"`
});
```

## Data Models (TypeScript)

```typescript
interface Project {
  project_id: string;
  client_name: string;
  status: 'draft' | 'processing' | 'qa_review' | 'ready' | 'delivered';
  package_tier: string;
  posts_count: number;
  last_run?: string;
}

interface PostDraft {
  post_id: string;
  content: string;
  word_count: number;
  readability_score?: number;
  has_cta: boolean;
  flags: QualityFlag[];
}

interface Deliverable {
  deliverable_id: string;
  project_id: string;
  file_path: string;
  format: 'txt' | 'docx';
  status: 'draft' | 'ready' | 'delivered';
  delivered_at?: string;
}
```

## Development Commands

```bash
# Development
npm run dev           # Start dev server

# Building
npm run build         # Production build
npm run preview       # Preview production build

# Testing
npm run test          # Run tests
npm run test:coverage # With coverage
```

## Documentation

**Complete Guide:** `OPERATOR_DASHBOARD.md`
**Implementation Plan:** `operator-dashboard/IMPLEMENTATION_PLAN.md`
**Setup Instructions:** `operator-dashboard/README.md`

---

# Internal CLI Agent System (Phase 9A)

## Overview

The **Internal CLI Agent** is a Claude Code-style conversational agent for managing content generation workflows. It provides a natural language interface to all content generation tools with intelligence features like workflow planning, proactive suggestions, error recovery, and conversation history.

**Version:** 2.0 (Week 2 Intelligence + Week 3 Polish)

## Running the Agent

### Basic Usage

```bash
# Start interactive chat
python agent_cli_enhanced.py chat

# Resume previous session
python agent_cli_enhanced.py chat --session <session_id>

# Enable debug mode
python agent_cli_enhanced.py chat --debug
```

### CLI Commands

```bash
# List recent sessions
python agent_cli_enhanced.py sessions
python agent_cli_enhanced.py sessions --limit 20

# Show scheduled tasks
python agent_cli_enhanced.py scheduled

# Show pending items
python agent_cli_enhanced.py pending

# Export conversation to markdown
python agent_cli_enhanced.py export -s <session_id>
python agent_cli_enhanced.py export -s <session_id> -o custom_path.md

# Search conversation history
python agent_cli_enhanced.py search -s <session_id> <query>
python agent_cli_enhanced.py search -s <session_id> "invoice" -r user

# Get conversation statistics
python agent_cli_enhanced.py summary -s <session_id>
```

### In-Chat Commands

While in chat mode:
- `help` - Show help message
- `pending` or `daily summary` - Show pending items and suggestions
- `scheduled` - Show upcoming scheduled tasks
- `reset` - Clear conversation history (keeps session)
- `new` - Start new session
- `exit` - Save and quit

## Agent Architecture

### Core Components

```
agent/
├── core_enhanced.py          # Main agent orchestrator
├── context.py                # Session and conversation management
├── tools.py                  # Tool wrappers for CLI commands
├── prompts.py                # System prompts and templates
├── workflows.py              # Workflow execution engine
├── planner.py                # Workflow planning (Week 2)
├── suggestions.py            # Proactive suggestions (Week 2)
├── error_recovery.py         # Retry logic with exponential backoff (Week 2)
├── scheduler.py              # Task scheduling (Week 2)
└── email_system.py           # Email integration (Week 2)
```

### Tool Execution Flow

1. **User Input** → Agent receives natural language request
2. **Claude Analysis** → Claude decides which tools to call
3. **Function Calling** → Agent receives tool calls with parameters
4. **Tool Execution** → `ContentAgentCoreEnhanced._execute_single_tool()`
   ```python
   tool_method = getattr(self.tools, tool_name)
   if asyncio.iscoroutinefunction(tool_method):
       result = await tool_method(**tool_input)
   else:
       result = tool_method(**tool_input)
   ```
5. **Result Return** → Results sent back to Claude
6. **Response** → Claude formats response for user

### Available Tools

The agent can execute 14 + 2 tools:

**Core Tools (14):**
- `generate_posts` - Generate social media posts
- `list_projects` - List all projects
- `get_project_status` - Get project details
- `list_clients` - List all clients
- `get_client_history` - Get client history
- `collect_feedback` - Collect post feedback
- `collect_satisfaction` - Satisfaction survey
- `upload_voice_samples` - Voice analysis
- `show_dashboard` - Analytics dashboard
- `read_file` - Read file contents
- `search_files` - Search for files
- `process_revision` - Handle revisions *(Week 3)*
- `generate_analytics_report` - Create reports *(Week 3)*
- `create_posting_schedule` - Schedule posts *(Week 3)*

**Special Tools (2):**
- `schedule_task` - Schedule future execution
- `send_email` - Send emails (deliverable, reminders, invoices)

### Adding New Tools

1. **Add method to `agent/tools.py`:**
   ```python
   async def new_tool(self, param1: str) -> Dict[str, Any]:
       """Tool description"""
       try:
           # Tool logic here
           return {
               "success": True,
               "message": "Tool executed successfully",
               "data": result
           }
       except Exception as e:
           return {"success": False, "error": str(e)}
   ```

2. **Register in `get_available_tools()`:**
   ```python
   {
       "name": "new_tool",
       "description": "What the tool does",
       "parameters": "param1, param2 (optional), param3 (default value)"
   }
   ```

3. **Agent automatically discovers** via `_get_enhanced_tool_definitions()`

## Intelligence Features (Week 2)

### 1. Workflow Planning

Multi-step operations are planned before execution:

```python
# agent/planner.py
plan = planner.plan_onboarding_workflow(
    client_name="Acme Corp",
    has_brief=True,
    has_voice_samples=False
)
# Returns WorkflowPlan with tasks, dependencies, estimated duration
```

**Workflow Types:**
- `plan_onboarding_workflow()` - Complete client setup
- `plan_batch_operations()` - Process multiple pending items
- `plan_simple_workflow()` - Single or sequential operations

### 2. Proactive Suggestions

Agent detects pending items automatically:

```python
# agent/suggestions.py
suggestions = engine.generate_suggestions()
# Checks for:
# - Missing feedback (>2 weeks old)
# - Overdue invoices (>7 days past due)
# - Pending deliverables
# - Client milestones
```

### 3. Error Recovery

Automatic retry with exponential backoff:

```python
# agent/error_recovery.py
success, result, error_record = await error_recovery.execute_with_retry_async(
    func=api_call,
    config=RetryConfig(max_retries=3)
)
# Retry pattern: 0s → 1s → 2s → 4s
```

### 4. Task Scheduling

Schedule future tasks:

```python
# agent/scheduler.py
task = scheduler.schedule_task(
    description="Follow up with client",
    tool_name="send_email",
    tool_params={...},
    execute_in=timedelta(days=1),
    frequency=ScheduleFrequency.ONCE
)
```

### 5. Email Integration

Send emails via templates:

```python
# agent/email_system.py
message = email_system.create_email_from_template(
    email_type=EmailType.DELIVERABLE,
    to_email="client@example.com",
    variables={"client_name": "Acme Corp", ...}
)
success, result = email_system.send_email(message)
```

## Polish Features (Week 3)

### Conversation History

**Database:** SQLite with WAL mode (`data/agent_sessions.db`)

**Tables:**
- `sessions` - Session metadata (client, project, timestamps)
- `conversation_messages` - All messages with role, content, timestamp

**Key Methods:**
```python
# agent/context.py
manager.save_message(session_id, role, content, metadata)
messages = manager.load_conversation(session_id, limit=None)
markdown = manager.export_conversation_markdown(session_id, output_path)
results = manager.search_conversation(session_id, query, role=None)
summary = manager.get_conversation_summary(session_id)
```

### Rich Console Output

**Components:**
- Syntax highlighting for code blocks (Monokai theme)
- Tree visualization for workflows (dependencies shown)
- Enhanced progress bars (spinner + bar + percentage + count)
- Panel-based messages with colored borders
- Priority-based color coding

**Implementation:**
```python
# agent_cli_enhanced.py
from rich.syntax import Syntax
from rich.tree import Tree
from rich.panel import Panel

# Code blocks displayed with highlighting
Syntax(code, language, theme="monokai", line_numbers=True)

# Workflows shown as trees
tree = Tree("Tasks")
tree.add("Task 1")
```

## Testing the Agent

### Run Agent Tests

```bash
# Run Week 2 intelligence tests (24 tests)
pytest tests/agent/test_week2_features.py -v

# Run Week 3 polish tests (16 tests)
pytest tests/agent/test_week3_features.py -v

# Run all agent tests
pytest tests/agent/ -v
```

### Verify Tool Execution

```bash
# Test tool discovery and execution
python test_tool_execution.py

# Output shows:
# - All 14 tools are discoverable
# - All methods exist on AgentTools
# - Agent exposes 16 tools to Claude
# - Week 3 tools fully integrated
```

## Database Schema

### Sessions Table

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    context_data TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL
)
```

### Conversation Messages Table

```sql
CREATE TABLE conversation_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata TEXT,  -- Optional JSON
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
)

CREATE INDEX idx_session_messages ON conversation_messages(session_id, timestamp);
CREATE INDEX idx_message_content ON conversation_messages(content);
```

### Scheduled Tasks Table

```sql
CREATE TABLE scheduled_tasks (
    task_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_params TEXT NOT NULL,  -- JSON
    scheduled_for TIMESTAMP NOT NULL,
    frequency TEXT,  -- ONCE, DAILY, WEEKLY, BIWEEKLY, MONTHLY
    status TEXT,  -- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    ...
)
```

## Agent Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (defaults work for most cases)
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
PARALLEL_GENERATION=True
MAX_CONCURRENT_API_CALLS=5
DEBUG_MODE=False
LOG_LEVEL=INFO
```

### Key Settings

**File:** `agent/core_enhanced.py`

```python
# Model selection
model = "claude-3-5-sonnet-20241022"

# Temperature for agent responses
temperature = 0.7

# Max tokens per response
max_tokens = 4096

# Retry configuration
RetryConfig(
    max_retries=3,
    initial_delay_seconds=1.0,
    max_delay_seconds=60.0,
    exponential_base=2.0,
    jitter=True  # Prevents thundering herd
)
```

## Common Agent Patterns

### Executing Tool from Natural Language

**User:** "Generate posts for Acme Corp"

**Flow:**
1. Agent receives message
2. Claude decides to call: `generate_posts(client_name="Acme Corp", brief_path="...")`
3. Agent executes via `getattr(self.tools, "generate_posts")`
4. Results returned to Claude
5. Claude formats response

### Creating Multi-Step Workflow

**User:** "Onboard new client StartupXYZ"

**Flow:**
1. Agent detects multi-step intent
2. Planner creates `WorkflowPlan` with 5 tasks
3. Agent displays plan with tree visualization
4. User confirms execution
5. Agent executes tasks sequentially with progress bar
6. Results displayed in panel

### Resuming Previous Session

**Command:** `python agent_cli_enhanced.py chat --session abc-123`

**Flow:**
1. Agent loads context: `context_manager.load_context(session_id)`
2. Agent loads messages: `context_manager.load_conversation(session_id)`
3. Messages added to `self.messages` for Claude API
4. Conversation continues from where it left off

## Debugging the Agent

### Enable Verbose Logging

```bash
# Set in .env
DEBUG_MODE=True
LOG_LEVEL=DEBUG

# Check logs
tail -f logs/content_jumpstart.log
```

### Test Individual Components

```python
# Test tool wrapper
from agent.tools import AgentTools
tools = AgentTools()
result = tools.list_projects(client_name="Acme Corp")

# Test workflow planner
from agent.planner import WorkflowPlanner
planner = WorkflowPlanner()
plan = planner.plan_simple_workflow(
    intent="Generate posts",
    tool_name="generate_posts",
    tool_params={"client_name": "Acme"}
)

# Test suggestion engine
from agent.suggestions import SuggestionEngine
engine = SuggestionEngine()
suggestions = engine.generate_suggestions()
```

### Verify Database State

```bash
# Check sessions
sqlite3 data/agent_sessions.db "SELECT * FROM sessions ORDER BY last_activity DESC LIMIT 5;"

# Check messages
sqlite3 data/agent_sessions.db "SELECT session_id, COUNT(*) FROM conversation_messages GROUP BY session_id;"

# Check scheduled tasks
sqlite3 data/agent_sessions.db "SELECT * FROM scheduled_tasks WHERE status='PENDING';"
```

## Agent Documentation

**User Guide:** `AGENT_USER_GUIDE.md` - Complete user documentation with examples

**Completion Docs:**
- `../PHASE_9A_WEEK1_COMPLETION.md` - Foundation implementation
- `../PHASE_9A_WEEK2_COMPLETION.md` - Intelligence layer
- `../PHASE_9A_WEEK3_COMPLETION.md` - Polish & testing

**Technical Details:**
- Week 2 features: Workflow planning, suggestions, error recovery, scheduling, email
- Week 3 features: Conversation history, rich output, tool wrappers, integration tests
- Test coverage: 40 tests (24 Week 2 + 16 Week 3), 100% passing
