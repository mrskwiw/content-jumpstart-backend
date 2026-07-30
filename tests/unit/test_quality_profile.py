"""Unit tests for quality_profile module.

Tests cover:
- QualityProfile model creation and validation
- Validators for readability and word count
- to_dict() method
- from_file() and save_to_file() methods
- DEFAULT_PROFILES dictionary
- get_default_profile() function
"""

import json
import pytest

from src.models.quality_profile import (
    QualityProfile,
    DEFAULT_PROFILES,
    get_default_profile,
)


class TestQualityProfileModel:
    """Tests for QualityProfile model creation."""

    def test_create_basic_profile(self):
        """Test creating a basic quality profile."""
        profile = QualityProfile(
            profile_name="test_profile",
            description="Test description",
        )

        assert profile.profile_name == "test_profile"
        assert profile.description == "Test description"
        # Default values
        assert profile.min_readability == 50.0
        assert profile.max_readability == 65.0
        assert profile.min_words == 150
        assert profile.max_words == 300
        assert profile.min_engagement_score == 2
        assert profile.require_cta is True
        assert profile.max_attempts == 2
        assert profile.enabled is True

    def test_create_custom_profile(self):
        """Test creating a profile with custom values."""
        profile = QualityProfile(
            profile_name="custom",
            description="Custom profile",
            min_readability=40.0,
            max_readability=80.0,
            min_words=100,
            max_words=500,
            min_engagement_score=1,
            require_cta=False,
            max_attempts=3,
            enabled=False,
        )

        assert profile.min_readability == 40.0
        assert profile.max_readability == 80.0
        assert profile.min_words == 100
        assert profile.max_words == 500
        assert profile.min_engagement_score == 1
        assert profile.require_cta is False
        assert profile.max_attempts == 3
        assert profile.enabled is False

    def test_field_constraints(self):
        """Test field constraints are enforced."""
        # min_readability must be 0-100
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="test",
                description="test",
                min_readability=-1.0,
            )

        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="test",
                description="test",
                min_readability=101.0,
            )

        # min_words must be 50-2000
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="test",
                description="test",
                min_words=10,
            )

        # max_attempts must be 1-5
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="test",
                description="test",
                max_attempts=0,
            )

        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="test",
                description="test",
                max_attempts=10,
            )


class TestQualityProfileValidators:
    """Tests for QualityProfile validators."""

    def test_max_readability_must_exceed_min(self):
        """Test that max_readability must be greater than min_readability."""
        with pytest.raises(ValueError) as exc_info:
            QualityProfile(
                profile_name="test",
                description="test",
                min_readability=70.0,
                max_readability=50.0,  # Less than min
            )
        assert "must be greater than min_readability" in str(exc_info.value)

    def test_max_readability_equal_to_min_fails(self):
        """Test that max_readability equal to min_readability fails."""
        with pytest.raises(ValueError) as exc_info:
            QualityProfile(
                profile_name="test",
                description="test",
                min_readability=60.0,
                max_readability=60.0,  # Equal to min
            )
        assert "must be greater than min_readability" in str(exc_info.value)

    def test_max_words_must_exceed_min(self):
        """Test that max_words must be greater than min_words."""
        with pytest.raises(ValueError) as exc_info:
            QualityProfile(
                profile_name="test",
                description="test",
                min_words=300,
                max_words=150,  # Less than min
            )
        assert "must be greater than min_words" in str(exc_info.value)

    def test_max_words_equal_to_min_fails(self):
        """Test that max_words equal to min_words fails."""
        with pytest.raises(ValueError) as exc_info:
            QualityProfile(
                profile_name="test",
                description="test",
                min_words=200,
                max_words=200,  # Equal to min
            )
        assert "must be greater than min_words" in str(exc_info.value)


class TestQualityProfileToDict:
    """Tests for to_dict() method."""

    def test_to_dict_returns_all_fields(self):
        """Test that to_dict returns all fields."""
        profile = QualityProfile(
            profile_name="test",
            description="test desc",
            min_readability=45.0,
            max_readability=70.0,
        )

        result = profile.to_dict()

        assert isinstance(result, dict)
        assert result["profile_name"] == "test"
        assert result["description"] == "test desc"
        assert result["min_readability"] == 45.0
        assert result["max_readability"] == 70.0
        assert "min_words" in result
        assert "max_words" in result
        assert "min_engagement_score" in result
        assert "require_cta" in result
        assert "max_attempts" in result
        assert "enabled" in result


class TestQualityProfileFileOperations:
    """Tests for from_file() and save_to_file() methods."""

    def test_save_and_load_profile(self, tmp_path):
        """Test saving and loading a profile from file."""
        profile = QualityProfile(
            profile_name="file_test",
            description="Testing file operations",
            min_readability=55.0,
            max_readability=75.0,
            min_words=200,
            max_words=400,
        )

        file_path = tmp_path / "test_profile.json"
        profile.save_to_file(str(file_path))

        assert file_path.exists()

        loaded = QualityProfile.from_file(str(file_path))

        assert loaded.profile_name == profile.profile_name
        assert loaded.description == profile.description
        assert loaded.min_readability == profile.min_readability
        assert loaded.max_readability == profile.max_readability
        assert loaded.min_words == profile.min_words
        assert loaded.max_words == profile.max_words

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that save_to_file creates parent directories."""
        profile = QualityProfile(
            profile_name="nested",
            description="test",
        )

        nested_path = tmp_path / "nested" / "dir" / "profile.json"
        profile.save_to_file(str(nested_path))

        assert nested_path.exists()

    def test_from_file_not_found(self):
        """Test from_file raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            QualityProfile.from_file("/nonexistent/path/profile.json")
        assert "Quality profile not found" in str(exc_info.value)

    def test_from_file_invalid_json(self, tmp_path):
        """Test from_file raises ValueError for invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{ not valid json }")

        with pytest.raises(ValueError) as exc_info:
            QualityProfile.from_file(str(file_path))
        assert "Invalid JSON" in str(exc_info.value)

    def test_from_file_missing_required_field(self, tmp_path):
        """Test from_file raises ValueError for missing required fields."""
        file_path = tmp_path / "incomplete.json"
        file_path.write_text('{"profile_name": "test"}')  # Missing description

        with pytest.raises(ValueError) as exc_info:
            QualityProfile.from_file(str(file_path))
        assert "Failed to load profile" in str(exc_info.value)

    def test_from_file_invalid_values(self, tmp_path):
        """Test from_file raises ValueError for invalid field values."""
        file_path = tmp_path / "invalid_values.json"
        # Invalid: min_readability > max_readability
        file_path.write_text(
            json.dumps(
                {
                    "profile_name": "test",
                    "description": "test",
                    "min_readability": 80.0,
                    "max_readability": 50.0,
                }
            )
        )

        with pytest.raises(ValueError) as exc_info:
            QualityProfile.from_file(str(file_path))
        assert "Failed to load profile" in str(exc_info.value)


class TestDefaultProfiles:
    """Tests for DEFAULT_PROFILES dictionary."""

    def test_expected_profiles_exist(self):
        """Test that expected default profiles exist."""
        expected = [
            "professional_linkedin",
            "casual_linkedin",
            "executive_linkedin",
            "twitter",
            "blog",
            "permissive",
        ]
        for profile_name in expected:
            assert profile_name in DEFAULT_PROFILES

    def test_profile_count(self):
        """Test the number of default profiles."""
        assert len(DEFAULT_PROFILES) == 6

    def test_all_profiles_are_valid(self):
        """Test that all default profiles are valid QualityProfile instances."""
        for name, profile in DEFAULT_PROFILES.items():
            assert isinstance(profile, QualityProfile)
            assert profile.profile_name == name

    def test_professional_linkedin_profile(self):
        """Test professional_linkedin profile settings."""
        profile = DEFAULT_PROFILES["professional_linkedin"]
        assert profile.min_readability == 50.0
        assert profile.max_readability == 65.0
        assert profile.min_words == 200
        assert profile.max_words == 300
        assert profile.require_cta is True
        assert profile.enabled is True

    def test_twitter_profile(self):
        """Test twitter profile has concise settings."""
        profile = DEFAULT_PROFILES["twitter"]
        assert profile.min_words == 50
        assert profile.max_words == 100
        assert profile.min_readability == 65.0  # Higher readability for Twitter

    def test_blog_profile(self):
        """Test blog profile has correct content settings."""
        profile = DEFAULT_PROFILES["blog"]
        assert profile.min_words == 800
        assert profile.max_words == 2500

    def test_permissive_profile(self):
        """Test permissive profile has relaxed settings."""
        profile = DEFAULT_PROFILES["permissive"]
        assert profile.min_engagement_score == 0
        assert profile.require_cta is False
        assert profile.max_attempts == 1
        assert profile.enabled is False  # Disabled by default


class TestGetDefaultProfile:
    """Tests for get_default_profile() function."""

    def test_get_professional_linkedin(self):
        """Test getting professional_linkedin profile."""
        profile = get_default_profile("professional_linkedin")
        assert profile.profile_name == "professional_linkedin"

    def test_get_default_without_arg(self):
        """Test getting default profile without argument."""
        profile = get_default_profile()
        assert profile.profile_name == "professional_linkedin"

    def test_get_all_valid_profiles(self):
        """Test getting all valid profile names."""
        for name in DEFAULT_PROFILES.keys():
            profile = get_default_profile(name)
            assert profile.profile_name == name

    def test_invalid_profile_raises_error(self):
        """Test that invalid profile name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_default_profile("nonexistent_profile")
        assert "Unknown profile" in str(exc_info.value)
        assert "nonexistent_profile" in str(exc_info.value)
        # Should list available profiles
        assert "professional_linkedin" in str(exc_info.value)


class TestQualityProfileConfig:
    """Tests for model config."""

    def test_json_schema_has_example(self):
        """Test that JSON schema includes an example."""
        schema = QualityProfile.model_json_schema()
        assert "example" in schema or "examples" in schema

    def test_model_serialization(self):
        """Test model serialization to JSON."""
        profile = QualityProfile(
            profile_name="serialize_test",
            description="test serialization",
        )

        json_str = profile.model_dump_json()
        data = json.loads(json_str)

        assert data["profile_name"] == "serialize_test"
        assert data["description"] == "test serialization"


# ---------------------------------------------------------------------------
# Additional tests for uncovered branches and boundary values
# ---------------------------------------------------------------------------


class TestQualityProfileBoundaryValues:
    """Boundary-value tests for numeric field constraints."""

    # --- min_readability boundaries ---

    def test_min_readability_exactly_zero_is_valid(self):
        """Test that min_readability=0.0 (lower bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_readability=0.0,
            max_readability=1.0,
        )
        assert profile.min_readability == 0.0

    def test_min_readability_exactly_100_is_invalid_when_no_headroom(self):
        """Test that min_readability=100.0 forces max_readability to be >100, which fails."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_readability=100.0,
                max_readability=100.0,
            )

    def test_min_readability_negative_is_invalid(self):
        """Test that min_readability < 0 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_readability=-0.01,
            )

    def test_max_readability_exactly_100_is_valid(self):
        """Test that max_readability=100.0 (upper bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_readability=50.0,
            max_readability=100.0,
        )
        assert profile.max_readability == 100.0

    def test_max_readability_above_100_is_invalid(self):
        """Test that max_readability > 100 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_readability=50.0,
                max_readability=100.1,
            )

    # --- min_words boundaries ---

    def test_min_words_exactly_50_is_valid(self):
        """Test that min_words=50 (lower bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_words=50,
            max_words=100,
        )
        assert profile.min_words == 50

    def test_min_words_below_50_is_invalid(self):
        """Test that min_words < 50 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_words=49,
                max_words=200,
            )

    def test_min_words_exactly_2000_max_must_exceed(self):
        """Test that min_words=2000 requires max_words > 2000."""
        with pytest.raises(ValueError):
            # max_words has an upper bound of 3000, so 2001 should work
            # but max_words=2000 equal to min is invalid
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_words=2000,
                max_words=2000,
            )

    def test_max_words_exactly_3000_is_valid(self):
        """Test that max_words=3000 (upper bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_words=100,
            max_words=3000,
        )
        assert profile.max_words == 3000

    def test_max_words_above_3000_is_invalid(self):
        """Test that max_words > 3000 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_words=100,
                max_words=3001,
            )

    def test_max_words_below_100_is_invalid(self):
        """Test that max_words < 100 is rejected (field ge=100)."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_words=50,
                max_words=99,
            )

    # --- min_engagement_score boundaries ---

    def test_min_engagement_score_exactly_0_is_valid(self):
        """Test that min_engagement_score=0 (lower bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_engagement_score=0,
        )
        assert profile.min_engagement_score == 0

    def test_min_engagement_score_exactly_3_is_valid(self):
        """Test that min_engagement_score=3 (upper bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            min_engagement_score=3,
        )
        assert profile.min_engagement_score == 3

    def test_min_engagement_score_above_3_is_invalid(self):
        """Test that min_engagement_score > 3 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_engagement_score=4,
            )

    def test_min_engagement_score_negative_is_invalid(self):
        """Test that min_engagement_score < 0 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                min_engagement_score=-1,
            )

    # --- max_attempts boundaries ---

    def test_max_attempts_exactly_1_is_valid(self):
        """Test that max_attempts=1 (lower bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            max_attempts=1,
        )
        assert profile.max_attempts == 1

    def test_max_attempts_exactly_5_is_valid(self):
        """Test that max_attempts=5 (upper bound) is accepted."""
        profile = QualityProfile(
            profile_name="bound_test",
            description="boundary",
            max_attempts=5,
        )
        assert profile.max_attempts == 5

    def test_max_attempts_above_5_is_invalid(self):
        """Test that max_attempts > 5 is rejected."""
        with pytest.raises(ValueError):
            QualityProfile(
                profile_name="bound_test",
                description="boundary",
                max_attempts=6,
            )


class TestQualityProfileModelValidate:
    """Tests for model_validate (from_dict) patterns."""

    def test_model_validate_from_dict(self):
        """Test creating a profile via model_validate from a plain dict."""
        data = {
            "profile_name": "validated",
            "description": "created via model_validate",
            "min_readability": 45.0,
            "max_readability": 70.0,
            "min_words": 100,
            "max_words": 400,
            "min_engagement_score": 1,
            "require_cta": False,
            "max_attempts": 3,
            "enabled": True,
        }
        profile = QualityProfile.model_validate(data)
        assert profile.profile_name == "validated"
        assert profile.min_readability == 45.0
        assert profile.max_readability == 70.0
        assert profile.min_words == 100
        assert profile.max_words == 400
        assert profile.min_engagement_score == 1
        assert profile.require_cta is False
        assert profile.max_attempts == 3

    def test_model_validate_uses_defaults(self):
        """Test that model_validate fills in default values for optional fields."""
        data = {"profile_name": "minimal", "description": "just the required fields"}
        profile = QualityProfile.model_validate(data)
        assert profile.min_readability == 50.0
        assert profile.max_readability == 65.0
        assert profile.min_words == 150
        assert profile.max_words == 300
        assert profile.min_engagement_score == 2
        assert profile.require_cta is True
        assert profile.max_attempts == 2
        assert profile.enabled is True

    def test_model_validate_rejects_invalid_data(self):
        """Test that model_validate raises on constraint violations."""
        with pytest.raises(ValueError):
            QualityProfile.model_validate(
                {
                    "profile_name": "bad",
                    "description": "bad data",
                    "min_readability": 80.0,
                    "max_readability": 40.0,  # less than min
                }
            )

    def test_model_validate_requires_profile_name(self):
        """Test that model_validate raises when profile_name is missing."""
        with pytest.raises(ValueError):
            QualityProfile.model_validate({"description": "no name"})

    def test_model_validate_requires_description(self):
        """Test that model_validate raises when description is missing."""
        with pytest.raises(ValueError):
            QualityProfile.model_validate({"profile_name": "no_desc"})


class TestQualityProfileToDictRoundTrip:
    """Tests for to_dict() round-trip behaviour."""

    def test_to_dict_round_trip_via_model_validate(self):
        """Test that to_dict output can be fed back into model_validate."""
        original = QualityProfile(
            profile_name="round_trip",
            description="round trip test",
            min_readability=40.0,
            max_readability=80.0,
            min_words=100,
            max_words=600,
            min_engagement_score=1,
            require_cta=False,
            max_attempts=4,
            enabled=False,
        )
        data = original.to_dict()
        restored = QualityProfile.model_validate(data)

        assert restored.profile_name == original.profile_name
        assert restored.description == original.description
        assert restored.min_readability == original.min_readability
        assert restored.max_readability == original.max_readability
        assert restored.min_words == original.min_words
        assert restored.max_words == original.max_words
        assert restored.min_engagement_score == original.min_engagement_score
        assert restored.require_cta == original.require_cta
        assert restored.max_attempts == original.max_attempts
        assert restored.enabled == original.enabled

    def test_to_dict_contains_all_expected_fields(self):
        """Test that to_dict always returns exactly the expected keys."""
        profile = QualityProfile(profile_name="p", description="d")
        result = profile.to_dict()
        expected_keys = {
            "profile_name",
            "description",
            "min_readability",
            "max_readability",
            "min_words",
            "max_words",
            "min_engagement_score",
            "require_cta",
            "check_genericity",
            "max_genericity",
            "max_attempts",
            "enabled",
        }
        assert set(result.keys()) == expected_keys


class TestQualityProfileSaveToFileContent:
    """Tests that save_to_file writes the correct JSON content."""

    def test_saved_json_content_matches_profile(self, tmp_path):
        """Test that the JSON file written by save_to_file matches the profile data."""
        profile = QualityProfile(
            profile_name="content_check",
            description="checking file content",
            min_readability=42.0,
            max_readability=78.0,
            min_words=120,
            max_words=450,
            min_engagement_score=1,
            require_cta=False,
            max_attempts=3,
            enabled=False,
        )
        file_path = tmp_path / "content_check.json"
        profile.save_to_file(str(file_path))

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["profile_name"] == "content_check"
        assert data["description"] == "checking file content"
        assert data["min_readability"] == 42.0
        assert data["max_readability"] == 78.0
        assert data["min_words"] == 120
        assert data["max_words"] == 450
        assert data["min_engagement_score"] == 1
        assert data["require_cta"] is False
        assert data["max_attempts"] == 3
        assert data["enabled"] is False

    def test_saved_file_is_valid_json(self, tmp_path):
        """Test that save_to_file always writes valid JSON."""
        profile = QualityProfile(profile_name="valid_json", description="must be valid json")
        file_path = tmp_path / "valid.json"
        profile.save_to_file(str(file_path))

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        parsed = json.loads(content)
        assert isinstance(parsed, dict)


class TestGetDefaultProfileAdditional:
    """Additional tests for get_default_profile() — error message and each named profile."""

    def test_error_message_lists_available_profiles(self):
        """Test that ValueError for unknown profile name lists all available profiles."""
        with pytest.raises(ValueError) as exc_info:
            get_default_profile("does_not_exist")
        error_msg = str(exc_info.value)
        for name in [
            "professional_linkedin",
            "casual_linkedin",
            "executive_linkedin",
            "twitter",
            "blog",
            "permissive",
        ]:
            assert name in error_msg

    def test_casual_linkedin_profile_values(self):
        """Test casual_linkedin profile has correct settings."""
        profile = get_default_profile("casual_linkedin")
        assert profile.profile_name == "casual_linkedin"
        assert profile.min_readability == 60.0
        assert profile.max_readability == 75.0
        assert profile.min_words == 200
        assert profile.max_words == 280
        assert profile.enabled is True

    def test_executive_linkedin_profile_values(self):
        """Test executive_linkedin profile has correct settings."""
        profile = get_default_profile("executive_linkedin")
        assert profile.profile_name == "executive_linkedin"
        assert profile.min_readability == 40.0
        assert profile.max_readability == 60.0
        assert profile.min_engagement_score == 1
        assert profile.require_cta is False

    def test_twitter_profile_values(self):
        """Test twitter profile has correct concise settings."""
        profile = get_default_profile("twitter")
        assert profile.profile_name == "twitter"
        assert profile.max_readability == 85.0
        assert profile.min_words == 50
        assert profile.max_words == 100

    def test_blog_profile_values(self):
        """Test blog profile has correct settings."""
        profile = get_default_profile("blog")
        assert profile.profile_name == "blog"
        assert profile.min_words == 800
        assert profile.max_words == 2500
        assert profile.max_readability == 70.0

    def test_permissive_profile_values(self):
        """Test permissive profile has fully relaxed settings."""
        profile = get_default_profile("permissive")
        assert profile.profile_name == "permissive"
        assert profile.min_readability == 30.0
        assert profile.max_readability == 85.0
        assert profile.min_words == 75
        assert profile.max_words == 500
        assert profile.min_engagement_score == 0
        assert profile.require_cta is False
        assert profile.max_attempts == 1
        assert profile.enabled is False

    def test_returns_same_object_as_default_profiles_dict(self):
        """Test that get_default_profile returns the same instance as DEFAULT_PROFILES."""
        profile = get_default_profile("professional_linkedin")
        assert profile is DEFAULT_PROFILES["professional_linkedin"]


class TestQualityProfileRequiredFields:
    """Tests verifying required fields (profile_name, description) cannot be omitted."""

    def test_profile_name_is_required(self):
        """Test that omitting profile_name raises ValidationError."""
        with pytest.raises((ValueError, TypeError)):
            QualityProfile(description="no name given")

    def test_description_is_required(self):
        """Test that omitting description raises ValidationError."""
        with pytest.raises((ValueError, TypeError)):
            QualityProfile(profile_name="no_desc")

    def test_profile_name_cannot_be_none(self):
        """Test that None profile_name is rejected."""
        with pytest.raises((ValueError, TypeError)):
            QualityProfile(profile_name=None, description="test")

    def test_description_cannot_be_none(self):
        """Test that None description is rejected."""
        with pytest.raises((ValueError, TypeError)):
            QualityProfile(profile_name="test", description=None)
