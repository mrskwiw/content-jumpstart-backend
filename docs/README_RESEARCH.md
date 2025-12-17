# Research Tools Documentation Index

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **RESEARCH_TOOLS.md** | Complete guide to all 12 research tools | Content creators, business owners |
| **RESEARCH_API.md** | Technical API reference | Developers, integrators |
| **RESEARCH_INTEGRATION.md** | Integration patterns and workflows | Technical users, advanced users |

---

## For Content Creators

**Start here:** `RESEARCH_TOOLS.md`

Learn about:
- What each tool does and when to use it
- Pricing and package bundles
- Quick start guide
- Common use cases
- Testing and troubleshooting

**Key sections:**
- Tool Catalog (page 1)
- Quick Start Guide (page 8)
- Pricing Strategy (page 10)
- Common Use Cases (page 11)

---

## For Developers

**Start here:** `RESEARCH_API.md`

Technical details about:
- Base class architecture
- Input/output schemas for each tool
- Error handling patterns
- Code examples
- Testing strategies

**Key sections:**
- Base Architecture (page 1)
- Implemented Tools API (page 2)
- Common Patterns (page 10)
- API Usage Examples (page 12)

---

## For Integration

**Start here:** `RESEARCH_INTEGRATION.md`

Integration workflows:
- Complete integration workflow
- Research-driven content generation
- Advanced integration techniques
- CLI integration
- Performance optimization

**Key sections:**
- Complete Integration Workflow (page 2)
- Integration Patterns (page 9)
- Advanced Techniques (page 11)
- Best Practices (page 17)

---

## Quick Reference

### Tool Status (6/12 Completed)

✅ **Implemented:**
1. Voice Analysis Tool ($400)
2. Brand Archetype Assessment Tool ($300)
3. SEO Keyword Research Tool ($400)
4. Competitive Analysis Tool ($500)
5. Market Trends Research Tool ($400)
6. Content Gap Analysis Tool ($500)

⏳ **Not Yet Implemented:**
7. Content Audit Tool ($400)
8. Platform Strategy Tool ($300)
9. Content Calendar Strategy Tool ($300)
10. Audience Research Tool ($500)
11. ICP Development Workshop ($600)
12. Story Mining Interview ($500)

### Basic Usage

```python
from src.research import VoiceAnalyzer

analyzer = VoiceAnalyzer(project_id="client_name")
result = analyzer.execute({
    'business_description': '...',
    'target_audience': '...',
    'sample_content': [...]
})

if result.success:
    print(f"✅ Complete! {result.outputs}")
```

### Running Tests

```bash
# All research tools
pytest tests/research/ -v

# Specific tool
pytest tests/research/test_voice_analysis.py -v

# With coverage
pytest tests/research/ --cov=src/research --cov-report=html
```

---

## Documentation Versions

- **Version:** 1.0.0
- **Last Updated:** December 2025
- **Implemented Tools:** 6/12
- **Total Documentation:** 3 files, ~500 pages equivalent

---

## Getting Help

### For Usage Questions
- Read: `RESEARCH_TOOLS.md`
- Run: `pytest tests/research/ -v` (see working examples)

### For Technical Questions
- Read: `RESEARCH_API.md`
- Review: Test files in `tests/research/`

### For Integration Questions
- Read: `RESEARCH_INTEGRATION.md`
- Example: See integration patterns (page 9)

### For Bugs or Features
- GitHub Issues: [Create Issue]
- Email: support@yourcompany.com

---

## Related Documentation

- **Main System:** `../README.md`
- **Agent Architecture:** `ARCHITECTURE.md`
- **Development Guide:** `DEVELOPMENT.md`
- **Usage Guide:** `USAGE.md`
- **Coordinator Agent:** `COORDINATOR_AGENT.md`
- **Revision Management:** `REVISION_MANAGEMENT.md`

---

## Next Steps

1. **New to research tools?** → Start with `RESEARCH_TOOLS.md`
2. **Ready to integrate?** → Read `RESEARCH_INTEGRATION.md`
3. **Building custom tools?** → Reference `RESEARCH_API.md`
4. **Want to test?** → Run `pytest tests/research/ -v`

---

**Happy Researching! 🔍📊**
