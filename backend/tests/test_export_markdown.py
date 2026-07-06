"""Tests for markdown export functionality"""

import pytest
from backend.services.export_service import _generate_markdown
from backend.models.client import Client
from backend.models.project import Project
from backend.models.post import Post


@pytest.fixture
def mock_client():
    """Create a mock client"""
    client = Client(id="test-client-123", name="Test Client Co.", email="test@example.com")
    return client


@pytest.fixture
def mock_project():
    """Create a mock project"""
    project = Project(
        id="test-project-456", name="Spring Campaign 2026", client_id="test-client-123"
    )
    return project


@pytest.fixture
def mock_posts():
    """Create mock posts"""
    posts = [
        Post(
            id="post-1",
            content="This is the first test post about productivity.",
            template_name="Problem Recognition",
            target_platform="LinkedIn",
            word_count=50,
            has_cta=True,
            readability_score=75.5,
        ),
        Post(
            id="post-2",
            content="This is the second test post with a great insight.",
            template_name="Statistic",
            target_platform="Twitter",
            word_count=35,
            has_cta=False,
            readability_score=82.3,
        ),
        Post(
            id="post-3",
            content="Final post without platform specified.",
            template_name="Question",
            target_platform=None,
            word_count=40,
            has_cta=True,
            readability_score=None,
        ),
    ]
    return posts


@pytest.mark.asyncio
async def test_generate_markdown_basic(mock_posts, mock_client, mock_project, tmp_path):
    """Test basic markdown generation"""
    output_path = tmp_path / "test_deliverable.md"

    result_path, file_size = await _generate_markdown(
        posts=mock_posts,
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    # Verify file was created
    assert result_path.exists()
    assert file_size > 0

    # Read content
    content = result_path.read_text(encoding="utf-8")

    # Verify YAML frontmatter
    assert content.startswith("---")
    assert "title: 30-Day Content Jumpstart Deliverable" in content
    assert f"client: {mock_client.name}" in content
    assert f"project: {mock_project.name}" in content
    assert "total_posts: 3" in content

    # Verify markdown structure
    assert "# 30-Day Content Jumpstart Deliverable" in content
    assert "## Table of Contents" in content
    assert "## Your Posts" in content

    # Verify all posts are included
    for i, post in enumerate(mock_posts, 1):
        assert f"### Post {i}:" in content
        assert post.content in content or f"> {post.content}" in content

    # Verify metadata table
    assert "| Property | Value |" in content
    assert "|----------|-------|" in content

    # Verify platform info
    assert "| **Platform** | LinkedIn |" in content
    assert "| **Platform** | Microblog |" in content  # "twitter" -> "Microblog" display name

    # Verify CTA info
    assert "✅ Yes" in content
    assert "❌ No" in content

    # Verify readability scores
    assert "75.5" in content
    assert "82.3" in content


@pytest.mark.asyncio
async def test_generate_markdown_table_of_contents(mock_posts, mock_client, mock_project, tmp_path):
    """Test table of contents generation"""
    output_path = tmp_path / "test_toc.md"

    result_path, _ = await _generate_markdown(
        posts=mock_posts,
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    content = result_path.read_text(encoding="utf-8")

    # Verify TOC links
    assert "1. [Post 1: Problem Recognition (LinkedIn)](#post-1)" in content
    assert "2. [Post 2: Statistic (Microblog)](#post-2)" in content
    assert "3. [Post 3: Question](#post-3)" in content  # No platform

    # Verify anchor targets
    assert "### Post 1: Problem Recognition {#post-1}" in content
    assert "### Post 2: Statistic {#post-2}" in content
    assert "### Post 3: Question {#post-3}" in content


@pytest.mark.asyncio
async def test_generate_markdown_content_blockquote(
    mock_posts, mock_client, mock_project, tmp_path
):
    """Test that post content is formatted as blockquote"""
    output_path = tmp_path / "test_blockquote.md"

    result_path, _ = await _generate_markdown(
        posts=mock_posts,
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    content = result_path.read_text(encoding="utf-8")

    # Verify content is in blockquote format
    assert "#### Content" in content
    assert "> This is the first test post about productivity." in content
    assert "> This is the second test post with a great insight." in content
    assert "> Final post without platform specified." in content


@pytest.mark.asyncio
async def test_generate_markdown_metadata_table(mock_posts, mock_client, mock_project, tmp_path):
    """Test metadata table generation"""
    output_path = tmp_path / "test_metadata.md"

    result_path, _ = await _generate_markdown(
        posts=mock_posts,
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    content = result_path.read_text(encoding="utf-8")

    # Verify metadata for post with all fields
    assert "| **Word Count** | 50 |" in content
    assert "| **Has CTA** | ✅ Yes |" in content
    assert "| **Readability Score** | 75.5 |" in content

    # Verify metadata for post without readability score
    assert "| **Word Count** | 40 |" in content

    # Verify N/A handling isn't present (we show actual values or skip)
    # Posts should always have word_count in the real system


@pytest.mark.asyncio
async def test_generate_markdown_footer(mock_posts, mock_client, mock_project, tmp_path):
    """Test footer generation"""
    output_path = tmp_path / "test_footer.md"

    result_path, _ = await _generate_markdown(
        posts=mock_posts,
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    content = result_path.read_text(encoding="utf-8")

    # Verify footer
    assert content.endswith("*Generated by 30-Day Content Jumpstart*\n")


@pytest.mark.asyncio
async def test_generate_markdown_empty_posts(mock_client, mock_project, tmp_path):
    """Test markdown generation with no posts"""
    output_path = tmp_path / "test_empty.md"

    result_path, file_size = await _generate_markdown(
        posts=[],
        client=mock_client,
        project=mock_project,
        output_path=output_path,
        include_audit_log=False,
        db=None,
    )

    # Should still create a valid file
    assert result_path.exists()
    assert file_size > 0

    content = result_path.read_text(encoding="utf-8")

    # Should have header and metadata
    assert "# 30-Day Content Jumpstart Deliverable" in content
    # With no posts, the export omits the post-count frontmatter and the posts
    # section by design (`if posts:` guards; the public path also flips such an
    # export to research-style). So neither total_posts nor "Your Posts" appears.
    assert "total_posts" not in content
    assert "## Your Posts" not in content
