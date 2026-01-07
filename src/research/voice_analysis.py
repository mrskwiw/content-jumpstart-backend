"""Voice Analysis Tool - Analyzes content samples to extract voice patterns

This tool analyzes 10-20 content samples to create a comprehensive voice profile
including tone, sentence patterns, vocabulary, and writing style.

Price: $400
Automation Level: 95%
Time: 2-3 minutes automated + 30 min review
"""

import json
import re
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.research_models import (
    CTAPattern,
    OpeningPattern,
    PersonalityTrait,
    PunctuationAnalysis,
    SentenceAnalysis,
    SignaturePhrase,
    ToneType,
    VocabularyAnalysis,
    VoiceGuide,
    VoiceProfile,
)
from ..utils.logger import logger
from ..validators.research_input_validator import (
    ResearchInputValidator,
    validate_content_samples,
)
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
from ..utils.anthropic_client import get_default_client

# Try to import textstat for readability scoring
try:
    import textstat

    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False
    logger.warning("textstat not installed - readability scoring disabled")


class VoiceAnalyzer(ResearchTool, CommonValidationMixin):
    """Analyzes content samples to extract voice and style patterns

    Takes 10-20 content samples and produces:
    - Voice profile (tone, formality, personality)
    - Writing pattern analysis (sentence structure, vocabulary)
    - Do/Don't style guide
    - Voice consistency recommendations
    """

    def __init__(self, project_id: str, config: Dict[str, Any] = None):
        """Initialize voice analyzer with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "voice_analysis"

    @property
    def price(self) -> int:
        return 400

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate voice analysis inputs with comprehensive security checks (TR-019)

        Security Features:
        - Max length checks (prevent DOS attacks)
        - Prompt injection sanitization
        - Type validation
        - Field presence validation

        Required:
        - content_samples: List of text samples (3-20 pieces)

        Args:
            inputs: Input dictionary

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # SECURITY: Validate content samples list (3-30 samples)
        # Using validate_content_samples convenience function
        inputs["content_samples"] = validate_content_samples(
            inputs.get("content_samples"),
            validator=self.validator,
        )

        # Enforce max 30 samples for performance (trim if needed)
        if len(inputs["content_samples"]) > 30:
            logger.warning(
                f"Got {len(inputs['content_samples'])} samples, using first 30 for analysis"
            )
            inputs["content_samples"] = inputs["content_samples"][:30]

        # Validate each sample is either string or dict with text field
        validated_samples = []
        for i, sample in enumerate(inputs["content_samples"]):
            if isinstance(sample, str):
                # Already validated by validate_content_samples
                validated_samples.append(sample)
            elif isinstance(sample, dict):
                # Extract and validate text field
                if "text" not in sample:
                    raise ValueError(f"Sample {i} missing 'text' field")
                text = self.validator.validate_text(
                    sample["text"],
                    field_name=f"content_sample_{i}.text",
                    min_length=50,
                    max_length=5000,
                    required=True,
                    sanitize=True,
                )
                validated_samples.append(text)
            else:
                raise ValueError(
                    f"Sample {i} must be string or dict with 'text' field, got {type(sample).__name__}"
                )

        inputs["content_samples"] = validated_samples

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> VoiceGuide:
        """Execute voice analysis

        Args:
            inputs: Validated inputs with content_samples

        Returns:
            VoiceGuide with complete analysis
        """
        # Extract text from samples
        samples = inputs["content_samples"][:30]  # Max 30 samples
        texts = []

        for sample in samples:
            if isinstance(sample, str):
                texts.append(sample.strip())
            elif isinstance(sample, dict):
                texts.append(sample["text"].strip())

        logger.info(f"Analyzing {len(texts)} content samples")

        # Run all analyses
        sentence_analysis = self._analyze_sentences(texts)
        punctuation_analysis = self._analyze_punctuation(texts)
        vocabulary_analysis = self._analyze_vocabulary(texts)
        opening_patterns = self._analyze_openings(texts)
        signature_phrases = self._extract_signature_phrases(texts)
        cta_patterns = self._analyze_ctas(texts)
        pronoun_usage = self._analyze_pronouns(texts)
        data_usage = self._analyze_data_usage(texts)
        readability = self._analyze_readability(texts)

        # Use Claude to identify tone and personality
        tone_personality = self._identify_tone_and_personality(texts)

        # Calculate consistency
        consistency_score = self._calculate_consistency(texts)

        # Build voice profile
        voice_profile = VoiceProfile(
            summary=tone_personality["summary"],
            primary_tone=tone_personality["primary_tone"],
            secondary_tone=tone_personality.get("secondary_tone"),
            formality_score=tone_personality["formality_score"],
            confidence_score=tone_personality["confidence_score"],
            personality_traits=tone_personality["personality_traits"],
            sentence_analysis=sentence_analysis,
            punctuation_analysis=punctuation_analysis,
            vocabulary_analysis=vocabulary_analysis,
            opening_patterns=opening_patterns,
            signature_phrases=signature_phrases,
            cta_patterns=cta_patterns,
            uses_data=data_usage["uses_data"],
            data_frequency=data_usage["frequency"],
            data_examples=data_usage["examples"],
            pronoun_usage=pronoun_usage["counts"],
            pronoun_focus=pronoun_usage["focus"],
            avg_paragraph_length=self._calculate_avg_paragraph_length(texts),
            uses_bullets=self._uses_bullets(texts),
            uses_emojis=self._uses_emojis(texts),
            uses_formatting=self._uses_formatting(texts),
            readability_score=readability["score"],
            reading_level=readability["level"],
            consistency_score=consistency_score,
            strengths=self._identify_strengths(tone_personality, sentence_analysis),
            improvement_areas=self._identify_improvements(consistency_score),
        )

        # Generate style guide
        voice_guide = self._generate_style_guide(voice_profile, texts)

        return voice_guide

    def generate_reports(self, voice_guide: VoiceGuide) -> Dict[str, Path]:
        """Generate voice analysis reports

        Creates:
        - JSON: Machine-readable voice profile
        - Markdown: Human-readable report
        - Text: Simple style guide

        Args:
            voice_guide: Complete voice guide

        Returns:
            Dictionary of format -> file path
        """
        outputs = {}

        # Save JSON
        json_data = voice_guide.model_dump()
        outputs["json"] = self._save_json(json_data, "voice_profile.json")

        # Generate Markdown report
        markdown_report = self._create_markdown_report(voice_guide)
        outputs["markdown"] = self._save_markdown(markdown_report, "voice_analysis_report.md")

        # Generate simple text guide
        text_guide = self._create_text_guide(voice_guide)
        outputs["text"] = self._save_text(text_guide, "voice_guide.txt")

        logger.info(f"Generated {len(outputs)} report formats")
        return outputs

    # ==================== Analysis Methods ====================

    def _analyze_sentences(self, texts: List[str]) -> SentenceAnalysis:
        """Analyze sentence patterns"""
        all_sentences = []

        for text in texts:
            # Split into sentences (simple approach)
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]
            all_sentences.extend(sentences)

        # Calculate sentence lengths
        lengths = [len(s.split()) for s in all_sentences]

        if not lengths:
            return SentenceAnalysis(
                avg_length=0,
                median_length=0,
                std_dev=0,
                min_length=0,
                max_length=0,
                variety_score=0,
            )

        avg_length = statistics.mean(lengths)
        median_length = statistics.median(lengths)
        std_dev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        min_length = min(lengths)
        max_length = max(lengths)

        # Variety score (higher std_dev = more variety)
        variety_score = min(10, (std_dev / avg_length) * 20) if avg_length > 0 else 0

        return SentenceAnalysis(
            avg_length=round(avg_length, 1),
            median_length=round(median_length, 1),
            std_dev=round(std_dev, 1),
            min_length=min_length,
            max_length=max_length,
            variety_score=round(variety_score, 1),
        )

    def _analyze_punctuation(self, texts: List[str]) -> PunctuationAnalysis:
        """Analyze punctuation usage"""
        combined_text = " ".join(texts)

        return PunctuationAnalysis(
            exclamation_marks=combined_text.count("!"),
            questions=combined_text.count("?"),
            em_dashes=combined_text.count("—") + combined_text.count("--"),
            ellipses=combined_text.count("..."),
            colons=combined_text.count(":"),
            semicolons=combined_text.count(";"),
        )

    def _analyze_vocabulary(self, texts: List[str]) -> VocabularyAnalysis:
        """Analyze word choice"""
        combined_text = " ".join(texts).lower()

        # Remove punctuation for word counting
        words = re.findall(r"\b[a-z]+\b", combined_text)

        total_words = len(words)
        unique_words = len(set(words))
        lexical_diversity = unique_words / total_words if total_words > 0 else 0

        # Average word length
        avg_word_length = statistics.mean([len(w) for w in words]) if words else 0

        # Complex words (3+ syllables - rough approximation)
        complex_words = len([w for w in words if len(w) >= 9])

        return VocabularyAnalysis(
            unique_words=unique_words,
            total_words=total_words,
            lexical_diversity=round(lexical_diversity, 3),
            avg_word_length=round(avg_word_length, 1),
            complex_words=complex_words,
        )

    def _analyze_openings(self, texts: List[str]) -> List[OpeningPattern]:
        """Analyze how posts typically open"""
        openings = []

        for text in texts:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                first_line = lines[0]
                openings.append(first_line[:100])  # First 100 chars

        # Classify opening types
        patterns = {"question": 0, "statistic": 0, "statement": 0, "quote": 0, "story": 0}

        examples = {}

        for opening in openings:
            if opening.strip().endswith("?"):
                patterns["question"] += 1
                if "question" not in examples:
                    examples["question"] = opening
            elif re.search(r"\d+%|\d+x|\$\d+", opening):
                patterns["statistic"] += 1
                if "statistic" not in examples:
                    examples["statistic"] = opening
            elif opening.startswith('"') or opening.startswith("'"):
                patterns["quote"] += 1
                if "quote" not in examples:
                    examples["quote"] = opening
            elif any(word in opening.lower() for word in ["remember", "story", "when", "time"]):
                patterns["story"] += 1
                if "story" not in examples:
                    examples["story"] = opening
            else:
                patterns["statement"] += 1
                if "statement" not in examples:
                    examples["statement"] = opening

        # Convert to OpeningPattern objects
        result = []
        for pattern_type, count in patterns.items():
            if count > 0:
                result.append(
                    OpeningPattern(
                        pattern_type=pattern_type,
                        example=examples.get(pattern_type, ""),
                        frequency=count,
                    )
                )

        # Sort by frequency
        result.sort(key=lambda x: x.frequency, reverse=True)

        return result

    def _extract_signature_phrases(self, texts: List[str]) -> List[SignaturePhrase]:
        """Extract recurring phrases (3-5 words)"""
        combined_text = " ".join(texts).lower()

        # Extract 3-5 word phrases
        words = re.findall(r"\b\w+\b", combined_text)

        phrases = []
        for n in [3, 4, 5]:  # 3-gram, 4-gram, 5-gram
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i : i + n])
                phrases.append(phrase)

        # Count occurrences
        phrase_counts = Counter(phrases)

        # Filter to phrases that appear 3+ times
        signature = [
            SignaturePhrase(phrase=phrase, count=count, context="Opening or transition")
            for phrase, count in phrase_counts.most_common(10)
            if count >= 3
        ]

        return signature[:5]  # Top 5

    def _analyze_ctas(self, texts: List[str]) -> List[CTAPattern]:
        """Analyze call-to-action patterns"""
        ctas = []

        for text in texts:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                last_line = lines[-1]
                ctas.append(last_line)

        # Classify CTA types
        patterns = {"question": [], "invitation": [], "directive": [], "link": []}

        for cta in ctas:
            if cta.endswith("?"):
                patterns["question"].append(cta)
            elif any(
                word in cta.lower() for word in ["comment", "share", "reply", "dm", "message"]
            ):
                patterns["invitation"].append(cta)
            elif cta.startswith(("Learn", "Check", "Read", "Download", "Sign", "Get")):
                patterns["directive"].append(cta)
            elif "http" in cta or "link" in cta.lower():
                patterns["link"].append(cta)

        # Convert to CTAPattern objects
        result = []
        for cta_type, examples in patterns.items():
            if examples:
                result.append(
                    CTAPattern(
                        cta_type=cta_type,
                        example=examples[0][:100],  # First example, max 100 chars
                        frequency=len(examples),
                    )
                )

        result.sort(key=lambda x: x.frequency, reverse=True)
        return result

    def _analyze_pronouns(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze pronoun usage"""
        combined_text = " ".join(texts).lower()

        counts = {
            "I": combined_text.count(" i ") + combined_text.count("i'"),
            "we": combined_text.count(" we ") + combined_text.count("we'"),
            "you": combined_text.count(" you ") + combined_text.count("you'"),
        }

        total = sum(counts.values())

        if total > 0:
            focus = max(counts, key=counts.get).lower()
        else:
            focus = "neutral"

        return {"counts": counts, "focus": focus}

    def _analyze_data_usage(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze use of data and statistics"""
        combined_text = " ".join(texts)

        # Find data patterns
        data_patterns = re.findall(
            r"\d+%|\d+x|\$\d[\d,]*|\d+\s*million|\d+\s*billion", combined_text
        )

        uses_data = len(data_patterns) > 0

        if len(data_patterns) >= len(texts):
            frequency = "frequently"
        elif len(data_patterns) >= len(texts) / 2:
            frequency = "sometimes"
        elif uses_data:
            frequency = "rarely"
        else:
            frequency = "never"

        examples = list(set(data_patterns))[:5]  # Up to 5 unique examples

        return {"uses_data": uses_data, "frequency": frequency, "examples": examples}

    def _analyze_readability(self, texts: List[str]) -> Dict[str, Any]:
        """Calculate readability score"""
        if not HAS_TEXTSTAT:
            return {"score": 60.0, "level": "High school level (estimated)"}  # Default middle score

        combined_text = " ".join(texts)

        try:
            # Flesch Reading Ease (0-100, higher = easier)
            score = textstat.flesch_reading_ease(combined_text)

            # Classify reading level
            if score >= 90:
                level = "5th grade level (very easy)"
            elif score >= 80:
                level = "6th grade level (easy)"
            elif score >= 70:
                level = "7th grade level (fairly easy)"
            elif score >= 60:
                level = "8th-9th grade level (plain English)"
            elif score >= 50:
                level = "10th-12th grade level (fairly difficult)"
            elif score >= 30:
                level = "College level (difficult)"
            else:
                level = "Graduate level (very difficult)"

            return {"score": round(score, 1), "level": level}
        except (ZeroDivisionError, ValueError, TypeError):
            return {"score": 60.0, "level": "High school level (estimated)"}

    def _identify_tone_and_personality(self, texts: List[str]) -> Dict[str, Any]:
        """Use Claude to identify tone and personality traits"""
        # Sample 3-5 representative texts
        sample_texts = texts[:5]

        prompt = f"""Analyze the following content samples and identify the writing voice characteristics:

SAMPLES:
---
{chr(10).join([f"Sample {i+1}:{chr(10)}{text}{chr(10)}---" for i, text in enumerate(sample_texts)])}

Provide analysis in JSON format:
{{
    "summary": "2-3 sentence description of the voice",
    "primary_tone": "one of: analytical, authoritative, casual, conversational, direct, empathetic, enthusiastic, formal, friendly, professional, technical, witty",
    "secondary_tone": "optional secondary tone",
    "formality_score": 1-10,
    "confidence_score": 1-10,
    "personality_traits": ["list of 2-4 traits from: approachable, bold, confident, data_driven, direct, empathetic, humble, innovative, motivating, vulnerable"]
}}

Focus on objective patterns in the writing, not what the content is about."""

        try:
            client = get_default_client()
            content = client.create_message(
                messages=[{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.3
            )
            # Find JSON in response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Convert strings to enums
                result["primary_tone"] = ToneType(result["primary_tone"])
                if result.get("secondary_tone"):
                    result["secondary_tone"] = ToneType(result["secondary_tone"])

                result["personality_traits"] = [
                    PersonalityTrait(trait) for trait in result.get("personality_traits", [])
                ]

                return result

        except Exception as e:
            logger.warning(f"Claude analysis failed: {e}, using fallback")

        # Fallback to rule-based analysis
        return {
            "summary": "Professional, direct communication style with clear value propositions.",
            "primary_tone": ToneType.PROFESSIONAL,
            "secondary_tone": ToneType.DIRECT,
            "formality_score": 6.0,
            "confidence_score": 7.5,
            "personality_traits": [PersonalityTrait.DIRECT, PersonalityTrait.CONFIDENT],
        }

    def _calculate_consistency(self, texts: List[str]) -> float:
        """Calculate voice consistency score (0-10)"""
        # Simple heuristic: variance in sentence length
        all_lengths = []

        for text in texts:
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]
            lengths = [len(s.split()) for s in sentences]
            if lengths:
                all_lengths.append(statistics.mean(lengths))

        if len(all_lengths) < 2:
            return 8.0  # Default if not enough data

        # Lower variance = higher consistency
        variance = statistics.variance(all_lengths)
        consistency = max(0, 10 - (variance / 5))

        return round(consistency, 1)

    def _calculate_avg_paragraph_length(self, texts: List[str]) -> float:
        """Calculate average paragraph length"""
        all_paragraphs = []

        for text in texts:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            all_paragraphs.extend(paragraphs)

        if not all_paragraphs:
            return 0.0

        lengths = [len(p.split()) for p in all_paragraphs]
        return round(statistics.mean(lengths), 1)

    def _uses_bullets(self, texts: List[str]) -> bool:
        """Check if content uses bullet points"""
        combined = " ".join(texts)
        return bool(re.search(r"^\s*[-•*]", combined, re.MULTILINE))

    def _uses_emojis(self, texts: List[str]) -> bool:
        """Check if content uses emojis"""
        combined = "".join(texts)
        # Simple check for common emojis
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags
            "]+",
            flags=re.UNICODE,
        )

        return bool(emoji_pattern.search(combined))

    def _uses_formatting(self, texts: List[str]) -> bool:
        """Check if content uses bold/italic formatting"""
        combined = " ".join(texts)
        return bool(re.search(r"\*\*|__|\*|_", combined))

    def _identify_strengths(
        self, tone_personality: Dict[str, Any], sentence_analysis: SentenceAnalysis
    ) -> List[str]:
        """Identify voice strengths"""
        strengths = []

        if sentence_analysis.variety_score >= 7:
            strengths.append("Strong sentence variety keeps readers engaged")

        if tone_personality["confidence_score"] >= 7.5:
            strengths.append("Confident, authoritative tone builds trust")

        if PersonalityTrait.DATA_DRIVEN in tone_personality.get("personality_traits", []):
            strengths.append("Data-driven approach adds credibility")

        if not strengths:
            strengths.append("Clear, professional communication style")

        return strengths

    def _identify_improvements(self, consistency_score: float) -> List[str]:
        """Identify areas for improvement"""
        improvements = []

        if consistency_score < 7:
            improvements.append("Voice consistency varies - use this guide to maintain tone")

        if not improvements:
            improvements.append("Maintain current voice patterns for consistency")

        return improvements

    def _generate_style_guide(self, voice_profile: VoiceProfile, texts: List[str]) -> VoiceGuide:
        """Generate complete style guide with do/don't examples"""

        # Extract good examples (varied selection)
        do_examples = []
        for i, text in enumerate(texts[:3]):
            # Get first paragraph or sentence
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                do_examples.append(lines[0][:200])

        # Generate don't examples (contrasts to current voice)
        dont_examples = self._generate_dont_examples(voice_profile)

        # Generate guidelines
        guidelines = {
            "tone": f"Maintain {voice_profile.primary_tone} tone with {voice_profile.formality_score}/10 formality",
            "sentence_length": f"Aim for {voice_profile.sentence_analysis.avg_length:.0f}-word average sentences",
            "data_usage": f"Include data/stats {voice_profile.data_frequency}",
            "openings": f"Start with {voice_profile.opening_patterns[0].pattern_type if voice_profile.opening_patterns else 'strong hook'}",
            "ctas": f"End with {voice_profile.cta_patterns[0].cta_type if voice_profile.cta_patterns else 'clear CTA'}",
        }

        # Generate templates
        opening_templates = [pattern.example for pattern in voice_profile.opening_patterns[:3]]

        cta_templates = [pattern.example for pattern in voice_profile.cta_patterns[:3]]

        # Checklist
        checklist = [
            f"✓ Tone is {voice_profile.primary_tone}",
            f"✓ Formality level is {voice_profile.formality_score}/10",
            f"✓ Sentence length averages {voice_profile.sentence_analysis.avg_length:.0f} words",
            "✓ Opening hook matches pattern",
            "✓ Clear CTA at the end",
        ]

        return VoiceGuide(
            profile=voice_profile,
            do_examples=do_examples,
            dont_examples=dont_examples,
            guidelines=guidelines,
            opening_templates=opening_templates,
            cta_templates=cta_templates,
            checklist=checklist,
        )

    def _generate_dont_examples(self, voice_profile: VoiceProfile) -> List[str]:
        """Generate contrasting don't examples"""
        dont_examples = []

        # Contrast formality
        if voice_profile.formality_score < 5:
            dont_examples.append(
                "We are pleased to announce that our organization has achieved "
                "significant milestones in the aforementioned quarter."
            )
        else:
            dont_examples.append("OMG you guys!! This is literally the BEST thing ever!! 🎉🎉")

        # Contrast confidence
        if voice_profile.confidence_score >= 7:
            dont_examples.append(
                "I think maybe we might have possibly found a solution, "
                "but I'm not entirely sure if it will work..."
            )

        return dont_examples

    # ==================== Report Generation ====================

    def _create_markdown_report(self, voice_guide: VoiceGuide) -> str:
        """Create comprehensive Markdown report"""
        profile = voice_guide.profile

        report = f"""# Voice Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Executive Summary

{profile.summary}

**Primary Tone:** {profile.primary_tone.value.title()}
{f"**Secondary Tone:** {profile.secondary_tone.value.title()}" if profile.secondary_tone else ""}
**Formality:** {profile.formality_score}/10
**Confidence:** {profile.confidence_score}/10

**Personality Traits:**
{chr(10).join([f"- {trait.value.replace('_', ' ').title()}" for trait in profile.personality_traits])}

---

## Writing Patterns

### Sentence Structure
- **Average Length:** {profile.sentence_analysis.avg_length} words
- **Variety Score:** {profile.sentence_analysis.variety_score}/10
- **Range:** {profile.sentence_analysis.min_length}-{profile.sentence_analysis.max_length} words

### Vocabulary
- **Lexical Diversity:** {profile.vocabulary_analysis.lexical_diversity:.1%}
- **Average Word Length:** {profile.vocabulary_analysis.avg_word_length} letters
- **Unique Words:** {profile.vocabulary_analysis.unique_words:,}

### Readability
- **Flesch Score:** {profile.readability_score}/100
- **Reading Level:** {profile.reading_level}

---

## Content Patterns

### Opening Hooks
{chr(10).join([f"{i+1}. **{p.pattern_type.title()}** ({p.frequency}x): {p.example}" for i, p in enumerate(profile.opening_patterns)])}

### Calls-to-Action
{chr(10).join([f"{i+1}. **{p.cta_type.title()}** ({p.frequency}x): {p.example}" for i, p in enumerate(profile.cta_patterns)])}

### Signature Phrases
{chr(10).join([f"- '{p.phrase}' ({p.count}x)" for p in profile.signature_phrases]) if profile.signature_phrases else "- No recurring phrases detected"}

### Data Usage
- **Frequency:** {profile.data_frequency.title()}
- **Examples:** {', '.join(profile.data_examples) if profile.data_examples else 'None'}

---

## Voice Consistency

**Consistency Score:** {profile.consistency_score}/10

### Strengths
{chr(10).join([f"✓ {s}" for s in profile.strengths])}

### Improvement Areas
{chr(10).join([f"• {i}" for i in profile.improvement_areas])}

---

## Style Guide

### DO Write Like This:
{chr(10).join([f'> {ex}' for ex in voice_guide.do_examples])}

### DON'T Write Like This:
{chr(10).join([f'> {ex}' for ex in voice_guide.dont_examples])}

### Guidelines

{chr(10).join([f"**{key.title()}:** {value}" for key, value in voice_guide.guidelines.items()])}

### Quality Checklist

{chr(10).join(voice_guide.checklist)}

---

## Recommendations

1. **Maintain Consistency:** Use this guide for all future content to maintain {profile.consistency_score}/10 consistency
2. **Opening Hooks:** Rotate between {', '.join([p.pattern_type for p in profile.opening_patterns[:3]])} patterns
3. **Voice Calibration:** Review this guide quarterly to ensure voice evolution stays on-brand

---

*This voice analysis is based on {len(voice_guide.do_examples)} content samples and provides a comprehensive profile for maintaining brand voice consistency.*
"""
        return report

    def _create_text_guide(self, voice_guide: VoiceGuide) -> str:
        """Create simple text guide"""
        profile = voice_guide.profile

        guide = f"""BRAND VOICE GUIDE
{'='*60}

VOICE SUMMARY
{profile.summary}

TONE: {profile.primary_tone.value.title()}
FORMALITY: {profile.formality_score}/10
CONFIDENCE: {profile.confidence_score}/10

{'='*60}

QUICK GUIDELINES
{'='*60}

{chr(10).join([f"{key.upper()}: {value}" for key, value in voice_guide.guidelines.items()])}

{'='*60}

DO WRITE LIKE THIS:
{'='*60}

{chr(10).join([f'{i+1}. {ex}{chr(10)}' for i, ex in enumerate(voice_guide.do_examples)])}

{'='*60}

DON'T WRITE LIKE THIS:
{'='*60}

{chr(10).join([f'{i+1}. {ex}{chr(10)}' for i, ex in enumerate(voice_guide.dont_examples)])}

{'='*60}

QUALITY CHECKLIST:
{chr(10).join(voice_guide.checklist)}

{'='*60}
End of Voice Guide
"""
        return guide
