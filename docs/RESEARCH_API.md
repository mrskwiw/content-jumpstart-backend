# Research Tools API Reference

## Overview

This document provides technical API documentation for all research tools in the 30-Day Content Jumpstart system.

## Base Architecture

All research tools inherit from the `ResearchTool` base class, providing consistent interface and execution flow.

### ResearchTool Base Class

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ResearchTool(ABC):
    """Base class for all research tools"""

    def __init__(self, project_id: str, output_dir: Path = None):
        """
        Initialize research tool

        Args:
            project_id: Unique identifier for client project
            output_dir: Optional custom output directory
        """
        self.project_id = project_id
        self.output_dir = output_dir or self._default_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name (e.g., 'voice_analysis')"""
        pass

    @property
    @abstractmethod
    def price(self) -> int:
        """Tool price in USD"""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs"""
        pass

    @abstractmethod
    def run_analysis(self, inputs: Dict[str, Any]) -> Any:
        """Execute the analysis"""
        pass

    @abstractmethod
    def generate_reports(self, analysis: Any) -> Dict[str, Path]:
        """Generate output reports"""
        pass

    def execute(self, inputs: Dict[str, Any]) -> ResearchResult:
        """
        Main execution method

        Returns:
            ResearchResult with success status, outputs, and metadata
        """
        pass
```

### ResearchResult Data Class

```python
@dataclass
class ResearchResult:
    """Result of research tool execution"""
    tool_name: str
    project_id: str
    executed_at: datetime
    success: bool
    outputs: Dict[str, Path]  # Format -> file path mapping
    metadata: Dict[str, Any]
    error: Optional[str] = None
```

---

## Implemented Tools API

### 1. Voice Analysis Tool

#### Class: `VoiceAnalyzer`

```python
from src.research import VoiceAnalyzer

analyzer = VoiceAnalyzer(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,    # Required, min 50 chars
    'target_audience': str,         # Required, min 10 chars
    'sample_content': List[str],    # Required, 3-10 samples (URLs or text)
    'business_name': str,           # Optional
    'industry': str                 # Optional
}
```

#### Output Schema

```python
from src.models.voice_sample import VoiceAnalysis

class VoiceAnalysis(BaseModel):
    business_name: str
    industry: str
    analysis_date: str

    # Voice Profile
    voice_profile: VoiceProfile

    # Content Patterns
    content_characteristics: ContentCharacteristics

    # Recommendations
    writing_do: List[str]
    writing_dont: List[str]
    template_customization_guide: List[str]
```

#### Usage Example

```python
analyzer = VoiceAnalyzer(project_id="acme_corp")

result = analyzer.execute({
    'business_description': 'B2B SaaS company helping...',
    'target_audience': 'Marketing leaders, CMOs',
    'sample_content': [
        'https://blog.acme.com/post1',
        'Our product helps teams collaborate...',
        'https://blog.acme.com/post3'
    ],
    'business_name': 'Acme Corp',
    'industry': 'B2B SaaS'
})

if result.success:
    # Access JSON output
    with open(result.outputs['json']) as f:
        data = json.load(f)

    # Read markdown report
    report = result.outputs['markdown'].read_text()
```

#### Error Handling

```python
# ValueError: Missing required input
if 'sample_content' not in inputs:
    raise ValueError("Missing required input: sample_content")

# ValueError: Not enough samples
if len(inputs['sample_content']) < 3:
    raise ValueError("Provide at least 3 content samples (got {n})")

# ValueError: Too many samples
if len(inputs['sample_content']) > 10:
    raise ValueError("Maximum 10 content samples allowed (got {n})")
```

---

### 2. Brand Archetype Assessment Tool

#### Class: `BrandArchetypeAnalyzer`

```python
from src.research import BrandArchetypeAnalyzer

analyzer = BrandArchetypeAnalyzer(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,    # Required, min 50 chars
    'target_audience': str,         # Required, min 10 chars
    'value_proposition': str,       # Required, min 20 chars
    'current_messaging': str,       # Optional
    'business_name': str,           # Optional
    'industry': str                 # Optional
}
```

#### Output Schema

```python
from src.models.research_models import BrandArchetypeAnalysis

class BrandArchetypeAnalysis(BaseModel):
    business_name: str
    industry: str
    analysis_date: str

    # Archetype Results
    primary_archetype: Archetype
    secondary_archetype: Archetype
    archetype_score: float  # 0-100

    # Messaging Framework
    core_values: List[str]
    brand_voice_attributes: List[str]
    messaging_themes: List[str]

    # Content Guidance
    content_angles: List[str]
    avoid_messaging: List[str]
    competitor_archetypes: List[CompetitorArchetype]
```

#### 12 Brand Archetypes

| Archetype | Motivation | Voice | Example Brands |
|-----------|------------|-------|----------------|
| Innocent | Safety, simplicity | Optimistic, pure | Dove, Coca-Cola |
| Sage | Understanding, wisdom | Knowledgeable, analytical | Google, Harvard |
| Explorer | Freedom, discovery | Adventurous, independent | Patagonia, Jeep |
| Outlaw | Liberation, revolution | Rebellious, disruptive | Harley-Davidson, Tesla |
| Magician | Transformation | Visionary, charismatic | Disney, Apple |
| Hero | Courage, mastery | Confident, inspiring | Nike, FedEx |
| Lover | Intimacy, passion | Warm, sensual | Chanel, Godiva |
| Jester | Joy, living in moment | Playful, humorous | M&M's, Old Spice |
| Everyman | Belonging, connection | Down-to-earth, friendly | IKEA, Target |
| Caregiver | Service, compassion | Nurturing, supportive | Johnson & Johnson, UNICEF |
| Ruler | Control, leadership | Authoritative, refined | Mercedes-Benz, Rolex |
| Creator | Innovation, imagination | Artistic, innovative | Lego, Adobe |

---

### 3. SEO Keyword Research Tool

#### Class: `SEOKeywordResearcher`

```python
from src.research import SEOKeywordResearcher

researcher = SEOKeywordResearcher(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,    # Required, min 50 chars
    'target_audience': str,         # Required, min 10 chars
    'industry': str,                # Required, min 5 chars
    'competitor_domains': List[str], # Optional, max 3 domains
    'business_name': str,           # Optional
    'focus_topics': List[str]       # Optional
}
```

#### Output Schema

```python
from src.models.seo_models import SEOKeywordResearch

class SEOKeywordResearch(BaseModel):
    business_name: str
    industry: str
    analysis_date: str

    # Keywords
    primary_keywords: List[Keyword]      # 10-15 keywords
    secondary_keywords: List[Keyword]    # 15-20 keywords
    long_tail_keywords: List[Keyword]    # 15-20 keywords

    # Topic Clusters
    topic_clusters: List[TopicCluster]

    # Recommendations
    content_opportunities: List[str]
    seasonal_recommendations: List[str]
    quick_wins: List[str]

class Keyword(BaseModel):
    keyword: str
    search_volume: str              # "High: 5K/mo"
    difficulty: str                 # "Low", "Medium", "High"
    search_intent: str              # "Informational", "Commercial", etc.
    relevance_score: int            # 0-100
    content_angle: str
```

---

### 4. Competitive Analysis Tool

#### Class: `CompetitiveAnalyzer`

```python
from src.research import CompetitiveAnalyzer

analyzer = CompetitiveAnalyzer(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,    # Required, min 50 chars
    'target_audience': str,         # Required, min 10 chars
    'competitors': List[str],       # Required, 1-5 competitors
    'analysis_focus': str,          # Optional: "content", "pricing", etc.
    'business_name': str,           # Optional
    'industry': str                 # Optional
}
```

#### Output Schema

```python
from src.models.competitive_analysis_models import CompetitiveAnalysis

class CompetitiveAnalysis(BaseModel):
    business_name: str
    industry: str
    analysis_date: str

    # Competitor Profiles
    competitors: List[CompetitorProfile]

    # Strategic Analysis
    positioning_map: List[PositioningInsight]
    competitive_advantages: List[str]
    differentiation_opportunities: List[str]
    messaging_gaps: List[str]

    # Content Strategy
    content_approach_comparison: List[ContentApproach]
    underserved_topics: List[str]

    # Recommendations
    immediate_actions: List[str]
    long_term_strategy: List[str]
```

---

### 5. Market Trends Research Tool

#### Class: `MarketTrendsResearcher`

```python
from src.research import MarketTrendsResearcher

researcher = MarketTrendsResearcher(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,    # Required, min 50 chars
    'target_audience': str,         # Required, min 10 chars
    'industry': str,                # Required, min 5 chars
    'time_horizon': str,            # Optional: "30days", "60days", "90days"
    'business_name': str,           # Optional
    'focus_areas': List[str]        # Optional
}
```

#### Output Schema

```python
from src.models.market_trends_models import MarketTrendsAnalysis

class MarketTrendsAnalysis(BaseModel):
    business_name: str
    industry: str
    analysis_date: str
    time_horizon: str

    # Trends
    emerging_trends: List[Trend]     # 10-15 trends

    # Analysis
    trend_categories: List[TrendCategory]
    social_conversation: List[SocialTrend]
    news_coverage: List[NewsCoverage]

    # Recommendations
    content_opportunities: List[str]
    timing_recommendations: List[str]
    thought_leadership_angles: List[str]

class Trend(BaseModel):
    trend_name: str
    momentum: str                    # "Emerging", "Growing", "Peaking"
    time_sensitivity: str            # "Act now", "Watch", "Long-term"
    relevance_to_business: str
    content_angle: str
    supporting_data: List[str]
```

---

### 6. Content Gap Analysis Tool

#### Class: `ContentGapAnalyzer`

```python
from src.research import ContentGapAnalyzer

analyzer = ContentGapAnalyzer(project_id: str, output_dir: Path = None)
```

#### Input Schema

```python
{
    'business_description': str,        # Required, min 50 chars
    'target_audience': str,             # Required, min 10 chars
    'current_content_topics': List[str], # Required, min 1 topic
    'competitors': List[str],           # Optional, max 5
    'business_name': str,               # Optional
    'industry': str                     # Optional
}
```

#### Output Schema

```python
from src.models.content_gap_models import ContentGapAnalysis

class ContentGapAnalysis(BaseModel):
    business_name: str
    industry: str
    analysis_date: str

    # Gaps by Priority
    critical_gaps: List[ContentGap]      # 3-5 must-create items
    high_priority_gaps: List[ContentGap] # 5-7 strong opportunities
    medium_priority_gaps: List[ContentGap] # 5-7 good opportunities

    # Strategic Analysis
    competitor_analysis: List[CompetitorContentAnalysis]
    buyer_journey_gaps: List[BuyerJourneyGap]
    format_gaps: List[FormatGap]

    # Action Items
    quick_wins: List[str]                # 5-7 high impact, low effort
    long_term_opportunities: List[str]   # 3-5 strategic initiatives
    immediate_actions: List[str]         # 3-5 what to do first
    ninety_day_roadmap: List[str]        # 10-12 items

    # Summary
    executive_summary: str
    total_gaps_identified: int
    estimated_opportunity: str

class ContentGap(BaseModel):
    gap_title: str
    gap_type: GapType                   # TOPIC, FORMAT, DEPTH, etc.
    priority: GapPriority               # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    search_volume: str
    competition: str
    business_impact: str
    target_audience: str
    buyer_stage: str
    content_angle: str
    example_topics: List[str]           # 3-5 specific topics
    estimated_effort: str               # Small/Medium/Large
```

---

## Common Patterns

### Initialization

All tools follow the same initialization pattern:

```python
# Basic initialization
tool = ToolClass(project_id="client_name")

# Custom output directory
tool = ToolClass(
    project_id="client_name",
    output_dir=Path("custom/output/path")
)
```

### Execution Flow

```python
# 1. Validate inputs
try:
    tool.validate_inputs(inputs)
except ValueError as e:
    print(f"Invalid inputs: {e}")
    return

# 2. Execute analysis
result = tool.execute(inputs)

# 3. Check success
if result.success:
    print(f"✅ {result.tool_name} completed")
    print(f"Duration: {result.metadata['duration_seconds']:.1f}s")
    print(f"Price: ${result.metadata['price']}")
else:
    print(f"❌ Error: {result.error}")

# 4. Access outputs
json_file = result.outputs['json']
markdown_file = result.outputs['markdown']
text_file = result.outputs['text']
```

### Error Handling

All tools raise `ValueError` for validation errors:

```python
try:
    result = tool.execute(inputs)
except ValueError as e:
    # Handle validation error
    print(f"Validation failed: {e}")
except Exception as e:
    # Handle unexpected error
    print(f"Execution failed: {e}")
```

### Output File Naming

```
data/research/{tool_name}/{project_id}/
├── {output_name}.json              # JSON format
├── {output_name}_report.md         # Markdown format
└── {output_name}_summary.txt       # Text format
```

Examples:
- `voice_analysis.json`, `voice_analysis_report.md`, `voice_summary.txt`
- `brand_archetype.json`, `brand_archetype_report.md`, `archetype_summary.txt`
- `seo_keywords.json`, `seo_keywords_report.md`, `keywords_summary.txt`

---

## API Usage Examples

### Batch Processing Multiple Tools

```python
from src.research import (
    VoiceAnalyzer,
    BrandArchetypeAnalyzer,
    SEOKeywordResearcher
)

project_id = "acme_corp"
base_inputs = {
    'business_description': '...',
    'target_audience': '...',
    'business_name': 'Acme Corp',
    'industry': 'B2B SaaS'
}

# Run multiple tools
tools = [
    (VoiceAnalyzer, {**base_inputs, 'sample_content': [...]}),
    (BrandArchetypeAnalyzer, {**base_inputs, 'value_proposition': '...'}),
    (SEOKeywordResearcher, base_inputs)
]

results = {}
for ToolClass, inputs in tools:
    tool = ToolClass(project_id=project_id)
    result = tool.execute(inputs)
    results[result.tool_name] = result

# Summary
total_price = sum(r.metadata['price'] for r in results.values())
total_time = sum(r.metadata['duration_seconds'] for r in results.values())

print(f"✅ Completed {len(results)} tools")
print(f"Total price: ${total_price}")
print(f"Total time: {total_time:.1f}s")
```

### Accessing Structured Data

```python
import json
from pathlib import Path

# Load JSON output
result = analyzer.execute(inputs)
json_path = result.outputs['json']

with open(json_path) as f:
    data = json.load(f)

# Access specific fields (example: Voice Analysis)
voice_profile = data['voice_profile']
tone = voice_profile['tone']
personality_traits = voice_profile['personality_traits']

# Use in content generation
generator = ContentGenerator(
    voice_tone=tone,
    personality_traits=personality_traits
)
```

### Custom Report Generation

```python
# Generate custom report from multiple tools
def create_comprehensive_report(project_id: str):
    """Combine multiple research reports into one"""

    # Load all JSON outputs
    research_dir = Path(f"data/research")
    voice_data = json.loads((research_dir / "voice_analysis" / project_id / "voice_analysis.json").read_text())
    archetype_data = json.loads((research_dir / "brand_archetype" / project_id / "brand_archetype.json").read_text())
    seo_data = json.loads((research_dir / "seo_keyword_research" / project_id / "seo_keywords.json").read_text())

    # Create combined report
    report = f"""
    # Comprehensive Research Report: {project_id}

    ## Voice Profile
    {voice_data['voice_profile']}

    ## Brand Archetype
    Primary: {archetype_data['primary_archetype']['name']}

    ## Target Keywords
    {[kw['keyword'] for kw in seo_data['primary_keywords']]}
    """

    return report
```

---

## Testing

### Unit Tests

Each tool has comprehensive test coverage:

```python
def test_tool_basic():
    """Test basic execution"""
    tool = ToolClass(project_id="test_project")
    result = tool.execute(valid_inputs)

    assert result.success
    assert result.tool_name == "expected_name"
    assert 'json' in result.outputs
    assert 'markdown' in result.outputs
    assert 'text' in result.outputs

    # Verify files exist
    for file_path in result.outputs.values():
        assert file_path.exists()

def test_tool_validation():
    """Test input validation"""
    tool = ToolClass(project_id="test_validation")

    # Missing required field
    with pytest.raises(ValueError, match="Missing required input"):
        tool.validate_inputs({})

    # Field too short
    with pytest.raises(ValueError, match="too short"):
        tool.validate_inputs({'field': 'x'})
```

### Integration Tests

```python
def test_tool_integration():
    """Test integration with content generator"""
    # Run research
    result = tool.execute(inputs)

    # Load outputs
    with open(result.outputs['json']) as f:
        research_data = json.load(f)

    # Use in content generation
    generator = ContentGenerator(research_data=research_data)
    posts = generator.generate_posts(num_posts=5)

    assert len(posts) == 5
    # Verify posts use research data
```

---

## Performance & Costs

### API Usage

All tools use Claude 3.5 Sonnet via Anthropic API:

| Tool | API Calls | Avg Tokens | Est. Cost |
|------|-----------|------------|-----------|
| Voice Analysis | 3-5 | 15K-25K | $0.50-$0.80 |
| Brand Archetype | 1-2 | 8K-12K | $0.25-$0.40 |
| SEO Keyword Research | 7-10 | 30K-45K | $1.00-$1.50 |
| Competitive Analysis | 5-7 | 25K-35K | $0.80-$1.20 |
| Market Trends | 5-8 | 25K-40K | $0.80-$1.30 |
| Content Gap Analysis | 10-12 | 45K-60K | $1.50-$2.00 |

**Note:** Costs are API costs only. Tool pricing ($300-$600) includes margins for value delivery.

### Execution Time

| Tool | Typical Duration | Max Duration |
|------|------------------|--------------|
| Voice Analysis | 2-3 min | 5 min |
| Brand Archetype | 1-2 min | 3 min |
| SEO Keyword Research | 3-4 min | 6 min |
| Competitive Analysis | 2-3 min | 5 min |
| Market Trends | 2-3 min | 5 min |
| Content Gap Analysis | 3-4 min | 7 min |

---

## Future API Enhancements

### Planned Features

**Async Execution:**
```python
# Future: async/await support
result = await tool.execute_async(inputs)
```

**Batch Processing:**
```python
# Future: parallel execution
results = ResearchBatch.execute_parallel([
    (VoiceAnalyzer, inputs1),
    (BrandArchetypeAnalyzer, inputs2),
    (SEOKeywordResearcher, inputs3)
])
```

**Streaming Results:**
```python
# Future: stream progress updates
for progress in tool.execute_streaming(inputs):
    print(f"{progress.step}: {progress.status}")
```

**Caching:**
```python
# Future: cache expensive analyses
tool = ToolClass(project_id="acme", use_cache=True)
result = tool.execute(inputs)  # Uses cache if available
```

---

## Support

For API issues, bugs, or feature requests:
- GitHub Issues: `github.com/yourusername/content-jumpstart/issues`
- Email: support@yourcompany.com
- Documentation: `docs/RESEARCH_TOOLS.md`

---

**Last Updated:** December 2025
**API Version:** 1.0.0
**Python Version:** 3.9+
