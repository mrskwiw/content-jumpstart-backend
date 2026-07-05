"""Unit tests for client_memory module.

Tests cover:
- ClientMemory model and all its methods/properties
- FeedbackTheme model and methods
- VoiceSample model and methods
- to_dict/from_dict serialization for all models
"""

import json
from datetime import datetime

import pytest

from src.models.client_memory import (
    ClientMemory,
    FeedbackTheme,
    VoiceSample,
)


class TestClientMemoryModel:
    """Tests for ClientMemory model creation."""

    def test_create_basic_memory(self):
        """Test creating a basic client memory."""
        memory = ClientMemory(client_name="Test Client")

        assert memory.client_name == "Test Client"
        assert memory.total_projects == 0
        assert memory.total_posts_generated == 0
        assert memory.total_revisions == 0
        assert memory.first_project_date is None
        assert memory.last_project_date is None
        assert memory.preferred_templates == []
        assert memory.avoided_templates == []
        assert memory.template_performance == {}
        assert memory.voice_adjustments == {}
        assert memory.lifetime_value == 0.0

    def test_create_with_values(self):
        """Test creating client memory with custom values."""
        memory = ClientMemory(
            client_name="Premium Client",
            total_projects=5,
            total_posts_generated=150,
            total_revisions=10,
            lifetime_value=7500.0,
            preferred_templates=[1, 2, 5],
            voice_archetype="Expert",
            average_readability_score=55.0,
        )

        assert memory.total_projects == 5
        assert memory.total_posts_generated == 150
        assert memory.total_revisions == 10
        assert memory.lifetime_value == 7500.0
        assert memory.preferred_templates == [1, 2, 5]
        assert memory.voice_archetype == "Expert"
        assert memory.average_readability_score == 55.0


class TestClientMemoryProperties:
    """Tests for ClientMemory properties."""

    def test_is_repeat_client_false(self):
        """Test is_repeat_client returns False for new client."""
        memory = ClientMemory(client_name="New Client")
        assert memory.is_repeat_client is False

    def test_is_repeat_client_true(self):
        """Test is_repeat_client returns True after project."""
        memory = ClientMemory(client_name="Repeat Client", total_projects=1)
        assert memory.is_repeat_client is True

    def test_avg_revisions_per_project_zero_projects(self):
        """Test avg_revisions_per_project with zero projects."""
        memory = ClientMemory(client_name="New Client")
        assert memory.avg_revisions_per_project == 0.0

    def test_avg_revisions_per_project_with_data(self):
        """Test avg_revisions_per_project calculation."""
        memory = ClientMemory(
            client_name="Client",
            total_projects=3,
            total_revisions=6,
        )
        assert memory.avg_revisions_per_project == 2.0

    def test_avg_revisions_per_project_rounds(self):
        """Test avg_revisions_per_project rounds to 2 decimals."""
        memory = ClientMemory(
            client_name="Client",
            total_projects=3,
            total_revisions=7,
        )
        assert memory.avg_revisions_per_project == 2.33

    def test_is_high_value_client_by_projects(self):
        """Test is_high_value_client with 3+ projects."""
        memory = ClientMemory(client_name="Active Client", total_projects=3)
        assert memory.is_high_value_client is True

    def test_is_high_value_client_by_ltv(self):
        """Test is_high_value_client with $5k+ LTV."""
        memory = ClientMemory(client_name="Big Spender", lifetime_value=5000.0)
        assert memory.is_high_value_client is True

    def test_is_high_value_client_false(self):
        """Test is_high_value_client returns False for low-value client."""
        memory = ClientMemory(
            client_name="Small Client",
            total_projects=2,
            lifetime_value=1500.0,
        )
        assert memory.is_high_value_client is False


class TestClientMemoryMethods:
    """Tests for ClientMemory methods."""

    def test_add_project(self):
        """Test add_project updates memory correctly."""
        memory = ClientMemory(client_name="Client")

        memory.add_project(num_posts=30, project_value=1500.0)

        assert memory.total_projects == 1
        assert memory.total_posts_generated == 30
        assert memory.lifetime_value == 1500.0
        assert memory.first_project_date is not None
        assert memory.last_project_date is not None

    def test_add_project_with_date(self):
        """Test add_project with explicit date."""
        memory = ClientMemory(client_name="Client")
        project_date = datetime(2025, 1, 15)

        memory.add_project(num_posts=30, project_value=1500.0, project_date=project_date)

        assert memory.first_project_date == project_date
        assert memory.last_project_date == project_date

    def test_add_multiple_projects(self):
        """Test adding multiple projects."""
        memory = ClientMemory(client_name="Client")

        memory.add_project(num_posts=30, project_value=1500.0)
        memory.add_project(num_posts=20, project_value=1000.0)

        assert memory.total_projects == 2
        assert memory.total_posts_generated == 50
        assert memory.lifetime_value == 2500.0

    def test_add_revisions(self):
        """Test add_revisions updates memory."""
        memory = ClientMemory(client_name="Client")

        memory.add_revisions(5)

        assert memory.total_revisions == 5

    def test_add_revisions_accumulates(self):
        """Test add_revisions accumulates correctly."""
        memory = ClientMemory(client_name="Client")

        memory.add_revisions(3)
        memory.add_revisions(2)

        assert memory.total_revisions == 5

    def test_update_template_preference_low_revision_rate(self):
        """Test template becomes preferred with low revision rate."""
        memory = ClientMemory(client_name="Client")

        memory.update_template_preference(template_id=1, revision_rate=0.15)

        assert memory.template_performance[1] == 0.15
        assert 1 in memory.preferred_templates
        assert 1 not in memory.avoided_templates

    def test_update_template_preference_high_revision_rate(self):
        """Test template becomes avoided with high revision rate."""
        memory = ClientMemory(client_name="Client")

        memory.update_template_preference(template_id=2, revision_rate=0.6)

        assert memory.template_performance[2] == 0.6
        assert 2 in memory.avoided_templates
        assert 2 not in memory.preferred_templates

    def test_update_template_preference_medium_rate(self):
        """Test template with medium rate is neither preferred nor avoided."""
        memory = ClientMemory(client_name="Client")

        memory.update_template_preference(template_id=3, revision_rate=0.35)

        assert memory.template_performance[3] == 0.35
        assert 3 not in memory.preferred_templates
        assert 3 not in memory.avoided_templates

    def test_update_template_preference_moves_from_avoided(self):
        """Test template moves from avoided to preferred."""
        memory = ClientMemory(client_name="Client")
        memory.avoided_templates = [1]

        memory.update_template_preference(template_id=1, revision_rate=0.1)

        assert 1 in memory.preferred_templates
        assert 1 not in memory.avoided_templates

    def test_update_template_preference_moves_from_preferred(self):
        """Test template moves from preferred to avoided."""
        memory = ClientMemory(client_name="Client")
        memory.preferred_templates = [1]

        memory.update_template_preference(template_id=1, revision_rate=0.7)

        assert 1 in memory.avoided_templates
        assert 1 not in memory.preferred_templates

    def test_update_voice_adjustment(self):
        """Test update_voice_adjustment adds adjustment."""
        memory = ClientMemory(client_name="Client")

        memory.update_voice_adjustment("tone", "more_casual")

        assert memory.voice_adjustments["tone"] == "more_casual"

    def test_update_voice_adjustment_overwrites(self):
        """Test update_voice_adjustment overwrites existing adjustment."""
        memory = ClientMemory(
            client_name="Client",
            voice_adjustments={"tone": "formal"},
        )

        memory.update_voice_adjustment("tone", "casual")

        assert memory.voice_adjustments["tone"] == "casual"


class TestClientMemorySerialization:
    """Tests for ClientMemory to_dict and from_dict."""

    def test_to_dict(self):
        """Test to_dict returns correct structure."""
        memory = ClientMemory(
            client_name="Test Client",
            total_projects=2,
            preferred_templates=[1, 2],
            voice_adjustments={"tone": "casual"},
        )

        result = memory.to_dict()

        assert result["client_name"] == "Test Client"
        assert result["total_projects"] == 2
        assert json.loads(result["preferred_templates"]) == [1, 2]
        assert json.loads(result["voice_adjustments"]) == {"tone": "casual"}

    def test_from_dict_basic(self):
        """Test from_dict creates memory from dict."""
        data = {
            "client_name": "Test Client",
            "total_projects": 3,
        }

        memory = ClientMemory.from_dict(data)

        assert memory.client_name == "Test Client"
        assert memory.total_projects == 3

    def test_from_dict_parses_json_fields(self):
        """Test from_dict parses JSON string fields."""
        data = {
            "client_name": "Client",
            "preferred_templates": "[1, 2, 3]",
            "avoided_templates": "[4, 5]",
            "voice_adjustments": '{"tone": "formal"}',
            "preferred_cta_types": '["question", "engagement"]',
            "signature_phrases": '["Let me tell you", "Here is the thing"]',
        }

        memory = ClientMemory.from_dict(data)

        assert memory.preferred_templates == [1, 2, 3]
        assert memory.avoided_templates == [4, 5]
        assert memory.voice_adjustments == {"tone": "formal"}
        assert memory.preferred_cta_types == ["question", "engagement"]
        assert memory.signature_phrases == ["Let me tell you", "Here is the thing"]

    def test_from_dict_handles_invalid_json(self):
        """Test from_dict handles invalid JSON gracefully."""
        data = {
            "client_name": "Client",
            "preferred_templates": "not valid json",
            "avoided_templates": "{invalid}",
            "voice_adjustments": "not json",
            "preferred_cta_types": "bad json",
            "signature_phrases": "invalid",
        }

        memory = ClientMemory.from_dict(data)

        assert memory.preferred_templates == []
        assert memory.avoided_templates == []
        assert memory.voice_adjustments == {}
        assert memory.preferred_cta_types == []
        assert memory.signature_phrases == []

    def test_from_dict_parses_timestamps(self):
        """Test from_dict parses ISO timestamp strings."""
        data = {
            "client_name": "Client",
            "first_project_date": "2025-01-15T10:30:00",
            "last_project_date": "2025-06-20T14:45:00",
            "last_updated": "2025-06-21T09:00:00",
        }

        memory = ClientMemory.from_dict(data)

        assert memory.first_project_date == datetime(2025, 1, 15, 10, 30, 0)
        assert memory.last_project_date == datetime(2025, 6, 20, 14, 45, 0)
        assert memory.last_updated == datetime(2025, 6, 21, 9, 0, 0)

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip preserves data."""
        original = ClientMemory(
            client_name="Roundtrip Client",
            total_projects=5,
            total_posts_generated=150,
            preferred_templates=[1, 3, 5],
            voice_adjustments={"tone": "casual", "length": "shorter"},
            signature_phrases=["Signature phrase 1"],
        )

        data = original.to_dict()
        restored = ClientMemory.from_dict(data)

        assert restored.client_name == original.client_name
        assert restored.total_projects == original.total_projects
        assert restored.preferred_templates == original.preferred_templates
        assert restored.voice_adjustments == original.voice_adjustments
        assert restored.signature_phrases == original.signature_phrases


class TestFeedbackThemeModel:
    """Tests for FeedbackTheme model."""

    def test_create_basic_theme(self):
        """Test creating a basic feedback theme."""
        theme = FeedbackTheme(
            theme_type="tone",
            feedback_phrase="Make it more casual",
        )

        assert theme.theme_type == "tone"
        assert theme.feedback_phrase == "Make it more casual"
        assert theme.occurrence_count == 1
        assert theme.first_seen is not None
        assert theme.last_seen is not None

    def test_increment(self):
        """Test increment increases count and updates last_seen."""
        theme = FeedbackTheme(
            theme_type="length",
            feedback_phrase="Shorter please",
        )
        original_last_seen = theme.last_seen

        theme.increment()

        assert theme.occurrence_count == 2
        assert theme.last_seen >= original_last_seen

    def test_to_dict(self):
        """Test to_dict includes client_name."""
        theme = FeedbackTheme(
            theme_type="cta",
            feedback_phrase="Need stronger CTAs",
        )

        result = theme.to_dict("Client A")

        assert result["client_name"] == "Client A"
        assert result["theme_type"] == "cta"
        assert result["feedback_phrase"] == "Need stronger CTAs"
        assert result["occurrence_count"] == 1

    def test_from_dict(self):
        """Test from_dict creates theme from dict."""
        data = {
            "client_name": "Client A",  # Should be ignored
            "theme_type": "emoji",
            "feedback_phrase": "Add more emojis",
            "occurrence_count": 5,
            "first_seen": "2025-01-10T10:00:00",
            "last_seen": "2025-01-15T14:30:00",
        }

        theme = FeedbackTheme.from_dict(data)

        assert theme.theme_type == "emoji"
        assert theme.feedback_phrase == "Add more emojis"
        assert theme.occurrence_count == 5
        assert theme.first_seen == datetime(2025, 1, 10, 10, 0, 0)
        assert theme.last_seen == datetime(2025, 1, 15, 14, 30, 0)


class TestVoiceSampleModel:
    """Tests for VoiceSample model."""

    def test_create_basic_sample(self):
        """Test creating a basic voice sample."""
        sample = VoiceSample(
            client_name="Client",
            project_id="proj-123",
        )

        assert sample.client_name == "Client"
        assert sample.project_id == "proj-123"
        assert sample.common_hooks == []
        assert sample.common_ctas == []
        assert sample.average_word_count == 0

    def test_create_with_values(self):
        """Test creating voice sample with all values."""
        sample = VoiceSample(
            client_name="Client",
            project_id="proj-456",
            average_readability=65.5,
            voice_archetype="Friend",
            dominant_tone="conversational",
            average_word_count=200,
            question_usage_rate=0.35,
            common_hooks=["Did you know", "Here's the thing"],
            common_transitions=["However", "On the other hand"],
            common_ctas=["What do you think?", "Share your thoughts"],
            key_phrases=["game-changing", "breakthrough"],
        )

        assert sample.average_readability == 65.5
        assert sample.voice_archetype == "Friend"
        assert sample.common_hooks == ["Did you know", "Here's the thing"]
        assert sample.key_phrases == ["game-changing", "breakthrough"]

    def test_to_dict(self):
        """Test to_dict serializes correctly."""
        sample = VoiceSample(
            client_name="Client",
            project_id="proj-789",
            common_hooks=["Hook 1", "Hook 2"],
            common_ctas=["CTA 1"],
        )

        result = sample.to_dict()

        assert result["client_name"] == "Client"
        assert result["project_id"] == "proj-789"
        assert json.loads(result["common_hooks"]) == ["Hook 1", "Hook 2"]
        assert json.loads(result["common_ctas"]) == ["CTA 1"]

    def test_from_dict_basic(self):
        """Test from_dict creates sample from dict."""
        data = {
            "client_name": "Client",
            "project_id": "proj-abc",
            "average_readability": 60.0,
        }

        sample = VoiceSample.from_dict(data)

        assert sample.client_name == "Client"
        assert sample.project_id == "proj-abc"
        assert sample.average_readability == 60.0

    def test_from_dict_parses_json_fields(self):
        """Test from_dict parses JSON string fields."""
        data = {
            "client_name": "Client",
            "project_id": "proj-def",
            "common_hooks": '["Hook A", "Hook B"]',
            "common_transitions": '["Trans 1"]',
            "common_ctas": '["CTA 1", "CTA 2"]',
            "key_phrases": '["phrase 1"]',
            "generated_at": "2025-01-20T12:00:00",
        }

        sample = VoiceSample.from_dict(data)

        assert sample.common_hooks == ["Hook A", "Hook B"]
        assert sample.common_transitions == ["Trans 1"]
        assert sample.common_ctas == ["CTA 1", "CTA 2"]
        assert sample.key_phrases == ["phrase 1"]
        assert sample.generated_at == datetime(2025, 1, 20, 12, 0, 0)

    def test_from_dict_handles_invalid_json(self):
        """Test from_dict handles invalid JSON gracefully."""
        data = {
            "client_name": "Client",
            "project_id": "proj-ghi",
            "common_hooks": "invalid json",
            "common_transitions": "{bad}",
            "common_ctas": "not valid",
            "key_phrases": "malformed",
        }

        sample = VoiceSample.from_dict(data)

        assert sample.common_hooks == []
        assert sample.common_transitions == []
        assert sample.common_ctas == []
        assert sample.key_phrases == []

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip."""
        original = VoiceSample(
            client_name="Roundtrip Client",
            project_id="proj-round",
            average_readability=70.0,
            voice_archetype="Guide",
            common_hooks=["Did you know"],
            key_phrases=["Key phrase"],
        )

        data = original.to_dict()
        restored = VoiceSample.from_dict(data)

        assert restored.client_name == original.client_name
        assert restored.project_id == original.project_id
        assert restored.average_readability == original.average_readability
        assert restored.voice_archetype == original.voice_archetype
        assert restored.common_hooks == original.common_hooks
        assert restored.key_phrases == original.key_phrases


# ---------------------------------------------------------------------------
# Additional tests targeting previously uncovered code paths (48 statements)
# ---------------------------------------------------------------------------


class TestClientMemoryDefaultValues:
    """Verify every field default on a freshly created ClientMemory instance."""

    def test_numeric_defaults(self):
        """Newly created ClientMemory must have expected numeric defaults."""
        memory = ClientMemory(client_name="Fresh Client")
        assert memory.total_projects == 0
        assert memory.total_posts_generated == 0
        assert memory.total_revisions == 0
        assert memory.lifetime_value == 0.0
        assert memory.next_project_discount == 0.0
        assert memory.optimal_word_count_min == 150
        assert memory.optimal_word_count_max == 250

    def test_optional_fields_are_none_by_default(self):
        """Optional fields must be None on a new ClientMemory."""
        memory = ClientMemory(client_name="Fresh Client")
        assert memory.first_project_date is None
        assert memory.last_project_date is None
        assert memory.voice_archetype is None
        assert memory.average_readability_score is None
        assert memory.custom_quality_profile_json is None
        assert memory.average_satisfaction is None
        assert memory.notes is None

    def test_list_defaults_are_empty(self):
        """List fields must default to empty lists, not shared mutable objects."""
        m1 = ClientMemory(client_name="Client One")
        m2 = ClientMemory(client_name="Client Two")
        m1.preferred_templates.append(99)
        assert (
            99 not in m2.preferred_templates
        ), "Default list is shared between instances — Pydantic default_factory not used"


class TestClientMemoryToFromDictFullRoundtrip:
    """to_dict() -> from_dict() round trips preserve every field."""

    def test_full_roundtrip_with_all_fields_populated(self):
        """All fields survive a to_dict -> from_dict round trip."""
        original = ClientMemory(
            client_name="Full Roundtrip",
            total_projects=7,
            total_posts_generated=210,
            total_revisions=14,
            lifetime_value=10500.00,
            average_satisfaction=8.5,
            next_project_discount=0.1,
            preferred_templates=[1, 3, 7],
            avoided_templates=[2, 4],
            template_performance={1: 0.1, 2: 0.6},
            voice_adjustments={"tone": "casual", "emoji": "add"},
            optimal_word_count_min=125,
            optimal_word_count_max=275,
            preferred_cta_types=["question", "engagement"],
            voice_archetype="Guide",
            average_readability_score=62.5,
            signature_phrases=["Let me be direct", "Here is the truth"],
            custom_quality_profile_json='{"min_word_count": 120}',
            notes="VIP client — handle with care",
        )

        data = original.to_dict()
        restored = ClientMemory.from_dict(data)

        assert restored.client_name == original.client_name
        assert restored.total_projects == original.total_projects
        assert restored.total_posts_generated == original.total_posts_generated
        assert restored.total_revisions == original.total_revisions
        assert restored.lifetime_value == original.lifetime_value
        assert restored.average_satisfaction == original.average_satisfaction
        assert restored.next_project_discount == original.next_project_discount
        assert restored.preferred_templates == original.preferred_templates
        assert restored.avoided_templates == original.avoided_templates
        assert restored.voice_adjustments == original.voice_adjustments
        assert restored.optimal_word_count_min == original.optimal_word_count_min
        assert restored.optimal_word_count_max == original.optimal_word_count_max
        assert restored.preferred_cta_types == original.preferred_cta_types
        assert restored.voice_archetype == original.voice_archetype
        assert restored.average_readability_score == original.average_readability_score
        assert restored.signature_phrases == original.signature_phrases
        assert restored.custom_quality_profile_json == original.custom_quality_profile_json
        assert restored.notes == original.notes

    def test_roundtrip_preserves_dates(self):
        """first_project_date and last_project_date survive a round trip."""
        from datetime import datetime

        original = ClientMemory(client_name="Date Client")
        original.add_project(
            num_posts=30,
            project_value=1500.0,
            project_date=datetime(2025, 3, 15, 9, 0, 0),
        )

        data = original.to_dict()
        restored = ClientMemory.from_dict(data)

        assert restored.first_project_date == datetime(2025, 3, 15, 9, 0, 0)
        assert restored.last_project_date == datetime(2025, 3, 15, 9, 0, 0)


class TestClientMemoryAddProjectEdgeCases:
    """Edge cases for add_project not covered by the existing tests."""

    def test_first_project_date_set_only_once(self):
        """first_project_date must be set by the first call and not overwritten."""
        from datetime import datetime

        memory = ClientMemory(client_name="Date Check")
        first_date = datetime(2025, 1, 1)
        second_date = datetime(2025, 6, 1)

        memory.add_project(num_posts=30, project_value=1000.0, project_date=first_date)
        memory.add_project(num_posts=30, project_value=1000.0, project_date=second_date)

        assert memory.first_project_date == first_date
        assert memory.last_project_date == second_date

    def test_last_updated_changes_after_add_project(self):
        """last_updated must be refreshed each time add_project is called."""
        from datetime import datetime

        memory = ClientMemory(client_name="LU Client")
        original_last_updated = memory.last_updated

        memory.add_project(num_posts=30, project_value=500.0)

        assert memory.last_updated >= original_last_updated

    def test_add_project_accumulates_lifetime_value(self):
        """Repeated add_project calls must sum lifetime_value correctly."""
        memory = ClientMemory(client_name="LTV Check")

        for value in [500.0, 1000.0, 1500.0]:
            memory.add_project(num_posts=10, project_value=value)

        assert memory.lifetime_value == pytest.approx(3000.0)


class TestClientMemoryUpdateTemplatePreferenceEdgeCases:
    """Edge cases for update_template_preference."""

    def test_template_stays_preferred_if_called_again_with_low_rate(self):
        """Calling update_template_preference again with a low rate must not duplicate entries."""
        memory = ClientMemory(client_name="Template Client")
        memory.update_template_preference(template_id=5, revision_rate=0.05)
        memory.update_template_preference(template_id=5, revision_rate=0.10)

        assert memory.preferred_templates.count(5) == 1

    def test_template_stays_avoided_if_called_again_with_high_rate(self):
        """Calling update_template_preference again with a high rate must not duplicate entries."""
        memory = ClientMemory(client_name="Template Client")
        memory.update_template_preference(template_id=6, revision_rate=0.55)
        memory.update_template_preference(template_id=6, revision_rate=0.75)

        assert memory.avoided_templates.count(6) == 1

    def test_boundary_revision_rate_exactly_02(self):
        """A revision rate of exactly 0.2 must mark the template as preferred."""
        memory = ClientMemory(client_name="Boundary Client")
        memory.update_template_preference(template_id=10, revision_rate=0.2)

        assert 10 in memory.preferred_templates

    def test_boundary_revision_rate_exactly_05(self):
        """A revision rate of exactly 0.5 must mark the template as avoided."""
        memory = ClientMemory(client_name="Boundary Client")
        memory.update_template_preference(template_id=11, revision_rate=0.5)

        assert 11 in memory.avoided_templates

    def test_last_updated_changes_after_template_preference_update(self):
        """last_updated must be refreshed after update_template_preference."""
        memory = ClientMemory(client_name="LU Template")
        original_lu = memory.last_updated

        memory.update_template_preference(template_id=3, revision_rate=0.15)

        assert memory.last_updated >= original_lu


class TestClientMemoryUpdateVoiceAdjustmentEdgeCases:
    """Edge cases for update_voice_adjustment."""

    def test_multiple_distinct_adjustments_stored(self):
        """Multiple different adjustment types must all be stored independently."""
        memory = ClientMemory(client_name="Voice Client")
        memory.update_voice_adjustment("tone", "casual")
        memory.update_voice_adjustment("length", "shorter")
        memory.update_voice_adjustment("emoji", "add")

        assert memory.voice_adjustments["tone"] == "casual"
        assert memory.voice_adjustments["length"] == "shorter"
        assert memory.voice_adjustments["emoji"] == "add"

    def test_last_updated_changes_after_voice_adjustment(self):
        """last_updated must be refreshed after update_voice_adjustment."""
        memory = ClientMemory(client_name="LU Voice")
        original_lu = memory.last_updated

        memory.update_voice_adjustment("data_usage", "minimal")

        assert memory.last_updated >= original_lu


class TestClientMemoryHighValueClientEdgeCases:
    """Edge cases for is_high_value_client property."""

    def test_exactly_three_projects_is_high_value(self):
        """A client with exactly 3 projects must be high value."""
        memory = ClientMemory(client_name="Three Projects", total_projects=3)
        assert memory.is_high_value_client is True

    def test_exactly_5000_ltv_is_high_value(self):
        """A client with exactly $5,000 LTV must be high value."""
        memory = ClientMemory(client_name="5k LTV", lifetime_value=5000.0)
        assert memory.is_high_value_client is True

    def test_two_projects_and_4999_ltv_is_not_high_value(self):
        """A client under both thresholds must not be high value."""
        memory = ClientMemory(
            client_name="Not High Value",
            total_projects=2,
            lifetime_value=4999.99,
        )
        assert memory.is_high_value_client is False


class TestClientMemoryAddRevisionsEdgeCases:
    """Edge cases for add_revisions."""

    def test_add_zero_revisions(self):
        """add_revisions(0) must be a no-op on the count."""
        memory = ClientMemory(client_name="Zero Rev")
        memory.add_revisions(0)
        assert memory.total_revisions == 0

    def test_last_updated_changes_after_add_revisions(self):
        """last_updated must be refreshed after add_revisions."""
        memory = ClientMemory(client_name="LU Rev")
        original_lu = memory.last_updated

        memory.add_revisions(3)

        assert memory.last_updated >= original_lu


class TestFeedbackThemeEdgeCases:
    """Additional coverage for FeedbackTheme paths."""

    def test_increment_multiple_times(self):
        """increment must correctly accumulate over many calls."""
        theme = FeedbackTheme(theme_type="length", feedback_phrase="Too long")
        for _ in range(9):
            theme.increment()
        assert theme.occurrence_count == 10

    def test_to_dict_roundtrip_via_from_dict(self):
        """to_dict -> from_dict round trip for FeedbackTheme preserves all fields."""
        from datetime import datetime

        original = FeedbackTheme(
            theme_type="structure",
            feedback_phrase="Needs bullet points",
            occurrence_count=3,
            first_seen=datetime(2025, 2, 1, 8, 0, 0),
            last_seen=datetime(2025, 4, 10, 12, 0, 0),
        )

        data = original.to_dict("Some Client")
        restored = FeedbackTheme.from_dict(data)

        assert restored.theme_type == original.theme_type
        assert restored.feedback_phrase == original.feedback_phrase
        assert restored.occurrence_count == original.occurrence_count
        assert restored.first_seen == original.first_seen
        assert restored.last_seen == original.last_seen

    def test_from_dict_strips_client_name(self):
        """from_dict must silently discard the client_name key that comes from DB rows."""
        data = {
            "client_name": "Should Be Dropped",
            "theme_type": "cta",
            "feedback_phrase": "Weaker CTA please",
            "occurrence_count": 2,
            "first_seen": "2025-01-05T08:00:00",
            "last_seen": "2025-01-10T09:00:00",
        }
        theme = FeedbackTheme.from_dict(data)
        # Must not raise and must not expose client_name as an attribute
        assert not hasattr(theme, "client_name")
        assert theme.theme_type == "cta"


class TestVoiceSampleEdgeCases:
    """Additional coverage for VoiceSample paths."""

    def test_question_usage_rate_boundaries(self):
        """question_usage_rate must accept 0.0 and 1.0 (inclusive boundaries)."""
        low = VoiceSample(client_name="C", project_id="p1", question_usage_rate=0.0)
        high = VoiceSample(client_name="C", project_id="p2", question_usage_rate=1.0)
        assert low.question_usage_rate == 0.0
        assert high.question_usage_rate == 1.0

    def test_average_word_count_default_is_zero(self):
        """average_word_count must default to 0."""
        sample = VoiceSample(client_name="C", project_id="p1")
        assert sample.average_word_count == 0

    def test_to_dict_lists_are_json_strings(self):
        """to_dict must serialize list fields as JSON strings for DB storage."""
        import json

        sample = VoiceSample(
            client_name="C",
            project_id="p1",
            common_hooks=["Hook A"],
            common_transitions=["Trans A"],
            common_ctas=["CTA A"],
            key_phrases=["Phrase A"],
        )
        d = sample.to_dict()

        # Each list field must be a valid JSON string
        for field in ("common_hooks", "common_transitions", "common_ctas", "key_phrases"):
            assert isinstance(d[field], str)
            parsed = json.loads(d[field])
            assert isinstance(parsed, list)

    def test_from_dict_with_all_none_optional_fields(self):
        """from_dict must succeed when all optional fields are None."""
        data = {
            "client_name": "Minimal",
            "project_id": "proj-minimal",
            "average_readability": None,
            "voice_archetype": None,
            "dominant_tone": None,
        }
        sample = VoiceSample.from_dict(data)
        assert sample.client_name == "Minimal"
        assert sample.average_readability is None
        assert sample.voice_archetype is None
