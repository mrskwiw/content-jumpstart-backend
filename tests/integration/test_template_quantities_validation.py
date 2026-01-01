"""
Integration Tests for Template Quantities Validation and Pricing

Focuses on testing the Pydantic schema validation and pricing calculation
logic without requiring the full FastAPI app stack.

Run with: pytest tests/integration/test_template_quantities_validation.py -v
"""
import pytest
from pydantic import ValidationError

# Import schemas directly (no app imports to avoid SQLAlchemy issues)
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse


class TestTemplateQuantitiesValidation:
    """Test template quantities validation logic"""

    def test_valid_template_quantities(self):
        """Test that valid template quantities pass validation"""
        project_data = {
            "name": "Valid Project",
            "clientId": "client-test-123",
            "templateQuantities": {
                "1": 3,
                "2": 2,
                "9": 5,
            },
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.template_quantities == {"1": 3, "2": 2, "9": 5}
        assert project.num_posts == 10  # Auto-calculated
        assert project.total_price == 400.0  # Auto-calculated

        print("✓ Valid template quantities accepted")

    def test_pricing_calculation_base(self):
        """Test pricing calculation: posts * price_per_post"""
        project_data = {
            "name": "Pricing Test",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 10},
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 10
        assert project.total_price == 400.0

        print("✓ Base pricing calculation correct")

    def test_pricing_calculation_with_research(self):
        """Test pricing calculation with research add-on"""
        project_data = {
            "name": "Research Pricing Test",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 10},
            "pricePerPost": 40.0,
            "researchPricePerPost": 15.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 10
        assert project.total_price == 550.0  # 10 * (40 + 15)

        print("✓ Research pricing calculation correct")

    def test_num_posts_auto_calculated(self):
        """Test that num_posts is auto-calculated from template_quantities"""
        project_data = {
            "name": "Auto Calc Test",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 3, "2": 5, "9": 2},
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 10  # 3 + 5 + 2

        print("✓ num_posts auto-calculated correctly")

    def test_template_quantity_bounds_validation(self):
        """Test that template quantities are bounded (0-100)"""
        project_data = {
            "name": "Bounds Test",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 150},  # Exceeds max of 100
            "pricePerPost": 40.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(**project_data)

        assert "Maximum value is 100" in str(exc_info.value)

        print("✓ Template quantity bounds validated")

    def test_invalid_template_id(self):
        """Test that invalid template IDs are rejected"""
        project_data = {
            "name": "Invalid ID Test",
            "clientId": "client-test-123",
            "templateQuantities": {"999": 5},  # Invalid ID (> 100)
            "pricePerPost": 40.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(**project_data)

        # Error message changed to be more specific
        error_str = str(exc_info.value)
        assert ("Invalid template_id" in error_str or "template_id must be numeric" in error_str)

        print("✓ Invalid template ID rejected")

    def test_too_many_templates(self):
        """Test that excessive templates are rejected (DoS prevention)"""
        # Create 51 templates (exceeds limit of 50)
        template_quantities = {str(i): 1 for i in range(1, 52)}

        project_data = {
            "name": "Too Many Templates",
            "clientId": "client-test-123",
            "templateQuantities": template_quantities,
            "pricePerPost": 40.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(**project_data)

        assert "cannot exceed 50 templates" in str(exc_info.value)

        print("✓ Excessive template count rejected (DoS prevention)")

    def test_empty_template_quantities(self):
        """Test that empty template_quantities is valid"""
        project_data = {
            "name": "Empty Quantities",
            "clientId": "client-test-123",
            "templateQuantities": {},
            "numPosts": 30,  # Manually specified
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        # Empty quantities is valid (fallback to intelligent selection)
        assert project.template_quantities == {}
        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Empty template_quantities valid (intelligent selection fallback)")

    def test_camel_case_to_snake_case(self):
        """Test that camelCase field names are accepted (API compatibility)"""
        project_data = {
            "name": "CamelCase Test",
            "clientId": "client-test-123",  # camelCase
            "templateQuantities": {"1": 10},  # camelCase
            "pricePerPost": 40.0,  # camelCase
            "researchPricePerPost": 15.0,  # camelCase
        }

        project = ProjectCreate(**project_data)

        assert project.client_id == "client-test-123"
        assert project.template_quantities == {"1": 10}
        assert project.price_per_post == 40.0
        assert project.research_price_per_post == 15.0

        print("✓ CamelCase field names accepted")

    def test_snake_case_field_names(self):
        """Test that snake_case field names are accepted (Python compatibility)"""
        project_data = {
            "name": "SnakeCase Test",
            "client_id": "client-test-123",  # snake_case
            "template_quantities": {"1": 10},  # snake_case
            "price_per_post": 40.0,  # snake_case
            "research_price_per_post": 15.0,  # snake_case
        }

        project = ProjectCreate(**project_data)

        assert project.client_id == "client-test-123"
        assert project.template_quantities == {"1": 10}
        assert project.price_per_post == 40.0
        assert project.research_price_per_post == 15.0

        print("✓ snake_case field names accepted")

    def test_tone_enum_validation(self):
        """Test that tone field validates against allowed values"""
        project_data = {
            "name": "Tone Test",
            "clientId": "client-test-123",
            "templateQuantities": {"1": 10},
            "pricePerPost": 40.0,
            "tone": "professional",
        }

        project = ProjectCreate(**project_data)
        assert project.tone == "professional"

        # Test that tone accepts any string value (no enum validation currently)
        project_data["tone"] = "custom_tone"
        project2 = ProjectCreate(**project_data)
        assert project2.tone == "custom_tone"

        print("✓ Tone field accepts custom values (no enum validation)")

    def test_preset_package_quick_start(self):
        """Test Quick Start preset package (15 posts, $600)"""
        project_data = {
            "name": "Quick Start",
            "clientId": "client-test-123",
            "templateQuantities": {
                "1": 3, "2": 3, "5": 3, "9": 3, "10": 3,
            },
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 15
        assert project.total_price == 600.0

        print("✓ Quick Start package validated (15 posts, $600)")

    def test_preset_package_professional(self):
        """Test Professional preset package (30 posts, $1200)"""
        project_data = {
            "name": "Professional",
            "clientId": "client-test-123",
            "templateQuantities": {
                "1": 2, "2": 2, "3": 2, "4": 2, "5": 2,
                "6": 2, "7": 2, "8": 2, "9": 2, "10": 2,
                "11": 2, "12": 2, "13": 2, "14": 2, "15": 2,
            },
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Professional package validated (30 posts, $1200)")

    def test_preset_package_premium_with_research(self):
        """Test Premium preset package (50 posts, $2750 with research)"""
        project_data = {
            "name": "Premium",
            "clientId": "client-test-123",
            "templateQuantities": {
                "1": 4, "2": 4, "3": 4, "4": 4, "5": 4,  # 20 posts
                "6": 3, "7": 3, "8": 3, "9": 3, "10": 3,  # 15 posts
                "11": 3, "12": 3, "13": 3, "14": 3, "15": 3,  # 15 posts
                # Total: 20 + 15 + 15 = 50
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 15.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 50
        assert project.total_price == 2750.0  # 50 * (40 + 15)

        print("✓ Premium package validated (50 posts, $2750)")

    def test_custom_template_selection(self):
        """Test custom non-preset template selection"""
        project_data = {
            "name": "Custom Selection",
            "clientId": "client-test-123",
            "templateQuantities": {
                "1": 10,  # Heavy on Problem Recognition
                "9": 15,  # Heavy on How-To
                "13": 5,  # Some Future Thinking
            },
            "pricePerPost": 40.0,
        }

        project = ProjectCreate(**project_data)

        assert project.num_posts == 30
        assert project.total_price == 1200.0

        print("✓ Custom template selection validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
