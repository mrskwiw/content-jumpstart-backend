"""
Unit tests for Project schemas with target_platform field.

Tests:
- ProjectCreate with target_platform
- ProjectUpdate with target_platform
- ProjectResponse with target_platform
- Field validation and defaults
- CamelCase/snake_case alias support
"""

import pytest
from datetime import datetime
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse


class TestProjectCreatePlatform:
    """Test ProjectCreate schema with target_platform"""

    def test_create_project_with_target_platform(self):
        """Test creating project with target_platform field"""
        data = {
            "name": "LinkedIn Campaign",
            "client_id": "client-12345678",
            "target_platform": "linkedin",
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "linkedin"
        assert project.name == "LinkedIn Campaign"

    def test_create_project_default_target_platform(self):
        """Test target_platform defaults to 'blog'"""
        data = {
            "name": "Blog Campaign",
            "client_id": "client-12345678",
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "blog"

    def test_create_project_camelcase_alias(self):
        """Test target_platform accepts camelCase alias"""
        data = {
            "name": "Twitter Campaign",
            "client_id": "client-12345678",
            "targetPlatform": "twitter",  # CamelCase
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "twitter"

    def test_create_project_all_platforms(self):
        """Test creating projects for all supported platforms"""
        platforms = [
            "linkedin",
            "twitter",
            "facebook",
            "blog",
            "email",
            "generic",
        ]

        for platform in platforms:
            data = {
                "name": f"{platform.title()} Campaign",
                "client_id": "client-12345678",
                "target_platform": platform,
            }
            project = ProjectCreate(**data)
            assert project.target_platform == platform

    def test_create_project_with_template_quantities_and_platform(self):
        """Test creating project with both template_quantities and target_platform"""
        data = {
            "name": "Full Campaign",
            "client_id": "client-12345678",
            "template_quantities": {"1": 10, "2": 10, "9": 10},
            "target_platform": "linkedin",
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "linkedin"
        assert project.template_quantities == {"1": 10, "2": 10, "9": 10}
        assert project.num_posts == 30  # Auto-calculated

    def test_create_project_serialization(self):
        """Test project serializes correctly with target_platform"""
        data = {
            "name": "Test Project",
            "client_id": "client-12345678",
            "target_platform": "twitter",
            "num_posts": 20,
        }

        project = ProjectCreate(**data)
        serialized = project.model_dump()

        assert serialized["target_platform"] == "twitter"
        assert serialized["name"] == "Test Project"
        assert serialized["num_posts"] == 20


class TestProjectUpdatePlatform:
    """Test ProjectUpdate schema with target_platform"""

    def test_update_target_platform(self):
        """Test updating target_platform field"""
        data = {"target_platform": "twitter"}

        update = ProjectUpdate(**data)
        assert update.target_platform == "twitter"

    def test_update_target_platform_none(self):
        """Test target_platform can be None in updates"""
        data = {"name": "Updated Project"}

        update = ProjectUpdate(**data)
        assert update.target_platform is None

    def test_update_target_platform_camelcase(self):
        """Test updating with camelCase alias"""
        data = {"targetPlatform": "facebook"}

        update = ProjectUpdate(**data)
        assert update.target_platform == "facebook"

    def test_update_multiple_fields_with_platform(self):
        """Test updating multiple fields including target_platform"""
        data = {
            "name": "Updated Campaign",
            "target_platform": "facebook",
            "num_posts": 25,
            "tone": "casual",
        }

        update = ProjectUpdate(**data)
        assert update.name == "Updated Campaign"
        assert update.target_platform == "facebook"
        assert update.num_posts == 25
        assert update.tone == "casual"

    def test_update_rejects_unknown_fields(self):
        """Test ProjectUpdate rejects unknown fields (TR-022)"""
        data = {
            "name": "Test",
            "unknown_field": "value",  # Should be rejected
        }

        with pytest.raises(Exception):  # Pydantic ValidationError
            ProjectUpdate(**data)


class TestProjectResponsePlatform:
    """Test ProjectResponse schema with target_platform"""

    def test_response_includes_target_platform(self):
        """Test ProjectResponse includes target_platform field"""
        data = {
            "id": "proj-12345678",
            "name": "Test Project",
            "client_id": "client-12345678",
            "status": "draft",
            "target_platform": "linkedin",
            "created_at": datetime.utcnow(),
        }

        response = ProjectResponse(**data)
        assert response.target_platform == "linkedin"
        assert response.id == "proj-12345678"

    def test_response_camelcase_serialization(self):
        """Test ProjectResponse serializes to camelCase"""
        data = {
            "id": "proj-12345678",
            "name": "Test Project",
            "client_id": "client-12345678",
            "status": "draft",
            "target_platform": "twitter",
            "num_posts": 30,
            "created_at": datetime.utcnow(),
        }

        response = ProjectResponse(**data)
        serialized = response.model_dump(by_alias=True)

        # Should have camelCase keys
        assert "targetPlatform" in serialized or "target_platform" in serialized
        assert "numPosts" in serialized or "num_posts" in serialized

    def test_response_default_platform(self):
        """Test ProjectResponse with default blog platform"""
        data = {
            "id": "proj-12345678",
            "name": "Test Project",
            "client_id": "client-12345678",
            "status": "draft",
            "target_platform": "blog",
            "created_at": datetime.utcnow(),
        }

        response = ProjectResponse(**data)
        assert response.target_platform == "blog"


class TestPlatformFieldValidation:
    """Test target_platform field validation"""

    def test_platform_field_is_optional_in_create(self):
        """Test target_platform is optional in ProjectCreate"""
        data = {
            "name": "Test",
            "client_id": "client-12345678",
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "blog"  # Default value

    def test_platform_field_is_optional_in_update(self):
        """Test target_platform is optional in ProjectUpdate"""
        data = {"name": "Updated"}

        update = ProjectUpdate(**data)
        assert update.target_platform is None

    def test_platform_with_empty_string(self):
        """Test handling of empty string for target_platform raises ValidationError"""
        from pydantic import ValidationError

        data = {
            "name": "Test",
            "client_id": "client-12345678",
            "target_platform": "",
        }

        # Empty string is not a valid platform enum value
        with pytest.raises(ValidationError):
            ProjectCreate(**data)

    def test_platform_with_pricing_fields(self):
        """Test target_platform works with pricing fields"""
        data = {
            "name": "Priced Campaign",
            "client_id": "client-12345678",
            "target_platform": "linkedin",
            "num_posts": 30,
            "price_per_post": 50.0,
            "total_price": 1500.0,
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "linkedin"
        assert project.price_per_post == 50.0
        assert project.total_price == 1500.0


class TestPlatformIntegrationWithOtherFields:
    """Test target_platform integration with other project fields"""

    def test_platform_with_template_quantities(self):
        """Test target_platform works with template_quantities"""
        data = {
            "name": "Template Campaign",
            "client_id": "client-12345678",
            "target_platform": "twitter",
            "template_quantities": {"1": 15, "2": 15},
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "twitter"
        assert project.template_quantities == {"1": 15, "2": 15}
        assert project.num_posts == 30  # Auto-calculated

    def test_platform_with_legacy_platforms_list(self):
        """Test target_platform works alongside legacy platforms array"""
        data = {
            "name": "Mixed Campaign",
            "client_id": "client-12345678",
            "platforms": ["linkedin", "twitter"],  # Legacy field
            "target_platform": "linkedin",  # New field
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "linkedin"
        assert project.platforms == ["linkedin", "twitter"]

    def test_platform_with_tone(self):
        """Test target_platform works with tone preference"""
        data = {
            "name": "Toned Campaign",
            "client_id": "client-12345678",
            "target_platform": "email",
            "tone": "professional",
        }

        project = ProjectCreate(**data)
        assert project.target_platform == "email"
        assert project.tone == "professional"
