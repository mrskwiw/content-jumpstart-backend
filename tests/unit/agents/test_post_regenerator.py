"""Tests for Post Regeneration Agent"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.post_regenerator import PostRegenerator, RegenerationReason
from src.models.client_brief import ClientBrief, Platform
from src.models.post import Post
from src.models.quality_profile import QualityProfile
from src.models.template import Template, TemplateType


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client"""
    client = MagicMock()
    # Return content that meets quality requirements: 200+ words, statement CTA.
    # "Improved post content here." = 4 words, repeat 55 times = 220 words.
    # Ends with a statement CTA so should_regenerate does not loop.
    improved_content = (
        " ".join(["Improved post content here."] * 55) + "\n\nBook your appointment today."
    )
    client.generate_post_content.return_value = improved_content
    return client


@pytest.fixture
def sample_brief():
    """Create sample client brief"""
    return ClientBrief(
        company_name="Test Co",
        business_description="Software company",
        ideal_customer="Businesses",
        main_problem_solved="Inefficiency",
    )


@pytest.fixture
def sample_template():
    """Create sample template"""
    from src.models.template import TemplateDifficulty

    return Template(
        template_id=1,
        name="Test Template",
        template_type=TemplateType.PROBLEM_RECOGNITION,
        structure="Test structure [TOPIC]",
        best_for="Testing purposes",
        difficulty=TemplateDifficulty.FAST,
        requires_story=False,
        requires_data=False,
    )


@pytest.fixture
def quality_profile():
    """Create test quality profile"""
    from src.models.quality_profile import get_default_profile

    return get_default_profile("professional_linkedin")


class TestRegenerationReason:
    """Test RegenerationReason class"""

    def test_create_reason_with_value(self):
        """Test creating reason with current value"""
        reason = RegenerationReason("low_readability", "Too difficult", 25.5)

        assert reason.reason_type == "low_readability"
        assert reason.details == "Too difficult"
        assert reason.current_value == 25.5

    def test_create_reason_without_value(self):
        """Test creating reason without current value"""
        reason = RegenerationReason("missing_cta", "No call-to-action")

        assert reason.reason_type == "missing_cta"
        assert reason.details == "No call-to-action"
        assert reason.current_value is None

    def test_repr_with_value(self):
        """Test string representation with value"""
        reason = RegenerationReason("too_short", "Not enough words", 50)

        repr_str = repr(reason)

        assert "too_short" in repr_str
        assert "Not enough words" in repr_str
        assert "50" in repr_str
        assert "current:" in repr_str

    def test_repr_without_value(self):
        """Test string representation without value"""
        reason = RegenerationReason("weak_headline", "Needs improvement")

        repr_str = repr(reason)

        assert "weak_headline" in repr_str
        assert "Needs improvement" in repr_str
        assert "current:" not in repr_str


class TestPostRegeneratorInit:
    """Test PostRegenerator initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        regenerator = PostRegenerator()

        assert regenerator.client is not None
        assert regenerator.voice_metrics is not None
        assert regenerator.profile is not None
        assert regenerator.profile.profile_name == "professional_linkedin"

    def test_init_with_custom_client(self, mock_anthropic_client):
        """Test initialization with custom client"""
        regenerator = PostRegenerator(client=mock_anthropic_client)

        assert regenerator.client == mock_anthropic_client

    def test_init_with_custom_profile(self, quality_profile):
        """Test initialization with custom quality profile"""
        regenerator = PostRegenerator(quality_profile=quality_profile)

        assert regenerator.profile == quality_profile
        assert regenerator.profile.profile_name == "professional_linkedin"


class TestShouldRegenerate:
    """Test should_regenerate method"""

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_low_readability_triggers_regeneration(self, mock_voice_metrics, quality_profile):
        """Test low readability triggers regeneration"""
        # Mock readability below threshold
        mock_voice_metrics.return_value.calculate_readability.return_value = 30.0

        regenerator = PostRegenerator(quality_profile=quality_profile)
        # Statement CTA — "What do you think?" would add a post_ends_with_question
        # reason and make this a 2-reason post; use a proper statement CTA instead.
        good_content = (
            " ".join(["word"] * 210) + "\n\nBook your appointment today."
        )  # 214 words with statement CTA
        post = Post(
            content=good_content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert len(reasons) == 1
        assert reasons[0].reason_type == "low_readability"
        assert reasons[0].current_value == 30.0

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_high_readability_triggers_regeneration(self, mock_voice_metrics, quality_profile):
        """Test high readability triggers regeneration"""
        # Mock readability above threshold
        mock_voice_metrics.return_value.calculate_readability.return_value = 90.0

        regenerator = PostRegenerator(quality_profile=quality_profile)
        # Statement CTA — same reason as low_readability test above.
        good_content = (
            " ".join(["word"] * 210) + "\n\nBook your appointment today."
        )  # 214 words with statement CTA
        post = Post(
            content=good_content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert len(reasons) == 1
        assert reasons[0].reason_type == "high_readability"
        assert reasons[0].current_value == 90.0

    def test_too_short_triggers_regeneration(self, quality_profile):
        """Test post too short triggers regeneration"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Short.",  # ~1 word
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert any(r.reason_type == "too_short" for r in reasons)

    def test_too_long_triggers_regeneration(self, quality_profile):
        """Test post too long triggers regeneration"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        # Create very long content (>300 words)
        long_content = " ".join(["word"] * 350)
        post = Post(
            content=long_content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert any(r.reason_type == "too_long" for r in reasons)

    def test_missing_cta_triggers_regeneration(self, quality_profile):
        """Test missing CTA triggers regeneration when required"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="This post has no question or call to action.",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert any(r.reason_type == "missing_cta" for r in reasons)

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_good_post_no_regeneration(self, mock_voice_metrics, quality_profile):
        """Test good post doesn't trigger regeneration"""
        # Mock good readability (within 50–65 range)
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(quality_profile=quality_profile)
        # Statement CTA required — question endings trigger post_ends_with_question.
        good_content = (
            " ".join(["word"] * 210) + "\n\nBook your appointment today."
        )  # 214 words with statement CTA
        post = Post(
            content=good_content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is False
        assert len(reasons) == 0

    def test_mid_post_cta_triggers_cta_not_last(self, quality_profile):
        """A CTA that appears in the body (not the final line) must trigger cta_not_last."""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        body = " ".join(["Good content here."] * 15)  # ~45 words of body
        post = Post(
            content=f"Book a call today.\n\n{body}\n\nClosing thought.",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        _, reasons = regenerator.should_regenerate(post)
        assert any(r.reason_type == "cta_not_last" for r in reasons)

    def test_cta_question_form_triggers_cta_is_question(self, quality_profile):
        """A CTA on the last line written as a question must trigger cta_is_question."""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        body = " ".join(["Good content here."] * 15)  # ~45 words of body
        post = Post(
            content=f"{body}\n\nBook your appointment?",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        _, reasons = regenerator.should_regenerate(post)
        assert any(r.reason_type == "cta_is_question" for r in reasons)

    def test_generic_question_closer_on_non_exempt_template_triggers_regen(self, quality_profile):
        """Generic question closer ('What do you think?') on a non-exempt template
        must trigger post_ends_with_question so it is not silently shipped."""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="We help patients who avoid the dentist for years.\n\nWhat do you think?",
            template_id=1,
            template_name="The Problem-Recognition Post",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        reason_types = {r.reason_type for r in reasons}
        assert "post_ends_with_question" in reason_types

    def test_question_closer_on_exempt_template_does_not_trigger_regen(self, quality_profile):
        """A post from an engagement-question template (Question Post, Contrarian
        Take, Reader Q&A) that ends with a question must NOT trigger
        post_ends_with_question — those question endings are intentional."""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        exempt_cases = [
            ("The Question Post", 5),
            ("Question", 5),  # exact stored name (template_loader.py)
            ("Against the Grain", 3),  # exact stored name — no "contrarian" in it
            ("Against the Grain Contrarian Take", 3),
            ("Reader Question Response", 14),
            ("Reader Question", 14),  # exact stored name (template_loader.py)
        ]
        for template_name, template_id in exempt_cases:
            post = Post(
                content="Thoughtful body content here.\n\nWhat do you think?",
                template_id=template_id,
                template_name=template_name,
                variant=1,
                client_name="Test",
            )
            _, reasons = regenerator.should_regenerate(post)
            reason_types = {r.reason_type for r in reasons}
            assert (
                "post_ends_with_question" not in reason_types
            ), f"Template '{template_name}' should be exempt but was flagged"

    def test_weak_headline_from_review_reason(self, quality_profile):
        """Test weak headline extraction from review reason"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Post content here.",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
            needs_review=True,
            review_reason="The headline has only 1/3 engagement elements",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert any(r.reason_type == "weak_headline" for r in reasons)
        weak_headline_reason = [r for r in reasons if r.reason_type == "weak_headline"][0]
        assert weak_headline_reason.current_value == 1

    def test_multiple_issues_all_reported(self, quality_profile):
        """Test multiple issues are all reported"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Short.",  # Too short, no CTA
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        assert should_regen is True
        assert len(reasons) >= 2  # At least too_short and missing_cta
        reason_types = {r.reason_type for r in reasons}
        assert "too_short" in reason_types
        assert "missing_cta" in reason_types


class TestRegeneratePost:
    """Test regenerate_post method"""

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_creates_new_post(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test regeneration creates new post"""
        # Mock good readability for regenerated post (so it doesn't retry)
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        original_post = Post(
            content="Original content",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Too short", 10)]

        regenerated = regenerator.regenerate_post(
            original_post, sample_template, sample_brief, reasons, attempt=1
        )

        # Should call API
        mock_anthropic_client.generate_post_content.assert_called_once()

        # Should have new content
        assert regenerated.content != original_post.content
        assert "Improved post content" in regenerated.content

        # Variant should be incremented
        assert regenerated.variant == 101  # Original 1 + 100 * 1

    def test_regenerate_stops_at_max_attempts(
        self, mock_anthropic_client, sample_template, sample_brief, quality_profile
    ):
        """Test regeneration stops at max attempts"""
        quality_profile.max_attempts = 2
        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        original_post = Post(
            content="Original",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Too short")]

        # Attempt 3 should return original
        result = regenerator.regenerate_post(
            original_post, sample_template, sample_brief, reasons, attempt=3
        )

        assert result == original_post
        mock_anthropic_client.generate_post_content.assert_not_called()

    def test_regenerate_handles_api_error(
        self, mock_anthropic_client, sample_template, sample_brief, quality_profile
    ):
        """Test regeneration handles API errors gracefully"""
        mock_anthropic_client.generate_post_content.side_effect = Exception("API Error")

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        original_post = Post(
            content="Original",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Too short")]

        result = regenerator.regenerate_post(
            original_post, sample_template, sample_brief, reasons, attempt=1
        )

        # Should return original on error
        assert result == original_post

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_includes_improvement_prompt(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test regeneration includes improvement guidance"""
        # Mock good readability for regenerated post
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        original_post = Post(
            content="Short",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Too short", 5)]

        regenerator.regenerate_post(
            original_post, sample_template, sample_brief, reasons, attempt=1
        )

        # Check API call includes improvement guidance
        call_kwargs = mock_anthropic_client.generate_post_content.call_args.kwargs
        context = call_kwargs["context"]
        assert "variant_guidance" in context
        assert "Expand content" in context["variant_guidance"]


class TestBuildImprovementPrompt:
    """Test _build_improvement_prompt method"""

    def test_prompt_for_low_readability(self, quality_profile):
        """Test prompt building for low readability"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("low_readability", "Too difficult", 30.0)]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Simplify language" in prompt
        assert "30.0" in prompt
        assert str(quality_profile.min_readability) in prompt

    def test_prompt_for_high_readability(self, quality_profile):
        """Test prompt building for high readability"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("high_readability", "Too simple", 90.0)]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Add sophistication" in prompt
        assert "90.0" in prompt

    def test_prompt_for_too_short(self, quality_profile):
        """Test prompt building for too short"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Not enough", 50)]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Expand content" in prompt
        assert "50 words" in prompt
        assert str(quality_profile.min_words) in prompt

    def test_prompt_for_too_long(self, quality_profile):
        """Test prompt building for too long"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_long", "Too wordy", 400)]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Tighten content" in prompt
        assert "400 words" in prompt
        assert str(quality_profile.max_words) in prompt

    def test_prompt_for_missing_cta(self, quality_profile):
        """Test prompt building for missing CTA"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("missing_cta", "No call-to-action")]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Add a statement CTA" in prompt
        assert "question" in prompt

    def test_prompt_for_weak_headline(self, quality_profile):
        """Test prompt building for weak headline"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("weak_headline", "Needs engagement", 1)]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "Strengthen opening" in prompt
        assert str(quality_profile.min_engagement_score) in prompt

    def test_prompt_for_cta_not_last(self, quality_profile):
        """Test prompt building for mid-post CTA placement issue"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test", template_id=1, template_name="Test", variant=1, client_name="Test"
        )
        reasons = [RegenerationReason("cta_not_last", "CTA in body")]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        prompt = regenerator._build_improvement_prompt(post, reasons, brief)
        assert "Move the CTA to the very last line" in prompt

    def test_prompt_for_cta_is_question(self, quality_profile):
        """Test prompt building for CTA-written-as-question issue"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test", template_id=1, template_name="Test", variant=1, client_name="Test"
        )
        reasons = [RegenerationReason("cta_is_question", "CTA is a question")]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        prompt = regenerator._build_improvement_prompt(post, reasons, brief)
        assert "Rewrite the CTA as a statement" in prompt

    def test_prompt_for_post_ends_with_question(self, quality_profile):
        """Test prompt building for generic question-ending post"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test", template_id=1, template_name="Test", variant=1, client_name="Test"
        )
        reasons = [RegenerationReason("post_ends_with_question", "Post ends with ?")]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        prompt = regenerator._build_improvement_prompt(post, reasons, brief)
        assert "Rewrite the final line as a statement" in prompt

    def test_prompt_for_multiple_reasons(self, quality_profile):
        """Test prompt building for multiple reasons"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        post = Post(
            content="Test",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [
            RegenerationReason("too_short", "Not enough", 50),
            RegenerationReason("missing_cta", "No CTA"),
        ]
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        prompt = regenerator._build_improvement_prompt(post, reasons, brief)

        assert "CRITICAL" in prompt
        assert "Expand content" in prompt
        assert "Add a statement CTA" in prompt


class TestCleanContent:
    """Test _clean_content method"""

    def test_clean_removes_quotes(self):
        """Test cleaning removes surrounding quotes"""
        regenerator = PostRegenerator()
        content = '"This is quoted content"'

        cleaned = regenerator._clean_content(content)

        assert cleaned == "This is quoted content"
        assert not cleaned.startswith('"')
        assert not cleaned.endswith('"')

    def test_clean_removes_markdown_headers(self):
        """Test cleaning removes markdown headers"""
        regenerator = PostRegenerator()
        content = "# Header\n## Subheader\nContent here"

        cleaned = regenerator._clean_content(content)

        assert "# " not in cleaned
        assert "## " not in cleaned
        assert "Header" in cleaned
        assert "Subheader" in cleaned

    def test_clean_normalizes_line_breaks(self):
        """Test cleaning normalizes excessive line breaks"""
        regenerator = PostRegenerator()
        content = "Line 1\n\n\n\nLine 2"

        cleaned = regenerator._clean_content(content)

        assert "\n\n\n" not in cleaned
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned

    def test_clean_strips_whitespace(self):
        """Test cleaning strips leading/trailing whitespace"""
        regenerator = PostRegenerator()
        content = "   \n\n  Content here  \n\n   "

        cleaned = regenerator._clean_content(content)

        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")
        assert "Content here" in cleaned


class TestRegenerateFailedPosts:
    """Test regenerate_failed_posts method"""

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_no_failed_posts(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test batch regeneration with no failed posts"""
        # Mock good readability (within min_readability=50.0, max_readability=65.0)
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        # Create content with 210+ words and a statement CTA to meet all quality
        # requirements. question endings now trigger post_ends_with_question.
        good_content = (
            " ".join(["word"] * 210) + "\n\nBook your appointment today."
        )  # 214 words with statement CTA
        posts = [
            Post(
                content=good_content,
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
        ]

        regenerated, stats = regenerator.regenerate_failed_posts(
            posts, [sample_template], sample_brief
        )

        assert len(regenerated) == 1
        assert stats["total_posts"] == 1
        assert stats["posts_regenerated"] == 0
        assert stats["posts_improved"] == 0
        assert stats["posts_unchanged"] == 0

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_failed_posts_success(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test successful batch regeneration"""
        # Mock good readability for regenerated posts
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        # Short post without CTA
        posts = [
            Post(
                content="Short",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
        ]

        regenerated, stats = regenerator.regenerate_failed_posts(
            posts, [sample_template], sample_brief
        )

        assert len(regenerated) == 1
        assert stats["total_posts"] == 1
        assert stats["posts_regenerated"] >= 1

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_tracks_reason_stats(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test regeneration tracks reason statistics"""
        # Mock good readability for regenerated posts
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        posts = [
            Post(
                content="Short",
                template_id=1,
                template_name="Test1",
                variant=1,
                client_name="Test",
            ),
            Post(
                content="Also short",
                template_id=1,
                template_name="Test2",
                variant=1,
                client_name="Test",
            ),
        ]

        regenerated, stats = regenerator.regenerate_failed_posts(
            posts, [sample_template], sample_brief
        )

        assert "reasons" in stats
        assert "too_short" in stats["reasons"]
        assert stats["reasons"]["too_short"] >= 2  # Both posts are too short

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_skips_missing_template(
        self, mock_voice_metrics, mock_anthropic_client, sample_brief, quality_profile
    ):
        """Test regeneration skips posts with missing templates"""
        # Mock good readability
        mock_voice_metrics.return_value.calculate_readability.return_value = 60.0

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        posts = [
            Post(
                content="Short",
                template_id=999,
                template_name="Test",
                variant=1,
                client_name="Test",
            )  # No template 999
        ]
        templates = []  # Empty template list

        regenerated, stats = regenerator.regenerate_failed_posts(posts, templates, sample_brief)

        assert len(regenerated) == 1
        assert regenerated[0] == posts[0]  # Original post unchanged
        assert stats["posts_unchanged"] >= 1


class TestEdgeCases:
    """Test edge cases for improved coverage"""

    def test_weak_headline_malformed_reason_silent_fail(self, quality_profile):
        """Test malformed review_reason for headline check fails silently (lines 129-130)"""
        regenerator = PostRegenerator(quality_profile=quality_profile)
        # Malformed review reason that will cause parsing to fail
        post = Post(
            content="Post content here.",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
            needs_review=True,
            review_reason="headline has only xyz/3 engagement elements",  # Non-numeric score
        )

        should_regen, reasons = regenerator.should_regenerate(post)

        # Should NOT have weak_headline reason due to parsing failure
        weak_headline_reasons = [r for r in reasons if r.reason_type == "weak_headline"]
        assert len(weak_headline_reasons) == 0

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_retries_when_still_has_issues(
        self,
        mock_voice_metrics,
        quality_profile,
    ):
        """Test regeneration retries when regenerated post still has issues (lines 205-206)"""
        # First call returns bad readability (triggers retry)
        # Second call returns good readability (stops retry)
        mock_voice_metrics.return_value.calculate_readability.side_effect = [
            30.0,
            30.0,
            60.0,
        ]

        mock_client = MagicMock()
        # First regeneration returns content that's still too short
        # Second regeneration returns good content
        first_content = " ".join(["word"] * 50) + " What do you think?"  # 51 words - too short
        second_content = " ".join(["word"] * 170) + " What do you think?"  # 171 words - good
        mock_client.generate_post_content.side_effect = [first_content, second_content]

        regenerator = PostRegenerator(client=mock_client, quality_profile=quality_profile)
        from src.models.template import Template, TemplateType, TemplateDifficulty

        template = Template(
            template_id=1,
            name="Test",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="Test",
            best_for="Test",
            difficulty=TemplateDifficulty.FAST,
            requires_story=False,
            requires_data=False,
        )
        brief = ClientBrief(
            company_name="Test",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        original_post = Post(
            content="Short",
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        reasons = [RegenerationReason("too_short", "Too short", 5)]

        # Allow up to 3 attempts
        quality_profile.max_attempts = 3
        regenerator.regenerate_post(original_post, template, brief, reasons, attempt=1)

        # Should have called generate twice due to retry
        assert mock_client.generate_post_content.call_count >= 2

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_regenerate_failed_posts_tracks_unchanged_when_not_improved(
        self,
        mock_voice_metrics,
        mock_anthropic_client,
        sample_template,
        sample_brief,
        quality_profile,
    ):
        """Test regeneration tracks posts_unchanged when regeneration doesn't improve (lines 360-361)"""
        # Always return bad readability so regeneration doesn't help
        mock_voice_metrics.return_value.calculate_readability.return_value = 30.0

        # Return content that still has issues (too short)
        short_content = "Still short content here."
        mock_anthropic_client.generate_post_content.return_value = short_content

        # Set max_attempts to 1 so it doesn't keep retrying
        quality_profile.max_attempts = 1

        regenerator = PostRegenerator(client=mock_anthropic_client, quality_profile=quality_profile)
        posts = [
            Post(
                content="Original short",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
        ]

        regenerated, stats = regenerator.regenerate_failed_posts(
            posts, [sample_template], sample_brief
        )

        # Post was regenerated but not improved
        assert stats["posts_regenerated"] == 1
        # The regenerated post should still be in the list (even if not improved)
        assert len(regenerated) == 1


class TestGenericVoiceCheck:
    """BRAND-CORE-02 wiring: assess_post drives a generic_voice regeneration reason.

    Readability is mocked into the professional_linkedin passing band (50-65) so the
    genericity signal is isolated from the readability/length/CTA checks.
    """

    # ~205-word specific post, statement CTA — should read as a point of view.
    _SPECIFIC = (
        "3 words killed our onboarding conversion last quarter. "
        + (
            "We A/B tested the signup button copy for six weeks across twelve thousand "
            "visitors, splitting traffic evenly until the confidence interval closed. "
            "The clever, playful version everyone on the team expected to win lost badly. "
            "The boring, literal one that told people exactly what happens next won by "
            "thirty four percent on completed signups, and the gap held through the second "
            "month after we shipped it to everyone who landed on the page. When someone is "
            "deciding whether to trust you with their email address, they are not looking "
            "to be entertained by a clever turn of phrase they have to decode. They are "
            "looking to understand, plainly and quickly, what happens the moment they click "
            "the button in front of them, and whether the promise on the page will actually "
            "be kept once they are inside the product and the marketing copy is behind them. "
        )
        * 1
        + "\n\nShip the boring version and measure it for a month."
    )

    # ~205-word cliche/AI-tell-dense post, statement CTA — reads as generic AI.
    _GENERIC = (
        "In today's fast-paced digital world, businesses must leverage cutting-edge "
        "solutions to unlock synergy and supercharge their growth. "
        + (
            "It is important to note that in order to stay ahead of the curve, organizations "
            "need to think outside the box and take their strategy to the next level. At the "
            "end of the day, moving the needle requires a robust, scalable, and seamless "
            "approach that empowers stakeholders to drive impactful results. Whether you are "
            "a small startup or a large enterprise, the key takeaway is that you must embrace "
            "innovation and foster a culture of excellence. In conclusion, it is crucial to "
            "remember that success is a journey, not a destination, and that best-in-class "
            "companies are always looking for new ways to add value and delight their "
            "customers at every single touchpoint along the way. "
        )
        * 1
        + "\n\nContact us today to elevate your business."
    )

    def _post(self, content, platform=None):
        kwargs = dict(
            content=content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test",
        )
        if platform is not None:
            kwargs["target_platform"] = platform
        return Post(**kwargs)

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_generic_post_triggers_generic_voice_reason(self, mock_vm, quality_profile):
        mock_vm.return_value.calculate_readability.return_value = 58.0  # in-band
        assert quality_profile.check_genericity is True  # professional_linkedin default
        regenerator = PostRegenerator(quality_profile=quality_profile)

        should_regen, reasons = regenerator.should_regenerate(self._post(self._GENERIC))

        assert should_regen is True
        assert any(r.reason_type == "generic_voice" for r in reasons)

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_specific_post_has_no_generic_voice_reason(self, mock_vm, quality_profile):
        mock_vm.return_value.calculate_readability.return_value = 58.0
        regenerator = PostRegenerator(quality_profile=quality_profile)

        _, reasons = regenerator.should_regenerate(self._post(self._SPECIFIC))

        assert all(r.reason_type != "generic_voice" for r in reasons)

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_check_disabled_never_flags_generic(self, mock_vm):
        # A profile with check_genericity off must not add a generic_voice reason,
        # even for blatantly generic content.
        mock_vm.return_value.calculate_readability.return_value = 58.0
        profile = QualityProfile(
            profile_name="no_generic_check",
            description="d",
            min_words=150,
            max_words=500,
            require_cta=False,
            check_genericity=False,
        )
        regenerator = PostRegenerator(quality_profile=profile)

        _, reasons = regenerator.should_regenerate(self._post(self._GENERIC))

        assert all(r.reason_type != "generic_voice" for r in reasons)

    @patch("src.agents.post_regenerator.VoiceMetrics")
    def test_platform_is_mapped_from_post(self, mock_vm, quality_profile):
        # target_platform drives the assess_post platform arg; a Twitter post must
        # still be evaluated (no crash) and use its own platform.
        mock_vm.return_value.calculate_readability.return_value = 58.0
        regenerator = PostRegenerator(quality_profile=quality_profile)

        post = self._post(self._GENERIC, platform=Platform.TWITTER)
        should_regen, reasons = regenerator.should_regenerate(post)

        assert isinstance(should_regen, bool)  # completes without error
