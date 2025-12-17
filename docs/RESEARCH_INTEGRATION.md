# Research Tools Integration Guide

## Overview

This guide shows how to integrate research tools into the 30-Day Content Jumpstart workflow for enhanced content quality and strategic alignment.

## Integration Approaches

### Approach 1: Pre-Generation Research (Recommended)
Run research tools before content generation to inform strategy and voice matching.

### Approach 2: Post-Generation Enhancement
Run research tools after initial content to refine and optimize.

### Approach 3: Hybrid Workflow
Combine pre and post-generation research for maximum impact.

---

## Complete Integration Workflow

### Step 1: Client Discovery (20 min)

**Traditional Workflow:**
```
Manual discovery call → Fill CLIENT_BRIEF_TEMPLATE → Start content creation
```

**Enhanced Workflow:**
```
Send CLIENT_BRIEF_TEMPLATE 24hrs before call
→ Pre-call research (Voice Analysis + Brand Archetype)
→ Discovery call with insights
→ Post-call strategic research (SEO + Competitive + Content Gap)
→ Content creation with full context
```

### Step 2: Pre-Call Research (Optional, 3-5 min)

```python
from src.research import VoiceAnalyzer, BrandArchetypeAnalyzer

# If client has existing content (blog, LinkedIn, etc.)
voice_analyzer = VoiceAnalyzer(project_id="acme_corp")
voice_result = voice_analyzer.execute({
    'business_description': '...',
    'target_audience': '...',
    'sample_content': [
        'https://blog.acme.com/post1',
        'https://www.linkedin.com/in/client/recent-activity',
        'https://blog.acme.com/post2'
    ]
})

# Quickly identify brand archetype
archetype_analyzer = BrandArchetypeAnalyzer(project_id="acme_corp")
archetype_result = archetype_analyzer.execute({
    'business_description': '...',
    'target_audience': '...',
    'value_proposition': '...'
})

# Use in discovery call:
# "I analyzed your existing content and noticed you have a [SAGE] archetype
# with very [ANALYTICAL] tone. Let's talk about whether you want to maintain
# that or shift toward [X]..."
```

**Benefits:**
- Show up to discovery call with insights (credibility boost)
- Guide conversation toward strategic topics
- Identify voice mismatches early
- Demonstrate value before contract signed

### Step 3: Post-Call Strategic Research (5-10 min)

After discovery call, run comprehensive research suite:

```python
from src.research import (
    SEOKeywordResearcher,
    CompetitiveAnalyzer,
    MarketTrendsResearcher,
    ContentGapAnalyzer
)

project_id = "acme_corp"

# Inputs from discovery call
discovery_inputs = {
    'business_description': '...',  # From CLIENT_BRIEF
    'target_audience': '...',       # From CLIENT_BRIEF
    'business_name': 'Acme Corp',
    'industry': 'B2B SaaS - Customer Success'
}

# 1. SEO Keyword Research (3-4 min)
seo_researcher = SEOKeywordResearcher(project_id=project_id)
seo_result = seo_researcher.execute({
    **discovery_inputs,
    'competitor_domains': ['competitor1.com', 'competitor2.com'],
    'focus_topics': ['churn prediction', 'customer retention', 'CS analytics']
})

# 2. Competitive Analysis (2-3 min)
competitive_analyzer = CompetitiveAnalyzer(project_id=project_id)
competitive_result = competitive_analyzer.execute({
    **discovery_inputs,
    'competitors': ['ChurnZero', 'Gainsight', 'Totango'],
    'analysis_focus': 'content'
})

# 3. Market Trends (2-3 min)
trends_researcher = MarketTrendsResearcher(project_id=project_id)
trends_result = trends_researcher.execute({
    **discovery_inputs,
    'time_horizon': '90days'
})

# 4. Content Gap Analysis (3-4 min)
gap_analyzer = ContentGapAnalyzer(project_id=project_id)
gap_result = gap_analyzer.execute({
    **discovery_inputs,
    'current_content_topics': [
        'Churn prediction basics',
        'Customer health scoring',
        'Retention strategies'
    ],
    'competitors': ['ChurnZero', 'Gainsight', 'Totango']
})

print(f"✅ Research complete!")
print(f"Total time: {sum([
    seo_result.metadata['duration_seconds'],
    competitive_result.metadata['duration_seconds'],
    trends_result.metadata['duration_seconds'],
    gap_result.metadata['duration_seconds']
]):.1f}s")
print(f"Total value: ${sum([
    seo_result.metadata['price'],
    competitive_result.metadata['price'],
    trends_result.metadata['price'],
    gap_result.metadata['price']
])}")
```

**Outputs:**
- 4 JSON files with structured data
- 4 Markdown reports for client delivery
- 4 Text summaries for quick review

**Time Investment:** 10-15 minutes
**Value Delivered:** $1,800 in research
**Client Perception:** Strategic partner, not order-taker

### Step 4: Research-Informed Content Generation

Use research outputs to inform content creation:

```python
import json
from pathlib import Path
from src.agents.content_generator import ContentGenerator

project_id = "acme_corp"
research_dir = Path(f"data/research")

# Load all research data
def load_research_data(project_id: str) -> dict:
    """Load all available research for project"""
    research = {}

    # Voice analysis
    voice_path = research_dir / "voice_analysis" / project_id / "voice_analysis.json"
    if voice_path.exists():
        with open(voice_path) as f:
            research['voice'] = json.load(f)

    # Brand archetype
    archetype_path = research_dir / "brand_archetype" / project_id / "brand_archetype.json"
    if archetype_path.exists():
        with open(archetype_path) as f:
            research['archetype'] = json.load(f)

    # SEO keywords
    seo_path = research_dir / "seo_keyword_research" / project_id / "seo_keywords.json"
    if seo_path.exists():
        with open(seo_path) as f:
            research['seo'] = json.load(f)

    # Competitive analysis
    competitive_path = research_dir / "competitive_analysis" / project_id / "competitive_analysis.json"
    if competitive_path.exists():
        with open(competitive_path) as f:
            research['competitive'] = json.load(f)

    # Market trends
    trends_path = research_dir / "market_trends_research" / project_id / "market_trends.json"
    if trends_path.exists():
        with open(trends_path) as f:
            research['trends'] = json.load(f)

    # Content gaps
    gaps_path = research_dir / "content_gap_analysis" / project_id / "content_gaps.json"
    if gaps_path.exists():
        with open(gaps_path) as f:
            research['gaps'] = json.load(f)

    return research

# Load research
research = load_research_data(project_id)

# Initialize content generator with research context
generator = ContentGenerator(
    project_id=project_id,
    voice_profile=research.get('voice', {}).get('voice_profile'),
    brand_archetype=research.get('archetype', {}).get('primary_archetype'),
    target_keywords=research.get('seo', {}).get('primary_keywords', []),
    competitor_insights=research.get('competitive', {}).get('positioning_map', []),
    trending_topics=research.get('trends', {}).get('emerging_trends', []),
    content_gaps=research.get('gaps', {}).get('critical_gaps', [])
)

# Generate 30 posts informed by research
posts = generator.generate_posts(
    num_posts=30,
    use_research=True
)

print(f"✅ Generated {len(posts)} research-backed posts")
```

**How Research Informs Generation:**

1. **Voice Profile** → Tone, sentence structure, vocabulary
2. **Brand Archetype** → Messaging themes, content angles
3. **SEO Keywords** → Topics to cover, search-friendly phrasing
4. **Competitive Analysis** → Differentiation angles, unique perspectives
5. **Market Trends** → Timely topics, thought leadership angles
6. **Content Gaps** → High-value topics competitors are missing

### Step 5: Quality Assurance with Research

Validate generated content against research findings:

```python
from src.agents.qa_agent import QAAgent

qa_agent = QAAgent(research_context=research)

for post in posts:
    qa_result = qa_agent.validate_post(post)

    # Check voice match
    if qa_result.voice_match_score < 0.8:
        print(f"⚠️  Post {post.id}: Voice mismatch")

    # Check keyword usage
    if not qa_result.uses_target_keywords:
        print(f"⚠️  Post {post.id}: Missing target keywords")

    # Check differentiation
    if qa_result.sounds_generic:
        print(f"⚠️  Post {post.id}: Too similar to competitors")

    # Check trend alignment
    if qa_result.trending_topic_opportunity:
        print(f"💡 Post {post.id}: Could leverage trend '{qa_result.trending_topic}'")
```

### Step 6: Client Delivery Package

Package research reports with content deliverable:

```
Acme Corp - Content Jumpstart Deliverable/
├── 00_Research_Reports/
│   ├── Voice_Analysis_Report.md
│   ├── Brand_Archetype_Assessment.md
│   ├── SEO_Keyword_Research.md
│   ├── Competitive_Analysis.md
│   ├── Market_Trends_Research.md
│   └── Content_Gap_Analysis.md
│
├── 01_Strategic_Summary.md          # Executive summary of all research
├── 02_Content_Strategy.md           # How research informed content
├── 03_30_Posts.docx                 # The actual posts
└── 04_Usage_Guide.md                # How to use research + posts
```

**Client Email Template:**

```
Subject: Your Content Jumpstart Deliverable + Strategic Research

Hi [Client],

Attached is your complete Content Jumpstart package with 30 ready-to-post pieces.

What's included:

📊 STRATEGIC RESEARCH ($1,800 value)
Before writing a single word, I conducted comprehensive research:
- Voice Analysis: Analyzed your existing content to match your authentic voice
- Brand Archetype: Identified your "Sage" archetype and messaging framework
- SEO Research: Found 47 target keywords with high search volume
- Competitive Analysis: Mapped your positioning vs. ChurnZero, Gainsight, Totango
- Market Trends: Identified 12 emerging trends in customer success space
- Content Gap Analysis: Discovered 23 opportunities competitors are missing

📝 30 POSTS ($1,800 value)
Every post is informed by the research above:
- Written in your analytical, data-driven voice
- Covers high-value keywords with low competition
- Differentiates from competitor messaging
- Leverages emerging trends for thought leadership
- Fills gaps in your current content strategy

📖 HOW TO USE
1. Review research reports first (15-20 min)
2. Read Strategic Summary to understand the approach
3. Review posts with research context in mind
4. Post 3-4x per week over next 6-8 weeks

💡 NEXT STEPS
- Review everything by [DATE]
- Send any revisions by [DATE] (up to 5 changes included)
- I'll deliver revised posts within 48 hours
- Schedule follow-up call to discuss performance in 2 weeks

Questions? Just reply to this email.

Looking forward to seeing these posts drive engagement!

[Your Name]
```

---

## Integration Patterns

### Pattern 1: Foundation Research (Minimum)

**Tools:** Voice Analysis + Brand Archetype
**Time:** 3-5 minutes
**Value:** $700
**Best for:** Clients with existing content, tight timelines

```python
# Quick foundation research
foundation_tools = [
    (VoiceAnalyzer, {'sample_content': [...]}),
    (BrandArchetypeAnalyzer, {'value_proposition': '...'})
]

for ToolClass, extra_inputs in foundation_tools:
    tool = ToolClass(project_id=project_id)
    result = tool.execute({**base_inputs, **extra_inputs})
```

**Use Case:** Ensure voice and brand consistency even on rushed projects.

### Pattern 2: SEO-Focused Research

**Tools:** SEO Keyword Research + Content Gap Analysis
**Time:** 6-8 minutes
**Value:** $900
**Best for:** Clients prioritizing organic reach

```python
# SEO research suite
seo_tools = [
    (SEOKeywordResearcher, {'competitor_domains': [...]}),
    (ContentGapAnalyzer, {'current_content_topics': [...]})
]
```

**Use Case:** B2B companies with strong SEO goals, content marketers.

### Pattern 3: Competitive Intelligence

**Tools:** Competitive Analysis + Market Trends + Content Gap
**Time:** 7-10 minutes
**Value:** $1,400
**Best for:** Crowded markets, startups positioning against incumbents

```python
# Competitive research suite
competitive_tools = [
    (CompetitiveAnalyzer, {'competitors': [...]}),
    (MarketTrendsResearcher, {'time_horizon': '90days'}),
    (ContentGapAnalyzer, {'competitors': [...]})
]
```

**Use Case:** SaaS companies competing with established players.

### Pattern 4: Complete Research Package (Premium)

**Tools:** All 6 tools
**Time:** 15-20 minutes
**Value:** $2,500
**Best for:** Premium clients, strategic engagements, thought leadership

```python
# Complete research suite
all_tools = [
    (VoiceAnalyzer, {'sample_content': [...]}),
    (BrandArchetypeAnalyzer, {'value_proposition': '...'}),
    (SEOKeywordResearcher, {'competitor_domains': [...]}),
    (CompetitiveAnalyzer, {'competitors': [...]}),
    (MarketTrendsResearcher, {'time_horizon': '90days'}),
    (ContentGapAnalyzer, {'current_content_topics': [...]})
]
```

**Use Case:** Clients who value strategic foundation, willing to invest in research.

---

## Advanced Integration Techniques

### Technique 1: Research-Driven Template Selection

Use research to intelligently select post templates:

```python
def select_templates_from_research(research: dict) -> List[str]:
    """Select templates based on research insights"""
    selected_templates = []

    # Voice analysis suggests analytical content
    if research['voice']['voice_profile']['tone'] == 'analytical':
        selected_templates.extend([
            'statistic_insight',      # Template 2
            'myth_busting',           # Template 7
            'comparison'              # Template 10
        ])

    # Brand archetype suggests content angles
    archetype = research['archetype']['primary_archetype']['name']
    if archetype == 'Sage':
        selected_templates.extend([
            'how_to',                # Template 9
            'future_thinking',       # Template 13
            'reader_q_response'      # Template 14
        ])
    elif archetype == 'Hero':
        selected_templates.extend([
            'personal_story',        # Template 6
            'milestone',             # Template 15
            'what_changed'           # Template 4
        ])

    # SEO keywords suggest informational content
    top_keywords = research['seo']['primary_keywords']
    informational_keywords = [
        kw for kw in top_keywords
        if kw['search_intent'] == 'Informational'
    ]
    if len(informational_keywords) > 5:
        selected_templates.extend([
            'problem_recognition',   # Template 1
            'how_to',                # Template 9
            'myth_busting'           # Template 7
        ])

    # Trending topics suggest thought leadership
    emerging_trends = research['trends']['emerging_trends']
    if len(emerging_trends) > 3:
        selected_templates.extend([
            'future_thinking',       # Template 13
            'contrarian_take',       # Template 3
            'what_changed'           # Template 4
        ])

    # Content gaps suggest specific formats
    format_gaps = research['gaps']['format_gaps']
    for gap in format_gaps:
        if gap['format_name'] == 'How-to guide':
            selected_templates.append('how_to')
        elif gap['format_name'] == 'Comparison':
            selected_templates.append('comparison')

    return list(set(selected_templates))  # Remove duplicates

# Use in content generation
research = load_research_data(project_id)
recommended_templates = select_templates_from_research(research)

print(f"📋 Recommended templates: {recommended_templates}")
```

### Technique 2: Research-Informed Bracket Filling

Automatically fill template brackets using research data:

```python
def fill_template_with_research(template: str, research: dict) -> str:
    """Auto-fill template brackets using research"""

    # Replace [AUDIENCE TYPE] with target audience
    target_audience = research.get('archetype', {}).get('target_audience', '')
    template = template.replace('[AUDIENCE TYPE]', target_audience)

    # Replace [PROBLEM] with top pain point from competitive analysis
    pain_points = research.get('competitive', {}).get('customer_pain_points', [])
    if pain_points:
        template = template.replace('[PROBLEM]', pain_points[0])

    # Replace [STATISTIC] with relevant data from trends
    trends = research.get('trends', {}).get('emerging_trends', [])
    if trends and '[STATISTIC]' in template:
        trend_data = trends[0].get('supporting_data', [])
        if trend_data:
            template = template.replace('[STATISTIC]', trend_data[0])

    # Replace [COMPETITOR] with top competitor
    competitors = research.get('competitive', {}).get('competitors', [])
    if competitors:
        template = template.replace('[COMPETITOR]', competitors[0]['competitor_name'])

    # Replace [KEYWORD] with primary keyword
    keywords = research.get('seo', {}).get('primary_keywords', [])
    if keywords:
        template = template.replace('[KEYWORD]', keywords[0]['keyword'])

    return template

# Example usage
template = """
Most [AUDIENCE TYPE] struggle with [PROBLEM].

Here's why:
- [REASON 1]
- [REASON 2]
- [REASON 3]

The solution? [SOLUTION]

(Unlike [COMPETITOR] who [THEIR APPROACH], we [OUR APPROACH])
"""

filled_template = fill_template_with_research(template, research)
```

### Technique 3: Real-Time Research Integration

Run lightweight research during content generation:

```python
class ResearchAwareContentGenerator(ContentGenerator):
    """Content generator with real-time research capabilities"""

    def generate_post(self, template: str, topic: str) -> Post:
        """Generate post with on-the-fly research"""

        # Quick keyword check
        if self._should_optimize_for_seo(topic):
            keywords = self._quick_keyword_research(topic)
            template = self._inject_keywords(template, keywords)

        # Quick trend check
        if self._should_check_trends(topic):
            trends = self._quick_trend_check(topic)
            if trends:
                template = self._add_trend_context(template, trends[0])

        # Generate post
        post = super().generate_post(template, topic)

        # Validate against research
        if not self._matches_voice_profile(post):
            post = self._adjust_voice(post)

        return post
```

---

## CLI Integration

### Command-Line Research Runner

```bash
# research_runner.py
python research_runner.py \
  --project-id acme_corp \
  --tools voice,archetype,seo,competitive,trends,gaps \
  --brief-file data/briefs/acme_corp.md \
  --output-dir data/research
```

### Batch Processing

```bash
# Process multiple clients
python research_batch.py \
  --clients-file clients.csv \
  --tools foundation \  # voice + archetype
  --parallel 3
```

---

## Troubleshooting Integration Issues

### Issue 1: Research Data Not Loading

**Problem:** `FileNotFoundError` when loading research JSON

**Solution:**
```python
def safe_load_research(project_id: str, tool_name: str) -> dict:
    """Safely load research with fallback"""
    try:
        path = Path(f"data/research/{tool_name}/{project_id}/{tool_name}.json")
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Research not found: {tool_name} for {project_id}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}
```

### Issue 2: Conflicting Research Insights

**Problem:** Voice analysis suggests "casual" but archetype suggests "professional"

**Solution:**
```python
def reconcile_research_conflicts(research: dict) -> dict:
    """Resolve conflicts in research data"""
    voice_tone = research['voice']['voice_profile']['tone']
    archetype = research['archetype']['primary_archetype']['name']

    # Archetype overrides voice for B2B
    if research['industry'].startswith('B2B'):
        if archetype in ['Sage', 'Ruler']:
            # Professional archetypes override casual voice
            research['voice']['voice_profile']['tone'] = 'professional'

    return research
```

### Issue 3: Research Overwhelming Content

**Problem:** Too much research data, unsure what to prioritize

**Solution:**
```python
def prioritize_research_insights(research: dict) -> dict:
    """Extract highest-priority insights"""
    return {
        'voice': research['voice']['voice_profile']['tone'],
        'archetype': research['archetype']['primary_archetype']['name'],
        'top_5_keywords': research['seo']['primary_keywords'][:5],
        'top_3_trends': research['trends']['emerging_trends'][:3],
        'top_5_gaps': research['gaps']['critical_gaps'][:5],
        'key_differentiator': research['competitive']['competitive_advantages'][0]
    }
```

---

## Performance Optimization

### Caching Research Results

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_research_data(project_id: str, tool_name: str) -> dict:
    """Cache research data for fast access"""
    return safe_load_research(project_id, tool_name)

# Use cached data
research = get_research_data("acme_corp", "voice_analysis")
```

### Parallel Research Execution

```python
import concurrent.futures

def run_research_parallel(project_id: str, tools: List[tuple]) -> dict:
    """Run multiple research tools in parallel"""

    def execute_tool(tool_config):
        ToolClass, inputs = tool_config
        tool = ToolClass(project_id=project_id)
        return tool.execute(inputs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(execute_tool, tc) for tc in tools]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    return {r.tool_name: r for r in results}

# Run 6 tools in ~5-7 minutes instead of 15-20
results = run_research_parallel(project_id, all_tools)
```

---

## Best Practices

### 1. Always Run Foundation Research
Never skip Voice Analysis and Brand Archetype. These are the baseline for quality.

### 2. Document Research Decisions
Track which research influenced which content decisions.

```python
post.metadata['research_informed_by'] = {
    'voice': 'analytical tone from voice analysis',
    'keyword': 'churn prediction (primary keyword)',
    'trend': 'AI in customer success (emerging trend)',
    'gap': 'predictive analytics deep-dive (critical gap)'
}
```

### 3. Use Research for Client Education
Share research reports to show your strategic thinking, not just execution.

### 4. Update Research Periodically
Re-run research every 90 days to capture market changes.

### 5. A/B Test Research Impact
Compare research-backed content vs. non-research content to measure ROI.

---

## Future Enhancements

- [ ] Auto-detect which tools to run based on client brief
- [ ] Research conflict resolution engine
- [ ] One-click "research to content" pipeline
- [ ] Research impact analytics dashboard
- [ ] Client-facing research recommendation engine

---

**Last Updated:** December 2025
**Version:** 1.0.0
