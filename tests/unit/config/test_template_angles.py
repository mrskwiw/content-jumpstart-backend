"""Unit tests for src/config/template_angles.py"""

from src.config.template_angles import TEMPLATE_ANGLES, MAX_QUANTITY_PER_TEMPLATE


class TestTemplateAnglesStructure:
    """Verify the shape and completeness of TEMPLATE_ANGLES."""

    def test_all_15_templates_present(self):
        assert set(TEMPLATE_ANGLES.keys()) == set(range(1, 16))

    def test_each_template_has_10_angles(self):
        for template_id, angles in TEMPLATE_ANGLES.items():
            assert (
                len(angles) == 10
            ), f"Template {template_id} has {len(angles)} angles, expected 10"

    def test_max_quantity_constant_matches_list_length(self):
        assert MAX_QUANTITY_PER_TEMPLATE == 10
        for template_id, angles in TEMPLATE_ANGLES.items():
            assert len(angles) == MAX_QUANTITY_PER_TEMPLATE, (
                f"Template {template_id}: list length {len(angles)} != "
                f"MAX_QUANTITY_PER_TEMPLATE {MAX_QUANTITY_PER_TEMPLATE}"
            )

    def test_angles_are_non_empty_strings(self):
        for template_id, angles in TEMPLATE_ANGLES.items():
            for i, angle in enumerate(angles):
                assert isinstance(angle, str), f"Template {template_id}, angle {i}: not a string"
                assert angle.strip(), f"Template {template_id}, angle {i}: empty or whitespace-only"

    def test_no_duplicate_angles_within_template(self):
        for template_id, angles in TEMPLATE_ANGLES.items():
            assert len(set(angles)) == len(
                angles
            ), f"Template {template_id} contains duplicate angles"

    def test_no_duplicate_angles_across_templates(self):
        all_angles = [angle for angles in TEMPLATE_ANGLES.values() for angle in angles]
        assert len(set(all_angles)) == len(
            all_angles
        ), "Duplicate angles found across different templates"

    def test_angles_have_reasonable_length(self):
        """Each angle should be a meaningful instruction — not a single word or a paragraph."""
        for template_id, angles in TEMPLATE_ANGLES.items():
            for i, angle in enumerate(angles):
                word_count = len(angle.split())
                assert (
                    word_count >= 10
                ), f"Template {template_id}, angle {i}: only {word_count} words (minimum 10)"
                assert (
                    word_count <= 60
                ), f"Template {template_id}, angle {i}: {word_count} words (maximum 60)"
