"""Test Business Report tool

Tests for the Business Report research tool that analyzes company perception,
strengths, pain points, and value proposition using web search and Google Maps.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.research.business_report import BusinessReportTool
from src.models.business_report_models import BusinessReportOutput


def test_business_report_basic():
    """Test basic business report execution"""

    # Sample company info
    company_name = "Acme Coffee Co"
    location = "Seattle, WA"

    # Initialize tool
    tool = BusinessReportTool(project_id="test_business_report")

    # Run analysis with mocked API calls
    with (
        patch("src.research.business_report.get_search_client") as mock_search_client,
        patch("src.research.business_report.get_google_maps_client") as mock_maps_client,
    ):

        # Mock web search results
        mock_search = Mock()
        mock_search.search.return_value = Mock(
            results=[
                Mock(
                    title="Acme Coffee - Best Local Roaster",
                    snippet="Known for exceptional quality and community focus",
                    url="https://example.com/review1",
                ),
                Mock(
                    title="Seattle Coffee Guide: Acme Coffee",
                    snippet="Premium artisanal coffee experience",
                    url="https://example.com/review2",
                ),
            ]
        )
        mock_search_client.return_value = mock_search

        # Mock Google Maps results
        mock_maps = Mock()
        mock_maps.search_local_businesses.return_value = [
            {
                "place_id": "ChIJ123abc",
                "rating": 4.6,
                "user_ratings_total": 156,
            }
        ]
        mock_maps.get_place_reviews.return_value = {
            "reviews": [
                {
                    "text": "Amazing coffee, knowledgeable staff",
                    "rating": 5,
                    "time": "2026-03-10",
                    "author_name": "John D.",
                },
                {
                    "text": "Great quality but a bit pricey",
                    "rating": 4,
                    "time": "2026-03-08",
                    "author_name": "Sarah M.",
                },
            ]
        }
        mock_maps_client.return_value = mock_maps

        # Run analysis
        result = tool.execute(
            {
                "company_name": company_name,
                "location": location,
                "max_web_results": 10,
                "max_reviews": 50,
            }
        )

    # Verify success
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "business_report"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "txt" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    # Verify metadata contains analysis data
    assert "data" in result.metadata
    data = result.metadata["data"]
    assert data["company_name"] == company_name
    assert data["location"] == location
    assert "perception_score" in data
    assert "top_strengths" in data
    assert "customer_pain_points" in data
    assert "problems_solved" in data

    print("\n[OK] Business Report Basic Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_business_report_validation():
    """Test input validation"""

    tool = BusinessReportTool(project_id="test_validation")

    # Test missing company_name
    with pytest.raises(ValueError, match="company_name is required"):
        tool.validate_inputs({"location": "Seattle, WA"})

    # Test empty company_name (caught by 'is required' check)
    with pytest.raises(ValueError, match="company_name is required"):
        tool.validate_inputs({"company_name": "", "location": "Seattle, WA"})

    # Test company_name too short
    with pytest.raises(ValueError, match="company_name is too short"):
        tool.validate_inputs({"company_name": "A", "location": "Seattle, WA"})

    # Test company_name too long
    with pytest.raises(ValueError, match="company_name too long"):
        tool.validate_inputs({"company_name": "A" * 201, "location": "Seattle, WA"})

    # Test missing location
    with pytest.raises(ValueError, match="location is required"):
        tool.validate_inputs({"company_name": "Acme Coffee"})

    # Test empty location (caught by 'is required' check)
    with pytest.raises(ValueError, match="location is required"):
        tool.validate_inputs({"company_name": "Acme Coffee", "location": ""})

    # Test location too short
    with pytest.raises(ValueError, match="location is too short"):
        tool.validate_inputs({"company_name": "Acme Coffee", "location": "A"})

    # Test location too long
    with pytest.raises(ValueError, match="location too long"):
        tool.validate_inputs({"company_name": "Acme Coffee", "location": "A" * 201})

    # Test max_web_results out of range (too low)
    with pytest.raises(ValueError, match="max_web_results must be between 1 and 50"):
        tool.validate_inputs(
            {
                "company_name": "Acme Coffee",
                "location": "Seattle, WA",
                "max_web_results": 0,
            }
        )

    # Test max_web_results out of range (too high)
    with pytest.raises(ValueError, match="max_web_results must be between 1 and 50"):
        tool.validate_inputs(
            {
                "company_name": "Acme Coffee",
                "location": "Seattle, WA",
                "max_web_results": 51,
            }
        )

    # Test max_reviews out of range (too low)
    with pytest.raises(ValueError, match="max_reviews must be between 1 and 200"):
        tool.validate_inputs(
            {
                "company_name": "Acme Coffee",
                "location": "Seattle, WA",
                "max_reviews": 0,
            }
        )

    # Test max_reviews out of range (too high)
    with pytest.raises(ValueError, match="max_reviews must be between 1 and 200"):
        tool.validate_inputs(
            {
                "company_name": "Acme Coffee",
                "location": "Seattle, WA",
                "max_reviews": 201,
            }
        )

    # Test valid inputs
    valid_inputs = {
        "company_name": "Acme Coffee Co",
        "location": "Seattle, WA",
        "max_web_results": 10,
        "max_reviews": 50,
    }
    assert tool.validate_inputs(valid_inputs) is True

    # Test with string numbers (should convert)
    string_inputs = {
        "company_name": "Acme Coffee Co",
        "location": "Seattle, WA",
        "max_web_results": "10",
        "max_reviews": "50",
    }
    assert tool.validate_inputs(string_inputs) is True
    assert isinstance(string_inputs["max_web_results"], int)
    assert isinstance(string_inputs["max_reviews"], int)

    print("[OK] Validation tests passed")


def test_business_report_no_web_results():
    """Test handling when web search returns no results"""

    tool = BusinessReportTool(project_id="test_no_web")

    with (
        patch("src.research.business_report.get_search_client") as mock_search_client,
        patch("src.research.business_report.get_google_maps_client") as mock_maps_client,
    ):

        # Mock empty web search
        mock_search = Mock()
        mock_search.search.return_value = Mock(results=[])
        mock_search_client.return_value = mock_search

        # Mock Google Maps with some reviews
        mock_place = Mock()
        mock_place.place_id = "ChIJ123"
        mock_place.rating = 4.5
        mock_place.reviews_count = 50

        mock_review = Mock()
        mock_review.text = "Great service"
        mock_review.rating = 5
        mock_review.date = "2026-03-10"
        mock_review.author = "User"

        mock_reviews_data = Mock()
        mock_reviews_data.reviews = [mock_review]

        mock_maps = Mock()
        mock_maps.search_local_businesses.return_value = [mock_place]
        mock_maps.get_place_reviews.return_value = mock_reviews_data
        mock_maps_client.return_value = mock_maps

        # Should still succeed with reviews only
        result = tool.execute(
            {
                "company_name": "Test Company",
                "location": "Test City",
                "max_web_results": 10,
                "max_reviews": 50,
            }
        )

        assert result.success
        # Verify it used reviews data
        data = result.metadata["data"]
        assert data["reviews_analyzed"] > 0
        assert data["web_sources_analyzed"] == 0

    print("[OK] No web results test passed")


def test_business_report_no_maps_data():
    """Test handling when Google Maps has no listing"""

    tool = BusinessReportTool(project_id="test_no_maps")

    with (
        patch("src.research.business_report.get_search_client") as mock_search_client,
        patch("src.research.business_report.get_google_maps_client") as mock_maps_client,
    ):

        # Mock web search with results
        mock_search = Mock()
        mock_search.search.return_value = Mock(
            results=[
                Mock(title="Test Company Info", snippet="Good company", url="https://example.com")
            ]
        )
        mock_search_client.return_value = mock_search

        # Mock empty Google Maps (no listing found)
        mock_maps = Mock()
        mock_maps.search_local_businesses.return_value = []
        mock_maps_client.return_value = mock_maps

        # Should still succeed with web results only
        result = tool.execute(
            {
                "company_name": "Test Company",
                "location": "Test City",
                "max_web_results": 10,
                "max_reviews": 50,
            }
        )

        assert result.success
        # Verify it used web data
        data = result.metadata["data"]
        assert data["web_sources_analyzed"] > 0
        assert data["reviews_analyzed"] == 0
        assert data["average_rating"] is None

    print("[OK] No maps data test passed")


def test_business_report_no_data():
    """Test handling when both web and maps return nothing"""

    tool = BusinessReportTool(project_id="test_no_data")

    with (
        patch("src.research.business_report.get_search_client") as mock_search_client,
        patch("src.research.business_report.get_google_maps_client") as mock_maps_client,
    ):

        # Mock empty web search
        mock_search = Mock()
        mock_search.search.return_value = Mock(results=[])
        mock_search_client.return_value = mock_search

        # Mock empty Google Maps
        mock_maps = Mock()
        mock_maps.search_local_businesses.return_value = []
        mock_maps_client.return_value = mock_maps

        # Should still succeed but with minimal/empty report
        result = tool.execute(
            {
                "company_name": "Nonexistent Company",
                "location": "Nowhere",
                "max_web_results": 10,
                "max_reviews": 50,
            }
        )

        # Tool should complete but with low confidence
        assert result.success
        data = result.metadata["data"]
        assert data["web_sources_analyzed"] == 0
        assert data["reviews_analyzed"] == 0
        assert data["confidence_level"] == "Low"

    print("[OK] No data test passed")


def test_business_report_output_formats():
    """Test that all output formats are generated correctly"""

    tool = BusinessReportTool(project_id="test_formats")

    with (
        patch("src.research.business_report.get_search_client") as mock_search_client,
        patch("src.research.business_report.get_google_maps_client") as mock_maps_client,
    ):

        # Mock minimal data
        mock_search = Mock()
        mock_search.search.return_value = Mock(
            results=[Mock(title="Test", snippet="Test", url="https://test.com")]
        )
        mock_search_client.return_value = mock_search

        mock_maps = Mock()
        mock_maps.search_local_businesses.return_value = []
        mock_maps_client.return_value = mock_maps

        result = tool.execute(
            {
                "company_name": "Test Company",
                "location": "Test City",
            }
        )

        assert result.success

        # Check all three formats exist
        assert "json" in result.outputs
        assert "markdown" in result.outputs
        assert "txt" in result.outputs

        # Verify files exist and have content
        json_path = Path(result.outputs["json"])
        assert json_path.exists()
        assert json_path.stat().st_size > 0

        markdown_path = Path(result.outputs["markdown"])
        assert markdown_path.exists()
        assert markdown_path.stat().st_size > 0

        txt_path = Path(result.outputs["txt"])
        assert txt_path.exists()
        assert txt_path.stat().st_size > 0

        # Verify markdown contains expected sections
        markdown_content = markdown_path.read_text(encoding="utf-8")
        assert "Business Report:" in markdown_content
        assert "Executive Summary" in markdown_content or "Perception Score" in markdown_content

        # Verify TXT contains expected sections
        txt_content = txt_path.read_text(encoding="utf-8")
        assert "BUSINESS REPORT:" in txt_content.upper()

    print("[OK] Output formats test passed")


def test_business_report_price():
    """Test that tool price is correct"""

    tool = BusinessReportTool(project_id="test_price")

    # Verify price (50 credits = light research tier)
    assert tool.price == 50

    print("[OK] Price test passed (50 credits)")


def test_business_report_tool_name():
    """Test that tool name is correct"""

    tool = BusinessReportTool(project_id="test_name")

    # Verify tool name
    assert tool.tool_name == "business_report"

    print("[OK] Tool name test passed")


if __name__ == "__main__":
    print("=" * 60)
    print("BUSINESS REPORT TOOL - UNIT TESTS")
    print("=" * 60)

    # Run all tests
    print("\n1. Testing basic execution...")
    result = test_business_report_basic()

    print("\n2. Testing input validation...")
    test_business_report_validation()

    print("\n3. Testing no web results scenario...")
    test_business_report_no_web_results()

    print("\n4. Testing no maps data scenario...")
    test_business_report_no_maps_data()

    print("\n5. Testing no data scenario...")
    test_business_report_no_data()

    print("\n6. Testing output formats...")
    test_business_report_output_formats()

    print("\n7. Testing price...")
    test_business_report_price()

    print("\n8. Testing tool name...")
    test_business_report_tool_name()

    # Print summary
    print(f"\n{'='*60}")
    print("BUSINESS REPORT TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {result.metadata['duration_seconds']:.1f} seconds")
    print(f"Price: ${result.metadata['price']}")
    print("\nOutput files:")
    for format_type, path in result.outputs.items():
        print(f"  {format_type:12s}: {path}")

    # Show markdown report excerpt
    markdown_path = result.outputs["markdown"]
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT (excerpt)")
        print(f"{'='*60}")
        print(content[:1500] + "...")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
