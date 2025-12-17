"""Data models for brief quality assessment"""

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class FieldQuality(str, Enum):
    """Quality levels for individual fields"""

    MISSING = "missing"  # Field is empty/None
    WEAK = "weak"  # Field exists but too generic/short
    ADEQUATE = "adequate"  # Field meets minimum requirements
    STRONG = "strong"  # Field is detailed and specific


class BriefQualityReport(BaseModel):
    """Comprehensive brief quality assessment"""

    # Overall metrics
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score (0.0-1.0)")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="How complete (0.0-1.0)")
    specificity_score: float = Field(
        ..., ge=0.0, le=1.0, description="How specific vs generic (0.0-1.0)"
    )
    usability_score: float = Field(
        ..., ge=0.0, le=1.0, description="How usable for generation (0.0-1.0)"
    )

    # Field-level assessment
    field_quality: Dict[str, FieldQuality] = Field(..., description="Quality rating for each field")
    missing_fields: List[str] = Field(
        default_factory=list, description="Empty required/important fields"
    )
    weak_fields: List[str] = Field(
        default_factory=list, description="Present but inadequate fields"
    )
    strong_fields: List[str] = Field(default_factory=list, description="High quality fields")

    # Recommendations
    priority_improvements: List[str] = Field(
        default_factory=list, description="Top 3-5 improvements needed"
    )
    can_generate_content: bool = Field(..., description="Ready for content generation?")
    minimum_questions_needed: int = Field(..., ge=0, description="Minimum questions to ask")

    # Metadata
    total_fields: int = Field(..., ge=0, description="Total fields assessed")
    filled_fields: int = Field(..., ge=0, description="Number of filled fields")
    required_fields_filled: int = Field(..., ge=0, description="Required fields filled")

    def to_summary_text(self) -> str:
        """Generate human-readable summary"""
        lines = [
            f"Overall Quality: {self.overall_score:.0%}",
            f"  - Completeness: {self.completeness_score:.0%}",
            f"  - Specificity: {self.specificity_score:.0%}",
            f"  - Usability: {self.usability_score:.0%}",
            "",
            f"Fields: {self.filled_fields}/{self.total_fields} filled",
            f"Status: {'✓ Ready for generation' if self.can_generate_content else '⚠ Needs improvement'}",
        ]

        if self.priority_improvements:
            lines.append("")
            lines.append("Priority Improvements:")
            for improvement in self.priority_improvements:
                lines.append(f"  • {improvement}")

        return "\n".join(lines)
