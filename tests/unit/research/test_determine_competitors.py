"""
Unit tests for Determine Competitors research tool.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.research.determine_competitors import CompetitorDeterminer
from src.models.determine_competitors_models import (
    DetermineCompetitorsReport,
    DiscoveredCompetitor,
    ThreatLevel,
)


@pytest.fixture
def tool():
    """Create CompetitorDeterminer instance"""
    return CompetitorDeterminer(project_id="test_123")


@pytest.fixture
def valid_inputs():
    """Valid inputs for competitor determination"""
    return {
        "business_description": "We help B2B SaaS companies reduce customer churn through AI-powered analytics and personalized engagement strategies. Our platform integrates with CRM systems to predict churn risk and recommend retention actions.",
        "industry": "B2B SaaS",
        "business_name": "Test Company",
        "location": "United States",
    }


@pytest.fixture
def mock_competitor_data():
    """Mock competitor data from Claude API"""
    return {
        "primary": [
            {
                "name": "ChurnZero",
                "market_position": "Customer success platform focused on SaaS retention",
                "threat_level": "high",
                "strength_areas": [
                    "Real-time alerts",
                    "Customer health scoring",
                    "In-app messaging",
                ],
                "differentiation_opportunity": "Focus on AI-powered predictions vs manual rules",
                "reasoning": "Direct competitor in B2B SaaS retention space",
            },
            {
                "name": "Gainsight",
                "market_position": "Enterprise customer success platform with product analytics",
                "threat_level": "high",
                "strength_areas": ["Enterprise features", "Product analytics", "Community tools"],
                "differentiation_opportunity": "Target mid-market with simpler implementation",
                "reasoning": "Market leader in customer success category",
            },
            {
                "name": "Totango",
                "market_position": "Customer success platform with prebuilt templates",
                "threat_level": "medium",
                "strength_areas": ["Quick setup", "Templates", "Multi-product support"],
                "differentiation_opportunity": "Emphasize AI-driven insights over templates",
                "reasoning": "Competes on ease of use and speed to value",
            },
        ],
        "emerging": [
            {
                "name": "Vitally",
                "market_position": "Modern customer success platform for data-driven teams",
                "threat_level": "medium",
                "strength_areas": ["Modern UI", "Data warehouse integration", "Automation"],
                "differentiation_opportunity": "Compete on AI capabilities and predictive accuracy",
                "reasoning": "Growing competitor with modern tech stack",
            }
        ],
    }


class TestCompetitorDeterminer:
    """Test CompetitorDeterminer functionality"""

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.tool_name == "determine_competitors"
        assert tool.price == 400
        assert tool.project_id == "test_123"

    def test_validation_requires_business_description(self, tool):
        """Test that business_description is required"""
        with pytest.raises(ValueError, match="business_description"):
            tool.validate_inputs({})

    def test_validation_business_description_too_short(self, tool):
        """Test business_description minimum length"""
        with pytest.raises(ValueError, match="minimum 70 characters"):
            tool.validate_inputs({"business_description": "Too short"})

    def test_validation_accepts_valid_inputs(self, tool, valid_inputs):
        """Test validation passes with valid inputs"""
        result = tool.validate_inputs(valid_inputs.copy())
        assert result is True

    def test_validation_industry_optional(self, tool):
        """Test industry is optional"""
        inputs = {
            "business_description": "A" * 100,
            "business_name": "Test",
        }
        assert tool.validate_inputs(inputs) is True
        assert inputs.get("industry") is None

    def test_validation_location_optional(self, tool):
        """Test location is optional"""
        inputs = {
            "business_description": "A" * 100,
            "business_name": "Test",
        }
        assert tool.validate_inputs(inputs) is True

    @patch.object(
        CompetitorDeterminer, "_filter_defunct_competitors", side_effect=lambda comps, _sc: comps
    )
    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_run_analysis_basic(
        self, mock_api, mock_filter, tool, valid_inputs, mock_competitor_data
    ):
        """Test basic analysis execution"""
        # Mock Claude API responses
        mock_api.side_effect = [
            mock_competitor_data,  # Discover competitors
            "The B2B SaaS retention market is highly competitive with established players.",  # Landscape
            ["Underserved mid-market segment", "Limited AI-powered prediction tools"],  # Gaps
            "Position as the AI-first retention platform for mid-market SaaS companies.",  # Positioning
        ]

        report = tool.run_analysis(valid_inputs)

        assert isinstance(report, DetermineCompetitorsReport)
        assert report.business_name == "Test Company"
        assert report.industry == "B2B SaaS"
        assert len(report.primary_competitors) == 3
        assert len(report.emerging_competitors) == 1

    @patch.object(
        CompetitorDeterminer, "_filter_defunct_competitors", side_effect=lambda comps, _sc: comps
    )
    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_competitor_parsing(
        self, mock_api, mock_filter, tool, valid_inputs, mock_competitor_data
    ):
        """Test competitor data parsing"""
        mock_api.side_effect = [
            mock_competitor_data,
            "Landscape summary",
            ["Gap 1"],
            "Position statement",
        ]

        report = tool.run_analysis(valid_inputs)

        # Check primary competitor
        comp1 = report.primary_competitors[0]
        assert comp1.name == "ChurnZero"
        assert comp1.threat_level == ThreatLevel.HIGH
        assert len(comp1.strength_areas) == 3
        assert "AI-powered predictions" in comp1.differentiation_opportunity

        # Check emerging competitor
        emerging = report.emerging_competitors[0]
        assert emerging.name == "Vitally"
        assert emerging.threat_level == ThreatLevel.MEDIUM

    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_market_gaps_identification(self, mock_api, tool, valid_inputs):
        """Test market gap identification"""

        # Mock returns gaps as array directly
        def side_effect_func(prompt, **kwargs):
            if "market gaps" in prompt.lower():
                return ["Gap 1", "Gap 2", "Gap 3"]
            elif "positioning" in prompt.lower():
                return "Positioning"
            elif "landscape" in prompt.lower():
                return "Landscape"
            else:
                return {"primary": [], "emerging": []}

        mock_api.side_effect = side_effect_func

        report = tool.run_analysis(valid_inputs)

        # When no competitors, fallback gaps are used
        assert len(report.market_gaps) >= 1

    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_positioning_recommendation(self, mock_api, tool, valid_inputs):
        """Test positioning recommendation generation"""
        # With no competitors, fallback positioning is used
        mock_api.side_effect = [
            {"primary": [], "emerging": []},
            "Landscape",
            [],
            "Focus on AI-driven insights and mid-market simplicity.",
        ]

        report = tool.run_analysis(valid_inputs)

        # When no competitors, fallback positioning is returned
        assert (
            "category leader" in report.recommended_positioning
            or "Position as" in report.recommended_positioning
        )

    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_empty_competitor_fallback(self, mock_api, tool, valid_inputs):
        """Test fallback when no competitors found"""
        mock_api.side_effect = [
            {"primary": [], "emerging": []},
            "Market is fragmented",
            ["First-mover advantage"],
            "Position as category leader",
        ]

        report = tool.run_analysis(valid_inputs)

        assert len(report.primary_competitors) == 0
        assert "fragmented" in report.competitive_landscape_summary
        assert "First-mover" in report.market_gaps[0]

    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_api_error_handling(self, mock_api, tool, valid_inputs):
        """Test graceful handling of API errors"""
        mock_api.side_effect = Exception("API error")

        report = tool.run_analysis(valid_inputs)

        # Should complete with fallback values
        assert isinstance(report, DetermineCompetitorsReport)
        assert len(report.primary_competitors) == 0

    def test_generate_reports(self, tool):
        """Test report generation"""
        report = DetermineCompetitorsReport(
            business_name="Test Co",
            industry="Technology",
            analysis_date="2024-01-01",
            primary_competitors=[
                DiscoveredCompetitor(
                    name="Competitor A",
                    market_position="Market leader",
                    threat_level=ThreatLevel.HIGH,
                    strength_areas=["Feature 1", "Feature 2"],
                    differentiation_opportunity="Focus on X",
                    reasoning="Direct competitor",
                )
            ],
            emerging_competitors=[],
            competitive_landscape_summary="Summary",
            market_gaps=["Gap 1", "Gap 2"],
            recommended_positioning="Position as X",
        )

        outputs = tool.generate_reports(report)

        assert "json" in outputs
        assert "markdown" in outputs
        assert "text" in outputs
        assert outputs["json"].exists()
        assert outputs["markdown"].exists()
        assert outputs["text"].exists()

    @patch.object(CompetitorDeterminer, "_call_claude_api")
    def test_full_execution(self, mock_api, tool, valid_inputs, mock_competitor_data):
        """Test full end-to-end execution"""
        mock_api.side_effect = [
            mock_competitor_data,
            "Landscape summary",
            ["Gap 1", "Gap 2"],
            "Positioning recommendation",
        ]

        result = tool.execute(valid_inputs)

        assert result.success is True
        assert "json" in result.outputs
        assert "markdown" in result.outputs
        assert "text" in result.outputs
        assert result.metadata["price"] == 400

    def test_markdown_report_formatting(self, tool):
        """Test markdown report formatting"""
        report = DetermineCompetitorsReport(
            business_name="Test Co",
            industry="Technology",
            analysis_date="2024-01-01",
            primary_competitors=[
                DiscoveredCompetitor(
                    name="Competitor A",
                    market_position="Leader",
                    threat_level=ThreatLevel.HIGH,
                    strength_areas=["Feature 1"],
                    differentiation_opportunity="Focus X",
                    reasoning="Direct",
                )
            ],
            emerging_competitors=[],
            competitive_landscape_summary="Summary",
            market_gaps=["Gap 1"],
            recommended_positioning="Position",
        )

        markdown = tool._format_markdown_report(report)

        assert "# Competitor Discovery Report" in markdown
        assert "Competitor A" in markdown
        assert "HIGH Threat" in markdown
        assert "Market Gaps" in markdown

    def test_executive_summary_formatting(self, tool):
        """Test executive summary formatting"""
        report = DetermineCompetitorsReport(
            business_name="Test Co",
            industry="Technology",
            analysis_date="2024-01-01",
            primary_competitors=[
                DiscoveredCompetitor(
                    name="Comp A",
                    market_position="Leader",
                    threat_level=ThreatLevel.HIGH,
                    strength_areas=["F1"],
                    differentiation_opportunity="X",
                    reasoning="Y",
                )
            ],
            emerging_competitors=[],
            competitive_landscape_summary="Summary",
            market_gaps=["Gap 1"],
            recommended_positioning="Position",
        )

        summary = tool._format_executive_summary(report)

        assert "COMPETITOR DISCOVERY REPORT" in summary
        assert "PRIMARY COMPETITORS" in summary
        assert "Comp A" in summary
