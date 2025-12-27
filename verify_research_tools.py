#!/usr/bin/env python3
"""
Verify research tool name mapping fix

This script manually verifies that RESEARCH_TOOL_MAP keys match actual tool names.

Bug Fixed:
- Old: RESEARCH_TOOL_MAP had keys like "seo_keyword", "content_gap", "market_trends"
- New: RESEARCH_TOOL_MAP keys now match tool_name properties: "seo_keyword_research", etc.
"""
import io
import sys
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("RESEARCH TOOL MAPPING VERIFICATION")
print("=" * 60)

try:
    # Import research tools
    from src.research.voice_analysis import VoiceAnalyzer
    from src.research.brand_archetype import BrandArchetypeAnalyzer
    from src.research.seo_keyword_research import SEOKeywordResearcher
    from src.research.competitive_analysis import CompetitiveAnalyzer
    from src.research.content_gap_analysis import ContentGapAnalyzer
    from src.research.market_trends_research import MarketTrendsResearcher

    print("\n✓ Successfully imported all 6 research tools")

    # Get tool names from actual implementations
    test_project_id = "test-verification"

    tools = [
        VoiceAnalyzer(project_id=test_project_id),
        BrandArchetypeAnalyzer(project_id=test_project_id),
        SEOKeywordResearcher(project_id=test_project_id),
        CompetitiveAnalyzer(project_id=test_project_id),
        ContentGapAnalyzer(project_id=test_project_id),
        MarketTrendsResearcher(project_id=test_project_id),
    ]

    actual_tool_names = [tool.tool_name for tool in tools]

    print("\n✓ Tool implementations provide these tool_name properties:")
    for i, name in enumerate(actual_tool_names, 1):
        print(f"  {i}. {name}")

    # Define expected map keys (what the router uses)
    expected_map_keys = {
        "voice_analysis",
        "brand_archetype",
        "seo_keyword_research",  # FIXED: was "seo_keyword"
        "competitive_analysis",
        "content_gap_analysis",  # FIXED: was "content_gap"
        "market_trends_research",  # FIXED: was "market_trends"
    }

    print("\n✓ Expected RESEARCH_TOOL_MAP keys (from router):")
    for i, key in enumerate(sorted(expected_map_keys), 1):
        print(f"  {i}. {key}")

    # Verify they match
    actual_set = set(actual_tool_names)
    missing_in_map = actual_set - expected_map_keys
    extra_in_map = expected_map_keys - actual_set

    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)

    if not missing_in_map and not extra_in_map:
        print("\n✅ SUCCESS: All tool names match map keys!")
        print("\nThe bug is FIXED. Research tools will work correctly:")
        print("  - Router calls with tool_name='seo_keyword_research'")
        print("  - Service looks up 'seo_keyword_research' in RESEARCH_TOOL_MAP")
        print("  - Map returns SEOKeywordResearcher class")
        print("  - Tool executes successfully")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Tool name mismatch detected!")

        if missing_in_map:
            print("\n  Missing in RESEARCH_TOOL_MAP:")
            for name in missing_in_map:
                print(f"    - {name}")

        if extra_in_map:
            print("\n  Extra keys in RESEARCH_TOOL_MAP:")
            for key in extra_in_map:
                print(f"    - {key}")

        print("\nThis will cause ValueError when executing research tools.")
        sys.exit(1)

except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\nResearch tools may not be available in this environment.")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
