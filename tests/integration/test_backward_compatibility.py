"""
Backward Compatibility Tests for Template System

Tests that the system maintains compatibility with projects created
using the old 'templates' array field before the template_quantities
refactor was implemented.

Run with: pytest tests/integration/test_backward_compatibility.py -v
"""
import pytest

# Import schemas directly (no app imports to avoid SQLAlchemy issues)
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from schemas.project import ProjectCreate, ProjectUpdate


class TestBackwardCompatibility:
    """Tests for backward compatibility with old template system"""

    def test_old_templates_field_accepted(self):
        """Test that projects with old 'templates' array field are accepted"""
        # Old format: templates as array of IDs (strings)
        project_data = {
            "name": "Legacy Project",
            "clientId": "client-test-123",
            "templates": ["1", "2", "9"],  # Old format
            "numPosts": 30,
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # Old templates field should be preserved
        assert project.templates == ["1", "2", "9"]
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Old 'templates' array format accepted")

    def test_templates_field_coexists_with_quantities(self):
        """Test that both old and new fields can coexist"""
        project_data = {
            "name": "Hybrid Project",
            "clientId": "client-test-123",
            "templates": ["1", "2", "9"],  # Old format (deprecated)
            "templateQuantities": {"1": 3, "2": 2, "9": 5},  # New format
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # Both fields should be preserved
        assert project.templates == ["1", "2", "9"]
        assert project.template_quantities == {"1": 3, "2": 2, "9": 5}
        assert project.num_posts == 10  # Calculated from quantities
        assert project.total_price == 400.0

        print("✓ Old and new template fields can coexist")

    def test_legacy_project_without_quantities(self):
        """Test legacy project with only templates field (no quantities)"""
        project_data = {
            "name": "Legacy Only",
            "clientId": "client-test-123",
            "templates": ["1", "3", "5", "7", "9"],
            "numPosts": 30,  # Manually specified
            "pricePerPost": 40.0,
            "totalPrice": 1200.0,  # Manually specified
        }

        project = ProjectCreate(**project_data)

        assert project.templates == ["1", "3", "5", "7", "9"]
        assert project.template_quantities is None  # No quantities specified
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Legacy project without quantities works")

    def test_update_legacy_project_with_quantities(self):
        """Test updating a legacy project to add template_quantities"""
        # Simulate updating an existing project
        update_data = {
            "templateQuantities": {"1": 10, "9": 20},  # Adding quantities
        }

        project_update = ProjectUpdate(**update_data)

        assert project_update.template_quantities == {"1": 10, "9": 20}

        print("✓ Legacy project can be updated with template_quantities")

    def test_migration_path_templates_to_quantities(self):
        """
        Test the migration path: converting old templates array
        to new template_quantities dict with equal distribution
        """
        # Step 1: Old project with equal distribution
        old_project = {
            "name": "Migration Test",
            "clientId": "client-test-123",
            "templates": ["1", "2", "9"],  # 3 templates
            "numPosts": 30,  # 10 posts per template
            "pricePerPost": 40.0,
        }

        old = ProjectCreate(**old_project)
        assert old.templates == ["1", "2", "9"]
        assert old.num_posts == 30

        # Step 2: Migrated project with explicit quantities
        # (simulating migration logic: 30 posts / 3 templates = 10 each)
        migrated_project = {
            "name": "Migration Test",
            "clientId": "client-test-123",
            "templates": ["1", "2", "9"],  # Keep for compatibility
            "templateQuantities": {"1": 10, "2": 10, "9": 10},  # Explicit quantities
            "pricePerPost": 40.0,
        }

        migrated = ProjectCreate(**migrated_project)
        assert migrated.templates == ["1", "2", "9"]
        assert migrated.template_quantities == {"1": 10, "2": 10, "9": 10}
        assert migrated.num_posts == 30
        assert migrated.total_price == 1200.0

        print("✓ Migration path from templates to quantities validated")

    def test_empty_templates_field(self):
        """Test that empty templates array is valid"""
        project_data = {
            "name": "Empty Templates",
            "clientId": "client-test-123",
            "templates": [],  # Empty array
            "numPosts": 30,  # Manually specified
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.templates == []
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Empty templates array valid")

    def test_none_templates_field(self):
        """Test that None/missing templates field is valid"""
        project_data = {
            "name": "No Templates Field",
            "clientId": "client-test-123",
            "numPosts": 30,
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.templates is None
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Missing templates field valid")

    def test_intelligent_selection_fallback(self):
        """
        Test fallback to intelligent selection when neither
        templates nor template_quantities are specified
        """
        project_data = {
            "name": "Intelligent Selection",
            "clientId": "client-test-123",
            "numPosts": 30,
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # Neither field specified - system should use intelligent selection
        assert project.templates is None
        assert project.template_quantities is None
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Fallback to intelligent selection working")


class TestTemplateFieldPriority:
    """Test priority when both old and new fields are present"""

    def test_quantities_takes_priority_for_calculation(self):
        """
        When both templates and template_quantities are present,
        template_quantities should be used for num_posts calculation
        """
        project_data = {
            "name": "Priority Test",
            "clientId": "client-test-123",
            "templates": ["1", "2"],  # 2 templates (old)
            "templateQuantities": {"1": 3, "2": 7},  # 10 posts (new)
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # template_quantities should be used for calculation
        assert project.num_posts == 10  # From quantities, not len(templates)
        assert project.total_price == 400.0

        print("✓ template_quantities takes priority for calculations")

    def test_explicit_num_posts_preserved(self):
        """
        Test that explicitly provided num_posts is preserved
        (auto-calculation only happens when num_posts is None)
        """
        project_data = {
            "name": "Manual Override",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 5, "2": 5},  # Would auto-calculate to 10
            "numPosts": 30,  # Explicit override
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # Explicit num_posts should be preserved (validator only sets if None)
        assert project.num_posts == 30  # Explicit value preserved
        assert project.total_price == 1200.0  # Calculated from explicit num_posts

        print("✓ Explicit num_posts preserved (not overridden by auto-calculation)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
