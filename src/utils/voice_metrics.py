"""
Voice metrics analyzer for enhanced brand voice analysis.

Extracts objective metrics from content including:
- Flesch Reading Ease score (readability)
- Voice dimensions (formality, tone, perspective)
- Sentence variety analysis

Adapted from content-creator skill's brand_voice_analyzer.py
"""

import re
from typing import Dict, List


class VoiceMetrics:
    """
    Analyzes text for objective voice characteristics.

    Provides readability scoring, voice dimension detection, and sentence analysis
    to complement pattern-based voice analysis.
    """

    def __init__(self):
        """Initialize voice dimension keyword mappings."""
        self.voice_dimensions = {
            "formality": {
                "formal": [
                    "hereby",
                    "therefore",
                    "furthermore",
                    "pursuant",
                    "regarding",
                    "aforementioned",
                    "notwithstanding",
                    "heretofore",
                ],
                "professional": [
                    "expertise",
                    "solution",
                    "optimize",
                    "strategic",
                    "methodology",
                    "framework",
                    "implementation",
                    "comprehensive",
                ],
                "conversational": [
                    "you might",
                    "let's explore",
                    "we think",
                    "imagine if",
                    "here's the thing",
                    "bottom line",
                    "real talk",
                ],
                "casual": [
                    "hey",
                    "cool",
                    "awesome",
                    "stuff",
                    "yeah",
                    "gonna",
                    "wanna",
                    "pretty much",
                    "kind of",
                ],
            },
            "tone": {
                "authoritative": [
                    "proven",
                    "research shows",
                    "experts agree",
                    "data indicates",
                    "studies confirm",
                    "evidence suggests",
                    "guaranteed",
                ],
                "friendly": [
                    "happy",
                    "excited",
                    "love",
                    "enjoy",
                    "together",
                    "share",
                    "glad",
                    "welcome",
                    "appreciate",
                ],
                "innovative": [
                    "cutting-edge",
                    "revolutionary",
                    "breakthrough",
                    "disruptive",
                    "next-generation",
                    "pioneering",
                    "transformative",
                ],
                "educational": [
                    "learn",
                    "understand",
                    "discover",
                    "explore",
                    "guide",
                    "step-by-step",
                    "how to",
                    "tutorial",
                ],
            },
            "perspective": {
                "authoritative": [
                    "our research",
                    "we have found",
                    "our data",
                    "we recommend",
                    "our analysis",
                    "we believe",
                    "our expertise",
                ],
                "collaborative": [
                    "together we",
                    "let's work",
                    "we can help",
                    "partner with",
                    "join us",
                    "work together",
                    "team up",
                ],
                "conversational": [
                    "you might",
                    "what if you",
                    "have you ever",
                    "imagine",
                    "think about",
                    "consider this",
                    "here's a question",
                ],
            },
        }

    def calculate_readability(self, text: str) -> float:
        """
        Calculate Flesch Reading Ease score.

        Score interpretation:
        - 90-100: Very easy (5th grade)
        - 80-89: Easy (6th grade)
        - 70-79: Fairly easy (7th grade)
        - 60-69: Standard (8th-9th grade)
        - 50-59: Fairly difficult (10th-12th grade)
        - 30-49: Difficult (college)
        - 0-29: Very difficult (college graduate)

        Args:
            text: Content to analyze

        Returns:
            Score from 0-100 (higher = easier to read)
        """
        if not text or not text.strip():
            return 0.0

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Split into words
        words = text.split()

        if len(sentences) == 0 or len(words) == 0:
            return 0.0

        # Count syllables
        total_syllables = sum(self._count_syllables(word) for word in words)

        # Calculate averages
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = total_syllables / len(words)

        # Flesch Reading Ease formula
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)

        # Clamp to 0-100 range
        return max(0.0, min(100.0, score))

    def _count_syllables(self, word: str) -> int:
        """
        Count syllables in a word (simplified algorithm).

        Args:
            word: Word to analyze

        Returns:
            Estimated syllable count (minimum 1)
        """
        word = word.lower().strip()

        # Remove non-alphabetic characters
        word = re.sub(r"[^a-z]", "", word)

        if not word:
            return 1

        vowels = "aeiou"
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e' at end
        if word.endswith("e") and syllable_count > 1:
            syllable_count -= 1

        # Minimum 1 syllable per word
        return max(1, syllable_count)

    def analyze_voice_dimensions(self, text: str) -> Dict[str, Dict]:
        """
        Analyze text for voice dimensions using keyword detection.

        Args:
            text: Content to analyze

        Returns:
            Dictionary with dimension analysis:
            {
                'formality': {'dominant': 'professional', 'scores': {...}},
                'tone': {'dominant': 'friendly', 'scores': {...}},
                'perspective': {'dominant': 'collaborative', 'scores': {...}}
            }
        """
        text_lower = text.lower()
        results = {}

        for dimension, categories in self.voice_dimensions.items():
            dim_scores = {}

            # Count keyword matches for each category
            for category, keywords in categories.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                dim_scores[category] = score

            # Determine dominant category
            total_matches = sum(dim_scores.values())
            if total_matches > 0:
                dominant = max(dim_scores, key=dim_scores.get)
                results[dimension] = {
                    "dominant": dominant,
                    "scores": dim_scores,
                    "total_matches": total_matches,
                }
            else:
                # No matches found - use neutral default
                results[dimension] = {
                    "dominant": "neutral",
                    "scores": dim_scores,
                    "total_matches": 0,
                }

        return results

    def analyze_sentence_variety(self, text: str) -> Dict:
        """
        Analyze sentence structure variety.

        Args:
            text: Content to analyze

        Returns:
            Dictionary with sentence analysis:
            {
                'average_length': 15.3,
                'variety': 'medium',  # 'low' | 'medium' | 'high'
                'count': 10,
                'lengths': [12, 18, 15, ...]
            }
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"average_length": 0, "variety": "low", "count": 0, "lengths": []}

        # Calculate word count per sentence
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # Calculate variety based on unique length counts
        unique_lengths = len(set(lengths))

        if unique_lengths < 3:
            variety = "low"
        elif unique_lengths < 5:
            variety = "medium"
        else:
            variety = "high"

        return {
            "average_length": round(avg_length, 1),
            "variety": variety,
            "count": len(sentences),
            "lengths": lengths,
        }

    def generate_recommendations(
        self, readability_score: float, sentence_variety: str, voice_dimensions: Dict
    ) -> List[str]:
        """
        Generate recommendations based on voice metrics.

        Args:
            readability_score: Flesch Reading Ease score
            sentence_variety: 'low' | 'medium' | 'high'
            voice_dimensions: Voice dimension analysis results

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Readability recommendations
        if readability_score < 30:
            recommendations.append(
                "Consider simplifying language - current readability is college graduate level"
            )
        elif readability_score < 50:
            recommendations.append(
                "Content is fairly difficult - consider shorter sentences and simpler words"
            )
        elif readability_score > 80:
            recommendations.append(
                "Content is very easy to read - ensure this matches your audience's expectations"
            )

        # Sentence variety recommendations
        if sentence_variety == "low":
            recommendations.append("Vary sentence length for better flow and engagement")
        elif sentence_variety == "high":
            recommendations.append("Excellent sentence variety - maintains reader interest")

        # Voice consistency recommendations
        formality = voice_dimensions.get("formality", {})
        if formality.get("total_matches", 0) > 0:
            dominant = formality.get("dominant")
            if dominant == "formal" and readability_score > 70:
                recommendations.append(
                    "Formal language with high readability - ensure this matches brand voice"
                )
            elif dominant == "casual" and readability_score < 60:
                recommendations.append(
                    "Casual tone with complex sentences - consider simplifying for consistency"
                )

        return recommendations

    def analyze_all(self, text: str) -> Dict:
        """
        Run all voice metrics analyses on text.

        Args:
            text: Content to analyze

        Returns:
            Complete voice metrics dictionary
        """
        readability = self.calculate_readability(text)
        dimensions = self.analyze_voice_dimensions(text)
        sentence_analysis = self.analyze_sentence_variety(text)
        recommendations = self.generate_recommendations(
            readability, sentence_analysis["variety"], dimensions
        )

        return {
            "readability_score": readability,
            "voice_dimensions": dimensions,
            "sentence_analysis": sentence_analysis,
            "recommendations": recommendations,
        }
