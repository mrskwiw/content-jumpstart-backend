"""
Unit tests for research section generation in export service.

Tests research formatters and integration into deliverables.
"""

import pytest
from pathlib import Path
from backend.services.export_service import (
    _generate_research_section,
    _format_voice_analysis,
    _format_brand_archetype,
    _format_seo_keywords,
    _format_competitive_analysis,
    _format_content_gap,
    _format_market_trends,
    _format_generic_research,
)
from backend.models import ResearchResult


class TestResearchFormatters:
    """Test research result formatters."""

    def test_format_voice_analysis(self):
        """Test voice analysis formatter."""
        data = {
            "tone": "Professional",
            "readability_score": 65.2,
            "recommendations": [
                "Use shorter sentences",
                "Add more examples",
                "Vary sentence structure",
            ],
        }

        lines = _format_voice_analysis(data)

        assert "**Tone:** Professional" in lines
        assert "**Readability Score:** 65.2" in lines
        assert "**Recommendations:**" in lines
        assert "- Use shorter sentences" in lines
        assert "- Add more examples" in lines
        assert "- Vary sentence structure" in lines

    def test_format_voice_analysis_missing_fields(self):
        """Test voice analysis formatter with missing fields."""
        data = {"tone": "Casual"}

        lines = _format_voice_analysis(data)

        assert "**Tone:** Casual" in lines
        assert "Readability Score" not in "\n".join(lines)

    def test_format_brand_archetype(self):
        """Test brand archetype formatter."""
        data = {
            "primary_archetype": "Hero",
            "secondary_archetype": "Creator",
            "content_themes": [
                "Overcoming challenges",
                "Innovation and creativity",
                "Transformation",
            ],
        }

        lines = _format_brand_archetype(data)

        assert "**Primary Archetype:** Hero" in lines
        assert "**Secondary Archetype:** Creator" in lines
        assert "**Content Themes:**" in lines
        assert "- Overcoming challenges" in lines
        assert "- Innovation and creativity" in lines

    def test_format_seo_keywords(self):
        """Test SEO keyword formatter with table."""
        data = {
            "primary_keywords": [
                {"keyword": "content marketing", "volume": 50000, "difficulty": "Medium"},
                {"keyword": "social media strategy", "volume": 25000, "difficulty": "High"},
                {"keyword": "seo optimization", "volume": 15000, "difficulty": "Low"},
            ]
        }

        lines = _format_seo_keywords(data)

        # Check table header
        assert "**Primary Keywords:**" in lines
        assert "| Keyword | Volume | Difficulty |" in lines
        assert "|---------|--------|------------|" in lines

        # Check table rows
        assert "| content marketing | 50,000 | Medium |" in lines
        assert "| social media strategy | 25,000 | High |" in lines
        assert "| seo optimization | 15,000 | Low |" in lines

    def test_format_seo_keywords_limit_10(self):
        """Test SEO keyword formatter limits to top 10."""
        # Create 15 keywords
        keywords = [
            {"keyword": f"keyword_{i}", "volume": 1000 * i, "difficulty": "Medium"}
            for i in range(15)
        ]
        data = {"primary_keywords": keywords}

        lines = _format_seo_keywords(data)

        # Count table rows (excluding header and separator)
        table_rows = [line for line in lines if line.startswith("| keyword_")]
        assert len(table_rows) == 10  # Should limit to 10

    def test_format_competitive_analysis(self):
        """Test competitive analysis formatter."""
        data = {
            "competitors": [
                {
                    "name": "Competitor A",
                    "strength": "High",
                    "key_differentiator": "Advanced AI features",
                },
                {
                    "name": "Competitor B",
                    "strength": "Medium",
                    "key_differentiator": "Lower pricing",
                },
            ]
        }

        lines = _format_competitive_analysis(data)

        assert "**Key Competitors:**" in lines
        assert "- **Competitor A** (Strength: High)" in lines
        assert "  - Advanced AI features" in lines
        assert "- **Competitor B** (Strength: Medium)" in lines
        assert "  - Lower pricing" in lines

    def test_format_content_gap_dict(self):
        """Test content gap formatter with dict gaps."""
        data = {
            "gaps": [
                {"topic": "SEO best practices", "priority": "High"},
                {"topic": "Social media trends", "priority": "Medium"},
            ]
        }

        lines = _format_content_gap(data)

        assert "**Content Gaps Identified:**" in lines
        assert "- **SEO best practices** (Priority: High)" in lines
        assert "- **Social media trends** (Priority: Medium)" in lines

    def test_format_content_gap_string(self):
        """Test content gap formatter with string gaps."""
        data = {"gaps": ["Email marketing strategies", "Video content creation"]}

        lines = _format_content_gap(data)

        assert "**Content Gaps Identified:**" in lines
        assert "- Email marketing strategies" in lines
        assert "- Video content creation" in lines

    def test_format_market_trends(self):
        """Test market trends formatter."""
        data = {
            "trends": [
                {"title": "AI-powered automation", "impact": "High"},
                {"title": "Short-form video content", "impact": "Medium"},
            ]
        }

        lines = _format_market_trends(data)

        assert "**Top Market Trends:**" in lines
        assert "- **AI-powered automation** (Impact: High)" in lines
        assert "- **Short-form video content** (Impact: Medium)" in lines

    def test_format_generic_research_lists(self):
        """Test generic formatter with lists."""
        data = {
            "recommendations": ["Use bullet points", "Add visuals", "Keep it concise"],
            "challenges": ["Limited budget", "Tight timeline"],
        }

        lines = _format_generic_research(data)

        assert "**Recommendations:**" in lines
        assert "- Use bullet points" in lines
        assert "- Add visuals" in lines
        assert "**Challenges:**" in lines
        assert "- Limited budget" in lines

    def test_format_generic_research_nested_dict(self):
        """Test generic formatter with nested dicts."""
        data = {
            "metrics": {
                "engagement_rate": "5.2%",
                "conversion_rate": "2.1%",
                "bounce_rate": "45%",
            }
        }

        lines = _format_generic_research(data)

        assert "**Metrics:**" in lines
        assert "- engagement_rate: 5.2%" in lines
        assert "- conversion_rate: 2.1%" in lines
        assert "- bounce_rate: 45%" in lines

    def test_format_generic_research_simple_values(self):
        """Test generic formatter with simple values."""
        data = {"score": 85, "status": "Completed", "duration": "12.5 seconds"}

        lines = _format_generic_research(data)

        assert "**Score:** 85" in lines
        assert "**Status:** Completed" in lines
        assert "**Duration:** 12.5 seconds" in lines


class TestGenerateResearchSection:
    """Test research section generation."""

    def test_generate_research_section_single_result(
        self, db_session, test_user, test_client, test_project
    ):
        """Test generating research section with single result."""
        result = ResearchResult(
            id="res-section1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            data={"tone": "Professional", "readability_score": 65.2},
            status="completed",
        )
        db_session.add(result)
        db_session.commit()

        sections = _generate_research_section(test_project.id, test_client.id, db_session)

        assert "voice_analysis" in sections
        lines = sections["voice_analysis"]

        assert "# Voice Analysis" in lines
        assert "**Cost:** $400.00" in lines
        assert "**Tone:** Professional" in lines

    def test_generate_research_section_multiple_results(
        self, db_session, test_user, test_client, test_project
    ):
        """Test generating research section with multiple results."""
        result1 = ResearchResult(
            id="res-multi1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            data={"tone": "Professional"},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-multi2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            data={
                "primary_keywords": [{"keyword": "seo", "volume": 10000, "difficulty": "Medium"}]
            },
            status="completed",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        sections = _generate_research_section(test_project.id, test_client.id, db_session)

        assert len(sections) == 2
        assert "voice_analysis" in sections
        assert "seo_keyword_research" in sections

    def test_generate_research_section_no_results(self, db_session, test_project):
        """Test generating research section with no results."""
        sections = _generate_research_section(test_project.id, test_project.client_id, db_session)

        assert sections == {}

    def test_generate_research_section_only_completed(
        self, db_session, test_user, test_client, test_project
    ):
        """Test that only completed results are included."""
        result1 = ResearchResult(
            id="res-comp1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            data={"tone": "Professional"},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-fail1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="failed",
            error_message="Timeout",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        sections = _generate_research_section(test_project.id, test_client.id, db_session)

        assert len(sections) == 1
        assert "voice_analysis" in sections
        assert "seo_keyword_research" not in sections  # Failed results excluded

    def test_generate_research_section_without_data(
        self, db_session, test_user, test_client, test_project
    ):
        """Test generating section for result without data field."""
        result = ResearchResult(
            id="res-nodata",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={"report": "path/to/report.md"},
            data=None,  # No structured data
            status="completed",
        )
        db_session.add(result)
        db_session.commit()

        sections = _generate_research_section(test_project.id, test_client.id, db_session)

        assert "voice_analysis" in sections
        lines = sections["voice_analysis"]

        # Should have header and metadata, but no results section
        assert "# Voice Analysis" in lines
        assert "**Cost:** $400.00" in lines
        assert "## Results" not in lines

    def test_generate_research_section_formats_timestamp(
        self, db_session, test_user, test_client, test_project
    ):
        """Test that timestamp is formatted correctly."""
        from datetime import datetime

        result = ResearchResult(
            id="res-time",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            data={},
            status="completed",
            created_at=datetime(2026, 2, 25, 14, 30, 0),
        )
        db_session.add(result)
        db_session.commit()

        sections = _generate_research_section(test_project.id, test_client.id, db_session)

        lines = sections["voice_analysis"]
        timestamp_line = [l for l in lines if l.startswith("**Executed:**")][0]

        assert "February 25, 2026 at 14:30" in timestamp_line
