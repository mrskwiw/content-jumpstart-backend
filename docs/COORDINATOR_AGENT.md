# Coordinator Agent - Usage Guide

The **CoordinatorAgent** is the main orchestrator for the Content Jumpstart system. It provides a simplified, unified interface for running the complete workflow from brief to deliverables.

## Features

### 1. **Multiple Brief Input Formats**
- **File path**: Path to text brief file
- **Dictionary**: Python dict with brief fields
- **ClientBrief object**: Pre-validated Pydantic model
- **Interactive builder**: CLI-based questionnaire

### 2. **Voice Sample Analysis (Optional)**
- Accepts 1+ sample posts for voice analysis
- Extracts tone patterns, hooks, CTAs
- Generates enhanced voice guide
- Merges insights into brief context

### 3. **Intelligent Information Gathering**
- Validates required fields automatically
- Detects missing information
- Optionally prompts interactively for missing fields
- Provides helpful error messages

### 4. **Complete Workflow Orchestration**
- Client type classification
- Template selection
- Content generation (async by default)
- QA validation
- Multi-format deliverables

### 5. **Progress Reporting**
- Step-by-step progress logging
- Quality metrics
- File generation summary
- Error handling with graceful degradation

## Quick Start

### Option 1: Using Existing Brief File

```bash
# Basic usage with brief file
python run_jumpstart.py path/to/brief.txt

# With voice samples for analysis
python run_jumpstart.py brief.txt --voice-samples sample1.txt sample2.txt sample3.txt

# Generate fewer posts (for testing)
python run_jumpstart.py brief.txt --num-posts 10

# Target specific platform
python run_jumpstart.py brief.txt --platform twitter

# Set custom start date for posting schedule
python run_jumpstart.py brief.txt --start-date 2025-12-01
```

### Option 2: Interactive Brief Builder

```bash
# Run interactive builder
python run_jumpstart.py --interactive
```

The interactive builder will prompt you for:
- Company/Client Name
- Business Description
- Ideal Customer Profile
- Main Problem Solved
- Customer Pain Points (multiple)
- Brand Personality Tones
- Key Phrases/Taglines
- Common Customer Questions
- Target Platforms
- Posting Frequency
- Data Usage Preference
- Main Call-to-Action

### Option 3: Programmatic Usage

```python
import asyncio
from pathlib import Path
from src.agents.coordinator import CoordinatorAgent
from src.models.client_brief import ClientBrief, TonePreference, Platform

async def generate_content():
    coordinator = CoordinatorAgent()

    # Option 1: With file path
    saved_files = await coordinator.run_complete_workflow(
        brief_input="path/to/brief.txt",
        num_posts=30,
    )

    # Option 2: With ClientBrief object
    brief = ClientBrief(
        company_name="My Company",
        business_description="We help businesses grow",
        ideal_customer="Small business owners",
        main_problem_solved="Scaling challenges",
        brand_personality=[TonePreference.DIRECT],
        target_platforms=[Platform.LINKEDIN],
        # ... other fields
    )

    saved_files = await coordinator.run_complete_workflow(
        brief_input=brief,
        num_posts=30,
    )

    # Option 3: With voice samples
    voice_samples = [
        "Sample post 1 text...",
        "Sample post 2 text...",
        "Sample post 3 text...",
    ]

    saved_files = await coordinator.run_complete_workflow(
        brief_input=brief,
        voice_samples=voice_samples,
        num_posts=30,
    )

    print(f"Generated {len(saved_files)} files")
    for key, path in saved_files.items():
        print(f"  {key}: {path}")

# Run
asyncio.run(generate_content())
```

## CLI Arguments

### Required (choose one)
- `brief` - Path to brief file
- `--interactive` / `-i` - Run interactive builder

### Optional
- `--voice-samples FILE [FILE ...]` - Paths to sample posts for voice analysis
- `--num-posts N` / `-n N` - Number of posts to generate (default: 30)
- `--platform {linkedin,twitter,facebook,blog,email}` / `-p` - Target platform
- `--start-date YYYY-MM-DD` - Posting schedule start date (default: today)
- `--no-analytics` - Skip analytics tracker generation
- `--no-docx` - Skip DOCX deliverable generation
- `--fill-missing` - Prompt for any missing required fields

## Workflow Steps

The coordinator runs a **7-step workflow**:

### 1. Process Client Brief
- Accepts file, dict, or ClientBrief object
- Parses with BriefParserAgent if needed
- Validates required fields
- Optionally prompts for missing information

### 2. Analyze Voice Samples (Optional)
- Converts sample texts to Post objects
- Runs VoiceAnalyzer to extract patterns
- Generates EnhancedVoiceGuide
- Used to inform content generation

### 3. Classify Client Type
- Uses ClientClassifier for keyword-based classification
- Determines: B2B_SAAS, AGENCY, COACH_CONSULTANT, CREATOR_FOUNDER, or UNKNOWN
- Returns confidence score (0.0-1.0)

### 4. Generate Content
- Selects appropriate templates based on client type
- Generates posts using ContentGeneratorAgent
- Async by default (5 concurrent API calls)
- Fallback to sync mode if configured

### 5. Run QA Validation
- Validates hooks, CTAs, length, headlines
- Generates quality score (0.0-1.0)
- Flags posts needing review
- Creates QAReport with all issues

### 6. Generate Deliverables
- Posts (TXT, JSON, Markdown, DOCX)
- Brand voice guides (basic + enhanced)
- Posting schedules (MD, CSV, iCalendar)
- Analytics trackers (CSV, Excel with formulas)
- QA report

### 7. Summary & Results
- Logs all generated files
- Shows output directory
- Returns dictionary of file paths

## Generated Files

A complete run generates **11+ deliverable files**:

### Posts
- `{client}_{timestamp}_deliverable.md` - Main deliverable (posts + metadata)
- `{client}_{timestamp}_posts.txt` - Plain text posts
- `{client}_{timestamp}_posts.json` - Structured JSON posts

### Voice Guides
- `{client}_{timestamp}_brand_voice.md` - Basic voice guide
- `{client}_{timestamp}_brand_voice_enhanced.md` - AI-analyzed patterns

### Schedules
- `{client}_{timestamp}_schedule.md` - Markdown calendar
- `{client}_{timestamp}_schedule.csv` - CSV import
- `{client}_{timestamp}_schedule.ics` - iCalendar (Google/Outlook)

### Analytics
- `{client}_{timestamp}_analytics_tracker.csv` - CSV tracker
- `{client}_{timestamp}_analytics_tracker.xlsx` - Excel with formulas

### Documents
- `{client}_{timestamp}_deliverable.docx` - Professional DOCX
- `{client}_{timestamp}_qa_report.md` - Quality report

## Voice Sample Analysis

### When to Use Voice Samples

Use voice samples when:
- Client has existing content you want to match
- You want to ensure tone consistency
- Client has a distinctive voice/style
- You need to extract specific patterns

### How Many Samples?

**Recommended: 3-10 samples**
- **Minimum 3** for pattern detection
- **5-7 ideal** for balanced analysis
- **10+ maximum** for comprehensive analysis

### What Makes a Good Sample?

Good voice samples should:
- Be representative of client's typical content
- Include varied post types (problem, solution, story, etc.)
- Show consistent voice/tone
- Be complete posts (not fragments)
- Ideally 150-300 words each

### Sample Preparation

```bash
# Create sample files
echo "First sample post text here..." > sample1.txt
echo "Second sample post text here..." > sample2.txt
echo "Third sample post text here..." > sample3.txt

# Run with samples
python run_jumpstart.py brief.txt --voice-samples sample1.txt sample2.txt sample3.txt
```

Or programmatically:

```python
voice_samples = [
    Path("sample1.txt").read_text(),
    Path("sample2.txt").read_text(),
    Path("sample3.txt").read_text(),
]

saved_files = await coordinator.run_complete_workflow(
    brief_input="brief.txt",
    voice_samples=voice_samples,
)
```

## Interactive Brief Builder

The interactive builder guides you through creating a complete client brief:

```bash
python run_jumpstart.py --interactive
```

### Builder Flow

1. **Company Name** - Client/company name
2. **Business Description** - What they do (1-2 sentences)
3. **Ideal Customer** - Who they serve (ICP)
4. **Main Problem Solved** - Key pain point addressed
5. **Pain Points** - Multiple customer pain points (one per line)
6. **Brand Tones** - Comma-separated tone preferences
   - Options: direct, approachable, witty, data_driven, empathetic, bold, thoughtful
7. **Key Phrases** - Taglines/catchphrases (one per line)
8. **Customer Questions** - Common questions (one per line)
9. **Platforms** - Comma-separated platforms
   - Options: linkedin, twitter, facebook, blog, email
10. **Posting Frequency** - e.g., "3-4x weekly", "Daily"
11. **Data Usage** - none, light, moderate, heavy
12. **Main CTA** - Primary call-to-action

### Example Interactive Session

```
Company/Client Name: TechStartup Solutions

Business Description (what they do): AI-powered project management for distributed teams

Ideal Customer Profile (who they serve): CTOs and Engineering Managers at 50-500 person tech companies

Main Problem Solved (what pain point): Remote teams struggle with project visibility and async collaboration

Customer Pain Points (enter one per line, empty line to finish):
  Pain point #1: Status updates take hours to compile
  Pain point #2: Context switching between 10+ tools
  Pain point #3: Timezone differences cause delays
  Pain point #4: <press enter>

Brand Personality Tones (select from: direct, approachable, witty, data_driven, empathetic, bold, thoughtful)
Enter tone preferences (comma-separated):
  Tones: direct, data_driven, approachable

Key Phrases/Taglines (enter one per line, empty line to finish):
  Phrase #1: Built for distributed teams
  Phrase #2: Real-time clarity, async-first
  Phrase #3: <press enter>

Common Customer Questions (enter one per line, empty line to finish):
  Question #1: How do you integrate with Slack/GitHub?
  Question #2: Can we try it without migrating from Jira?
  Question #3: <press enter>

Target Platforms (select from: linkedin, twitter, facebook, blog, email)
Enter platforms (comma-separated):
  Platforms: linkedin, twitter

Posting Frequency (e.g., '3-4x weekly', 'Daily'): 4x weekly

Data Usage Preference (none, light, moderate, heavy):
  Data usage: moderate

Main Call-to-Action (e.g., 'Book a demo', 'Sign up'): Book a demo

============================================================
BRIEF COMPLETE!
============================================================

Client: TechStartup Solutions
Platforms: linkedin, twitter
Tones: direct, data_driven, approachable
```

## Configuration

### Environment Variables

The coordinator respects all settings from `.env`:

```bash
# API Configuration
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Performance
PARALLEL_GENERATION=True
MAX_CONCURRENT_API_CALLS=5

# Quality Thresholds
MIN_POST_WORD_COUNT=75
OPTIMAL_POST_MIN_WORDS=150
OPTIMAL_POST_MAX_WORDS=250
MAX_POST_WORD_COUNT=350

# Paths
DEFAULT_OUTPUT_DIR=data/outputs

# Logging
DEBUG_MODE=False
LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from src.config import settings

# Override settings for this run
settings.PARALLEL_GENERATION = False
settings.MAX_CONCURRENT_API_CALLS = 3

# Run workflow
saved_files = await coordinator.run_complete_workflow(...)
```

## Error Handling

The coordinator handles errors gracefully:

### Missing Brief File
```
Error: Brief file not found: path/to/missing.txt
```

### Missing Required Fields
```
ValueError: Missing required fields: Business Description, Ideal Customer
Please provide these fields in your brief or use the interactive builder.
```

### API Errors
- **Rate Limits**: Automatically retries with exponential backoff
- **Connection Errors**: Retries up to 3 times
- **Generation Errors**: Creates placeholder posts to maintain count

### Voice Sample Errors
```
Warning: Voice sample not found: sample1.txt
Warning: No valid voice samples found
```
(Continues workflow without voice analysis)

## Performance

### Token Usage
- **Brief parsing**: ~500 tokens
- **Post generation**: ~300 tokens/post × 30 = 9,000 tokens
- **Total per client**: ~15,000 tokens (~$0.40-0.60)

### Timing (30 posts)
- **Async mode**: ~60-90 seconds
- **Sync mode**: ~240-300 seconds
- **Voice analysis**: +5-10 seconds (negligible)

### API Calls
- **Brief parsing**: 1 call
- **Post generation**: 30 calls (5 concurrent with async)
- **Total**: 31 API calls per run

## Best Practices

### 1. Start with Interactive Builder
For first-time users or new clients:
```bash
python run_jumpstart.py --interactive
```

### 2. Use Voice Samples When Available
If client has existing content:
```bash
python run_jumpstart.py brief.txt --voice-samples sample*.txt
```

### 3. Test with Fewer Posts
Before generating full 30 posts:
```bash
python run_jumpstart.py brief.txt --num-posts 5
```

### 4. Set Realistic Start Dates
Plan posting schedules in advance:
```bash
python run_jumpstart.py brief.txt --start-date 2025-12-15
```

### 5. Review QA Report
Always check the QA report for issues:
```
data/outputs/{Client}/{Client}_{timestamp}_qa_report.md
```

## Troubleshooting

### "Missing required fields" error
- Use `--interactive` flag or
- Use `--fill-missing` flag to prompt for fields

### "Brief file not found"
- Check file path is correct
- Use absolute path if relative doesn't work

### Voice samples not loading
- Check file paths exist
- Ensure files are UTF-8 encoded text
- Verify files contain actual post content

### Slow generation
- Check `PARALLEL_GENERATION=True` in .env
- Verify API key is valid
- Check network connection

### Low quality scores
- Provide voice samples for better tone matching
- Review and improve brief detail
- Check customer pain points are specific

## Examples

### Example 1: Complete Workflow with Voice Samples

```bash
# Prepare voice samples
cat > sample1.txt << 'EOF'
Your engineering team spends more time updating Jira tickets than coding.
Last week, your EM spent 4 hours on a status report that was outdated by the time
it hit the exec inbox. This is the distributed team paradox.
EOF

cat > sample2.txt << 'EOF'
83% of distributed engineering teams miss deadlines by 2.3 weeks on average.
The reason? Not lack of talent. Not scope creep. Information latency.
By the time you discover a blocker in standup, 2 days are already lost.
EOF

# Run workflow
python run_jumpstart.py \
    brief.txt \
    --voice-samples sample1.txt sample2.txt \
    --num-posts 30 \
    --platform linkedin \
    --start-date 2025-12-01
```

### Example 2: Quick Test Run

```bash
# Generate just 5 posts for testing
python run_jumpstart.py tests/fixtures/sample_brief.txt --num-posts 5 --no-docx
```

### Example 3: Interactive with Custom Platform

```bash
# Build brief interactively, then generate Twitter content
python run_jumpstart.py --interactive --platform twitter --num-posts 20
```

### Example 4: Programmatic with Voice Analysis

```python
import asyncio
from src.agents.coordinator import run_workflow
from pathlib import Path

async def main():
    # Load voice samples
    samples = [
        Path("samples/post1.txt").read_text(),
        Path("samples/post2.txt").read_text(),
        Path("samples/post3.txt").read_text(),
    ]

    # Run complete workflow
    files = await run_workflow(
        brief_input="briefs/client_brief.txt",
        voice_samples=samples,
        num_posts=30,
        include_analytics=True,
        include_docx=True,
    )

    print(f"Generated {len(files)} files")

asyncio.run(main())
```

## Summary

The **CoordinatorAgent** provides a unified, intelligent interface for content generation:

✅ **Flexible input**: Files, dicts, objects, or interactive
✅ **Voice analysis**: Optional sample analysis for tone matching
✅ **Smart validation**: Detects missing fields, prompts for info
✅ **Complete orchestration**: Brief → Posts → QA → Deliverables
✅ **Progress reporting**: Clear logging at each step
✅ **Error handling**: Graceful degradation on failures
✅ **Multi-format output**: 11+ deliverable files

**Get started in 3 commands:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run workflow
python run_jumpstart.py --interactive
```
