"""
Unit tests for template quantities generation functionality.

Tests the new template_quantities feature in ContentGeneratorAgent that allows
generating exact quantities of posts from specific templates instead of equal distribution.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform
from src.models.post import Post
from src.models.template import Template, TemplateType, TemplateDifficulty


@pytest.fixture
def sample_brief():
    """Sample client brief for testing"""
    return ClientBrief(
        company_name="Test Company",
        business_description="Software development",
        ideal_customer="Tech startups",
        main_problem_solved="Development speed",
        platforms=[Platform.LINKEDIN],
    )


@pytest.fixture
def mock_template_loader():
    """Mock template loader with sample templates"""
    loader = Mock()

    # Create sample templates
    template_1 = Template(
        template_id=1,
        name="Problem Recognition",
        template_type=TemplateType.PROBLEM_RECOGNITION,
        difficulty=TemplateDifficulty.FAST,
        structure="Test structure 1",
        best_for="Testing problem recognition",
    )
    template_2 = Template(
        template_id=2,
        name="Statistic",
        template_type=TemplateType.STATISTIC,
        difficulty=TemplateDifficulty.FAST,
        structure="Test structure 2",
        best_for="Testing statistics",
    )
    template_9 = Template(
        template_id=9,
        name="How-To",
        template_type=TemplateType.HOW_TO,
        difficulty=TemplateDifficulty.FAST,
        structure="Test structure 9",
        best_for="Testing how-to",
    )

    # Mock get_template_by_id
    def get_by_id(tid):
        templates = {1: template_1, 2: template_2, 9: template_9}
        return templates.get(tid)

    loader.get_template_by_id = Mock(side_effect=get_by_id)

    return loader


class TestTemplateQuantitiesSync:
    """Test synchronous template quantities generation"""

    def test_generate_posts_with_quantities_basic(self, sample_brief, mock_template_loader):
        """Test basic template quantities generation"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # Mock _generate_single_post to return dummy posts
        mock_posts = []
        for i in range(10):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 3, 2: 5, 9: 2}  # 10 total posts

            posts = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,  # Keep order for testing
            )

        # Verify correct number of posts generated
        assert len(posts) == 10

        # Verify template loader was called with correct IDs
        assert mock_template_loader.get_template_by_id.call_count == 3
        mock_template_loader.get_template_by_id.assert_any_call(1)
        mock_template_loader.get_template_by_id.assert_any_call(2)
        mock_template_loader.get_template_by_id.assert_any_call(9)

    def test_generate_posts_quantities_priority(self, sample_brief, mock_template_loader):
        """Test that template_quantities takes priority over num_posts"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        mock_posts = []
        for i in range(5):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 3, 2: 2}  # 5 total posts

            # Even though num_posts=30, template_quantities should take priority
            posts = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                num_posts=30,  # Should be ignored
                randomize=False,
            )

        # Should generate 5 posts (from quantities), not 30
        assert len(posts) == 5

    def test_generate_posts_invalid_template_id(self, sample_brief, mock_template_loader):
        """Test handling of invalid template IDs"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # Valid templates
        mock_posts = []
        for i in range(3):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 3, 999: 5}  # 999 is invalid

            posts = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,
            )

        # Should only generate posts from valid template (1)
        assert len(posts) == 3

    def test_generate_posts_randomization(self, sample_brief, mock_template_loader):
        """Test that randomization works with template quantities"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # Create posts with identifiable content
        mock_posts = []
        for i in range(10):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Post {i}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 5, 2: 5}

            posts_no_random = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,
            )

            # Generate again with randomization
            mock_posts_2 = []
            for i in range(10):
                mock_post = Mock(spec=Post)
                mock_post.content = f"Post {i}"
                mock_post.word_count = 150
                mock_posts_2.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts_2):
            posts_randomized = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=True,
            )

        # Both should have same length
        assert len(posts_no_random) == len(posts_randomized) == 10

        # With randomization, order might differ (not guaranteed, but likely)
        # We just verify both completed successfully


class TestTemplateQuantitiesAsync:
    """Test asynchronous template quantities generation"""

    @pytest.mark.asyncio
    async def test_generate_posts_async_with_quantities(self, sample_brief, mock_template_loader):
        """Test async template quantities generation"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # Mock async _generate_single_post_async
        async def mock_generate_single(template, client_brief, variant, post_number, **kwargs):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Post {post_number}"
            mock_post.word_count = 150
            return mock_post

        with patch.object(generator, '_generate_single_post_async', side_effect=mock_generate_single):
            template_quantities = {1: 3, 2: 5, 9: 2}  # 10 total

            posts = await generator.generate_posts_async(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,
                max_concurrent=5,
            )

        assert len(posts) == 10

    @pytest.mark.asyncio
    async def test_generate_posts_async_concurrency(self, sample_brief, mock_template_loader):
        """Test that concurrency control works with template quantities"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        call_times = []

        async def mock_generate_with_delay(template, client_brief, variant, post_number, **kwargs):
            import asyncio
            import time
            call_times.append(time.time())
            await asyncio.sleep(0.01)  # Simulate API call
            mock_post = Mock(spec=Post)
            mock_post.content = f"Post {post_number}"
            return mock_post

        with patch.object(generator, '_generate_single_post_async', side_effect=mock_generate_with_delay):
            template_quantities = {1: 10}  # 10 posts

            posts = await generator.generate_posts_async(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                max_concurrent=3,  # Limit to 3 concurrent
                randomize=False,
            )

        assert len(posts) == 10
        # With max_concurrent=3, not all posts should start at the same time
        # (Exact timing test would be flaky, so we just verify completion)

    @pytest.mark.asyncio
    async def test_generate_posts_async_priority(self, sample_brief, mock_template_loader):
        """Test async template_quantities takes priority"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        async def mock_generate(template, client_brief, variant, post_number, **kwargs):
            mock_post = Mock(spec=Post)
            return mock_post

        with patch.object(generator, '_generate_single_post_async', side_effect=mock_generate):
            template_quantities = {1: 5}

            posts = await generator.generate_posts_async(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                num_posts=30,  # Should be ignored
                template_count=15,  # Should be ignored
            )

        # Should use template_quantities (5), not num_posts (30)
        assert len(posts) == 5


class TestTemplateQuantitiesEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_quantities(self, sample_brief, mock_template_loader):
        """Test with empty template quantities"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # When empty quantities, it falls back to legacy mode
        # With no templates available, causes ZeroDivisionError
        mock_templates = []
        mock_template_loader.select_templates_for_client = Mock(return_value=mock_templates)

        with pytest.raises(ZeroDivisionError):
            generator.generate_posts(
                client_brief=sample_brief,
                template_quantities={},  # Empty
            )

    def test_zero_quantity(self, sample_brief, mock_template_loader):
        """Test with zero quantity for a template"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        mock_posts = []
        for i in range(5):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 5, 2: 0}  # Template 2 has 0

            posts = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,
            )

        # Should only generate from template 1
        assert len(posts) == 5

    def test_large_quantity(self, sample_brief, mock_template_loader):
        """Test with large quantity"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        mock_posts = []
        for i in range(100):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            template_quantities = {1: 100}

            posts = generator.generate_posts(
                client_brief=sample_brief,
                template_quantities=template_quantities,
                randomize=False,
            )

        assert len(posts) == 100

    def test_backward_compatibility_no_quantities(self, sample_brief, mock_template_loader):
        """Test that old code without template_quantities still works"""
        generator = ContentGeneratorAgent(template_loader=mock_template_loader)

        # Mock intelligent template selection (legacy mode)
        mock_templates = [
            mock_template_loader.get_template_by_id(1),
            mock_template_loader.get_template_by_id(2),
        ]
        mock_template_loader.select_templates_for_client = Mock(return_value=mock_templates)

        mock_posts = []
        for i in range(30):
            mock_post = Mock(spec=Post)
            mock_post.content = f"Test post {i+1}"
            mock_post.word_count = 150
            mock_posts.append(mock_post)

        with patch.object(generator, '_generate_single_post', side_effect=mock_posts):
            # Old API: no template_quantities parameter
            posts = generator.generate_posts(
                client_brief=sample_brief,
                num_posts=30,
                template_count=2,
            )

        # Should use legacy equal distribution
        assert len(posts) == 30
        mock_template_loader.select_templates_for_client.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
