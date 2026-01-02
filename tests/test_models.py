"""Unit tests for data models"""

import pytest

from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.template import Template, TemplateDifficulty, TemplateType


class TestTemplate:
    """Tests for Template model"""

    def test_template_creation(self):
        """Test creating a valid template"""
        template = Template(
            template_id=1,
            name="Test Template",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="[HOOK] test [CTA]",
            best_for="Testing purposes",
            difficulty=TemplateDifficulty.FAST,
        )
        assert template.template_id == 1
        assert template.name == "Test Template"
        assert template.template_type == TemplateType.PROBLEM_RECOGNITION


class TestClientBrief:
    """Tests for ClientBrief model"""

    def test_brief_creation(self):
        """Test creating a valid client brief"""
        brief = ClientBrief(
            company_name="Test Company",
            business_description="A test business",
            ideal_customer="Test customers",
            main_problem_solved="Solving test problems",
            brand_personality=[TonePreference.APPROACHABLE],
            target_platforms=[Platform.LINKEDIN],
        )
        assert brief.company_name == "Test Company"
        assert TonePreference.APPROACHABLE in brief.brand_personality
        assert Platform.LINKEDIN in brief.target_platforms

    def test_to_context_dict(self):
        """Test converting brief to context dictionary"""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Testing",
            ideal_customer="Testers",
            main_problem_solved="Test problems",
        )
        context = brief.to_context_dict()
        assert "company_name" in context
        assert context["company_name"] == "Test Co"


class TestPost:
    """Tests for Post model"""

    def test_post_creation(self):
        """Test creating a valid post"""
        content = "This is a test post with enough words to pass validation. " * 10
        post = Post(
            content=content,
            template_id=1,
            template_name="Test Template",
            client_name="Test Client",
        )
        assert post.template_id == 1
        assert post.word_count > 0
        assert post.character_count > 0

    def test_post_too_short(self):
        """Test that short posts are allowed but flagged with low word count"""
        # Post model allows short content - validation happens at QA stage
        post = Post(
            content="Too short",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        # Word count should be calculated
        assert post.word_count == 2
        assert post.character_count == len("Too short")

    def test_cta_detection(self):
        """Test CTA detection"""
        content = "This is a test post with many words to meet minimum. " * 10
        content += "What do you think? Reply below!"

        post = Post(
            content=content,
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_flag_for_review(self):
        """Test flagging post for review"""
        content = "This is a test post with enough words to pass validation. " * 10
        post = Post(
            content=content,
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        post.flag_for_review("Test reason")
        assert post.needs_review is True
        assert post.review_reason == "Test reason"
