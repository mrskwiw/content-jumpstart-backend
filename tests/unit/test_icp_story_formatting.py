"""Test ICP Workshop and Story Mining formatting improvements."""

import pytest
from datetime import datetime


def test_icp_export_formatting():
    """Test ICP Workshop export formatting."""
    from backend.services.export_service import _format_icp_workshop

    sample_data = {
        "profile_name": "Mid-Market SaaS Directors",
        "one_sentence_summary": "Directors of Customer Success at mid-market B2B SaaS companies (100-500 employees) seeking predictive churn analytics to reduce churn by 30%+.",
        "demographics": {
            "company_size": "100-500 employees",
            "industry": "B2B SaaS",
            "revenue_range": "$5M-$50M ARR",
            "job_titles": ["Director of CS", "VP Customer Success"],
            "technologies_used": ["Salesforce", "Gainsight"],
        },
        "psychographics": {
            "goals": ["Reduce churn by 30%", "Prove CS ROI"],
            "challenges": ["Reactive not proactive", "No predictive insights"],
            "values": ["Data-driven decisions", "Customer-centric"],
        },
        "behavioral": {
            "buying_process": "3-6 month evaluation with trials",
            "platforms_active_on": ["LinkedIn", "Industry blogs"],
        },
        "success_criteria": {
            "definition_of_success": "Reduce churn rate significantly with measurable ROI",
            "kpis_tracked": ["Churn rate", "NRR", "Customer health score"],
        },
    }

    lines = _format_icp_workshop(sample_data)
    output = "\n".join(lines)

    assert "Ideal Customer Profile" in output
    assert "Mid-Market SaaS Directors" in output
    assert "100-500 employees" in output
    assert "Director of CS" in output
    assert "Goals:" in output
    assert "Reduce churn" in output
    assert "Challenges:" in output

    print("[OK] ICP export test passed")


def test_story_export_formatting():
    """Test Story Mining export formatting."""
    from backend.services.export_service import _format_story_mining

    sample_data = {
        "total_stories": 5,
        "customer_journey": {
            "before": {
                "situation": "Manual churn tracking, reactive firefighting",
                "pain_points": ["High churn", "No early warning"],
            },
            "decision": {"trigger": "Lost major customer"},
            "after": {"results": ["40% churn reduction", "Proactive interventions"]},
        },
        "key_quotes": ["This saved our business", "Game changer for our team"],
        "story_angles": ["ROI story", "Transformation story"],
    }

    lines = _format_story_mining(sample_data)
    output = "\n".join(lines)

    assert "Customer Success Stories" in output
    assert "5" in output or "Stories Identified" in output
    assert "Before" in output or "Pain State" in output
    assert "After" in output or "Success State" in output
    assert "Key Customer Quotes" in output
    assert "This saved our business" in output

    print("[OK] Story export test passed")


def test_icp_context_builder():
    """Test ICP Workshop context builder."""
    from backend.services.research_context_builder import _format_icp_workshop

    sample_data = {
        "one_sentence_summary": "Directors at mid-market SaaS companies",
        "demographics": {"company_size": "100-500 employees"},
        "psychographics": {
            "goals": ["Reduce churn by 30%"],
            "challenges": ["No predictive insights"],
        },
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()
    context = _format_icp_workshop(result)

    assert "ICP Workshop" in context
    assert "Mar 13" in context
    assert "Directors" in context or "mid-market" in context
    assert "Size:" in context or "100-500" in context

    print("[OK] ICP context test passed")


def test_story_context_builder():
    """Test Story Mining context builder."""
    from backend.services.research_context_builder import _format_story_mining

    sample_data = {
        "total_stories": 5,
        "customer_journey": {
            "before": {"situation": "Manual processes"},
            "after": {"results": ["40% improvement"]},
        },
        "key_quotes": ["Game changer"],
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()
    context = _format_story_mining(result)

    assert "Story Mining" in context
    assert "Mar 13" in context
    assert "5 stories" in context
    assert "Game changer" in context or "Quote:" in context

    print("[OK] Story context test passed")


def test_empty_data_handling():
    """Test both formatters with empty data."""
    from backend.services.export_service import _format_icp_workshop, _format_story_mining

    # ICP
    lines = _format_icp_workshop({})
    assert "No data available" in "\n".join(lines)

    # Story
    lines = _format_story_mining({})
    assert "No data available" in "\n".join(lines)

    print("[OK] Empty data test passed")


if __name__ == "__main__":
    test_icp_export_formatting()
    test_story_export_formatting()
    test_icp_context_builder()
    test_story_context_builder()
    test_empty_data_handling()
    print("\n[OK] All ICP Workshop and Story Mining tests passed!")
