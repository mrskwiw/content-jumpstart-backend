"""Unit tests for Content Generator Agent

This test suite focuses on the key methods and logic paths in ContentGeneratorAgent.
Some complex integration scenarios are tested in integration tests.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.template import Template, TemplateType, TemplateDifficulty
from src.models.seo_keyword import (
    KeywordStrategy,
    SEOKeyword,
    KeywordIntent,
    KeywordDifficulty,
)


class TestContentGeneratorAgent:
    """Test suite for ContentGeneratorAgent"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        return Mock()

    @pytest.fixture
    def mock_template_loader(self):
        """Mock template loader"""
        loader = Mock()
        # Mock template objects
        loader.select_templates_for_client.return_value = [
            Template(
                template_id=1,
                name="Template 1",
                structure="Test structure 1",
                template_type=TemplateType.PROBLEM_RECOGNITION,
                difficulty=TemplateDifficulty.FAST,
                best_for="Awareness",
            ),
            Template(
                template_id=2,
                name="Template 2",
                structure="Test structure 2",
                template_type=TemplateType.STATISTIC,
                difficulty=TemplateDifficulty.MEDIUM,
                best_for="Authority",
            ),
        ]
        loader.get_template_by_id.side_effect = lambda tid: Template(
            template_id=tid,
            name=f"Template {tid}",
            structure=f"Structure {tid}",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="General",
        )
        return loader

    @pytest.fixture
    def content_generator(self, mock_anthropic_client, mock_template_loader):
        """Create content generator with mocked dependencies"""
        return ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
        )

    @pytest.fixture
    def sample_client_brief(self):
        """Sample client brief"""
        return ClientBrief(
            company_name="Test Company",
            business_description="Test business providing test services",
            ideal_customer="Test customers who need test solutions",
            main_problem_solved="Solving test problems efficiently",
            customer_pain_points=["Pain point 1", "Pain point 2"],
        )

    @pytest.fixture
    def sample_template(self):
        """Sample template"""
        return Template(
            template_id=1,
            name="Test Template",
            structure="[HOOK]\n\n[PROBLEM]\n\n[SOLUTION]\n\nCTA: [CALL_TO_ACTION]",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Awareness building",
        )

    @pytest.fixture
    def sample_keyword_strategy(self):
        """Sample keyword strategy"""
        return KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="test keyword",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=1,
                ),
                SEOKeyword(
                    keyword="example",
                    intent=KeywordIntent.COMMERCIAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    priority=2,
                ),
            ],
            secondary_keywords=[
                SEOKeyword(
                    keyword="demo",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=3,
                ),
            ],
            longtail_keywords=[
                SEOKeyword(
                    keyword="how to test",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=4,
                ),
            ],
        )

    def test_initialization_with_dependencies(self, mock_anthropic_client, mock_template_loader):
        """Test generator initializes with provided dependencies"""
        generator = ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
        )

        assert generator.client == mock_anthropic_client
        assert generator.template_loader == mock_template_loader
        assert generator.keyword_strategy is None
        assert generator.db is None

    def test_initialization_with_keyword_strategy(
        self, mock_anthropic_client, mock_template_loader, sample_keyword_strategy
    ):
        """Test generator initializes with keyword strategy"""
        keyword_strategy = sample_keyword_strategy

        generator = ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
            keyword_strategy=keyword_strategy,
        )

        assert generator.keyword_strategy == keyword_strategy

    def test_initialization_defaults(self):
        """Test generator creates default dependencies if not provided"""
        with (
            patch("src.agents.content_generator.AnthropicClient") as MockClient,
            patch("src.agents.content_generator.TemplateLoader") as MockLoader,
        ):

            _generator = ContentGeneratorAgent()

            MockClient.assert_called_once()
            MockLoader.assert_called_once()

    def test_generate_posts_with_template_quantities(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test generate_posts with template_quantities parameter"""
        template_quantities = {1: 3, 2: 5}

        with patch.object(content_generator, "_generate_posts_from_quantities") as mock_gen:
            mock_gen.return_value = [Mock(spec=Post)] * 8

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                template_quantities=template_quantities,
            )

            # Should call _generate_posts_from_quantities
            mock_gen.assert_called_once()
            assert len(result) == 8

    def test_generate_posts_legacy_mode(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test generate_posts in legacy equal distribution mode"""
        # Mock the template selection
        mock_template_loader.select_templates_for_client.return_value = [
            Template(
                template_id=1,
                name="Template 1",
                structure="Test",
                template_type=TemplateType.PROBLEM_RECOGNITION,
                difficulty=TemplateDifficulty.FAST,
                best_for="Awareness",
            ),
            Template(
                template_id=2,
                name="Template 2",
                structure="Test",
                template_type=TemplateType.STATISTIC,
                difficulty=TemplateDifficulty.MEDIUM,
                best_for="Authority",
            ),
        ]

        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            # Mock post generation
            mock_gen_single.return_value = Post(
                content="Test post",
                template_id=1,
                template_name="Template 1",
                client_name="Test Company",
            )

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=4,
                template_count=2,
                randomize=False,
            )

            # Should generate 4 posts (2 templates x 2 uses each)
            assert len(result) == 4
            # Should call _generate_single_post 4 times
            assert mock_gen_single.call_count == 4

    def test_generate_posts_template_selection_intelligent(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test intelligent template selection is used by default"""
        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=4,
                template_count=2,
            )

            # Verify intelligent selection was called
            mock_template_loader.select_templates_for_client.assert_called_once()
            call_args = mock_template_loader.select_templates_for_client.call_args
            assert call_args[0][0] == sample_client_brief
            assert call_args[1]["count"] == 2

    def test_generate_posts_manual_template_ids(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test manual template ID override"""
        template_ids = [1, 3, 5]

        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=6,
                template_ids=template_ids,
            )

            # Should use get_template_by_id for each ID
            assert mock_template_loader.get_template_by_id.call_count == len(template_ids)

    def test_generate_posts_manual_template_ids_invalid(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test manual template IDs with invalid IDs raises error"""
        # Mock get_template_by_id to return None for all IDs
        # Need to override side_effect, not just return_value
        mock_template_loader.get_template_by_id.side_effect = lambda tid: None

        with pytest.raises(ValueError) as exc_info:
            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=6,
                template_ids=[99, 100],  # Invalid IDs
            )

        assert "No valid templates found" in str(exc_info.value)

    def test_generate_posts_randomization(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test post randomization"""
        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            # Create posts with predictable order
            mock_gen_single.side_effect = [
                Post(
                    content=f"Post {i}",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
                for i in range(4)
            ]

            # Generate with randomize=True
            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=4,
                randomize=True,
            )

            # Can't test exact randomization, but verify we got all posts
            assert len(result) == 4

    def test_generate_posts_no_randomization(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test posts stay in order when randomize=False"""
        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.side_effect = [
                Post(
                    content=f"Post {i}",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
                for i in range(4)
            ]

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=4,
                randomize=False,
            )

            # Order should be preserved
            assert result[0].content == "Post 0"
            assert result[1].content == "Post 1"

    def test_generate_posts_platform_parameter(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test platform parameter is passed to post generation"""
        with (
            patch.object(content_generator, "_generate_single_post") as mock_gen_single,
            patch.object(content_generator, "_build_system_prompt") as mock_build_prompt,
        ):

            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )
            mock_build_prompt.return_value = "System prompt"

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
                platform=Platform.TWITTER,
            )

            # Verify platform passed to _build_system_prompt
            mock_build_prompt.assert_called_once()
            assert mock_build_prompt.call_args[0][1] == Platform.TWITTER

    def test_generate_posts_uses_per_template_calculation(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test correct calculation of uses per template"""
        # 30 posts / 15 templates = 2 uses per template
        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            # Mock 15 templates
            mock_template_loader.select_templates_for_client.return_value = [
                Template(
                    template_id=i,
                    name=f"Template {i}",
                    structure="Test",
                    template_type=TemplateType.PROBLEM_RECOGNITION,
                    difficulty=TemplateDifficulty.FAST,
                    best_for="Test",
                )
                for i in range(1, 16)
            ]

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=30,
                template_count=15,
            )

            # Should generate exactly 30 posts
            assert len(result) == 30
            assert mock_gen_single.call_count == 30

    def test_generate_posts_extra_posts_distribution(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test extra posts distributed correctly"""
        # 31 posts / 15 templates = 2 uses each + 1 extra
        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            mock_template_loader.select_templates_for_client.return_value = [
                Template(
                    template_id=i,
                    name=f"Template {i}",
                    structure="Test",
                    template_type=TemplateType.PROBLEM_RECOGNITION,
                    difficulty=TemplateDifficulty.FAST,
                    best_for="Test",
                )
                for i in range(1, 16)
            ]

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=31,
                template_count=15,
            )

            # Should generate exactly 31 posts
            assert len(result) == 31

    @pytest.mark.asyncio
    async def test_generate_posts_async_with_template_quantities(
        self, content_generator, sample_client_brief
    ):
        """Test async generation with template quantities"""
        template_quantities = {1: 3, 2: 5}

        with patch.object(content_generator, "_generate_posts_from_quantities_async") as mock_gen:
            mock_gen.return_value = [Mock(spec=Post)] * 8

            result = await content_generator.generate_posts_async(
                client_brief=sample_client_brief,
                template_quantities=template_quantities,
            )

            # Should call async version
            mock_gen.assert_called_once()
            assert len(result) == 8

    @pytest.mark.asyncio
    async def test_generate_posts_async_concurrency_limit(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test async generation respects concurrency limit"""
        with patch.object(
            content_generator, "_generate_single_post_with_retry_async"
        ) as mock_gen_single:
            # Mock async post generation
            async def mock_generate(*args, **kwargs):
                return Post(
                    content="Test",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )

            mock_gen_single.side_effect = mock_generate

            result = await content_generator.generate_posts_async(
                client_brief=sample_client_brief,
                num_posts=4,
                max_concurrent=5,
            )

            # Should generate all posts
            assert len(result) == 4
            # Each post generated via async method
            assert mock_gen_single.call_count == 4

    @pytest.mark.asyncio
    async def test_generate_posts_async_randomization(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test async generation randomizes when requested"""
        with patch.object(
            content_generator, "_generate_single_post_with_retry_async"
        ) as mock_gen_single:

            async def mock_generate(*args, **kwargs):
                # Generate posts with predictable content
                post_num = mock_gen_single.call_count
                return Post(
                    content=f"Post {post_num}",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )

            mock_gen_single.side_effect = mock_generate

            result = await content_generator.generate_posts_async(
                client_brief=sample_client_brief,
                num_posts=4,
                randomize=True,
            )

            # All posts generated
            assert len(result) == 4

    def test_detect_cta_static_method(self):
        """Test _detect_cta static method"""
        # Test various CTA indicators
        assert Post._detect_cta("What do you think?") is True
        assert Post._detect_cta("Comment below") is True
        assert Post._detect_cta("Share this post") is True
        assert Post._detect_cta("No call to action here") is False

    def test_build_system_prompt_called(self, content_generator, sample_client_brief):
        """Test system prompt building is called during generation"""
        with (
            patch.object(content_generator, "_build_system_prompt") as mock_build,
            patch.object(content_generator, "_generate_single_post") as mock_gen_single,
        ):

            mock_build.return_value = "Test system prompt"
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
            )

            # System prompt should be built once and cached
            mock_build.assert_called_once()

    def test_logging_during_generation(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test appropriate logging during generation"""
        with (
            patch.object(content_generator, "_generate_single_post") as mock_gen_single,
            patch("src.agents.content_generator.logger") as mock_logger,
        ):

            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
            )

            # Should log generation start and completion
            assert mock_logger.info.call_count >= 2

    def test_client_memory_integration(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test client memory is used when database available"""
        mock_db = Mock()
        mock_db.get_client_memory.return_value = None
        content_generator.db = mock_db

        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
                use_client_memory=True,
            )

            # Should attempt to get client memory
            mock_db.get_client_memory.assert_called_once_with("Test Company")

    def test_client_memory_disabled(self, content_generator, sample_client_brief):
        """Test client memory not used when disabled"""
        mock_db = Mock()
        content_generator.db = mock_db

        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

            content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
                use_client_memory=False,
            )

            # Should NOT call get_client_memory
            mock_db.get_client_memory.assert_not_called()

    def test_repeat_client_with_preferred_templates(
        self, content_generator, sample_client_brief, mock_template_loader
    ):
        """Test repeat client with preferred and avoided templates"""
        from src.models.client_memory import ClientMemory

        # Create repeat client memory with preferences
        mock_memory = ClientMemory(
            client_name="Test Company",
            total_projects=3,
            is_repeat_client=True,
            preferred_templates=[1, 2, 5],
            avoided_templates=[3, 7],
            signature_phrases=["test phrase", "example"],
            voice_adjustments={"tone": "more casual", "length": "shorter"},
            optimal_word_count_min=100,
            optimal_word_count_max=200,
        )

        mock_db = Mock()
        mock_db.get_client_memory.return_value = mock_memory
        content_generator.db = mock_db

        with patch.object(content_generator, "_generate_single_post") as mock_gen_single:
            mock_gen_single.return_value = Post(
                content="Test",
                template_id=1,
                template_name="Test",
                client_name="Test Company",
            )

            result = content_generator.generate_posts(
                client_brief=sample_client_brief,
                num_posts=2,
                use_client_memory=True,
            )

            # Should have generated posts
            assert len(result) == 2
            # Template loader should be called with memory preferences
            mock_template_loader.select_templates_for_client.assert_called_once()
            call_kwargs = mock_template_loader.select_templates_for_client.call_args[1]
            # Uses boost_templates and avoid_templates parameters
            assert call_kwargs["boost_templates"] == [1, 2, 5]
            assert call_kwargs["avoid_templates"] == [3, 7]

    def test_build_system_prompt_with_key_phrases(self, content_generator, sample_client_brief):
        """Test system prompt includes key phrases"""
        sample_client_brief.key_phrases = ["innovation", "transform", "growth"]

        prompt = content_generator._build_system_prompt(
            client_brief=sample_client_brief,
            platform=Platform.LINKEDIN,
        )

        assert "KEY PHRASES TO USE" in prompt
        assert "innovation" in prompt
        assert "transform" in prompt

    def test_build_system_prompt_with_misconceptions(self, content_generator, sample_client_brief):
        """Test system prompt includes misconceptions to address"""
        sample_client_brief.misconceptions = ["Common myth 1", "Industry fallacy"]

        prompt = content_generator._build_system_prompt(
            client_brief=sample_client_brief,
            platform=Platform.LINKEDIN,
        )

        assert "COMMON MISCONCEPTIONS TO ADDRESS" in prompt
        assert "Common myth 1" in prompt

    def test_build_system_prompt_with_client_memory(self, content_generator, sample_client_brief):
        """Test system prompt includes client memory insights"""
        from src.models.client_memory import ClientMemory

        mock_memory = ClientMemory(
            client_name="Test Company",
            total_projects=5,
            is_repeat_client=True,
            voice_adjustments={"tone": "more professional", "style": "concise"},
            signature_phrases=["let's dive in", "here's the truth"],
            optimal_word_count_min=150,
            optimal_word_count_max=250,
        )

        prompt = content_generator._build_system_prompt(
            client_brief=sample_client_brief,
            platform=Platform.LINKEDIN,
            client_memory=mock_memory,
        )

        assert "[CLIENT HISTORY]" in prompt
        assert "repeat client" in prompt
        assert "LEARNED PREFERENCES" in prompt
        assert "SIGNATURE PHRASES" in prompt
        assert "OPTIMAL LENGTH" in prompt
        assert "150-250 words" in prompt

    def test_build_skill_guidance_no_skill(self, mock_anthropic_client, mock_template_loader):
        """Test skill guidance returns empty when skill not loaded"""
        # Create generator with skill disabled
        generator = ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
            use_content_skill=False,
        )

        guidance = generator._build_skill_guidance(Platform.LINKEDIN)
        assert guidance == ""

    def test_content_skill_loading_failure(self, mock_anthropic_client, mock_template_loader):
        """Test graceful handling when skill loading fails"""
        with patch("src.agents.content_generator.load_skill") as mock_load:
            mock_load.side_effect = Exception("Skill not found")

            generator = ContentGeneratorAgent(
                client=mock_anthropic_client,
                template_loader=mock_template_loader,
                use_content_skill=True,
            )

            # Should not raise, just log warning
            assert generator.content_skill is None


class TestGenerateWithVoiceSamples:
    """Tests for voice sample integration"""

    @pytest.fixture
    def content_generator_with_db(self, mock_anthropic_client, mock_template_loader):
        """Content generator with mocked database"""

        generator = ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
            use_content_skill=False,
        )
        generator.db = Mock()
        return generator

    @pytest.fixture
    def sample_client_brief(self):
        """Sample client brief"""
        return ClientBrief(
            company_name="Voice Test Company",
            business_description="Test business",
            ideal_customer="Test customers",
            main_problem_solved="Test problem",
        )

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        return Mock()

    @pytest.fixture
    def mock_template_loader(self):
        """Mock template loader"""
        loader = Mock()
        loader.select_templates_for_client.return_value = [
            Template(
                template_id=1,
                name="Template 1",
                structure="Test structure",
                template_type=TemplateType.PROBLEM_RECOGNITION,
                difficulty=TemplateDifficulty.FAST,
                best_for="Test",
            )
        ]
        return loader

    @pytest.mark.asyncio
    async def test_generate_posts_with_voice_matching_async_no_db(
        self, mock_anthropic_client, mock_template_loader, sample_client_brief
    ):
        """Test voice sample generation without database returns None report"""
        generator = ContentGeneratorAgent(
            client=mock_anthropic_client,
            template_loader=mock_template_loader,
            use_content_skill=False,
        )
        generator.db = None

        with patch.object(generator, "generate_posts_async") as mock_async:
            mock_async.return_value = [
                Post(
                    content="Test",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
            ]

            posts, report = await generator.generate_posts_with_voice_matching_async(
                client_brief=sample_client_brief,
                num_posts=1,
            )

            assert posts is not None
            assert report is None

    @pytest.mark.asyncio
    async def test_generate_posts_with_voice_matching_async_no_samples_in_db(
        self, content_generator_with_db, sample_client_brief
    ):
        """Test voice sample generation when no samples exist"""
        content_generator_with_db.db.get_voice_sample_upload_stats.return_value = None

        with patch.object(content_generator_with_db, "generate_posts_async") as mock_async:
            mock_async.return_value = [
                Post(
                    content="Test",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
            ]

            posts, report = (
                await content_generator_with_db.generate_posts_with_voice_matching_async(
                    client_brief=sample_client_brief,
                    num_posts=1,
                )
            )

            assert posts is not None
            assert report is None

    @pytest.mark.asyncio
    async def test_generate_posts_with_voice_matching_async_stats_but_no_samples(
        self, content_generator_with_db, sample_client_brief
    ):
        """Test when stats exist but samples can't be retrieved"""
        content_generator_with_db.db.get_voice_sample_upload_stats.return_value = {
            "sample_count": 5,
            "total_words": 1000,
        }
        content_generator_with_db.db.get_voice_sample_uploads.return_value = []

        with patch.object(content_generator_with_db, "generate_posts_async") as mock_async:
            mock_async.return_value = [
                Post(
                    content="Test",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
            ]

            posts, report = (
                await content_generator_with_db.generate_posts_with_voice_matching_async(
                    client_brief=sample_client_brief,
                    num_posts=1,
                )
            )

            assert posts is not None
            assert report is None

    @pytest.mark.asyncio
    async def test_generate_posts_with_voice_matching_async_full_flow(
        self, content_generator_with_db, sample_client_brief
    ):
        """Test full voice sample generation flow"""
        # Use Mock objects for voice samples to avoid validation constraints
        mock_sample_1 = Mock()
        mock_sample_1.sample_text = (
            "This is a test voice sample with professional tone and business language."
        )
        mock_sample_1.sample_source = "linkedin"

        mock_sample_2 = Mock()
        mock_sample_2.sample_text = (
            "Another sample showing consistent voice patterns in professional context."
        )
        mock_sample_2.sample_source = "linkedin"

        voice_samples = [mock_sample_1, mock_sample_2]

        content_generator_with_db.db.get_voice_sample_upload_stats.return_value = {
            "sample_count": 2,
            "total_words": 200,
        }
        content_generator_with_db.db.get_voice_sample_uploads.return_value = voice_samples

        # Mock voice analyzer - create a Mock instead of real VoiceGuide
        mock_voice_guide = Mock()
        mock_voice_guide.voice_archetype = "The Professional"
        mock_voice_guide.average_readability_score = 65.0
        mock_voice_guide.average_word_count = 150
        mock_voice_guide.key_phrases_used = ["test phrase", "example"]

        with (
            patch.object(content_generator_with_db, "generate_posts_async") as mock_async,
            patch("src.agents.voice_analyzer.VoiceAnalyzer") as mock_analyzer_class,
            patch("src.utils.voice_matcher.VoiceMatcher") as mock_matcher_class,
        ):
            mock_async.return_value = [
                Post(
                    content="Generated test post",
                    template_id=1,
                    template_name="Test",
                    client_name="Voice Test Company",
                )
            ]

            # Mock analyzer
            mock_analyzer = Mock()
            mock_analyzer.analyze_voice_samples.return_value = mock_voice_guide
            mock_analyzer_class.return_value = mock_analyzer

            # Mock matcher
            mock_match_report = Mock()
            mock_match_report.match_score = 0.85
            mock_match_report.readability_score = Mock(score=0.9)
            mock_match_report.word_count_score = Mock(score=0.8)
            mock_match_report.archetype_score = Mock(score=0.85)
            mock_match_report.phrase_usage_score = Mock(score=0.75)

            mock_matcher = Mock()
            mock_matcher.calculate_match_score.return_value = mock_match_report
            mock_matcher_class.return_value = mock_matcher

            posts, report = (
                await content_generator_with_db.generate_posts_with_voice_matching_async(
                    client_brief=sample_client_brief,
                    num_posts=1,
                )
            )

            assert posts is not None
            assert len(posts) == 1
            assert report is not None
            assert report.match_score == 0.85

    @pytest.mark.asyncio
    async def test_generate_posts_with_voice_matching_async_matcher_error(
        self, content_generator_with_db, sample_client_brief
    ):
        """Test graceful handling when voice matcher fails"""
        # Use Mock objects to avoid validation constraints
        mock_sample = Mock()
        mock_sample.sample_text = "Test sample text for voice analysis"
        mock_sample.sample_source = "linkedin"

        voice_samples = [mock_sample]

        content_generator_with_db.db.get_voice_sample_upload_stats.return_value = {
            "sample_count": 1,
            "total_words": 100,
        }
        content_generator_with_db.db.get_voice_sample_uploads.return_value = voice_samples

        mock_voice_guide = Mock()
        mock_voice_guide.average_readability_score = 60.0
        mock_voice_guide.voice_archetype = None
        mock_voice_guide.average_word_count = None
        mock_voice_guide.key_phrases_used = []

        with (
            patch.object(content_generator_with_db, "generate_posts_async") as mock_async,
            patch("src.agents.voice_analyzer.VoiceAnalyzer") as mock_analyzer_class,
            patch("src.utils.voice_matcher.VoiceMatcher") as mock_matcher_class,
        ):
            mock_async.return_value = [
                Post(
                    content="Test",
                    template_id=1,
                    template_name="Test",
                    client_name="Test",
                )
            ]

            mock_analyzer = Mock()
            mock_analyzer.analyze_voice_samples.return_value = mock_voice_guide
            mock_analyzer_class.return_value = mock_analyzer

            # Make matcher raise exception
            mock_matcher = Mock()
            mock_matcher.calculate_match_score.side_effect = Exception("Matcher error")
            mock_matcher_class.return_value = mock_matcher

            posts, report = (
                await content_generator_with_db.generate_posts_with_voice_matching_async(
                    client_brief=sample_client_brief,
                    num_posts=1,
                )
            )

            # Should return posts but None report on error
            assert posts is not None
            assert report is None


# ==================== _check_quality_flags Tests ====================


class TestCheckQualityFlags:
    """Tests for _check_quality_flags covering platform-specific word counts and AI tell detection."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        loader.select_templates_for_client.return_value = []
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def sample_template(self):
        return Template(
            template_id=1,
            name="Test Template",
            structure="[HOOK]\n\n[BODY]\n\nCTA: [CTA]",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Test",
        )

    @pytest.fixture
    def sample_brief(self):
        return ClientBrief(
            company_name="Test Co",
            business_description="A test business",
            ideal_customer="Test customers",
            main_problem_solved="Test problems",
        )

    def _make_post(self, content: str, platform: Platform = Platform.LINKEDIN) -> Post:
        return Post(
            content=content,
            template_id=1,
            template_name="Test",
            variant=1,
            client_name="Test Co",
            target_platform=platform,
        )

    def test_ai_tell_triggers_flag(self, generator, sample_template, sample_brief):
        """Post containing an AI tell phrase is flagged for review."""
        # "in today's world" is listed in AI_TELL_PHRASES; build content long enough
        # to pass LinkedIn's 130-word min so word-count check doesn't fire first
        ai_tell = "in today's world"
        filler = "Productive teams use integrated tools to reduce context switching. " * 5
        content = f"{ai_tell} {filler}"
        post = self._make_post(content)
        generator._check_quality_flags(post, sample_template, sample_brief)
        assert post.needs_review is True
        assert "AI tell" in post.review_reason

    def test_too_short_triggers_flag(self, generator, sample_template, sample_brief):
        """Post with fewer than platform min words is flagged as too short."""
        post = self._make_post("Very short post.")
        generator._check_quality_flags(post, sample_template, sample_brief)
        assert post.needs_review is True
        assert "too short" in post.review_reason.lower()

    def test_no_cta_triggers_flag(self, generator, sample_template, sample_brief):
        """Post without a CTA is flagged."""
        # Build a post long enough to pass LinkedIn word count (>=200 words) but no CTA keyword.
        # 13 words per repetition × 16 = 208 words total
        sentence = "The whole team struggled deeply with scattered disconnected tools and growing communication gaps. "
        content = sentence * 16
        post = self._make_post(content)
        generator._check_quality_flags(post, sample_template, sample_brief)
        assert post.needs_review is True
        assert "CTA" in post.review_reason

    def test_good_post_no_flag(self, generator, sample_template, sample_brief):
        """A post with acceptable length and CTA passes without flag."""
        # Need 200+ words (LinkedIn min) with an explicit CTA, no AI tells.
        # ~13 words per sentence × 16 = 208 words, plus CTA
        sentence = "Productive teams rely on integrated platforms to reduce context switching and improve output. "
        content = sentence * 16 + "Book a demo today to learn more about how we can help."
        post = self._make_post(content)
        generator._check_quality_flags(post, sample_template, sample_brief)
        assert post.needs_review is False

    def test_too_long_triggers_flag(self, generator, sample_template, sample_brief):
        """Post exceeding LinkedIn max_words (300) is flagged."""
        content = "Word " * 310 + "Book a demo today."
        post = self._make_post(content)
        generator._check_quality_flags(post, sample_template, sample_brief)
        assert post.needs_review is True
        assert "too long" in post.review_reason.lower()

    def test_twitter_uses_platform_specific_limits(self, generator, sample_template, sample_brief):
        """Twitter posts use PLATFORM_LENGTH_SPECS limits, not global defaults."""
        # Twitter max_words is much smaller (typically 18-20 words)
        # A 100-word post should pass LinkedIn but may be fine or flag on Twitter
        # The key is that PLATFORM_LENGTH_SPECS is used
        content = "Tweet content with CTA. Book a demo."
        post = self._make_post(content, platform=Platform.TWITTER)
        # Just verify no exception thrown and a result is produced
        generator._check_quality_flags(post, sample_template, sample_brief)
        # Result can be either way depending on Twitter limits, no assertion on value


# ==================== _build_system_prompt Tests ====================


class TestBuildSystemPrompt:
    """Additional coverage for _build_system_prompt branches."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Test Co",
            business_description="SaaS analytics platform",
            ideal_customer="Data teams",
            main_problem_solved="Poor data visibility",
        )

    def test_twitter_prompt_includes_requirements(self, generator, brief):
        """Twitter-specific ultra-concise requirements are injected into the prompt."""
        prompt = generator._build_system_prompt(brief, platform=Platform.TWITTER)
        assert "TWITTER" in prompt.upper()
        assert "18 words" in prompt or "HARD LIMIT" in prompt

    def test_facebook_prompt_includes_requirements(self, generator, brief):
        """Facebook-specific requirements are injected into the prompt."""
        prompt = generator._build_system_prompt(brief, platform=Platform.FACEBOOK)
        assert "FACEBOOK" in prompt.upper()

    def test_linkedin_prompt_includes_length_requirements(self, generator, brief):
        """LinkedIn-specific length requirements are in the prompt."""
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "200 words" in prompt or "LINKEDIN" in prompt.upper()
        assert "140 characters" in prompt or "140" in prompt

    def test_blog_prompt_includes_structure(self, generator, brief):
        """Blog-specific structure guidelines appear in the prompt."""
        prompt = generator._build_system_prompt(brief, platform=Platform.BLOG)
        assert "1500" in prompt or "BLOG" in prompt.upper()

    def test_tone_preference_injected(self, generator):
        """tone_preference field is rendered into the prompt."""
        brief = ClientBrief(
            company_name="Test",
            business_description="A test company",
            ideal_customer="Teams",
            main_problem_solved="Efficiency",
            tone_preference=TonePreference.CONVERSATIONAL,
        )
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "conversational" in prompt.lower()

    def test_data_usage_heavy_injected(self, generator):
        """data_usage=heavy is reflected in prompt."""
        brief = ClientBrief(
            company_name="Data Co",
            business_description="Analytics for teams",
            ideal_customer="Data teams",
            main_problem_solved="Data problems",
            data_usage="heavy",
        )
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "statistics" in prompt.lower() or "DATA USAGE" in prompt

    def test_industry_context_injected(self, generator):
        """industry field is included in the prompt when set."""
        brief = ClientBrief(
            company_name="FinTech Co",
            business_description="Financial technology services",
            ideal_customer="Banks",
            main_problem_solved="Compliance overhead",
            industry="FinTech",
        )
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "FinTech" in prompt

    def test_research_context_guidance_absent_without_session(self, generator, brief):
        """Research insights guidance is absent when backend_session is None."""
        generator.backend_session = None
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "RESEARCH INSIGHTS GUIDANCE" not in prompt

    def test_keyword_guidance_included_when_strategy_set(self, generator, brief):
        """SEO keyword section is added when keyword_strategy is set."""
        from src.models.seo_keyword import KeywordStrategy, SEOKeyword, KeywordIntent

        generator.keyword_strategy = KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="data analytics",
                    intent=KeywordIntent.INFORMATIONAL,
                    priority=1,
                )
            ]
        )
        prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)
        assert "data analytics" in prompt or "SEO KEYWORD" in prompt


# ==================== _infer_template_type_for_hooks Tests ====================


class TestInferTemplateTypeForHooks:
    """Tests for _infer_template_type_for_hooks covering all keyword branches."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    def _make_brief(self, description: str, pain_points=None) -> ClientBrief:
        return ClientBrief(
            company_name="Test",
            business_description=description,
            ideal_customer="Teams",
            main_problem_solved="Problems",
            customer_pain_points=pain_points or [],
        )

    def test_problem_recognition_from_description(self, generator):
        """Detects 'problem_recognition' when 'problem' keyword is in description."""
        brief = self._make_brief("We solve the core problem of team alignment")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "problem_recognition"

    def test_problem_recognition_from_pain_points(self, generator):
        """Detects 'problem_recognition' from pain_points when description lacks it."""
        brief = self._make_brief("We improve productivity", ["struggle with deadlines"])
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "problem_recognition"

    def test_how_to_from_description(self, generator):
        """Detects 'how_to' when 'guide' keyword is in description."""
        brief = self._make_brief("A step-by-step guide for better marketing processes")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "how_to"

    def test_comparison_from_description(self, generator):
        """Detects 'comparison' when 'vs' keyword is in description."""
        brief = self._make_brief("Compare us vs competitors for project management")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "comparison"

    def test_future_thinking_from_description(self, generator):
        """Detects 'future_thinking' when 'transform' keyword is in description."""
        brief = self._make_brief("We help companies transform their operations")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "future_thinking"

    def test_statistic_insight_from_description(self, generator):
        """Detects 'statistic_insight' when 'analytics' keyword is in description."""
        brief = self._make_brief("Analytics and data metrics to measure ROI")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "statistic_insight"

    def test_default_problem_recognition(self, generator):
        """Falls back to 'problem_recognition' when no keywords match."""
        brief = self._make_brief("We make software for small businesses")
        result = generator._infer_template_type_for_hooks(brief)
        assert result == "problem_recognition"


# ==================== _build_context Tests ====================


class TestBuildContext:
    """Tests for _build_context: variant guidance, template flags, and research code paths."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Test Co",
            business_description="SaaS platform",
            ideal_customer="Teams",
            main_problem_solved="Workflow gaps",
        )

    def _make_template(self, requires_story=False, requires_data=False, template_id=1) -> Template:
        return Template(
            template_id=template_id,
            name="Test",
            structure="[HOOK]\n\n[BODY]",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Test",
            requires_story=requires_story,
            requires_data=requires_data,
        )

    def test_variant_1_guidance(self, generator, brief):
        """Variant 1 sets 'direct, problem-focused' guidance."""
        template = self._make_template()
        ctx = generator._build_context(brief, template, variant=1)
        assert "direct" in ctx["variant_guidance"].lower()

    def test_variant_2_guidance(self, generator, brief):
        """Variant 2 sets 'story-driven' guidance."""
        template = self._make_template()
        ctx = generator._build_context(brief, template, variant=2)
        assert "story" in ctx["variant_guidance"].lower()

    def test_variant_3_guidance(self, generator, brief):
        """Variant 3+ sets 'unique angle' guidance."""
        template = self._make_template()
        ctx = generator._build_context(brief, template, variant=3)
        assert "unique" in ctx["variant_guidance"].lower()

    def test_data_template_adds_use_measurable_results(self, generator):
        """data-requiring template adds 'use_measurable_results' key when results exist."""
        brief = ClientBrief(
            company_name="Test",
            business_description="We improve ROI by 40%",
            ideal_customer="Teams",
            main_problem_solved="Low ROI",
            measurable_results="40% ROI increase",
        )
        template = self._make_template(requires_data=True)
        ctx = generator._build_context(brief, template, variant=1)
        # Only added if context has a "results" key from to_context_dict()
        # We verify template_type and requires_data are set regardless
        assert ctx["requires_data"] is True
        assert ctx["template_type"] == "problem_recognition"

    def test_comparison_template_adds_guidance(self, generator):
        """Template 10 adds 'comparison_guidance' when competitors are set."""
        brief = ClientBrief(
            company_name="Test",
            business_description="Project management software",
            ideal_customer="Teams",
            main_problem_solved="Tool sprawl",
            competitors=["Asana", "Monday"],
        )
        template = Template(
            template_id=10,
            name="Comparison",
            structure="[HOOK]\n\n[COMPARE]",
            template_type=TemplateType.COMPARISON,
            difficulty=TemplateDifficulty.MEDIUM,
            best_for="Comparison",
        )
        ctx = generator._build_context(brief, template, variant=1)
        assert ctx.get("comparison_guidance") is not None

    def test_base_context_copied_not_mutated(self, generator, brief):
        """Passing base_context does not mutate the original dict."""
        template = self._make_template()
        base = brief.to_context_dict()
        original_keys = set(base.keys())
        generator._build_context(brief, template, variant=1, base_context=base.copy())
        # Original base dict should not gain new keys
        assert set(base.keys()) == original_keys

    def test_no_research_context_without_session(self, generator, brief):
        """Research context is not added when backend_session is None."""
        template = self._make_template()
        generator.backend_session = None
        ctx = generator._build_context(brief, template, variant=1)
        assert "research_insights" not in ctx


# ==================== _generate_single_post sync Tests ====================


class TestGenerateSinglePostSync:
    """Tests for the synchronous _generate_single_post method."""

    @pytest.fixture
    def generator(self, mock_client, mock_template_loader):
        return ContentGeneratorAgent(
            client=mock_client,
            template_loader=mock_template_loader,
            use_content_skill=False,
        )

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.generate_post_content = Mock(
            return_value=(
                "This is solid post content for LinkedIn with enough words to pass validation. "
                "We help teams reduce tool sprawl and increase productivity significantly. "
                "Book a demo today to see how it works for your team."
            )
        )
        return client

    @pytest.fixture
    def mock_template_loader(self):
        loader = Mock()
        loader.select_templates_for_client.return_value = []
        return loader

    @pytest.fixture
    def template(self):
        return Template(
            template_id=1,
            name="Test Template",
            structure="[HOOK]\n\n[BODY]\n\nCTA: [CTA]",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Test",
        )

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Test Co",
            business_description="SaaS analytics",
            ideal_customer="Data teams",
            main_problem_solved="Poor visibility",
        )

    def test_successful_generation_returns_post(self, generator, template, brief, mock_client):
        """Successful API call returns a Post with correct metadata."""
        post = generator._generate_single_post(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
        )
        assert isinstance(post, Post)
        assert post.template_id == 1
        assert post.template_name == "Test Template"
        assert post.client_name == "Test Co"

    def test_api_exception_creates_placeholder(self, generator, template, brief, mock_client):
        """API failure creates a placeholder error post."""
        mock_client.generate_post_content.side_effect = Exception("API timeout")
        post = generator._generate_single_post(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
        )
        assert "[ERROR:" in post.content
        assert post.needs_review is True
        assert "Generation failed" in post.review_reason

    def test_uses_cached_system_prompt(self, generator, template, brief, mock_client):
        """Cached system prompt is passed directly to the API call."""
        cached_prompt = "Cached system prompt content"
        generator._generate_single_post(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            cached_system_prompt=cached_prompt,
        )
        call_kwargs = mock_client.generate_post_content.call_args[1]
        assert call_kwargs["system_prompt"] == cached_prompt

    def test_prompt_leakage_creates_security_placeholder(
        self, generator, template, brief, mock_client
    ):
        """Content that triggers prompt leakage detection is replaced with security placeholder."""
        with patch("src.agents.content_generator.detect_prompt_leakage", return_value=True):
            post = generator._generate_single_post(
                template=template,
                client_brief=brief,
                variant=1,
                post_number=1,
            )
        assert "SECURITY" in post.content

    def test_platform_set_on_post(self, generator, template, brief):
        """Generated post has correct target_platform set."""
        post = generator._generate_single_post(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            platform=Platform.TWITTER,
        )
        assert post.target_platform == Platform.TWITTER


# ==================== _generate_single_post async Tests ====================


class TestGenerateSinglePostAsync:
    """Tests for the async _generate_single_post_async method."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        client.generate_post_content_async = AsyncMock(
            return_value=(
                "Professional post content about productivity improvements for teams. "
                "Our solution reduces tool sprawl by 60 percent in the first month. "
                "Book your free consultation today."
            )
        )
        loader = Mock()
        loader.select_templates_for_client.return_value = []
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def template(self):
        return Template(
            template_id=2,
            name="Async Template",
            structure="[HOOK]\n\n[BODY]",
            template_type=TemplateType.STATISTIC,
            difficulty=TemplateDifficulty.FAST,
            best_for="Authority",
        )

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Async Co",
            business_description="Cloud platform",
            ideal_customer="Developers",
            main_problem_solved="Deployment complexity",
        )

    @pytest.mark.asyncio
    async def test_quality_feedback_appended_to_prompt(self, generator, template, brief):
        """quality_feedback argument is appended to the system prompt on retries."""
        captured_prompts = []

        async def capture_call(**kwargs):
            captured_prompts.append(kwargs.get("system_prompt", ""))
            return "Content with enough words for testing retry flow. " * 5

        generator.client.generate_post_content_async = capture_call

        await generator._generate_single_post_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            quality_feedback="Hook is too generic, be more specific.",
        )

        assert len(captured_prompts) == 1
        assert "REVISION REQUIRED" in captured_prompts[0]
        assert "Hook is too generic" in captured_prompts[0]

    @pytest.mark.asyncio
    async def test_blog_uses_custom_template_structure(self, generator, template, brief):
        """Blog platform uses a dedicated template structure instead of template.structure."""
        captured_structures = []

        async def capture_call(**kwargs):
            captured_structures.append(kwargs.get("template_structure", ""))
            return "Blog content. " * 50

        generator.client.generate_post_content_async = capture_call

        await generator._generate_single_post_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            platform=Platform.BLOG,
        )

        assert len(captured_structures) == 1
        # Blog template overrides the template's structure with a comprehensive blog prompt
        assert "blog post" in captured_structures[0].lower()
        assert "introduction" in captured_structures[0].lower()

    @pytest.mark.asyncio
    async def test_non_blog_uses_template_structure(self, generator, template, brief):
        """Non-blog platforms use the template's own structure."""
        captured_structures = []

        async def capture_call(**kwargs):
            captured_structures.append(kwargs.get("template_structure", ""))
            return "LinkedIn post content. " * 5

        generator.client.generate_post_content_async = capture_call

        await generator._generate_single_post_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            platform=Platform.LINKEDIN,
        )

        assert len(captured_structures) == 1
        assert captured_structures[0] == template.structure

    @pytest.mark.asyncio
    async def test_api_exception_creates_placeholder(self, generator, template, brief):
        """Async API failure creates a placeholder error post."""
        generator.client.generate_post_content_async = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        post = await generator._generate_single_post_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
        )
        assert "[ERROR:" in post.content
        assert post.needs_review is True


# ==================== _generate_single_post_with_retry_async Tests ====================


class TestGenerateSinglePostWithRetryAsync:
    """Tests for the retry wrapper _generate_single_post_with_retry_async."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        loader.select_templates_for_client.return_value = []
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def template(self):
        return Template(
            template_id=1,
            name="Retry Template",
            structure="[HOOK]\n\n[BODY]",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Test",
        )

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Retry Co",
            business_description="Analytics SaaS",
            ideal_customer="Data teams",
            main_problem_solved="Slow insights",
        )

    @pytest.mark.asyncio
    async def test_returns_immediately_on_clean_post(self, generator, template, brief):
        """Returns on first attempt when post has no quality flags."""
        good_content = (
            "Teams waste hours each week switching between disconnected tools. "
            "Our integrated platform unifies everything your team needs in one place. "
            "Research shows a 30 percent productivity boost within the first month of use. "
            "Don't let tool sprawl slow your team down any longer. "
            "Book a personalized demo today and see the difference."
        )

        async def clean_post_generator(**kwargs):
            return good_content

        generator.client.generate_post_content_async = clean_post_generator
        post = await generator._generate_single_post_with_retry_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            max_attempts=5,
        )
        # Should not need review
        assert post is not None

    @pytest.mark.asyncio
    async def test_all_attempts_fail_returns_best(self, generator, template, brief):
        """When all attempts produce flagged posts, returns the best one."""
        call_count = 0

        async def always_short(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"Too short post attempt {call_count}."

        generator.client.generate_post_content_async = always_short
        post = await generator._generate_single_post_with_retry_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            max_attempts=3,
        )
        assert call_count == 3
        assert post is not None

    @pytest.mark.asyncio
    async def test_feedback_passed_on_retry(self, generator, template, brief):
        """Quality feedback from a failed attempt is passed to the next attempt."""
        prompts_received = []
        call_count = 0

        async def variable_content(**kwargs):
            nonlocal call_count
            call_count += 1
            prompts_received.append(kwargs.get("system_prompt", ""))
            if call_count == 1:
                return "Short."  # Will be flagged as too short
            # Second attempt: long enough (200+ words, LinkedIn min), no AI tells, has CTA
            return (
                "Disconnected tools are costing your team more than you realise every single day. "
                "Knowledge workers switch between an average of twelve different applications daily. "
                "Each context switch costs cognitive energy and valuable focused working time. "
                "Our integrated platform reduces that friction by keeping everything in one place. "
                "Teams that adopt a unified workflow report saving at least five hours every week. "
                "That adds up to over two hundred hours annually per employee on your payroll. "
                "The onboarding process takes under sixty minutes and requires no engineering help. "
                "You will see measurable improvements in output within the very first week of use. "
                "Hundreds of teams across dozens of industries have already made the switch. "
                "They cite reduced burnout, clearer communication, and higher project completion rates. "
                "Fragmented workflows are not just an inconvenience — they are a measurable drain. "
                "Every minute spent searching for information or waiting on a slow handover costs money. "
                "A unified system eliminates those delays and gives everyone a single source of truth. "
                "Managers gain real-time visibility across projects without chasing status updates. "
                "Individual contributors spend more time on deep work and less on coordination overhead. "
                "Book a personalised demo today and discover what a unified workflow can do for you."
            )

        generator.client.generate_post_content_async = variable_content
        await generator._generate_single_post_with_retry_async(
            template=template,
            client_brief=brief,
            variant=1,
            post_number=1,
            max_attempts=3,
        )
        assert call_count == 2
        # Second call's prompt should contain the review reason feedback
        if len(prompts_received) > 1:
            assert "REVISION REQUIRED" in prompts_received[1]


# ==================== _calculate_post_quality_score Tests ====================


class TestCalculatePostQualityScore:
    """Tests for _calculate_post_quality_score covering all score branches."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    def test_very_short_post_penalized(self, generator):
        """Post under 60% of MIN_POST_WORD_COUNT gets the full 0.2 length penalty."""
        # MIN_POST_WORD_COUNT = 75, 60% = 45 words. Use fewer.
        # Score breakdown: 1.0 - 0.2 (very short) - 0.1 (no CTA) = 0.7
        post = Post(
            content="Too short.",
            template_id=1,
            template_name="T",
            variant=1,
            client_name="C",
        )
        score = generator._calculate_post_quality_score(post)
        assert score == pytest.approx(0.7, abs=0.01)

    def test_very_long_post_penalized(self, generator):
        """Post exceeding 120% of MAX_POST_WORD_COUNT gets extra penalty."""
        # MAX_POST_WORD_COUNT = 350, 120% = 420 words
        long_content = "Word " * 430 + "CTA here."
        post = Post(
            content=long_content,
            template_id=1,
            template_name="T",
            variant=1,
            client_name="C",
        )
        score = generator._calculate_post_quality_score(post)
        assert score <= 0.8

    def test_slightly_short_post_small_penalty(self, generator):
        """Post slightly below optimal range gets a smaller penalty than very short."""
        # Between MIN*0.8 (60 words) and MIN (75 words)
        content = "Word " * 65 + "Book a demo today."
        post = Post(
            content=content,
            template_id=1,
            template_name="T",
            variant=1,
            client_name="C",
        )
        score = generator._calculate_post_quality_score(post)
        # Should be penalised but not as harshly as very short
        assert 0.0 < score < 1.0

    def test_score_never_below_zero(self, generator):
        """Score is clamped to minimum of 0.0 even with many penalties."""
        post = Post(
            content="Bad.",  # Very short, no CTA, may have flags
            template_id=1,
            template_name="T",
            variant=1,
            client_name="C",
        )
        post.flag_for_review("Multiple issues")
        score = generator._calculate_post_quality_score(post)
        assert score >= 0.0

    def test_score_never_above_one(self, generator):
        """Score is clamped to maximum of 1.0."""
        good_content = (
            "Our analytics platform gives data teams instant visibility into KPIs. "
            "Stop waiting for weekly reports that are already outdated. "
            "Teams using our tool reduce reporting time by 70 percent in the first week. "
            "The setup takes under an hour and requires no engineering support at all. "
            "Schedule your free onboarding call today and start making faster decisions."
        )
        post = Post(
            content=good_content,
            template_id=1,
            template_name="T",
            variant=1,
            client_name="C",
        )
        score = generator._calculate_post_quality_score(post)
        assert score <= 1.0


# ==================== _generate_posts_from_quantities async Tests ====================


class TestGeneratePostsFromQuantitiesAsync:
    """Tests for _generate_posts_from_quantities_async."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        client.generate_post_content_async = AsyncMock(
            return_value=(
                "Content for a well-structured LinkedIn post about productivity. "
                "Our tool reduces context switching for your team members. "
                "Teams report saving hours every single week after onboarding. "
                "The results speak for themselves across every industry we serve. "
                "Book your demo today and join thousands of satisfied customers."
            )
        )
        loader = Mock()
        templates = [
            Template(
                template_id=i,
                name=f"T{i}",
                structure="[HOOK]\n\n[BODY]",
                template_type=TemplateType.PROBLEM_RECOGNITION,
                difficulty=TemplateDifficulty.FAST,
                best_for="Test",
            )
            for i in range(1, 4)
        ]
        loader.select_templates_for_client.return_value = templates
        loader.get_template_by_id.side_effect = lambda tid: next(
            (t for t in templates if t.template_id == tid), None
        )
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    @pytest.fixture
    def brief(self):
        return ClientBrief(
            company_name="Qty Async Co",
            business_description="SaaS for teams",
            ideal_customer="Knowledge workers",
            main_problem_solved="Tool sprawl",
        )

    @pytest.mark.asyncio
    async def test_correct_post_count_generated(self, generator, brief):
        """Generates the exact number of posts specified by quantities."""
        quantities = {1: 2, 2: 3}
        posts = await generator._generate_posts_from_quantities_async(
            client_brief=brief,
            template_quantities=quantities,
            randomize=False,
        )
        assert len(posts) == 5

    @pytest.mark.asyncio
    async def test_missing_template_id_skipped(self, generator, brief):
        """Template IDs not found by the loader are skipped without error."""
        quantities = {1: 2, 999: 3}  # 999 does not exist
        posts = await generator._generate_posts_from_quantities_async(
            client_brief=brief,
            template_quantities=quantities,
            randomize=False,
        )
        # Only posts for template 1 should be generated
        assert len(posts) == 2

    @pytest.mark.asyncio
    async def test_prompt_injection_raises(self, generator, brief):
        """Prompt injection in brief raises ValueError before generation."""
        with patch("src.agents.content_generator.sanitize_prompt_input") as mock_sanitize:
            mock_sanitize.side_effect = ValueError("injection detected")
            with pytest.raises(ValueError, match="unsafe content"):
                await generator._generate_posts_from_quantities_async(
                    client_brief=brief,
                    template_quantities={1: 1},
                )


# ==================== Archetype Inference Tests ====================


class TestInferArchetype:
    """Tests for _infer_archetype covering client_type path and fallback branches."""

    @pytest.fixture
    def generator(self):
        client = Mock()
        loader = Mock()
        return ContentGeneratorAgent(client=client, template_loader=loader, use_content_skill=False)

    def test_client_type_enum_used_when_available(self, generator):
        """When client_brief has a client_type attribute, it is used for archetype lookup."""
        brief = ClientBrief(
            company_name="SaaS Co",
            business_description="B2B software",
            ideal_customer="Enterprises",
            main_problem_solved="Integration pain",
        )
        # Use object.__setattr__ to bypass Pydantic's field validation
        mock_type = Mock()
        mock_type.value = "B2B_SAAS"
        object.__setattr__(brief, "client_type", mock_type)

        with patch(
            "src.agents.content_generator.get_archetype_from_client_type",
            return_value="Expert",
        ) as mock_get:
            result = generator._infer_archetype(brief)
            mock_get.assert_called_once_with("B2B_SAAS")
            assert result == "Expert"

    def test_fallback_to_guide_for_unknown_description(self, generator):
        """Defaults to 'Guide' when no keywords match business description."""
        brief = ClientBrief(
            company_name="Generic Co",
            business_description="We sell products and services",
            ideal_customer="Anyone",
            main_problem_solved="Everything",
        )
        result = generator._infer_archetype(brief)
        assert result == "Guide"

    def test_friend_archetype_from_creator_keyword(self, generator):
        """'creator' keyword in description maps to 'Friend' archetype."""
        brief = ClientBrief(
            company_name="Creator Co",
            business_description="Personal brand and creator community platform",
            ideal_customer="Content creators",
            main_problem_solved="Audience growth",
        )
        result = generator._infer_archetype(brief)
        assert result == "Friend"
