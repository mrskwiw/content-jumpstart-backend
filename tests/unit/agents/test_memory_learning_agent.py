"""Unit tests for MemoryLearningAgent"""

from datetime import datetime
from pathlib import Path

import pytest

from src.agents.memory_learning_agent import MemoryLearningAgent
from src.database.project_db import ProjectDatabase
from src.models.client_memory import FeedbackTheme
from src.models.post import Post
from src.models.project import Project, Revision
from src.models.voice_guide import EnhancedVoiceGuide


class TestMemoryLearningAgent:
    """Test MemoryLearningAgent functionality"""

    @pytest.fixture(autouse=True)
    def cleanup_test_data(self):
        """Clean up test data before and after each test"""
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        db = ProjectDatabase(db_path)

        # Clean up before test
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM template_performance WHERE client_name LIKE "TestClient_%"')
            cursor.execute(
                'DELETE FROM client_feedback_themes WHERE client_name LIKE "TestClient_%"'
            )
            cursor.execute('DELETE FROM client_voice_samples WHERE client_name LIKE "TestClient_%"')
            cursor.execute('DELETE FROM client_history WHERE client_name LIKE "TestClient_%"')
            conn.commit()

        yield

        # Clean up after test
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM template_performance WHERE client_name LIKE "TestClient_%"')
            cursor.execute(
                'DELETE FROM client_feedback_themes WHERE client_name LIKE "TestClient_%"'
            )
            cursor.execute('DELETE FROM client_voice_samples WHERE client_name LIKE "TestClient_%"')
            cursor.execute('DELETE FROM client_history WHERE client_name LIKE "TestClient_%"')
            conn.commit()

    @pytest.fixture
    def db(self):
        """Get database instance"""
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def agent(self, db):
        """Get learning agent"""
        return MemoryLearningAgent(db)

    @pytest.fixture
    def test_client(self):
        """Test client name"""
        return f"TestClient_Learning_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    @pytest.fixture
    def sample_project(self, test_client):
        """Sample project"""
        return Project(
            project_id=f"{test_client}_20251201_120000",
            client_name=test_client,
            num_posts=30,
            deliverable_path=f"data/outputs/{test_client}/deliverable.md",
        )

    @pytest.fixture
    def sample_posts(self, test_client):
        """Sample posts"""
        return [
            Post(
                content="Test post 1",
                template_id=1,
                template_name="Problem Recognition",
                variant=1,
                client_name=test_client,
            ),
            Post(
                content="Test post 2",
                template_id=1,
                template_name="Problem Recognition",
                variant=2,
                client_name=test_client,
            ),
            Post(
                content="Test post 3",
                template_id=6,
                template_name="Personal Story",
                variant=1,
                client_name=test_client,
            ),
        ]

    @pytest.fixture
    def sample_voice_guide(self, test_client):
        """Sample voice guide"""
        from src.models.voice_guide import VoicePattern

        return EnhancedVoiceGuide(
            company_name=test_client,
            generated_from_posts=30,
            dominant_tones=["professional", "friendly"],
            tone_consistency_score=0.85,
            voice_archetype="Expert",
            average_readability_score=72.5,
            average_word_count=220,
            average_paragraph_count=3.5,
            question_usage_rate=0.4,
            common_opening_hooks=[
                VoicePattern(
                    pattern_type="opening",
                    examples=["Ever wonder why...", "Here's the thing..."],
                    frequency=10,
                    description="Curiosity-driven openings",
                )
            ],
            common_transitions=[
                VoicePattern(
                    pattern_type="transition",
                    examples=["The key is...", "But here's what matters..."],
                    frequency=8,
                    description="Authority transitions",
                )
            ],
            common_ctas=[
                VoicePattern(
                    pattern_type="cta",
                    examples=["What's your take?", "Drop a comment..."],
                    frequency=15,
                    description="Engagement-focused CTAs",
                )
            ],
            key_phrases_used=["data-driven", "actionable insights"],
            dos=["Use conversational tone"],
            donts=["Don't be too formal"],
        )

    def test_learn_from_project_creates_memory(
        self, agent, sample_project, sample_posts, test_client
    ):
        """Test that learning from project creates client memory"""
        memory = agent.learn_from_project(sample_project, sample_posts)

        assert memory is not None
        assert memory.client_name == test_client
        assert memory.total_projects == 1
        assert memory.total_posts_generated == 30
        assert memory.is_repeat_client is True

    def test_learn_from_project_with_voice_guide(
        self, agent, sample_project, sample_posts, sample_voice_guide
    ):
        """Test learning with voice guide"""
        memory = agent.learn_from_project(sample_project, sample_posts, sample_voice_guide)

        assert memory.voice_archetype == "Expert"
        assert memory.average_readability_score == 72.5
        assert len(memory.signature_phrases) > 0

    def test_learn_from_template_usage(self, agent, db, sample_project, sample_posts, test_client):
        """Test template usage learning"""
        agent.learn_from_project(sample_project, sample_posts)

        # Check template performance was recorded
        perf = db.get_template_performance(test_client)

        assert 1 in perf  # Template 1 used twice
        assert 6 in perf  # Template 6 used once
        assert perf[1]["usage_count"] == 2
        assert perf[6]["usage_count"] == 1

    def test_extract_feedback_themes_tone(self, agent):
        """Test tone theme extraction"""
        feedback = "Please make this more casual and friendly"
        themes = agent._extract_feedback_themes(feedback)

        assert len(themes) > 0
        tone_themes = [t for t in themes if t.theme_type == "tone"]
        assert len(tone_themes) == 1
        assert tone_themes[0].feedback_phrase == "more casual"

    def test_extract_feedback_themes_length(self, agent):
        """Test length theme extraction"""
        feedback = "This is too long, please make it shorter"
        themes = agent._extract_feedback_themes(feedback)

        length_themes = [t for t in themes if t.theme_type == "length"]
        assert len(length_themes) == 1
        assert length_themes[0].feedback_phrase == "too long"

    def test_extract_feedback_themes_cta(self, agent):
        """Test CTA theme extraction"""
        feedback = "The call to action needs to be stronger"
        themes = agent._extract_feedback_themes(feedback)

        cta_themes = [t for t in themes if t.theme_type == "cta"]
        assert len(cta_themes) == 1
        assert cta_themes[0].feedback_phrase == "stronger cta"

    def test_extract_feedback_themes_data(self, agent):
        """Test data usage theme extraction"""
        feedback = "Can you add more stats and numbers to support the claims?"
        themes = agent._extract_feedback_themes(feedback)

        data_themes = [t for t in themes if t.theme_type == "data_usage"]
        assert len(data_themes) == 1
        assert data_themes[0].feedback_phrase == "add more data"

    def test_extract_feedback_themes_emoji(self, agent):
        """Test emoji theme extraction"""
        feedback = "Please add some emojis to make it more engaging"
        themes = agent._extract_feedback_themes(feedback)

        emoji_themes = [t for t in themes if t.theme_type == "emoji"]
        assert len(emoji_themes) == 1
        assert emoji_themes[0].feedback_phrase == "add emoji"

    def test_extract_feedback_themes_structure(self, agent):
        """Test structure theme extraction"""
        feedback = "The flow could be better. Can you reorganize this?"
        themes = agent._extract_feedback_themes(feedback)

        structure_themes = [t for t in themes if t.theme_type == "structure"]
        assert len(structure_themes) == 1
        assert structure_themes[0].feedback_phrase == "improve structure"

    def test_learn_from_revision(self, agent, db, sample_project, test_client):
        """Test learning from revision"""
        # Create project first
        db.create_project(sample_project)

        # Create revision
        revision = Revision(
            revision_id=f"{sample_project.project_id}_rev_1",
            project_id=sample_project.project_id,
            attempt_number=1,
            feedback="Please make this more casual and shorter",
        )
        db.create_revision(revision)

        # Learn from revision
        memory = agent.learn_from_revision(revision)

        assert memory.total_revisions == 1

        # Check themes were recorded
        themes = db.get_feedback_themes(test_client)
        assert len(themes) >= 2  # tone and length themes

    def test_synthesize_multi_project_learnings_insufficient_projects(self, agent, test_client):
        """Test synthesis with insufficient projects"""
        # Create memory with only 1 project
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Try to synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        # Should return memory unchanged (need 2+ projects)
        assert result.total_projects == 1

    def test_synthesize_multi_project_learnings_with_templates(self, agent, db, test_client):
        """Test synthesis with template performance data"""
        # Create memory with 2+ projects
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Add template performance
        # Template 1: good (2 uses, no revisions)
        db.update_template_performance(test_client, 1, False, 8.5)
        db.update_template_performance(test_client, 1, False, 8.5)

        # Template 6: bad (2 uses, both revised)
        db.update_template_performance(test_client, 6, True, 5.0)
        db.update_template_performance(test_client, 6, True, 5.0)

        # Synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        assert 1 in result.preferred_templates  # Good template
        assert 6 in result.avoided_templates  # Bad template

    def test_synthesize_multi_project_learnings_with_themes(self, agent, db, test_client):
        """Test synthesis with recurring feedback themes"""
        # Create memory with 2+ projects
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Record recurring theme
        theme = FeedbackTheme(theme_type="tone", feedback_phrase="more casual")
        db.record_feedback_theme(test_client, theme)
        db.record_feedback_theme(test_client, theme)  # 2nd occurrence

        # Synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        assert "tone" in result.voice_adjustments
        assert result.voice_adjustments["tone"] == "more casual"

    def test_get_memory_insights(self, agent, db, test_client):
        """Test getting memory insights"""
        # Create memory
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.voice_archetype = "Expert"
        memory.signature_phrases = ["data-driven", "actionable"]
        agent.db.update_client_memory(memory)

        # Get insights
        insights = agent.get_memory_insights(test_client)

        assert insights["client_name"] == test_client
        assert insights["total_projects"] == 1
        assert insights["is_repeat_client"] is True
        assert insights["voice_archetype"] == "Expert"
        assert len(insights["signature_phrases"]) == 2

    def test_get_memory_insights_not_found(self, agent):
        """Test insights for non-existent client"""
        insights = agent.get_memory_insights("NonExistentClient")

        assert "error" in insights
        assert insights["error"] == "Client not found"

    def test_learn_from_revision_project_not_found(self, agent):
        """Test learning from revision when project doesn't exist"""
        revision = Revision(
            revision_id="nonexistent_rev",
            project_id="nonexistent_project",
            attempt_number=1,
            feedback="Some feedback",
        )

        memory = agent.learn_from_revision(revision)

        # Should return default memory with "Unknown" client
        assert memory.client_name == "Unknown"

    def test_learn_from_revision_with_existing_memory(self, agent, db, sample_project, test_client):
        """Test learning from revision with pre-existing memory"""
        db.create_project(sample_project)

        # Create pre-existing memory
        existing_memory = db.get_or_create_client_memory(test_client)
        existing_memory.add_revisions(5)  # Already has 5 revisions
        db.update_client_memory(existing_memory)

        revision = Revision(
            revision_id=f"{sample_project.project_id}_rev_2",
            project_id=sample_project.project_id,
            attempt_number=1,
            feedback="More feedback",
        )
        db.create_revision(revision)

        # Pass existing memory
        memory = agent.learn_from_revision(revision, memory=existing_memory)

        assert memory.total_revisions == 6  # 5 + 1

    def test_extract_feedback_themes_too_short(self, agent):
        """Test length theme extraction for 'too short'"""
        feedback = "This is too short, please add more detail"
        themes = agent._extract_feedback_themes(feedback)

        length_themes = [t for t in themes if t.theme_type == "length"]
        assert len(length_themes) == 1
        assert length_themes[0].feedback_phrase == "too short"

    def test_extract_feedback_themes_remove_cta(self, agent):
        """Test CTA theme extraction for removing CTA"""
        feedback = "Please remove the CTA from this post"
        themes = agent._extract_feedback_themes(feedback)

        cta_themes = [t for t in themes if t.theme_type == "cta"]
        assert len(cta_themes) == 1
        assert cta_themes[0].feedback_phrase == "remove cta"

    def test_extract_feedback_themes_less_data(self, agent):
        """Test data usage theme for less data"""
        feedback = "Too many numbers, please remove some stats"
        themes = agent._extract_feedback_themes(feedback)

        data_themes = [t for t in themes if t.theme_type == "data_usage"]
        assert len(data_themes) == 1
        assert data_themes[0].feedback_phrase == "less data"

    def test_extract_feedback_themes_remove_emoji(self, agent):
        """Test emoji theme for removing emojis"""
        feedback = "No emoji please, it looks unprofessional"
        themes = agent._extract_feedback_themes(feedback)

        emoji_themes = [t for t in themes if t.theme_type == "emoji"]
        assert len(emoji_themes) == 1
        assert emoji_themes[0].feedback_phrase == "remove emoji"

    def test_learn_from_voice_guide_empty_patterns(
        self, agent, sample_project, sample_posts, test_client
    ):
        """Test learning from voice guide with empty patterns"""
        voice_guide = EnhancedVoiceGuide(
            company_name=test_client,
            generated_from_posts=30,
            dominant_tones=["professional"],
            tone_consistency_score=0.85,
            voice_archetype="Expert",
            average_readability_score=70.0,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],  # Empty
            common_transitions=[],  # Empty
            common_ctas=[],  # Empty
            key_phrases_used=[],
            dos=[],
            donts=[],
        )

        memory = agent.learn_from_project(sample_project, sample_posts, voice_guide)

        assert memory.voice_archetype == "Expert"
        assert memory.average_readability_score == 70.0

    def test_learn_from_voice_guide_running_average(
        self, agent, db, sample_project, sample_posts, test_client
    ):
        """Test readability score running average calculation"""
        # First project
        voice_guide1 = EnhancedVoiceGuide(
            company_name=test_client,
            generated_from_posts=30,
            dominant_tones=["professional"],
            tone_consistency_score=0.85,
            voice_archetype="Expert",
            average_readability_score=70.0,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase1", "phrase2"],
            dos=[],
            donts=[],
        )

        memory = agent.learn_from_project(sample_project, sample_posts, voice_guide1)
        assert memory.average_readability_score == 70.0

        # Second project
        project2 = Project(
            project_id=f"{test_client}_20251202_120000",
            client_name=test_client,
            num_posts=30,
            deliverable_path=f"data/outputs/{test_client}/deliverable2.md",
        )

        voice_guide2 = EnhancedVoiceGuide(
            company_name=test_client,
            generated_from_posts=30,
            dominant_tones=["casual"],
            tone_consistency_score=0.80,
            voice_archetype="Storyteller",  # Different, should not override
            average_readability_score=80.0,  # Different - should average
            average_word_count=250,
            average_paragraph_count=4.0,
            question_usage_rate=0.4,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase3", "phrase4"],  # Different phrases
            dos=[],
            donts=[],
        )

        memory = agent.learn_from_project(project2, sample_posts, voice_guide2)

        # Running average: (70 * 1 + 80) / 2 = 75
        assert memory.average_readability_score == 75.0
        # Voice archetype should remain "Expert" (first project)
        assert memory.voice_archetype == "Expert"
        # Signature phrases should have new ones added
        assert len(memory.signature_phrases) >= 2

    def test_synthesize_with_voice_samples_short_posts(self, agent, db, test_client):
        """Test synthesis with voice samples showing short posts"""
        from src.models.client_memory import VoiceSample

        # Create memory with 2+ projects
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Store voice sample with short average word count
        voice_sample = VoiceSample(
            client_name=test_client,
            project_id="proj1",
            average_readability=70.0,
            voice_archetype="Expert",
            dominant_tone="professional",
            average_word_count=150,  # Short
            question_usage_rate=0.3,
            common_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases=[],
        )
        db.store_voice_sample(voice_sample)

        # Synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        # Should set optimal word count for short posts
        assert result.optimal_word_count_min == 100
        assert result.optimal_word_count_max == 200

    def test_synthesize_with_voice_samples_long_posts(self, agent, db, test_client):
        """Test synthesis with voice samples showing long posts"""
        from src.models.client_memory import VoiceSample

        # Create memory with 2+ projects
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Store voice sample with long average word count
        voice_sample = VoiceSample(
            client_name=test_client,
            project_id="proj1",
            average_readability=70.0,
            voice_archetype="Expert",
            dominant_tone="professional",
            average_word_count=350,  # Long
            question_usage_rate=0.3,
            common_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases=[],
        )
        db.store_voice_sample(voice_sample)

        # Synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        # Should set optimal word count for long posts
        assert result.optimal_word_count_min == 250
        assert result.optimal_word_count_max == 350

    def test_synthesize_with_voice_samples_medium_posts(self, agent, db, test_client):
        """Test synthesis with voice samples showing medium posts"""
        from src.models.client_memory import VoiceSample

        # Create memory with 2+ projects
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Store voice sample with medium average word count
        voice_sample = VoiceSample(
            client_name=test_client,
            project_id="proj1",
            average_readability=70.0,
            voice_archetype="Expert",
            dominant_tone="professional",
            average_word_count=250,  # Medium
            question_usage_rate=0.3,
            common_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases=[],
        )
        db.store_voice_sample(voice_sample)

        # Synthesize
        result = agent.synthesize_multi_project_learnings(test_client)

        # Should set optimal word count for medium posts
        assert result.optimal_word_count_min == 150
        assert result.optimal_word_count_max == 250

    def test_get_memory_insights_with_themes_and_templates(self, agent, db, test_client):
        """Test insights with feedback themes and template performance"""
        # Create memory
        memory = agent.db.get_or_create_client_memory(test_client)
        memory.add_project(30, 1800.0)
        agent.db.update_client_memory(memory)

        # Add feedback themes
        theme = FeedbackTheme(theme_type="tone", feedback_phrase="more casual")
        db.record_feedback_theme(test_client, theme)

        # Add template performance
        db.update_template_performance(test_client, 1, False, 8.5)
        db.update_template_performance(test_client, 2, True, 6.0)

        # Get insights
        insights = agent.get_memory_insights(test_client)

        assert "top_feedback_themes" in insights
        assert len(insights["top_feedback_themes"]) >= 1
        assert "best_templates" in insights
        assert len(insights["best_templates"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ---------------------------------------------------------------------------
# Additional coverage tests — appended to existing suite
# ---------------------------------------------------------------------------


class TestExtractFeedbackThemesAdditional:
    """Cover remaining branches in _extract_feedback_themes."""

    @pytest.fixture
    def agent(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        db = ProjectDatabase(db_path)
        return MemoryLearningAgent(db)

    def test_empty_feedback_returns_no_themes(self, agent):
        """Empty string produces no themes."""
        themes = agent._extract_feedback_themes("")
        assert themes == []

    def test_unrelated_feedback_returns_no_themes(self, agent):
        """Feedback with no matching signals returns empty list."""
        themes = agent._extract_feedback_themes("Looks good! Nice work overall.")
        assert themes == []

    def test_more_professional_tone_theme(self, agent):
        """'more professional' phrase maps to 'more professional' tone theme."""
        themes = agent._extract_feedback_themes("Please make this more professional and formal")
        tone_themes = [t for t in themes if t.theme_type == "tone"]
        assert len(tone_themes) == 1
        assert tone_themes[0].feedback_phrase == "more professional"

    def test_more_direct_tone_theme(self, agent):
        """'get to the point' phrase maps to 'more direct' tone theme."""
        themes = agent._extract_feedback_themes("Can you get to the point faster?")
        tone_themes = [t for t in themes if t.theme_type == "tone"]
        assert len(tone_themes) == 1
        assert tone_themes[0].feedback_phrase == "more direct"

    def test_more_warm_tone_theme(self, agent):
        """'warmer' phrase maps to 'more warm' tone theme."""
        themes = agent._extract_feedback_themes("The tone feels cold. Can you make it warmer?")
        tone_themes = [t for t in themes if t.theme_type == "tone"]
        assert len(tone_themes) == 1
        assert tone_themes[0].feedback_phrase == "more warm"

    def test_only_one_tone_theme_per_feedback(self, agent):
        """Even if multiple tone signals exist, only one tone theme is extracted."""
        themes = agent._extract_feedback_themes("Please be more casual and also more professional")
        tone_themes = [t for t in themes if t.theme_type == "tone"]
        assert len(tone_themes) == 1  # Break ensures only first match

    def test_longer_feedback_triggers_length_theme(self, agent):
        """'longer' keyword triggers 'too short' length theme."""
        themes = agent._extract_feedback_themes(
            "Could you make this a bit longer with more context?"
        )
        length_themes = [t for t in themes if t.theme_type == "length"]
        assert len(length_themes) == 1
        assert length_themes[0].feedback_phrase == "too short"

    def test_more_concise_triggers_too_long_theme(self, agent):
        """'more concise' keyword triggers 'too long' length theme."""
        themes = agent._extract_feedback_themes("Please be more concise in the next version.")
        length_themes = [t for t in themes if t.theme_type == "length"]
        assert len(length_themes) == 1
        assert length_themes[0].feedback_phrase == "too long"

    def test_cta_with_clearer_trigger(self, agent):
        """'call to action' + 'clearer' → stronger cta theme."""
        themes = agent._extract_feedback_themes(
            "The call to action could be clearer and more prominent."
        )
        cta_themes = [t for t in themes if t.theme_type == "cta"]
        assert len(cta_themes) == 1
        assert cta_themes[0].feedback_phrase == "stronger cta"

    def test_no_cta_feedback_phrase(self, agent):
        """'no cta' triggers remove cta theme."""
        themes = agent._extract_feedback_themes("Please remove the CTA, we want no cta here.")
        cta_themes = [t for t in themes if t.theme_type == "cta"]
        assert len(cta_themes) == 1
        assert cta_themes[0].feedback_phrase == "remove cta"

    def test_add_stats_triggers_data_theme(self, agent):
        """'add stats' triggers add more data theme."""
        themes = agent._extract_feedback_themes("Can you add stats to support this claim?")
        data_themes = [t for t in themes if t.theme_type == "data_usage"]
        assert len(data_themes) == 1
        assert data_themes[0].feedback_phrase == "add more data"

    def test_add_numbers_triggers_data_theme(self, agent):
        """'add numbers' triggers add more data theme."""
        themes = agent._extract_feedback_themes("Please add numbers to make it more credible.")
        data_themes = [t for t in themes if t.theme_type == "data_usage"]
        assert len(data_themes) == 1
        assert data_themes[0].feedback_phrase == "add more data"

    def test_less_data_triggers_less_data_theme(self, agent):
        """'less data' triggers less data theme."""
        themes = agent._extract_feedback_themes("You have less data needs here. Remove some.")
        data_themes = [t for t in themes if t.theme_type == "data_usage"]
        assert len(data_themes) == 1
        assert data_themes[0].feedback_phrase == "less data"

    def test_use_emoji_triggers_add_emoji_theme(self, agent):
        """'use emoji' triggers add emoji theme."""
        themes = agent._extract_feedback_themes("Please use emoji to make it more fun.")
        emoji_themes = [t for t in themes if t.theme_type == "emoji"]
        assert len(emoji_themes) == 1
        assert emoji_themes[0].feedback_phrase == "add emoji"

    def test_no_emojis_triggers_remove_emoji_theme(self, agent):
        """'no emojis' triggers remove emoji theme."""
        themes = agent._extract_feedback_themes("No emojis please, keep it clean.")
        emoji_themes = [t for t in themes if t.theme_type == "emoji"]
        assert len(emoji_themes) == 1
        assert emoji_themes[0].feedback_phrase == "remove emoji"

    def test_flow_triggers_structure_theme(self, agent):
        """'flow' keyword triggers improve structure theme."""
        themes = agent._extract_feedback_themes("The flow of this post could be improved.")
        structure_themes = [t for t in themes if t.theme_type == "structure"]
        assert len(structure_themes) == 1
        assert structure_themes[0].feedback_phrase == "improve structure"

    def test_reorganize_triggers_structure_theme(self, agent):
        """'reorganize' keyword triggers improve structure theme."""
        themes = agent._extract_feedback_themes("Please reorganize the sections differently.")
        structure_themes = [t for t in themes if t.theme_type == "structure"]
        assert len(structure_themes) == 1

    def test_multiple_theme_types_in_one_feedback(self, agent):
        """Feedback with length + emoji signals produces both themes."""
        themes = agent._extract_feedback_themes("This is too long and please add some emoji to it.")
        theme_types = {t.theme_type for t in themes}
        assert "length" in theme_types
        assert "emoji" in theme_types

    def test_feedback_themes_returns_list_of_feedback_theme(self, agent):
        """Return type is always a list of FeedbackTheme instances."""
        themes = agent._extract_feedback_themes("Add emoji please")
        assert isinstance(themes, list)
        for theme in themes:
            assert isinstance(theme, FeedbackTheme)


class TestLearnFromProjectAdditional:
    """Cover additional branches in learn_from_project and _learn_from_voice_guide."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        db = ProjectDatabase(db_path)
        client_prefix = "TestCoverage_"
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'DELETE FROM template_performance WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(
                f'DELETE FROM client_feedback_themes WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(
                f'DELETE FROM client_voice_samples WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(f'DELETE FROM client_history WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()
        yield
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'DELETE FROM template_performance WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(
                f'DELETE FROM client_feedback_themes WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(
                f'DELETE FROM client_voice_samples WHERE client_name LIKE "{client_prefix}%"'
            )
            cursor.execute(f'DELETE FROM client_history WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()

    @pytest.fixture
    def db(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def agent(self, db):
        return MemoryLearningAgent(db)

    @pytest.fixture
    def client_name(self):
        return f"TestCoverage_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    @pytest.fixture
    def project(self, client_name):
        return Project(
            project_id=f"{client_name}_proj1",
            client_name=client_name,
            num_posts=10,
            deliverable_path=f"data/outputs/{client_name}/deliverable.md",
        )

    @pytest.fixture
    def posts(self, client_name):
        return [
            Post(
                content="Test post",
                template_id=3,
                template_name="Contrarian",
                variant=1,
                client_name=client_name,
            )
        ]

    def test_learn_from_project_without_voice_guide(self, agent, project, posts, client_name):
        """Learning without a voice guide still creates memory."""
        memory = agent.learn_from_project(project, posts, voice_guide=None)
        assert memory.client_name == client_name
        assert memory.total_posts_generated == 10

    def test_learn_from_project_sets_voice_archetype_once(
        self, agent, db, project, posts, client_name
    ):
        """First project with voice guide sets voice_archetype; second doesn't overwrite."""
        from src.models.voice_guide import EnhancedVoiceGuide

        vg1 = EnhancedVoiceGuide(
            company_name=client_name,
            generated_from_posts=10,
            dominant_tones=["professional"],
            tone_consistency_score=0.80,
            voice_archetype="Expert",
            average_readability_score=70.0,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase_a"],
            dos=[],
            donts=[],
        )

        mem1 = agent.learn_from_project(project, posts, voice_guide=vg1)
        assert mem1.voice_archetype == "Expert"

        # Second project with different archetype
        project2 = Project(
            project_id=f"{client_name}_proj2",
            client_name=client_name,
            num_posts=10,
            deliverable_path=f"data/outputs/{client_name}/deliverable2.md",
        )
        vg2 = EnhancedVoiceGuide(
            company_name=client_name,
            generated_from_posts=10,
            dominant_tones=["casual"],
            tone_consistency_score=0.75,
            voice_archetype="Friend",  # Different
            average_readability_score=80.0,
            average_word_count=180,
            average_paragraph_count=2.5,
            question_usage_rate=0.5,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase_b"],
            dos=[],
            donts=[],
        )

        mem2 = agent.learn_from_project(project2, posts, voice_guide=vg2)
        # Archetype should remain "Expert" — first project set it
        assert mem2.voice_archetype == "Expert"

    def test_learn_from_project_signature_phrases_no_duplicates(
        self, agent, db, project, posts, client_name
    ):
        """Repeated key phrases are not added to signature_phrases twice."""
        from src.models.voice_guide import EnhancedVoiceGuide

        vg = EnhancedVoiceGuide(
            company_name=client_name,
            generated_from_posts=10,
            dominant_tones=["professional"],
            tone_consistency_score=0.80,
            voice_archetype="Expert",
            average_readability_score=70.0,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase_x", "phrase_y"],
            dos=[],
            donts=[],
        )
        agent.learn_from_project(project, posts, voice_guide=vg)

        # Second project with same phrases
        project2 = Project(
            project_id=f"{client_name}_proj2",
            client_name=client_name,
            num_posts=10,
            deliverable_path=f"data/outputs/{client_name}/deliverable2.md",
        )
        vg2 = EnhancedVoiceGuide(
            company_name=client_name,
            generated_from_posts=10,
            dominant_tones=["professional"],
            tone_consistency_score=0.80,
            voice_archetype="Expert",
            average_readability_score=70.0,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=["phrase_x", "phrase_y"],  # Same as before
            dos=[],
            donts=[],
        )
        mem2 = agent.learn_from_project(project2, posts, voice_guide=vg2)

        # phrase_x and phrase_y should each appear exactly once
        assert mem2.signature_phrases.count("phrase_x") == 1
        assert mem2.signature_phrases.count("phrase_y") == 1

    def test_learn_from_project_multiple_templates_tracked(self, agent, db, client_name):
        """Multiple different templates in one project are all recorded."""
        project = Project(
            project_id=f"{client_name}_multi",
            client_name=client_name,
            num_posts=3,
            deliverable_path=f"data/outputs/{client_name}/deliverable.md",
        )
        posts = [
            Post(
                content="p1", template_id=1, template_name="T1", variant=1, client_name=client_name
            ),
            Post(
                content="p2", template_id=2, template_name="T2", variant=1, client_name=client_name
            ),
            Post(
                content="p3", template_id=2, template_name="T2", variant=2, client_name=client_name
            ),
        ]
        agent.learn_from_project(project, posts)

        perf = db.get_template_performance(client_name)
        assert 1 in perf
        assert 2 in perf
        assert perf[1]["usage_count"] == 1
        assert perf[2]["usage_count"] == 2

    def test_learn_from_voice_guide_no_readability_score(self, agent, project, posts, client_name):
        """Voice guide with no readability score does not crash."""
        from src.models.voice_guide import EnhancedVoiceGuide

        vg = EnhancedVoiceGuide(
            company_name=client_name,
            generated_from_posts=10,
            dominant_tones=["professional"],
            tone_consistency_score=0.80,
            voice_archetype="Expert",
            average_readability_score=0.0,  # Falsy — branch skips average update
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.3,
            common_opening_hooks=[],
            common_transitions=[],
            common_ctas=[],
            key_phrases_used=[],
            dos=[],
            donts=[],
        )
        memory = agent.learn_from_project(project, posts, voice_guide=vg)
        # Should not raise; readability not updated when score is falsy
        assert memory is not None


class TestSynthesizeMultiProjectLearningsAdditional:
    """Cover remaining branches in synthesize_multi_project_learnings."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        db = ProjectDatabase(db_path)
        client_prefix = "TestSynth_"
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for table in (
                "template_performance",
                "client_feedback_themes",
                "client_voice_samples",
                "client_history",
            ):
                cursor.execute(f'DELETE FROM {table} WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()
        yield
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for table in (
                "template_performance",
                "client_feedback_themes",
                "client_voice_samples",
                "client_history",
            ):
                cursor.execute(f'DELETE FROM {table} WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()

    @pytest.fixture
    def db(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def agent(self, db):
        return MemoryLearningAgent(db)

    @pytest.fixture
    def client_name(self):
        return f"TestSynth_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    def test_synthesize_unknown_client_returns_none(self, agent):
        """Client that has never been seen returns None."""
        result = agent.synthesize_multi_project_learnings("NonExistentClientXYZ123")
        assert result is None

    def test_synthesize_no_voice_samples_leaves_word_count_default(self, agent, db, client_name):
        """Synthesis with no voice samples does not alter optimal word count."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        result = agent.synthesize_multi_project_learnings(client_name)

        # No voice samples → word count fields stay at model defaults
        assert result is not None
        # Defaults from ClientMemory model — just verify no exception was raised
        assert result.optimal_word_count_min is not None

    def test_synthesize_theme_appearing_once_not_added_to_adjustments(self, agent, db, client_name):
        """Themes appearing only once are NOT added to voice_adjustments."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        # Record theme only once
        theme = FeedbackTheme(theme_type="tone", feedback_phrase="more casual")
        db.record_feedback_theme(client_name, theme)

        result = agent.synthesize_multi_project_learnings(client_name)

        # Occurrence count is 1 → should NOT be in voice_adjustments
        assert "tone" not in result.voice_adjustments

    def test_synthesize_template_usage_count_below_two_ignored(self, agent, db, client_name):
        """Templates used fewer than 2 times are ignored in preferred/avoided."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        # Template 99 used only once with no revisions
        db.update_template_performance(client_name, 99, False, 9.0)

        result = agent.synthesize_multi_project_learnings(client_name)

        assert 99 not in result.preferred_templates
        assert 99 not in result.avoided_templates


class TestGetMemoryInsightsAdditional:
    """Cover remaining branches in get_memory_insights."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        db = ProjectDatabase(db_path)
        client_prefix = "TestInsights_"
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for table in (
                "template_performance",
                "client_feedback_themes",
                "client_voice_samples",
                "client_history",
            ):
                cursor.execute(f'DELETE FROM {table} WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()
        yield
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for table in (
                "template_performance",
                "client_feedback_themes",
                "client_voice_samples",
                "client_history",
            ):
                cursor.execute(f'DELETE FROM {table} WHERE client_name LIKE "{client_prefix}%"')
            conn.commit()

    @pytest.fixture
    def db(self):
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def agent(self, db):
        return MemoryLearningAgent(db)

    @pytest.fixture
    def client_name(self):
        return f"TestInsights_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    def test_insights_no_themes_no_templates(self, agent, db, client_name):
        """Insights without themes or template data omit those keys."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        insights = agent.get_memory_insights(client_name)

        assert "error" not in insights
        assert "top_feedback_themes" not in insights
        assert "best_templates" not in insights

    def test_insights_contains_all_required_keys(self, agent, db, client_name):
        """Insights dict always includes required keys."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        insights = agent.get_memory_insights(client_name)

        required_keys = [
            "client_name",
            "total_projects",
            "is_repeat_client",
            "is_high_value",
            "avg_revisions_per_project",
            "lifetime_value",
            "preferred_templates",
            "avoided_templates",
            "voice_adjustments",
            "optimal_word_count",
            "voice_archetype",
            "signature_phrases",
        ]
        for key in required_keys:
            assert key in insights, f"Missing key: {key}"

    def test_insights_lifetime_value_format(self, agent, db, client_name):
        """lifetime_value is formatted as a dollar string."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        insights = agent.get_memory_insights(client_name)

        assert insights["lifetime_value"].startswith("$")

    def test_insights_optimal_word_count_format(self, agent, db, client_name):
        """optimal_word_count contains 'words' in its value."""
        memory = db.get_or_create_client_memory(client_name)
        memory.add_project(30, 1800.0)
        db.update_client_memory(memory)

        insights = agent.get_memory_insights(client_name)

        assert "words" in insights["optimal_word_count"]
