"""
Test research tool name mapping between router and service

Critical bug fix: RESEARCH_TOOL_MAP keys must match actual tool names
"""
import pytest


def test_research_tool_map_keys_match_tool_names():
    """
    Verify RESEARCH_TOOL_MAP keys match actual tool_name properties

    This test prevents the bug where:
    - Router uses tool_name="seo_keyword_research"
    - Service map has key="seo_keyword"
    - Result: ValueError("Research tool 'seo_keyword_research' not found")
    """
    # Import tools directly to check their tool_name properties
    from src.research.voice_analysis import VoiceAnalyzer
    from src.research.brand_archetype import BrandArchetypeAnalyzer
    from src.research.seo_keyword_research import SEOKeywordResearcher
    from src.research.competitive_analysis import CompetitiveAnalyzer
    from src.research.content_gap_analysis import ContentGapAnalyzer
    from src.research.market_trends_research import MarketTrendsResearcher

    # Import the service map
    from backend.services.research_service import RESEARCH_TOOL_MAP

    # Instantiate tools to get their tool_name property
    test_project_id = "test-project"

    tools = [
        VoiceAnalyzer(project_id=test_project_id),
        BrandArchetypeAnalyzer(project_id=test_project_id),
        SEOKeywordResearcher(project_id=test_project_id),
        CompetitiveAnalyzer(project_id=test_project_id),
        ContentGapAnalyzer(project_id=test_project_id),
        MarketTrendsResearcher(project_id=test_project_id),
    ]

    # Verify each tool's name is in the map
    for tool in tools:
        tool_name = tool.tool_name
        assert tool_name in RESEARCH_TOOL_MAP, (
            f"Tool '{tool_name}' not found in RESEARCH_TOOL_MAP. "
            f"Available keys: {list(RESEARCH_TOOL_MAP.keys())}"
        )

        # Verify the map points to the correct class
        expected_class = tool.__class__
        actual_class = RESEARCH_TOOL_MAP[tool_name]
        assert actual_class == expected_class, (
            f"RESEARCH_TOOL_MAP['{tool_name}'] points to {actual_class.__name__}, "
            f"expected {expected_class.__name__}"
        )


def test_research_tool_map_has_all_available_tools():
    """Verify all 6 implemented tools are in the map"""
    from backend.services.research_service import RESEARCH_TOOL_MAP

    expected_tools = {
        "voice_analysis",
        "brand_archetype",
        "seo_keyword_research",  # NOT "seo_keyword"
        "competitive_analysis",
        "content_gap_analysis",  # NOT "content_gap"
        "market_trends_research",  # NOT "market_trends"
    }

    actual_tools = set(RESEARCH_TOOL_MAP.keys())

    assert actual_tools == expected_tools, (
        f"Tool map mismatch. Expected: {expected_tools}, Got: {actual_tools}"
    )


def test_router_tool_names_exist_in_map():
    """
    Verify all tool names from research router exist in RESEARCH_TOOL_MAP

    This ensures the router's tool names will be found when passed to the service
    """
    from backend.routers.research import RESEARCH_TOOLS
    from backend.services.research_service import RESEARCH_TOOL_MAP

    # Get all available tool names from router
    available_tools = [tool.name for tool in RESEARCH_TOOLS if tool.status == "available"]

    # Verify each is in the service map
    for tool_name in available_tools:
        assert tool_name in RESEARCH_TOOL_MAP, (
            f"Router tool '{tool_name}' not found in RESEARCH_TOOL_MAP. "
            f"This will cause ValueError when executing research. "
            f"Available keys: {list(RESEARCH_TOOL_MAP.keys())}"
        )


def test_prepare_inputs_tool_name_branches():
    """
    Verify _prepare_inputs uses correct tool names in conditionals

    Bug was:
    - Tool name: "seo_keyword_research"
    - Conditional: if tool_name == "seo_keyword"
    - Result: Input preparation skipped, validation fails
    """
    from backend.services.research_service import research_service
    from models import Project, Client

    # Create mock models
    class MockProject:
        platforms = ["LinkedIn"]
        tone = "professional"

    class MockClient:
        name = "Test Client"
        business_description = "Test business description that is long enough for validation"
        ideal_customer = "Test ideal customer description"

    project = MockProject()
    client = MockClient()

    # Test each tool name triggers correct input preparation
    test_cases = [
        ("seo_keyword_research", {"main_topics": ["topic1"]}),  # NOT "seo_keyword"
        ("content_gap_analysis", {"current_content_topics": ["topic1"]}),  # NOT "content_gap"
        ("market_trends_research", {"industry": "tech"}),  # NOT "market_trends"
    ]

    for tool_name, expected_params in test_cases:
        params = expected_params
        result = research_service._prepare_inputs(project, client, tool_name, params)

        # Verify expected params are in result
        for key in expected_params:
            assert key in result, (
                f"Tool '{tool_name}' did not prepare input '{key}'. "
                f"Check _prepare_inputs conditional uses correct tool name."
            )
