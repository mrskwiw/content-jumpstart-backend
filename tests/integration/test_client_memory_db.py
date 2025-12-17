"""Integration tests for client memory database operations"""

from datetime import datetime
from pathlib import Path

import pytest

from src.database.project_db import ProjectDatabase
from src.models.client_memory import FeedbackTheme, VoiceSample


class TestClientMemoryDatabase:
    """Test client memory database operations"""

    @pytest.fixture
    def db(self):
        """Get database instance"""
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def test_client(self):
        """Test client name"""
        return f"TestClient_MemoryTest_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def test_01_get_or_create_client_memory(self, db, test_client):
        """Test getting or creating client memory"""
        print("\n[TEST 1] Get or Create Client Memory")
        print("-" * 60)

        memory = db.get_or_create_client_memory(test_client)
        assert memory is not None
        assert memory.client_name == test_client
        assert memory.total_projects == 0
        assert not memory.is_repeat_client
        print(f"[OK] Created new memory for: {memory.client_name}")
        print(f"  - Total projects: {memory.total_projects}")
        print(f"  - Is repeat client: {memory.is_repeat_client}")

    def test_02_add_project_and_update(self, db, test_client):
        """Test adding project and updating memory"""
        print("\n[TEST 2] Add Project and Update Memory")
        print("-" * 60)

        memory = db.get_or_create_client_memory(test_client)
        memory.add_project(num_posts=30, project_value=1800.0)
        success = db.update_client_memory(memory)

        assert success
        assert memory.total_projects == 1
        assert memory.total_posts_generated == 30
        assert memory.lifetime_value == 1800.0
        assert memory.is_repeat_client
        print(f"[OK] Updated memory: {success}")
        print(f"  - Total projects: {memory.total_projects}")
        print(f"  - Total posts: {memory.total_posts_generated}")
        print(f"  - Lifetime value: ${memory.lifetime_value}")
        print(f"  - Is repeat client: {memory.is_repeat_client}")

    def test_03_update_template_preferences(self, db, test_client):
        """Test updating template preferences"""
        print("\n[TEST 3] Update Template Preferences")
        print("-" * 60)

        memory = db.get_or_create_client_memory(test_client)
        memory.update_template_preference(template_id=1, revision_rate=0.15)
        memory.update_template_preference(template_id=6, revision_rate=0.60)
        success = db.update_client_memory(memory)

        assert success
        assert 1 in memory.preferred_templates
        assert 6 in memory.avoided_templates
        assert memory.template_performance[1] == 0.15
        assert memory.template_performance[6] == 0.60
        print(f"[OK] Updated template preferences: {success}")
        print(f"  - Preferred templates: {memory.preferred_templates}")
        print(f"  - Avoided templates: {memory.avoided_templates}")
        print(f"  - Template performance: {memory.template_performance}")

    def test_04_update_voice_adjustments(self, db, test_client):
        """Test updating voice adjustments"""
        print("\n[TEST 4] Update Voice Adjustments")
        print("-" * 60)

        memory = db.get_or_create_client_memory(test_client)
        memory.update_voice_adjustment("tone", "more_casual")
        memory.update_voice_adjustment("length", "shorter")
        success = db.update_client_memory(memory)

        assert success
        assert memory.voice_adjustments["tone"] == "more_casual"
        assert memory.voice_adjustments["length"] == "shorter"
        print(f"[OK] Updated voice adjustments: {success}")
        print(f"  - Voice adjustments: {memory.voice_adjustments}")

    def test_05_store_voice_sample(self, db, test_client):
        """Test storing voice sample"""
        print("\n[TEST 5] Store Voice Sample")
        print("-" * 60)

        voice_sample = VoiceSample(
            client_name=test_client,
            project_id=f"{test_client}_20251201_120000",
            average_readability=65.5,
            voice_archetype="Expert",
            dominant_tone="professional_friendly",
            average_word_count=220,
            question_usage_rate=0.4,
            common_hooks=["Ever wonder why...", "Here's the thing about..."],
            common_transitions=["The key is...", "But here's what matters..."],
            common_ctas=["What's your take?", "Drop a comment if..."],
            key_phrases=["data-driven", "actionable insights", "bottom line"],
        )
        success = db.store_voice_sample(voice_sample)

        assert success
        print(f"[OK] Stored voice sample: {success}")
        print(f"  - Project: {voice_sample.project_id}")
        print(f"  - Archetype: {voice_sample.voice_archetype}")
        print(f"  - Readability: {voice_sample.average_readability}")

    def test_06_retrieve_voice_samples(self, db, test_client):
        """Test retrieving voice samples"""
        print("\n[TEST 6] Retrieve Voice Samples")
        print("-" * 60)

        samples = db.get_voice_samples(test_client, limit=5)

        assert len(samples) > 0
        assert all(isinstance(s, VoiceSample) for s in samples)
        print(f"[OK] Retrieved {len(samples)} voice samples")
        for sample in samples:
            print(
                f"  - {sample.project_id}: {sample.voice_archetype}, readability={sample.average_readability}"
            )

    def test_07_record_feedback_themes(self, db, test_client):
        """Test recording feedback themes"""
        print("\n[TEST 7] Record Feedback Themes")
        print("-" * 60)

        theme1 = FeedbackTheme(theme_type="tone", feedback_phrase="more casual")
        success1 = db.record_feedback_theme(test_client, theme1)
        assert success1
        print(f"[OK] Recorded theme 'tone: more casual': {success1}")

        theme2 = FeedbackTheme(theme_type="length", feedback_phrase="too long")
        success2 = db.record_feedback_theme(test_client, theme2)
        assert success2
        print(f"[OK] Recorded theme 'length: too long': {success2}")

        # Record same theme again to test increment
        success3 = db.record_feedback_theme(test_client, theme1)
        assert success3
        print(f"[OK] Recorded theme 'tone: more casual' again (should increment): {success3}")

    def test_08_retrieve_feedback_themes(self, db, test_client):
        """Test retrieving feedback themes"""
        print("\n[TEST 8] Retrieve Feedback Themes")
        print("-" * 60)

        themes = db.get_feedback_themes(test_client)

        assert len(themes) > 0
        assert all(isinstance(t, FeedbackTheme) for t in themes)

        # Check that 'tone: more casual' has count of 2
        tone_themes = [
            t for t in themes if t.theme_type == "tone" and t.feedback_phrase == "more casual"
        ]
        assert len(tone_themes) == 1
        assert tone_themes[0].occurrence_count == 2

        print(f"[OK] Retrieved {len(themes)} feedback themes")
        for theme in themes:
            print(
                f"  - {theme.theme_type}: '{theme.feedback_phrase}' (occurred {theme.occurrence_count}x)"
            )

    def test_09_update_template_performance(self, db, test_client):
        """Test updating template performance"""
        print("\n[TEST 9] Update Template Performance")
        print("-" * 60)

        # Template 1: used, not revised (good)
        success1 = db.update_template_performance(
            test_client, template_id=1, was_revised=False, quality_score=8.5
        )
        assert success1
        print(f"[OK] Template 1 (kept): {success1}")

        # Template 1 used again, revised this time
        success2 = db.update_template_performance(
            test_client, template_id=1, was_revised=True, quality_score=7.0
        )
        assert success2
        print(f"[OK] Template 1 (revised): {success2}")

        # Template 6: used and revised (problematic)
        success3 = db.update_template_performance(
            test_client, template_id=6, was_revised=True, quality_score=5.5
        )
        assert success3
        print(f"[OK] Template 6 (revised): {success3}")

    def test_10_retrieve_template_performance(self, db, test_client):
        """Test retrieving template performance"""
        print("\n[TEST 10] Retrieve Template Performance")
        print("-" * 60)

        perf = db.get_template_performance(test_client)

        assert len(perf) > 0
        assert 1 in perf
        assert 6 in perf

        # Verify template 1 stats
        t1 = perf[1]
        assert t1["usage_count"] == 2
        assert t1["revision_count"] == 1
        assert t1["revision_rate"] == 0.5  # 1/2
        assert t1["client_kept_count"] == 1

        # Verify template 6 stats
        t6 = perf[6]
        assert t6["usage_count"] == 1
        assert t6["revision_count"] == 1
        assert t6["revision_rate"] == 1.0  # 1/1
        assert t6["client_kept_count"] == 0

        print(f"[OK] Retrieved performance for {len(perf)} templates")
        for template_id, data in perf.items():
            print(f"  - Template {template_id}:")
            print(
                f"    Usage: {data['usage_count']}, Revisions: {data['revision_count']}, Rate: {data['revision_rate']:.2f}"
            )
            print(
                f"    Avg Quality: {data['average_quality_score']:.1f}, Kept: {data['client_kept_count']}"
            )

    def test_11_get_all_client_names(self, db, test_client):
        """Test getting all client names"""
        print("\n[TEST 11] Get All Client Names")
        print("-" * 60)

        client_names = db.get_all_client_names()

        assert len(client_names) > 0
        assert test_client in client_names
        print(f"[OK] Retrieved {len(client_names)} client names")
        for name in client_names[:5]:  # Show first 5
            print(f"  - {name}")

    def test_12_retrieve_updated_memory(self, db, test_client):
        """Test retrieving final updated memory"""
        print("\n[TEST 12] Retrieve Updated Memory")
        print("-" * 60)

        updated_memory = db.get_client_memory(test_client)

        assert updated_memory is not None
        assert updated_memory.client_name == test_client
        assert updated_memory.total_projects >= 1
        assert updated_memory.total_posts_generated >= 30
        assert updated_memory.lifetime_value >= 1800.0
        assert len(updated_memory.preferred_templates) > 0
        assert len(updated_memory.avoided_templates) > 0
        assert len(updated_memory.voice_adjustments) > 0

        print("[OK] Retrieved updated memory")
        print(f"  - Total projects: {updated_memory.total_projects}")
        print(f"  - Total posts: {updated_memory.total_posts_generated}")
        print(f"  - Lifetime value: ${updated_memory.lifetime_value}")
        print(f"  - Preferred templates: {updated_memory.preferred_templates}")
        print(f"  - Avoided templates: {updated_memory.avoided_templates}")
        print(f"  - Voice adjustments: {updated_memory.voice_adjustments}")
        print(f"  - Avg revisions/project: {updated_memory.avg_revisions_per_project}")
        print(f"  - High value client: {updated_memory.is_high_value_client}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
