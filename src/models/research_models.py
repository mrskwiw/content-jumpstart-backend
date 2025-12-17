"""Data models for research tools"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ToneType(str, Enum):
    """Primary tone types"""

    ANALYTICAL = "analytical"
    AUTHORITATIVE = "authoritative"
    CASUAL = "casual"
    CONVERSATIONAL = "conversational"
    DIRECT = "direct"
    EMPATHETIC = "empathetic"
    ENTHUSIASTIC = "enthusiastic"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    TECHNICAL = "technical"
    WITTY = "witty"


class PersonalityTrait(str, Enum):
    """Personality traits"""

    APPROACHABLE = "approachable"
    BOLD = "bold"
    CONFIDENT = "confident"
    DATA_DRIVEN = "data_driven"
    DIRECT = "direct"
    EMPATHETIC = "empathetic"
    HUMBLE = "humble"
    INNOVATIVE = "innovative"
    MOTIVATING = "motivating"
    VULNERABLE = "vulnerable"


class SentenceAnalysis(BaseModel):
    """Analysis of sentence patterns"""

    avg_length: float = Field(description="Average sentence length in words")
    median_length: float = Field(description="Median sentence length")
    std_dev: float = Field(description="Standard deviation of sentence length")
    min_length: int = Field(description="Shortest sentence length")
    max_length: int = Field(description="Longest sentence length")
    variety_score: float = Field(description="Sentence variety (0-10)")


class PunctuationAnalysis(BaseModel):
    """Analysis of punctuation usage"""

    exclamation_marks: int = Field(description="Count of exclamation marks")
    questions: int = Field(description="Count of questions")
    em_dashes: int = Field(description="Count of em dashes")
    ellipses: int = Field(description="Count of ellipses")
    colons: int = Field(description="Count of colons")
    semicolons: int = Field(description="Count of semicolons")


class VocabularyAnalysis(BaseModel):
    """Analysis of word choice"""

    unique_words: int = Field(description="Count of unique words")
    total_words: int = Field(description="Total word count")
    lexical_diversity: float = Field(description="Unique/total ratio")
    avg_word_length: float = Field(description="Average word length")
    complex_words: int = Field(description="Words with 3+ syllables")


class OpeningPattern(BaseModel):
    """Pattern for opening hooks"""

    pattern_type: str = Field(description="Type of opening (question, stat, story, etc.)")
    example: str = Field(description="Example opening line")
    frequency: int = Field(description="How many times this pattern appears")


class SignaturePhrase(BaseModel):
    """Recurring phrase or expression"""

    phrase: str = Field(description="The signature phrase")
    count: int = Field(description="Number of occurrences")
    context: str = Field(description="Where it's typically used")


class CTAPattern(BaseModel):
    """Call-to-action pattern"""

    cta_type: str = Field(description="Type of CTA (question, invitation, etc.)")
    example: str = Field(description="Example CTA")
    frequency: int = Field(description="How often used")


class VoiceProfile(BaseModel):
    """Complete voice analysis profile"""

    # Summary
    summary: str = Field(description="2-3 sentence voice description")

    # Tone
    primary_tone: ToneType = Field(description="Primary tone")
    secondary_tone: Optional[ToneType] = Field(None, description="Secondary tone")
    formality_score: float = Field(description="Formality level (1-10)")
    confidence_score: float = Field(description="Confidence level (1-10)")

    # Personality
    personality_traits: List[PersonalityTrait] = Field(description="Key personality traits")

    # Writing patterns
    sentence_analysis: SentenceAnalysis
    punctuation_analysis: PunctuationAnalysis
    vocabulary_analysis: VocabularyAnalysis

    # Content patterns
    opening_patterns: List[OpeningPattern] = Field(description="How posts typically start")
    signature_phrases: List[SignaturePhrase] = Field(description="Recurring phrases")
    cta_patterns: List[CTAPattern] = Field(description="CTA styles")

    # Data usage
    uses_data: bool = Field(description="Whether data/statistics are used")
    data_frequency: str = Field(description="How often (frequently/sometimes/rarely)")
    data_examples: List[str] = Field(description="Examples of data usage")

    # Pronoun preferences
    pronoun_usage: Dict[str, int] = Field(description="I/we/you frequency")
    pronoun_focus: str = Field(description="Primary focus (you/we/I)")

    # Structure preferences
    avg_paragraph_length: float = Field(description="Average paragraph length")
    uses_bullets: bool = Field(description="Uses bullet points")
    uses_emojis: bool = Field(description="Uses emojis")
    uses_formatting: bool = Field(description="Uses bold/italic")

    # Readability
    readability_score: float = Field(description="Flesch Reading Ease (0-100)")
    reading_level: str = Field(description="Grade level description")

    # Recommendations
    consistency_score: float = Field(description="Voice consistency (0-10)")
    strengths: List[str] = Field(description="Voice strengths")
    improvement_areas: List[str] = Field(description="Areas to improve")


class VoiceGuide(BaseModel):
    """Voice style guide with examples"""

    profile: VoiceProfile

    # Do/Don't examples
    do_examples: List[str] = Field(description="Good examples of brand voice")
    dont_examples: List[str] = Field(description="Examples that don't match voice")

    # Writing guidelines
    guidelines: Dict[str, str] = Field(description="Writing guidelines by category")

    # Templates
    opening_templates: List[str] = Field(description="Opening hook templates")
    cta_templates: List[str] = Field(description="CTA templates")

    # Quality checklist
    checklist: List[str] = Field(description="Checklist for maintaining voice")
