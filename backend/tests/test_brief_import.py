"""
Tests for brief file import/parsing endpoints
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path


def test_parse_valid_brief(client: TestClient):
    """Test parsing a valid brief file"""
    # Get sample brief
    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    brief_path = fixtures_dir / "sample_brief.txt"

    if not brief_path.exists():
        pytest.skip(f"Sample brief not found at {brief_path}")

    with open(brief_path, "rb") as f:
        response = client.post(
            "/api/briefs/parse",
            files={"file": ("sample_brief.txt", f, "text/plain")},
        )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["success"] is True
    assert "fields" in data
    assert "warnings" in data
    assert "metadata" in data

    # Verify metadata
    assert data["metadata"]["filename"] == "sample_brief.txt"
    assert "parseTimeMs" in data["metadata"]
    assert data["metadata"]["fieldsTotal"] == 8

    # Verify at least some fields were extracted
    assert len(data["fields"]) == 8
    assert "companyName" in data["fields"]
    assert "businessDescription" in data["fields"]

    # Verify field structure
    for field_name, field_data in data["fields"].items():
        assert "value" in field_data
        assert "confidence" in field_data
        assert field_data["confidence"] in ["high", "medium", "low"]


def test_parse_invalid_file_type(client: TestClient):
    """Test rejection of invalid file types"""
    response = client.post(
        "/api/briefs/parse",
        files={"file": ("brief.pdf", b"PDF content", "application/pdf")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["code"] == "INVALID_FILE_TYPE"
    assert "Only .txt and .md files are supported" in data["detail"]["message"]


def test_parse_file_too_large(client: TestClient):
    """Test rejection of files that are too large"""
    # Create a file larger than 50KB
    large_content = b"x" * (51 * 1024)  # 51KB

    response = client.post(
        "/api/briefs/parse",
        files={"file": ("large_brief.txt", large_content, "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["code"] == "FILE_TOO_LARGE"
    assert "must be less than 50KB" in data["detail"]["message"]


def test_parse_invalid_utf8(client: TestClient):
    """Test rejection of files with invalid UTF-8 encoding"""
    # Create invalid UTF-8 bytes
    invalid_utf8 = b"Hello \xff\xfe World"

    response = client.post(
        "/api/briefs/parse",
        files={"file": ("invalid.txt", invalid_utf8, "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["code"] == "ENCODING_ERROR"
    assert "must be UTF-8 encoded" in data["detail"]["message"]


def test_parse_requires_authentication(client: TestClient):
    """Test that parsing endpoint requires authentication"""
    # Create a client without authentication
    from main import app

    unauthenticated_client = TestClient(app)

    # Try to parse without auth
    response = unauthenticated_client.post(
        "/api/briefs/parse",
        files={"file": ("brief.txt", b"content", "text/plain")},
    )

    # Should be unauthorized
    assert response.status_code == 401


def test_confidence_scoring():
    """Test confidence scoring logic"""
    # This tests the _add_confidence_scores function indirectly
    # by verifying the response structure from a real parse

    # Note: This would require a TestClient with auth
    # Skipping for now since confidence scoring is tested in unit tests
    pytest.skip("Confidence scoring tested via unit tests")
