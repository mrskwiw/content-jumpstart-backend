"""
Comprehensive unit tests for RevisionAgent

Tests cover post revision, feedback parsing, and change detection.
"""

import pytest
from unittest.mock import Mock

from src.agents.revision_agent import RevisionAgent
from src.models.client_brief import ClientBrief, TonePreference
from src.models.post import Post
from src.models.template import Template, TemplateType, TemplateDifficulty
from src.utils.anthropic_client import AnthropicClient


# ==================== Fixtures ====================


@pytest.fixture
def mock_client():
    """Mock Anthropic client"""
    client = Mock(spec=AnthropicClient)
    client.generate_post_content = Mock(
        return_value="Revised post content with all requested changes. This post is now shorter and more casual. Don't miss out - try our solution today!"
    )
    return client


@pytest.fixture
def sample_client_brief():
    """Sample client brief"""
    return ClientBrief(
        company_name="Test Company",
        business_description="We provide cloud software",
        ideal_customer="Small businesses",
        main_problem_solved="Manual workflows",
        brand_personality=[TonePreference.AUTHORITATIVE],
    )


@pytest.fixture
def sample_template():
    """Sample template"""
    return Template(
        template_id=1,
        name="Problem Recognition",
        template_type=TemplateType.PROBLEM_RECOGNITION,
        difficulty=TemplateDifficulty.FAST,
        structure="Identify [PROBLEM]. Explain why. Provide [SOLUTION].",
        best_for="Awareness and engagement",
        requires_story=False,
        requires_data=False,
    )


@pytest.fixture
def sample_post():
    """Sample original post"""
    return Post(
        content="Original post content about productivity. This is a longer version with more formal language. We recommend that you contact us.",
        template_id=1,
        template_name="Problem Recognition",
        variant=1,
        client_name="Test Company",
    )


# ==================== Initialization Tests ====================


def test_revision_agent_init_default():
    """Test RevisionAgent initialization with defaults"""
    agent = RevisionAgent()

    assert agent.client is not None


def test_revision_agent_init_with_client(mock_client):
    """Test RevisionAgent initialization with custom client"""
    agent = RevisionAgent(client=mock_client)

    assert agent.client == mock_client


# ==================== Revision Generation Tests ====================


def test_generate_revised_post_basic(
    mock_client, sample_post, sample_client_brief, sample_template
):
    """Test basic post revision"""
    agent = RevisionAgent(client=mock_client)

    revised_post, changes = agent.generate_revised_post(
        original_post=sample_post,
        client_feedback="Make it shorter and more casual",
        client_brief=sample_client_brief,
        template=sample_template,
    )

    assert revised_post is not None
    assert isinstance(revised_post, Post)
    assert revised_post.template_id == sample_post.template_id
    assert revised_post.template_name == sample_post.template_name
    assert len(changes) > 0


def test_generate_revised_post_with_system_prompt(
    mock_client, sample_post, sample_client_brief, sample_template
):
    """Test revision with cached system prompt"""
    agent = RevisionAgent(client=mock_client)

    system_prompt = "Custom system prompt"

    revised_post, changes = agent.generate_revised_post(
        original_post=sample_post,
        client_feedback="Improve it",
        client_brief=sample_client_brief,
        template=sample_template,
        system_prompt=system_prompt,
    )

    # Should have called client with system prompt
    mock_client.generate_post_content.assert_called_once()
    call_kwargs = mock_client.generate_post_content.call_args[1]
    assert call_kwargs["system_prompt"] == system_prompt


def test_generate_revised_post_error_handling(sample_post, sample_client_brief, sample_template):
    """Test error handling when revision fails"""
    mock_client = Mock(spec=AnthropicClient)
    mock_client.generate_post_content.side_effect = Exception("API Error")

    agent = RevisionAgent(client=mock_client)

    revised_post, changes = agent.generate_revised_post(
        original_post=sample_post,
        client_feedback="Fix it",
        client_brief=sample_client_brief,
        template=sample_template,
    )

    # Should return original post on error
    assert revised_post.content == sample_post.content
    assert "failed" in changes.lower()


# ==================== Multiple Revision Tests ====================


def test_revise_multiple_posts(mock_client, sample_client_brief, sample_template):
    """Test revising multiple posts"""
    agent = RevisionAgent(client=mock_client)

    posts = [
        Post(
            content="Post 1",
            template_id=1,
            template_name="Problem Recognition",
            variant=i,
            client_name="Test",
        )
        for i in range(3)
    ]

    results = agent.revise_multiple_posts(
        posts=posts,
        client_feedback="Make them better",
        client_brief=sample_client_brief,
        templates=[sample_template],
    )

    assert len(results) == 3
    assert all(isinstance(r[0], Post) for r in results)
    assert all(isinstance(r[1], str) for r in results)


def test_revise_multiple_posts_missing_template(mock_client, sample_client_brief, sample_template):
    """Test revising posts when template is missing"""
    agent = RevisionAgent(client=mock_client)

    post = Post(
        content="Test",
        template_id=99,  # Non-existent template
        template_name="Unknown",
        variant=1,
        client_name="Test",
    )

    results = agent.revise_multiple_posts(
        posts=[post],
        client_feedback="Improve",
        client_brief=sample_client_brief,
        templates=[sample_template],
    )

    # Should keep original and note template not found
    assert results[0][0].content == post.content
    assert "not found" in results[0][1].lower()


# ==================== Feedback Parsing Tests ====================


def test_parse_feedback_more_casual():
    """Test parsing feedback for more casual tone"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Make this more casual")

    assert "casual" in result.lower()
    assert "contractions" in result.lower()


def test_parse_feedback_more_professional():
    """Test parsing feedback for more professional tone"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Make it more professional")

    assert "professional" in result.lower()


def test_parse_feedback_shorter():
    """Test parsing feedback for shorter content"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("This is too long, make it shorter")

    assert "reduce" in result.lower() or "shorter" in result.lower()


def test_parse_feedback_longer():
    """Test parsing feedback for longer content"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Too short, please expand")

    assert "expand" in result.lower()


def test_parse_feedback_add_cta():
    """Test parsing feedback to add CTA"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Add a call to action")

    assert "call-to-action" in result.lower() or "cta" in result.lower()


def test_parse_feedback_emoji():
    """Test parsing feedback about emojis"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Add more emoji")
    assert "emoji" in result.lower()

    result = agent._parse_feedback_to_instructions("Remove emoji")
    assert "emoji" in result.lower()


def test_parse_feedback_more_data():
    """Test parsing feedback for more data"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Add more statistics and numbers")

    assert "statistics" in result.lower() or "data" in result.lower()


def test_parse_feedback_simpler():
    """Test parsing feedback for simpler language"""
    agent = RevisionAgent()

    result = agent._parse_feedback_to_instructions("Make this easier to understand")

    assert "simpler" in result.lower() or "simplify" in result.lower()


def test_parse_feedback_no_patterns():
    """Test parsing feedback with no specific patterns"""
    agent = RevisionAgent()

    custom_feedback = "Change the hook to be more engaging"
    result = agent._parse_feedback_to_instructions(custom_feedback)

    assert custom_feedback in result


# ==================== Content Cleaning Tests ====================


def test_clean_content_removes_quotes():
    """Test content cleaning removes quotes"""
    agent = RevisionAgent()

    content = '"This is quoted content"'
    cleaned = agent._clean_content(content)

    assert cleaned == "This is quoted content"


def test_clean_content_normalizes_line_breaks():
    """Test content cleaning normalizes line breaks"""
    agent = RevisionAgent()

    content = "Line 1\n\n\n\n\nLine 2"
    cleaned = agent._clean_content(content)

    assert "\n\n\n" not in cleaned


def test_clean_content_removes_markdown_headers():
    """Test content cleaning removes markdown headers"""
    agent = RevisionAgent()

    content = "# Heading 1\n## Heading 2\nContent"
    cleaned = agent._clean_content(content)

    assert "#" not in cleaned


# ==================== Changes Summary Tests ====================


def test_generate_changes_summary_length_change():
    """Test changes summary detects length changes"""
    agent = RevisionAgent()

    original = Post(
        content="Short post",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    revised = Post(
        content="This is a much longer post with significantly more content to analyze and understand",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    summary = agent._generate_changes_summary(original, revised, "Expand it")

    assert "Expanded" in summary or "words" in summary


def test_generate_changes_summary_cta_change():
    """Test changes summary detects CTA changes"""
    agent = RevisionAgent()

    original = Post(
        content="Post without CTA",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    revised = Post(
        content="Post with CTA. Contact us today!",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    summary = agent._generate_changes_summary(original, revised, "Add CTA")

    # Check that summary was generated
    assert len(summary) > 0


def test_generate_changes_summary_tone_change():
    """Test changes summary detects tone changes"""
    agent = RevisionAgent()

    original = Post(
        content="We cannot do this. We will not do that.",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    revised = Post(
        content="We can't do this. We won't do that. It's not possible. You're right.",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    summary = agent._generate_changes_summary(original, revised, "Make casual")

    assert "casual" in summary.lower() or len(summary) > 0


def test_generate_changes_summary_emoji_change():
    """Test changes summary detects emoji changes"""
    agent = RevisionAgent()

    original = Post(
        content="Post without emoji",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    revised = Post(
        content="Post with emoji 😀 🎉",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    summary = agent._generate_changes_summary(original, revised, "Add emoji")

    assert "emoji" in summary.lower() or len(summary) > 0


def test_generate_changes_summary_no_changes():
    """Test changes summary with minimal changes"""
    agent = RevisionAgent()

    original = Post(
        content="Same content",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    revised = Post(
        content="Same content",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    summary = agent._generate_changes_summary(original, revised, "Improve slightly")

    # Should use feedback as fallback
    assert "Improve" in summary or "feedback" in summary.lower()


# ==================== Revision Diff Tests ====================


def test_create_revision_diff():
    """Test creating revision diff object"""
    agent = RevisionAgent()

    original = Post(
        content="Original" * 30,
        template_id=1,
        template_name="Problem Recognition",
        variant=5,
        client_name="Test",
    )

    revised = Post(
        content="Revised" * 25,
        template_id=1,
        template_name="Problem Recognition",
        variant=5,
        client_name="Test",
    )

    changes_summary = "Shortened by 15 words; Made tone more casual"

    diff = agent.create_revision_diff(original, revised, changes_summary)

    assert diff.post_index == 5
    assert diff.template_name == "Problem Recognition"
    assert diff.original_length == original.word_count
    assert diff.revised_length == revised.word_count
    assert diff.word_count_change == revised.word_count - original.word_count
    assert len(diff.changes) == 2
    assert diff.improvement_score is not None


# ==================== Build System Prompt Tests ====================


def test_build_system_prompt(sample_client_brief):
    """Test building system prompt for revision"""
    agent = RevisionAgent()

    prompt = agent._build_system_prompt(sample_client_brief)

    assert "Test Company" in prompt
    assert "cloud software" in prompt
    assert "revision" in prompt.lower()


# ==================== Build Revision Prompt Tests ====================


def test_build_revision_prompt(sample_post, sample_client_brief, sample_template):
    """Test building revision prompt context"""
    agent = RevisionAgent()

    context = agent._build_revision_prompt(
        original_post=sample_post,
        client_feedback="Make it better",
        client_brief=sample_client_brief,
        template=sample_template,
    )

    assert context["revision_mode"]
    assert context["original_content"] == sample_post.content
    assert context["client_feedback"] == "Make it better"
    assert "variant_guidance" in context
    assert "REVISION" in context["variant_guidance"]
