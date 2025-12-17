"""
Voice sample upload and matching models for Phase 8C

These models support the voice sample upload workflow where clients can provide
existing content samples to bootstrap accurate voice analysis.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class VoiceSampleUpload(BaseModel):
    """Uploaded voice sample from client"""

    id: Optional[int] = None
    client_name: str
    upload_date: datetime = Field(default_factory=datetime.now)
    sample_text: str
    sample_source: str  # linkedin, blog, twitter, email, mixed
    word_count: int
    file_name: str

    @field_validator("sample_source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate sample source is from allowed list"""
        allowed_sources = ["linkedin", "blog", "twitter", "email", "mixed", "other"]
        if v.lower() not in allowed_sources:
            raise ValueError(f"Invalid source '{v}'. Must be one of: {', '.join(allowed_sources)}")
        return v.lower()

    @field_validator("word_count")
    @classmethod
    def validate_word_count(cls, v: int) -> int:
        """Validate word count is within acceptable range"""
        if v < 100:
            raise ValueError("Sample must be at least 100 words")
        if v > 2000:
            raise ValueError("Sample exceeds maximum 2,000 words")
        return v

    @property
    def preview(self) -> str:
        """First 200 chars of sample for display"""
        if len(self.sample_text) <= 200:
            return self.sample_text
        return self.sample_text[:200] + "..."

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "id": self.id,
            "client_name": self.client_name,
            "upload_date": self.upload_date.isoformat(),
            "sample_text": self.sample_text,
            "sample_source": self.sample_source,
            "word_count": self.word_count,
            "file_name": self.file_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceSampleUpload":
        """Create from dictionary (from database)"""
        if isinstance(data["upload_date"], str):
            data["upload_date"] = datetime.fromisoformat(data["upload_date"])
        return cls(**data)


class VoiceMatchComponentScore(BaseModel):
    """Individual component score for voice matching"""

    component: str
    score: float  # 0.0-1.0
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None


class VoiceMatchReport(BaseModel):
    """Report comparing generated content to voice samples"""

    client_name: str
    project_id: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    match_score: float  # 0.0-1.0 overall score

    # Component scores
    readability_score: Optional[VoiceMatchComponentScore] = None
    word_count_score: Optional[VoiceMatchComponentScore] = None
    archetype_score: Optional[VoiceMatchComponentScore] = None
    phrase_usage_score: Optional[VoiceMatchComponentScore] = None

    # Recommendations
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)

    # Match quality interpretation
    @property
    def match_quality(self) -> str:
        """Human-readable match quality"""
        if self.match_score >= 0.9:
            return "Excellent"
        elif self.match_score >= 0.8:
            return "Good"
        elif self.match_score >= 0.7:
            return "Acceptable"
        elif self.match_score >= 0.6:
            return "Weak"
        else:
            return "Poor"

    @property
    def match_quality_emoji(self) -> str:
        """Emoji representation of match quality"""
        if self.match_score >= 0.9:
            return "🟢"
        elif self.match_score >= 0.8:
            return "🟡"
        elif self.match_score >= 0.7:
            return "🟠"
        else:
            return "🔴"

    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = [
            f"# Voice Match Report: {self.client_name}",
            "",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Overall Match Score:** {self.match_score:.2f} / 1.00 {self.match_quality_emoji} ({self.match_quality})",
            "",
            "## Component Scores",
            "",
        ]

        # Add component scores
        components = [
            ("Readability", self.readability_score),
            ("Word Count", self.word_count_score),
            ("Brand Archetype", self.archetype_score),
            ("Phrase Usage", self.phrase_usage_score),
        ]

        for name, score_obj in components:
            if score_obj:
                lines.append(f"### {name}")
                lines.append(f"**Score:** {score_obj.score:.2f} / 1.00")
                if score_obj.target_value is not None and score_obj.actual_value is not None:
                    lines.append(f"- Target: {score_obj.target_value:.1f}")
                    lines.append(f"- Actual: {score_obj.actual_value:.1f}")
                    if score_obj.difference is not None:
                        lines.append(f"- Difference: {score_obj.difference:.1f}")
                lines.append("")

        # Add strengths
        if self.strengths:
            lines.append("## Strengths ✓")
            lines.append("")
            for strength in self.strengths:
                lines.append(f"- {strength}")
            lines.append("")

        # Add weaknesses
        if self.weaknesses:
            lines.append("## Areas for Improvement")
            lines.append("")
            for weakness in self.weaknesses:
                lines.append(f"- {weakness}")
            lines.append("")

        # Add improvement suggestions
        if self.improvements:
            lines.append("## Recommendations")
            lines.append("")
            for improvement in self.improvements:
                lines.append(f"- {improvement}")
            lines.append("")

        # Add interpretation guide
        lines.extend(
            [
                "## Match Score Interpretation",
                "",
                "- **0.9-1.0 (Excellent):** Voice indistinguishable from samples",
                "- **0.8-0.89 (Good):** Minor differences, highly professional",
                "- **0.7-0.79 (Acceptable):** Noticeable but acceptable differences",
                "- **0.6-0.69 (Weak):** Significant differences",
                "- **<0.6 (Poor):** Re-generation recommended",
            ]
        )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "client_name": self.client_name,
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "match_score": self.match_score,
            "readability_score": self.readability_score.model_dump()
            if self.readability_score
            else None,
            "word_count_score": self.word_count_score.model_dump()
            if self.word_count_score
            else None,
            "archetype_score": self.archetype_score.model_dump() if self.archetype_score else None,
            "phrase_usage_score": self.phrase_usage_score.model_dump()
            if self.phrase_usage_score
            else None,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvements": self.improvements,
        }


class VoiceSampleBatch(BaseModel):
    """Batch of voice samples for a single client"""

    client_name: str
    samples: List[VoiceSampleUpload]
    total_words: int = 0
    upload_date: datetime = Field(default_factory=datetime.now)

    def __init__(self, **data):
        """Initialize batch and calculate total word count across all samples"""
        super().__init__(**data)
        # Calculate total words
        self.total_words = sum(sample.word_count for sample in self.samples)

    @property
    def sample_count(self) -> int:
        """Number of samples in batch"""
        return len(self.samples)

    @property
    def average_word_count(self) -> float:
        """Average words per sample"""
        if not self.samples:
            return 0.0
        return self.total_words / len(self.samples)

    @property
    def sources(self) -> List[str]:
        """Unique sources in batch"""
        return list(set(sample.sample_source for sample in self.samples))

    def is_valid(self) -> bool:
        """Check if batch meets minimum requirements"""
        # Minimum 500 words total
        if self.total_words < 500:
            return False
        # Maximum 10 samples
        if len(self.samples) > 10:
            return False
        # Each sample 100-2000 words (already validated by VoiceSampleUpload)
        return True

    def validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        errors = []
        if self.total_words < 500:
            errors.append(f"Total word count ({self.total_words}) is below minimum 500 words")
        if len(self.samples) > 10:
            errors.append(f"Too many samples ({len(self.samples)}). Maximum is 10 samples")
        if len(self.samples) == 0:
            errors.append("No samples provided")
        return errors
