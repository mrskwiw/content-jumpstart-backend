# Research Tools Documentation

## Overview

The 30-Day Content Jumpstart system includes 12 automated research add-on tools that provide deep client intelligence before content creation begins. These tools transform the discovery process from manual research to AI-powered analysis, delivering professional reports in JSON, Markdown, and Text formats.

**Total Available Tools:** 12 ($300-$600 each)
**Total Market Value:** $4,900 in research services

## Value Proposition

### For Content Creators
- **Time Savings:** What takes 3-5 hours manually now takes 3-5 minutes
- **Consistency:** Every client gets the same depth of analysis
- **Professionalism:** Deliver branded research reports as premium deliverables
- **Upsell Opportunity:** Add $300-$600 to each engagement

### For Clients
- **Strategic Foundation:** Content backed by research, not guesswork
- **Competitive Intelligence:** See how they stack up against competitors
- **Data-Driven Decisions:** Real search volumes, trends, and opportunities
- **Actionable Insights:** Specific recommendations, not generic advice

## Tool Catalog

### Client Foundation Tools ($700 Total)

#### 1. Voice Analysis Tool ($400)
**Purpose:** Extract writing patterns from client's existing content

**Inputs:**
- Business description
- Target audience
- Sample content (URLs or text, 3-10 samples)

**Outputs:**
- Voice profile (tone, style, personality traits)
- Writing patterns (sentence structure, vocabulary, formatting)
- Content characteristics (readability, complexity, emotional tone)
- Recommendation engine (what works, what to avoid)

**Use Case:** Before writing any content, analyze client's blog posts, LinkedIn content, or emails to match their authentic voice.

**Test Command:**
```bash
python -m pytest tests/research/test_voice_analysis.py::test_voice_analysis_basic -v
```

#### 2. Brand Archetype Assessment ($300)
**Purpose:** Identify brand personality and messaging framework

**Inputs:**
- Business description
- Target audience
- Value proposition
- Current messaging (optional)

**Outputs:**
- Primary archetype (Hero, Sage, Explorer, etc.)
- Secondary archetype influence
- Archetype-specific messaging guidelines
- Content angle recommendations
- Competitor archetype comparison

**Use Case:** Establish consistent brand personality before creating content. Ensures all 30 posts align with a coherent brand identity.

**Test Command:**
```bash
python -m pytest tests/research/test_brand_archetype.py::test_brand_archetype_basic -v
```

---

### SEO & Competition Tools ($1,400 Total)

#### 3. SEO Keyword Research Tool ($400)
**Purpose:** Discover target keywords and search opportunities

**Inputs:**
- Business description
- Target audience
- Industry/vertical
- Competitor domains (optional, max 3)

**Outputs:**
- 30-50 target keywords with metrics
- Search intent classification (informational, commercial, transactional)
- Keyword difficulty scores
- Content topic recommendations
- Seasonal trends and timing

**Use Case:** Identify which topics to cover in the 30 posts to maximize organic reach. Helps prioritize high-value, low-competition keywords.

**Test Command:**
```bash
python -m pytest tests/research/test_seo_keyword_research.py::test_seo_keyword_research_basic -v
```

#### 4. Competitive Analysis Tool ($500)
**Purpose:** Research competitors and identify positioning gaps

**Inputs:**
- Business description
- Target audience
- Competitor names (1-5 competitors)
- Analysis focus (optional: content, pricing, features, positioning)

**Outputs:**
- Competitor positioning analysis
- Content strategy comparison
- Messaging differentiation
- Competitive advantages to emphasize
- Weaknesses to avoid

**Use Case:** Understand the competitive landscape before creating content. Identify angles competitors aren't covering.

**Test Command:**
```bash
python -m pytest tests/research/test_competitive_analysis.py::test_competitive_analysis_basic -v
```

#### 5. Content Gap Analysis Tool ($500)
**Purpose:** Identify content opportunities competitors are missing

**Inputs:**
- Business description
- Target audience
- Current content topics (list)
- Competitors (optional, max 5)

**Outputs:**
- 15-25 specific content gaps prioritized by impact
- Gap classification (Topic, Format, Depth, Freshness, Stage, Audience Segment)
- Priority levels (Critical, High, Medium, Low)
- Competitor content analysis
- Buyer journey gaps (Awareness, Consideration, Decision)
- Format gaps (Blog, Video, Checklist, Template, etc.)
- Quick wins (high impact, low effort)
- 90-day content roadmap

**Use Case:** Discover untapped content opportunities. Find topics with high search volume but low competition.

**Test Command:**
```bash
python -m pytest tests/research/test_content_gap_analysis.py::test_content_gap_analysis_basic -v
```

---

### Market Intelligence Tools ($400 Total)

#### 6. Market Trends Research Tool ($400)
**Purpose:** Discover trending topics and emerging opportunities

**Inputs:**
- Business description
- Target audience
- Industry/vertical
- Time horizon (optional: 30/60/90 days)

**Outputs:**
- 10-15 emerging trends with momentum scores
- Trend classification (Emerging, Growing, Peaking, Declining)
- Social media conversation analysis
- News coverage and media mentions
- Content angle recommendations
- Timing recommendations

**Use Case:** Create timely, relevant content that rides current trends. Position client as thought leader on emerging topics.

**Test Command:**
```bash
python -m pytest tests/research/test_market_trends_research.py::test_market_trends_research_basic -v
```

---

### Strategy & Planning Tools ($1,300 Total)

#### 7. Content Audit Tool ($400)
**Purpose:** Analyze existing content performance and opportunities

**Status:** Not yet implemented

**Inputs:**
- Existing content inventory (URLs or text)
- Performance metrics (optional: views, engagement, conversions)
- Content goals

**Outputs:**
- Content performance analysis
- Gaps in current coverage
- Refresh/update recommendations
- Repurposing opportunities
- Archive/consolidate recommendations

**Use Case:** Before creating new content, understand what's already working and what needs improvement.

#### 8. Platform Strategy Tool ($300)
**Purpose:** Recommend optimal platform mix for distribution

**Status:** Not yet implemented

**Inputs:**
- Target audience demographics
- Content types/formats
- Business goals (awareness, leads, sales)
- Current platform presence

**Outputs:**
- Platform prioritization (LinkedIn, Twitter, Blog, Email, etc.)
- Platform-specific content recommendations
- Posting frequency recommendations
- Cross-promotion strategies

**Use Case:** Determine where to publish the 30 posts for maximum impact.

#### 9. Content Calendar Strategy Tool ($300)
**Purpose:** Create strategic 90-day content calendar

**Status:** Not yet implemented

**Inputs:**
- Content topics (from other research tools)
- Business calendar (launches, events, seasons)
- Posting frequency goals
- Platform mix

**Outputs:**
- 90-day editorial calendar
- Topic clustering and themes
- Optimal posting schedule
- Campaign planning
- Content mix recommendations

**Use Case:** Transform 30 posts into a strategic publishing plan.

#### 10. Audience Research Tool ($500)
**Purpose:** Deep-dive into target audience demographics and psychographics

**Status:** Not yet implemented

**Inputs:**
- Target audience description
- Industry/vertical
- Current customer data (optional)

**Outputs:**
- Audience personas (2-4 detailed profiles)
- Demographics and firmographics
- Pain points and challenges
- Content consumption habits
- Preferred platforms and formats
- Buying triggers and objections

**Use Case:** Understand who you're writing for before creating content.

---

### Workshop Assistants ($1,100 Total)

#### 11. ICP Development Workshop ($600)
**Purpose:** Facilitate ideal customer profile definition through guided conversation

**Status:** Not yet implemented (partial automation)

**Format:** Interactive conversation, not fully automated

**Outputs:**
- Comprehensive ICP document
- Targeting criteria
- Messaging framework
- Content priorities

**Use Case:** Run a 45-60 minute discovery session with client to define their ideal customer.

#### 12. Story Mining Interview ($500)
**Purpose:** Extract customer success stories and case study material

**Status:** Not yet implemented (partial automation)

**Format:** Interactive interview, not fully automated

**Outputs:**
- 3-5 documented success stories
- Customer journey maps
- Quantified results
- Testimonial-ready quotes

**Use Case:** Gather real stories to make content authentic and compelling.

---

## Implementation Status

### ✅ Completed Tools (6/12) - $2,500 Value
1. ✅ Voice Analysis Tool ($400)
2. ✅ Brand Archetype Assessment Tool ($300)
3. ✅ SEO Keyword Research Tool ($400)
4. ✅ Competitive Analysis Tool ($500)
5. ✅ Market Trends Research Tool ($400)
6. ✅ Content Gap Analysis Tool ($500)

### ⏳ Remaining Tools (6/12) - $2,400 Value
7. ⏳ Content Audit Tool ($400)
8. ⏳ Platform Strategy Tool ($300)
9. ⏳ Content Calendar Strategy Tool ($300)
10. ⏳ Audience Research Tool ($500)
11. ⏳ ICP Development Workshop ($600)
12. ⏳ Story Mining Interview ($500)

---

## Quick Start Guide

### Basic Usage

All research tools follow the same execution pattern:

```python
from src.research import VoiceAnalyzer

# Initialize tool with project ID
analyzer = VoiceAnalyzer(project_id="client_acme_corp")

# Execute analysis
result = analyzer.execute({
    'business_description': 'We help B2B SaaS companies...',
    'target_audience': 'Marketing leaders, CMOs, growth teams',
    'sample_content': ['https://blog.acme.com/post1', 'https://blog.acme.com/post2']
})

# Check results
if result.success:
    print(f"✅ Analysis complete!")
    print(f"Duration: {result.metadata['duration_seconds']:.1f}s")
    print(f"Price: ${result.metadata['price']}")
    print(f"Outputs: {result.outputs.keys()}")
else:
    print(f"❌ Error: {result.error}")
```

### Output Formats

Every tool generates 3 output formats:

1. **JSON** - Machine-readable, structured data for programmatic use
2. **Markdown** - Human-readable report for client delivery
3. **Text** - Plain text summary for quick review

### File Locations

```
data/research/{tool_name}/{project_id}/
├── {tool_name}_analysis.json      # Structured data
├── {tool_name}_report.md          # Client-ready report
└── {tool_name}_summary.txt        # Quick summary
```

---

## Pricing Strategy

### Package Bundles

**Foundation Package ($650)** - Save $50
- Voice Analysis ($400)
- Brand Archetype Assessment ($300)

**SEO Package ($1,300)** - Save $100
- SEO Keyword Research ($400)
- Competitive Analysis ($500)
- Content Gap Analysis ($500)

**Complete Research Package ($2,400)** - Save $300
- All 6 completed tools
- Foundation + SEO + Market Trends

**Ultimate Package ($4,500)** - Save $400
- All 12 tools when complete

### Add-On Pricing

Offer research tools as pre-content add-ons:

**Basic Jumpstart:** $1,800 (30 posts)
**+ Foundation Research:** $2,450 (30 posts + Voice + Archetype) - Save $50
**+ SEO Research:** $3,100 (30 posts + Foundation + SEO Package) - Save $150
**+ Complete Research:** $4,200 (30 posts + All 6 tools) - Save $300

---

## Common Use Cases

### Use Case 1: New Client Onboarding
**Recommended Tools:**
1. Voice Analysis ($400) - Match their existing content
2. Brand Archetype Assessment ($300) - Establish brand personality
3. SEO Keyword Research ($400) - Identify target topics

**Total:** $1,100 | **Time Saved:** 8-10 hours | **Value Delivered:** Strategic foundation document

### Use Case 2: Competitive Positioning
**Recommended Tools:**
1. Competitive Analysis ($500) - Understand landscape
2. Content Gap Analysis ($500) - Find opportunities
3. Market Trends Research ($400) - Ride emerging trends

**Total:** $1,400 | **Time Saved:** 10-12 hours | **Value Delivered:** Competitive strategy report

### Use Case 3: Content Strategy Refresh
**Recommended Tools:**
1. Content Audit ($400) - Assess current content
2. Content Gap Analysis ($500) - Identify opportunities
3. Content Calendar Strategy ($300) - Plan next 90 days

**Total:** $1,200 | **Time Saved:** 6-8 hours | **Value Delivered:** 90-day content roadmap

---

## Integration with Main Pipeline

Research tools integrate seamlessly with the content generation pipeline:

```python
from src.research import VoiceAnalyzer, BrandArchetypeAnalyzer, SEOKeywordResearcher
from src.agents.content_generator import ContentGenerator

# Step 1: Run research
voice_result = VoiceAnalyzer(project_id="acme").execute({...})
archetype_result = BrandArchetypeAnalyzer(project_id="acme").execute({...})
seo_result = SEOKeywordResearcher(project_id="acme").execute({...})

# Step 2: Load research into content generator
generator = ContentGenerator(
    voice_profile=voice_result.outputs['json'],
    brand_archetype=archetype_result.outputs['json'],
    target_keywords=seo_result.outputs['json']
)

# Step 3: Generate content
posts = generator.generate_posts(num_posts=30)
```

---

## Testing

### Run All Research Tool Tests

```bash
# All tests
pytest tests/research/ -v

# Specific tool
pytest tests/research/test_voice_analysis.py -v

# With coverage
pytest tests/research/ --cov=src/research --cov-report=html
```

### Expected Test Duration

| Tool | Test Duration | Notes |
|------|--------------|-------|
| Voice Analysis | 2-3 min | Analyzes 3-5 content samples |
| Brand Archetype | 1-2 min | Single analysis request |
| SEO Keyword Research | 3-4 min | 7-step process |
| Competitive Analysis | 2-3 min | Analyzes 3 competitors |
| Market Trends Research | 2-3 min | Trend discovery + analysis |
| Content Gap Analysis | 3-4 min | 10-step comprehensive analysis |

---

## Best Practices

### 1. Run Foundation Tools First
Always start with Voice Analysis and Brand Archetype before creating content. These establish the baseline personality and tone.

### 2. Bundle for Value
Offer research packages, not individual tools. Clients perceive more value in "Complete Research Package" vs. à la carte.

### 3. Use Research to Differentiate
Most content creators skip research. Use these tools to justify premium pricing and demonstrate expertise.

### 4. Deliver Research Separately
Send research reports 24-48 hours before delivering content. This builds anticipation and shows your process.

### 5. White-Label for Agencies
Agency clients can rebrand research reports and resell at 3-5x markup.

---

## Troubleshooting

### Common Issues

**Issue:** `ValueError: Missing required input`
**Solution:** Check that all required inputs are provided. Use `analyzer.validate_inputs(inputs)` to test.

**Issue:** `anthropic.RateLimitError`
**Solution:** Add delay between API calls or reduce parallel tool execution.

**Issue:** Output files not generated
**Solution:** Check `data/research/` directory permissions. Ensure `project_id` is valid.

**Issue:** Test timeouts
**Solution:** Increase pytest timeout: `pytest --timeout=600 tests/research/`

---

## API Keys Required

Research tools require:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
```

Using Claude 3.5 Sonnet for all analysis tasks.

---

## Future Enhancements

### Planned Features
- [ ] Batch processing (run multiple tools in parallel)
- [ ] Research dashboard UI
- [ ] Client-facing report templates
- [ ] Export to PowerPoint/PDF
- [ ] Multi-language support
- [ ] Custom report branding
- [ ] API endpoints for integration
- [ ] Scheduled research refresh (monthly updates)

### Advanced Integrations
- [ ] CRM integration (HubSpot, Salesforce)
- [ ] Analytics integration (Google Analytics, LinkedIn Analytics)
- [ ] Social listening tools (Brandwatch, Mention)
- [ ] SEO tools (Ahrefs, SEMrush API)

---

## Support & Documentation

- **Technical Docs:** See `docs/RESEARCH_API.md` for API reference
- **Integration Guide:** See `docs/RESEARCH_INTEGRATION.md`
- **GitHub Issues:** Report bugs or request features
- **Tests:** `tests/research/` for usage examples

---

## License & Usage

These research tools are part of the 30-Day Content Jumpstart system. For commercial use, white-labeling, or resale, contact the author.

**Last Updated:** December 2025
**Version:** 1.0.0
**Implemented Tools:** 6/12
