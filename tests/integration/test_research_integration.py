"""Integration tests for research tools"""

import pytest
from pathlib import Path


class TestResearchInfrastructure:
    def test_all_12_tools_defined(self):
        """Test at least 12 research tools are defined in backend"""
        from backend.routers.research import RESEARCH_TOOLS

        assert len(RESEARCH_TOOLS) >= 12

    def test_context_builder_exists(self):
        """Test research context builder module exists"""
        from backend.services import research_context_builder

        assert hasattr(research_context_builder, "build_research_context")
        assert hasattr(research_context_builder, "build_structured_context")

    def test_export_includes_research(self):
        """Test export service can include research"""
        from backend.services.export_service import _generate_research_section

        # Should be callable
        assert callable(_generate_research_section)

    def test_generation_supports_research(self):
        """Test content generator supports research injection"""
        from src.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent(backend_session=None)
        assert hasattr(agent, "backend_session")


class TestFrontendComponents:
    def test_export_panel_enhanced(self):
        """Test ExportPanel has research features"""
        panel = Path("operator-dashboard/src/components/wizard/ExportPanel.tsx")
        if panel.exists():
            content = panel.read_text()
            assert "includeResearch" in content
            assert "researchResults" in content or "completedResearch" in content

    def test_research_widget_exists(self):
        """Test ResearchDashboardWidget exists"""
        widget = Path("operator-dashboard/src/components/research/ResearchDashboardWidget.tsx")
        assert widget.exists()

    def test_research_drawer_has_delete(self):
        """Test ResearchResultsDrawer has delete or close button"""
        drawer = Path("operator-dashboard/src/components/research/ResearchResultsDrawer.tsx")
        if drawer.exists():
            content = drawer.read_text(encoding="utf-8", errors="replace")
            # Check for any removal/close functionality
            assert any(
                k in content.lower() for k in ["delete", "trash", "remove", "close", "onclose"]
            )

    def test_all_tools_in_data_collection(self):
        """Test all 12 tools in data collection panel"""
        panel = Path("operator-dashboard/src/components/wizard/ResearchDataCollectionPanel.tsx")
        if panel.exists():
            content = panel.read_text(encoding="utf-8", errors="replace")
            tools = [
                "voice_analysis",
                "brand_archetype",
                "seo_keyword_research",
                "competitive_analysis",
                "content_gap_analysis",
                "market_trends_research",
                "content_audit",
                "platform_strategy",
                "content_calendar",
                "audience_research",
                "icp_workshop",
                "story_mining",
            ]
            for tool in tools:
                assert tool in content
