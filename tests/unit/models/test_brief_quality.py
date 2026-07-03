"""Tests for Brief Quality Models"""

import pytest
from pydantic import ValidationError

from src.models.brief_quality import BriefQualityReport, FieldQuality


class TestFieldQuality:
    """Test FieldQuality enum"""

    def test_enum_values(self):
        """Test all enum values are accessible"""
        assert FieldQuality.MISSING == "missing"
        assert FieldQuality.WEAK == "weak"
        assert FieldQuality.ADEQUATE == "adequate"
        assert FieldQuality.STRONG == "strong"

    def test_enum_members(self):
        """Test enum members list"""
        values = {member.value for member in FieldQuality}
        assert values == {"missing", "weak", "adequate", "strong"}

    def test_enum_string_comparison(self):
        """Test enum can be compared with strings"""
        assert FieldQuality.STRONG == "strong"
        assert FieldQuality.WEAK != "strong"


class TestBriefQualityReport:
    """Test BriefQualityReport model"""

    def test_create_valid_report(self):
        """Test creating a valid quality report"""
        report = BriefQualityReport(
            overall_score=0.85,
            completeness_score=0.90,
            specificity_score=0.80,
            usability_score=0.85,
            field_quality={
                "company_name": FieldQuality.STRONG,
                "business_description": FieldQuality.ADEQUATE,
                "ideal_customer": FieldQuality.WEAK,
            },
            missing_fields=["customer_pain_points"],
            weak_fields=["ideal_customer"],
            strong_fields=["company_name"],
            priority_improvements=["Add customer pain points", "Improve ideal customer detail"],
            can_generate_content=True,
            minimum_questions_needed=2,
            total_fields=10,
            filled_fields=8,
            required_fields_filled=3,
        )

        assert report.overall_score == 0.85
        assert report.completeness_score == 0.90
        assert report.can_generate_content is True
        assert len(report.priority_improvements) == 2
        assert "customer_pain_points" in report.missing_fields

    def test_create_minimal_report(self):
        """Test creating report with minimal required fields"""
        report = BriefQualityReport(
            overall_score=0.50,
            completeness_score=0.60,
            specificity_score=0.40,
            usability_score=0.50,
            field_quality={},
            can_generate_content=False,
            minimum_questions_needed=5,
            total_fields=10,
            filled_fields=4,
            required_fields_filled=2,
        )

        assert report.overall_score == 0.50
        assert report.missing_fields == []  # Default empty list
        assert report.weak_fields == []
        assert report.strong_fields == []
        assert report.priority_improvements == []

    def test_default_factory_fields(self):
        """Test fields with default_factory create empty lists"""
        report = BriefQualityReport(
            overall_score=0.75,
            completeness_score=0.80,
            specificity_score=0.70,
            usability_score=0.75,
            field_quality={"company_name": FieldQuality.STRONG},
            can_generate_content=True,
            minimum_questions_needed=0,
            total_fields=10,
            filled_fields=10,
            required_fields_filled=4,
        )

        # These should be empty lists, not None
        assert isinstance(report.missing_fields, list)
        assert isinstance(report.weak_fields, list)
        assert isinstance(report.strong_fields, list)
        assert isinstance(report.priority_improvements, list)


class TestBriefQualityReportValidation:
    """Test Pydantic validation constraints"""

    def test_score_must_be_between_0_and_1(self):
        """Test scores must be in range [0.0, 1.0]"""
        # Test overall_score > 1.0
        with pytest.raises(ValidationError) as exc_info:
            BriefQualityReport(
                overall_score=1.5,  # Invalid - too high
                completeness_score=0.90,
                specificity_score=0.80,
                usability_score=0.85,
                field_quality={},
                can_generate_content=True,
                minimum_questions_needed=0,
                total_fields=10,
                filled_fields=10,
                required_fields_filled=4,
            )
        assert "overall_score" in str(exc_info.value)

    def test_score_must_be_non_negative(self):
        """Test scores cannot be negative"""
        with pytest.raises(ValidationError) as exc_info:
            BriefQualityReport(
                overall_score=0.85,
                completeness_score=-0.10,  # Invalid - negative
                specificity_score=0.80,
                usability_score=0.85,
                field_quality={},
                can_generate_content=True,
                minimum_questions_needed=0,
                total_fields=10,
                filled_fields=10,
                required_fields_filled=4,
            )
        assert "completeness_score" in str(exc_info.value)

    def test_counts_must_be_non_negative(self):
        """Test count fields must be >= 0"""
        with pytest.raises(ValidationError) as exc_info:
            BriefQualityReport(
                overall_score=0.85,
                completeness_score=0.90,
                specificity_score=0.80,
                usability_score=0.85,
                field_quality={},
                can_generate_content=True,
                minimum_questions_needed=-1,  # Invalid - negative
                total_fields=10,
                filled_fields=10,
                required_fields_filled=4,
            )
        assert "minimum_questions_needed" in str(exc_info.value)

    def test_boundary_scores_valid(self):
        """Test boundary values (0.0 and 1.0) are valid"""
        # Should not raise
        report = BriefQualityReport(
            overall_score=0.0,  # Minimum valid
            completeness_score=1.0,  # Maximum valid
            specificity_score=0.5,
            usability_score=0.5,
            field_quality={},
            can_generate_content=False,
            minimum_questions_needed=0,  # Minimum valid
            total_fields=0,
            filled_fields=0,
            required_fields_filled=0,
        )
        assert report.overall_score == 0.0
        assert report.completeness_score == 1.0
        assert report.minimum_questions_needed == 0


class TestToSummaryText:
    """Test to_summary_text method"""

    def test_summary_with_improvements(self):
        """Test summary includes priority improvements"""
        report = BriefQualityReport(
            overall_score=0.65,
            completeness_score=0.70,
            specificity_score=0.60,
            usability_score=0.65,
            field_quality={},
            priority_improvements=[
                "Add customer pain points",
                "Improve business description",
                "Define target platforms",
            ],
            can_generate_content=False,
            minimum_questions_needed=3,
            total_fields=10,
            filled_fields=6,
            required_fields_filled=3,
        )

        summary = report.to_summary_text()

        # Check format
        assert "Overall Quality: 65%" in summary
        assert "Completeness: 70%" in summary
        assert "Specificity: 60%" in summary
        assert "Usability: 65%" in summary
        assert "Fields: 6/10 filled" in summary
        assert "⚠ Needs improvement" in summary

        # Check improvements listed
        assert "Priority Improvements:" in summary
        assert "• Add customer pain points" in summary
        assert "• Improve business description" in summary
        assert "• Define target platforms" in summary

    def test_summary_without_improvements(self):
        """Test summary without priority improvements"""
        report = BriefQualityReport(
            overall_score=0.95,
            completeness_score=0.95,
            specificity_score=0.95,
            usability_score=0.95,
            field_quality={},
            priority_improvements=[],  # Empty
            can_generate_content=True,
            minimum_questions_needed=0,
            total_fields=10,
            filled_fields=10,
            required_fields_filled=4,
        )

        summary = report.to_summary_text()

        # Check format
        assert "Overall Quality: 95%" in summary
        assert "✓ Ready for generation" in summary
        assert "Fields: 10/10 filled" in summary

        # Should NOT include improvements section
        assert "Priority Improvements:" not in summary

    def test_summary_ready_for_generation(self):
        """Test summary shows ready status when can_generate_content=True"""
        report = BriefQualityReport(
            overall_score=0.90,
            completeness_score=0.90,
            specificity_score=0.90,
            usability_score=0.90,
            field_quality={},
            can_generate_content=True,  # Ready
            minimum_questions_needed=0,
            total_fields=10,
            filled_fields=9,
            required_fields_filled=4,
        )

        summary = report.to_summary_text()
        assert "✓ Ready for generation" in summary
        assert "⚠ Needs improvement" not in summary

    def test_summary_needs_improvement(self):
        """Test summary shows needs improvement when can_generate_content=False"""
        report = BriefQualityReport(
            overall_score=0.60,
            completeness_score=0.65,
            specificity_score=0.55,
            usability_score=0.60,
            field_quality={},
            can_generate_content=False,  # Not ready
            minimum_questions_needed=4,
            total_fields=10,
            filled_fields=5,
            required_fields_filled=2,
        )

        summary = report.to_summary_text()
        assert "⚠ Needs improvement" in summary
        assert "✓ Ready for generation" not in summary

    def test_summary_percentage_formatting(self):
        """Test percentage values are formatted correctly"""
        report = BriefQualityReport(
            overall_score=0.876,  # Should round to 88%
            completeness_score=0.833,  # Should round to 83%
            specificity_score=0.925,  # Should round to 92%
            usability_score=0.801,  # Should round to 80%
            field_quality={},
            can_generate_content=True,
            minimum_questions_needed=0,
            total_fields=10,
            filled_fields=8,
            required_fields_filled=4,
        )

        summary = report.to_summary_text()

        # Check rounding (:.0% format)
        assert "Overall Quality: 88%" in summary
        assert "Completeness: 83%" in summary
        assert "Specificity: 92%" in summary
        assert "Usability: 80%" in summary

    def test_summary_multiline_structure(self):
        """Test summary has proper multiline structure"""
        report = BriefQualityReport(
            overall_score=0.75,
            completeness_score=0.80,
            specificity_score=0.70,
            usability_score=0.75,
            field_quality={},
            priority_improvements=["First improvement", "Second improvement"],
            can_generate_content=False,
            minimum_questions_needed=2,
            total_fields=10,
            filled_fields=7,
            required_fields_filled=3,
        )

        summary = report.to_summary_text()
        lines = summary.split("\n")

        # Should have multiple lines
        assert len(lines) > 5

        # Check structure
        assert lines[0].startswith("Overall Quality:")
        assert lines[1].startswith("  - Completeness:")
        assert lines[2].startswith("  - Specificity:")
        assert lines[3].startswith("  - Usability:")
        assert lines[4] == ""  # Empty line
        assert lines[5].startswith("Fields:")
        assert lines[6].startswith("Status:")


class TestFieldQualityInReport:
    """Test FieldQuality usage in BriefQualityReport"""

    def test_field_quality_dict_with_all_enum_values(self):
        """Test field_quality dict can contain all enum values"""
        report = BriefQualityReport(
            overall_score=0.70,
            completeness_score=0.75,
            specificity_score=0.65,
            usability_score=0.70,
            field_quality={
                "field1": FieldQuality.MISSING,
                "field2": FieldQuality.WEAK,
                "field3": FieldQuality.ADEQUATE,
                "field4": FieldQuality.STRONG,
            },
            can_generate_content=False,
            minimum_questions_needed=3,
            total_fields=10,
            filled_fields=6,
            required_fields_filled=2,
        )

        assert report.field_quality["field1"] == FieldQuality.MISSING
        assert report.field_quality["field2"] == FieldQuality.WEAK
        assert report.field_quality["field3"] == FieldQuality.ADEQUATE
        assert report.field_quality["field4"] == FieldQuality.STRONG

    def test_field_quality_empty_dict(self):
        """Test field_quality can be empty dict"""
        report = BriefQualityReport(
            overall_score=0.50,
            completeness_score=0.60,
            specificity_score=0.40,
            usability_score=0.50,
            field_quality={},  # Empty
            can_generate_content=False,
            minimum_questions_needed=5,
            total_fields=10,
            filled_fields=3,
            required_fields_filled=1,
        )

        assert report.field_quality == {}
        assert len(report.field_quality) == 0
