"""Data models for enhanced brand voice guide"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VoicePattern(BaseModel):
    """A detected pattern in the client'''s voice"""

    pattern_type: str = Field(..., description="Type of pattern (opening, transition, cta, tone)")
    examples: List[str] = Field(..., description="Actual examples from posts (top 3)")
    frequency: int = Field(..., description="How often this pattern appears", ge=0)
    description: str = Field(..., description="What this pattern achieves")


class EnhancedVoiceGuide(BaseModel):
    """Enhanced brand voice guide based on generated content analysis"""

    # Basic Info
    company_name: str = Field(..., description="Company name")
    generated_from_posts: int = Field(..., description="Number of posts analyzed", ge=1)
    generated_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")

    # Tone Analysis
    dominant_tones: List[str] = Field(default_factory=list, description="Top tones identified")
    tone_consistency_score: float = Field(
        ..., description="Tone consistency score (0.0-1.0)", ge=0.0, le=1.0
    )

    # Language Patterns
    common_opening_hooks: List[VoicePattern] = Field(
        default_factory=list, description="Top opening hook patterns"
    )
    common_transitions: List[VoicePattern] = Field(
        default_factory=list, description="Top transition phrase patterns"
    )
    common_ctas: List[VoicePattern] = Field(
        default_factory=list, description="Top call-to-action patterns"
    )
    key_phrases_used: List[str] = Field(
        default_factory=list, description="Phrases that appeared 3+ times"
    )

    # Structural Patterns
    average_word_count: int = Field(..., description="Average post length in words", ge=0)
    average_paragraph_count: float = Field(
        ..., description="Average number of paragraphs per post", ge=0.0
    )
    question_usage_rate: float = Field(
        ..., description="Percentage of posts with questions (0.0-1.0)", ge=0.0, le=1.0
    )

    # Recommendations
    dos: List[str] = Field(default_factory=list, description="DO recommendations")
    donts: List[str] = Field(default_factory=list, description="DON'''T recommendations")
    examples: List[str] = Field(default_factory=list, description="Strong example excerpts")

    # NEW: Voice Metrics (from content-creator skill integration)
    average_readability_score: Optional[float] = Field(
        None,
        description="Flesch Reading Ease score (0-100, higher = easier to read)",
        ge=0.0,
        le=100.0,
    )
    voice_dimensions: Optional[Dict] = Field(
        None, description="Voice dimension analysis (formality, tone, perspective)"
    )
    sentence_variety: Optional[str] = Field(
        None, description="Sentence structure variety: 'low' | 'medium' | 'high'"
    )
    voice_archetype: Optional[str] = Field(
        None, description="Brand archetype: Expert | Friend | Innovator | Guide | Motivator"
    )

    # Phase 8C: Voice Sample Metadata
    source: Optional[str] = Field(
        None, description="Source of voice analysis: 'client_samples' or 'generated'"
    )
    sample_count: Optional[int] = Field(
        None, description="Number of client samples analyzed (if source='client_samples')", ge=0
    )
    sample_source: Optional[str] = Field(
        None, description="Source of samples: linkedin, blog, twitter, email, mixed"
    )
    sample_upload_date: Optional[datetime] = Field(None, description="When samples were uploaded")

    # Phase 8C: Emoji Patterns
    emoji_frequency: Optional[float] = Field(None, description="Emojis per 100 words", ge=0.0)
    common_emojis: List[str] = Field(
        default_factory=list, description="Most frequently used emojis"
    )

    # Phase 8C: Jargon Analysis
    jargon_ratio: Optional[float] = Field(
        None, description="Technical terms / total words ratio", ge=0.0, le=1.0
    )
    industry_terms: List[str] = Field(
        default_factory=list, description="Industry-specific terms identified"
    )

    def to_markdown(self) -> str:
        """Export voice guide as formatted markdown"""
        lines = []

        # Header
        lines.append(f"# Enhanced Brand Voice Guide: {self.company_name}\n")
        lines.append(
            f"*Generated from {self.generated_from_posts} posts on {self.generated_at.strftime('%B %d, %Y')}*\n"
        )
        lines.append("\n---\n")

        # Voice Summary
        lines.append("\n## Voice Summary\n")
        if self.dominant_tones:
            tones_str = ", ".join([tone.title() for tone in self.dominant_tones])
            lines.append(f"**Dominant Tones:** {tones_str}\n")

        score_pct = int(self.tone_consistency_score * 100)
        score_indicator = "✓" if score_pct >= 70 else "~"
        lines.append(f"**Tone Consistency Score:** {score_pct}% {score_indicator}\n")

        # NEW: Voice Metrics Section
        if self.voice_archetype or self.average_readability_score is not None:
            lines.append("\n### Voice Metrics\n")

            if self.voice_archetype:
                lines.append(f"**Brand Archetype:** {self.voice_archetype}\n")

            if self.average_readability_score is not None:
                readability = self.average_readability_score
                lines.append(f"**Readability Score:** {readability:.1f}/100 ")

                # Readability interpretation
                if readability >= 80:
                    lines.append("(Very Easy - 6th grade)\n")
                elif readability >= 70:
                    lines.append("(Fairly Easy - 7th grade)\n")
                elif readability >= 60:
                    lines.append("(Standard - 8th-9th grade)\n")
                elif readability >= 50:
                    lines.append("(Fairly Difficult - High school)\n")
                else:
                    lines.append("(Difficult - College level)\n")

            if self.sentence_variety:
                variety_emoji = {"low": "📉", "medium": "📊", "high": "📈"}
                emoji = variety_emoji.get(self.sentence_variety, "")
                lines.append(f"**Sentence Variety:** {self.sentence_variety.title()} {emoji}\n")

            if self.voice_dimensions:
                lines.append("\n**Voice Dimensions:**\n")

                formality = self.voice_dimensions.get("formality", {})
                if formality.get("dominant"):
                    lines.append(f"- Formality: {formality['dominant'].title()}\n")

                tone = self.voice_dimensions.get("tone", {})
                if tone.get("dominant"):
                    lines.append(f"- Tone: {tone['dominant'].title()}\n")

                perspective = self.voice_dimensions.get("perspective", {})
                if perspective.get("dominant"):
                    lines.append(f"- Perspective: {perspective['dominant'].title()}\n")

        lines.append("\n---\n")

        # Opening Hooks
        if self.common_opening_hooks:
            lines.append("\n## Opening Hooks\n")
            lines.append("\nYour posts typically start with:\n")
            for i, pattern in enumerate(self.common_opening_hooks[:5], 1):
                lines.append(
                    f"\n### {i}. **{pattern.description}** (appears {pattern.frequency} times)\n"
                )
                for example in pattern.examples[:2]:
                    lines.append(f'   - Example: "{example}"\n')

        # Common Transitions
        if self.common_transitions:
            lines.append("\n---\n")
            lines.append("\n## Common Transitions\n")
            lines.append("\nYou guide readers with phrases like:\n\n")
            for pattern in self.common_transitions[:5]:
                for example in pattern.examples[:1]:
                    lines.append(f'- "{example}" ({pattern.frequency} times)\n')

            lines.append(f"\n**Pattern:** {self.common_transitions[0].description}\n")

        # Call-to-Action Patterns
        if self.common_ctas:
            lines.append("\n---\n")
            lines.append("\n## Call-to-Action Patterns\n")
            lines.append("\nYour posts end with:\n")

            question_ctas = [p for p in self.common_ctas if "question" in p.description.lower()]
            other_ctas = [p for p in self.common_ctas if "question" not in p.description.lower()]

            if question_ctas:
                total_questions = sum(p.frequency for p in question_ctas)
                lines.append(f"\n### 1. **Open-ended questions** ({total_questions} posts)\n")
                for pattern in question_ctas[:2]:
                    for example in pattern.examples[:1]:
                        lines.append(f'   - "{example}"\n')

            if other_ctas:
                total_other = sum(p.frequency for p in other_ctas)
                lines.append(f"\n### 2. **{other_ctas[0].description}** ({total_other} posts)\n")
                for pattern in other_ctas[:2]:
                    for example in pattern.examples[:1]:
                        lines.append(f'   - "{example}"\n')

        # Key Phrases
        if self.key_phrases_used:
            lines.append("\n---\n")
            lines.append("\n## Key Phrases (Used 3+ Times)\n\n")
            for phrase in self.key_phrases_used[:10]:
                lines.append(f'- "{phrase}"\n')

        # Structural Patterns
        lines.append("\n---\n")
        lines.append("\n## Structural Patterns\n\n")
        lines.append(f"- **Average Length:** {self.average_word_count} words\n")
        lines.append(f"- **Average Paragraphs:** {self.average_paragraph_count:.1f}\n")
        question_pct = int(self.question_usage_rate * 100)
        lines.append(f"- **Question Usage:** {question_pct}% of posts include questions\n")

        if self.average_word_count >= 200 and self.average_word_count <= 250:
            lines.append("\n**Insight:** You favor mid-length posts (200-250 words)\n")
        elif self.average_word_count < 200:
            lines.append("\n**Insight:** You write concise posts (<200 words)\n")
        else:
            lines.append("\n**Insight:** You write detailed posts (>250 words)\n")

        # Writing Guidelines
        lines.append("\n---\n")
        lines.append("\n## Writing Guidelines\n")

        if self.dos:
            lines.append("\n### ✅ DO:\n\n")
            for do in self.dos:
                lines.append(f"- {do}\n")

        if self.donts:
            lines.append("\n### ❌ DON'T:\n\n")
            for dont in self.donts:
                lines.append(f"- {dont}\n")

        if self.examples:
            lines.append("\n---\n")
            lines.append("\n## Strong Examples\n")
            for example in self.examples:
                lines.append(f"\n**Example:**\n> {example}\n")

        lines.append("\n---\n")
        lines.append(
            "\n*Use this guide when creating future content to maintain voice consistency.*\n"
        )

        return "".join(lines)
