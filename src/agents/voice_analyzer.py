"""Voice pattern analyzer for enhanced brand voice guide generation"""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List

from ..config.brand_frameworks import infer_archetype_from_voice_dimensions
from ..models.client_brief import ClientBrief
from ..models.post import Post
from ..models.voice_guide import EnhancedVoiceGuide, VoicePattern
from ..utils.logger import logger
from ..utils.voice_metrics import VoiceMetrics


class VoiceAnalyzer:
    """Analyzes generated posts to extract voice patterns"""

    def __init__(self):
        """Initialize voice analyzer with metrics calculator."""
        self.voice_metrics = VoiceMetrics()

    def analyze_voice_patterns(
        self, posts: List[Post], client_brief: ClientBrief
    ) -> EnhancedVoiceGuide:
        """Main analysis method"""
        logger.info(f"Analyzing {len(posts)} posts")

        hooks = [self._extract_hook(p.content) for p in posts]
        hook_patterns = self._cluster_patterns(hooks, "opening")

        transitions = []
        for post in posts:
            transitions.extend(self._extract_transitions(post.content))
        transition_patterns = self._cluster_patterns(transitions, "transition")

        ctas = [self._extract_cta(p.content) for p in posts if p.has_cta]
        cta_patterns = self._cluster_patterns(ctas, "cta")

        all_text = " ".join([p.content for p in posts])
        key_phrases = self._find_recurring_ngrams(all_text, min_freq=3)

        avg_words = sum(p.word_count for p in posts) / len(posts)
        avg_paragraphs = self._calculate_avg_paragraphs(posts)
        question_rate = sum(1 for p in posts if "?" in p.content) / len(posts)

        tone_score = self._calculate_tone_consistency(posts, client_brief)
        dos = self._generate_dos(hook_patterns, transition_patterns, cta_patterns)
        donts = self._generate_donts(posts, client_brief)
        examples = self._select_best_examples(posts, hook_patterns)
        dominant_tones = self._extract_dominant_tones(posts, client_brief)

        # NEW: Calculate voice metrics from content-creator skill
        logger.info("Calculating advanced voice metrics...")
        readability_score = self.voice_metrics.calculate_readability(all_text)
        voice_dimensions = self.voice_metrics.analyze_voice_dimensions(all_text)
        sentence_analysis = self.voice_metrics.analyze_sentence_variety(all_text)

        # NEW: Determine brand archetype
        archetype = self._determine_archetype(voice_dimensions, client_brief)

        # NEW: Add readability recommendations to dos/donts
        if readability_score < 50:
            donts.append("DON'T: Use overly complex sentences (consider simpler language)")
        elif readability_score > 80:
            dos.append("DO: Maintain accessible, easy-to-read language")

        if sentence_analysis["variety"] == "low":
            dos.append("DO: Vary sentence length for better engagement")

        logger.info(
            f"Voice analysis complete - Archetype: {archetype}, Readability: {readability_score:.1f}"
        )

        return EnhancedVoiceGuide(
            company_name=client_brief.company_name,
            generated_from_posts=len(posts),
            dominant_tones=dominant_tones,
            tone_consistency_score=tone_score,
            common_opening_hooks=hook_patterns[:5],
            common_transitions=transition_patterns[:5],
            common_ctas=cta_patterns[:5],
            key_phrases_used=key_phrases,
            average_word_count=int(avg_words),
            average_paragraph_count=avg_paragraphs,
            question_usage_rate=question_rate,
            dos=dos,
            donts=donts,
            examples=examples,
            # NEW: Voice metrics fields
            average_readability_score=readability_score,
            voice_dimensions=voice_dimensions,
            sentence_variety=sentence_analysis["variety"],
            voice_archetype=archetype,
        )

    def analyze_voice_samples(
        self, samples: List[str], client_name: str, source: str = "mixed"
    ) -> EnhancedVoiceGuide:
        """
        Analyze client's existing content samples for authentic voice

        This method analyzes real client samples (not generated content) to create
        a voice guide that represents their true writing style.

        Args:
            samples: List of text samples (each 100-2000 words)
            client_name: Client name
            source: Source type (linkedin, blog, twitter, email, mixed)

        Returns:
            Voice guide based on real client samples
        """
        from datetime import datetime

        # Convert samples to Post objects for analysis
        mock_posts = [
            Post(
                content=sample,
                template_id=0,  # Not from a template
                template_name="client_sample",
                variant=idx + 1,
                client_name=client_name,
            )
            for idx, sample in enumerate(samples)
        ]

        # Create minimal brief for analysis
        from src.models.client_brief import ClientBrief

        minimal_brief = ClientBrief(
            company_name=client_name,
            business_description=f"Analyzing uploaded samples from {source}",
            ideal_customer="Unknown - inferring from samples",
            main_problem_solved="Unknown",
        )

        # Use existing voice analysis logic
        voice_guide = self.analyze_voice_patterns(posts=mock_posts, client_brief=minimal_brief)

        # Mark as sample-based (not generated)
        voice_guide.source = "client_samples"
        voice_guide.sample_count = len(samples)
        voice_guide.sample_source = source
        voice_guide.sample_upload_date = datetime.now()

        # Analyze emoji patterns
        combined_text = "\n\n".join(samples)
        emoji_freq, common_emojis = self._analyze_emoji_patterns(combined_text)
        voice_guide.emoji_frequency = emoji_freq
        voice_guide.common_emojis = common_emojis

        # Analyze jargon
        jargon_ratio, industry_terms = self._analyze_jargon(combined_text)
        voice_guide.jargon_ratio = jargon_ratio
        voice_guide.industry_terms = industry_terms

        return voice_guide

    def _analyze_emoji_patterns(self, text: str) -> tuple[float, List[str]]:
        """
        Analyze emoji usage in text

        Returns:
            Tuple of (emojis_per_100_words, list_of_common_emojis)
        """
        import re
        from collections import Counter

        # Emoji regex pattern (basic Unicode ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )

        emojis = emoji_pattern.findall(text)
        word_count = len(text.split())

        if word_count == 0:
            return 0.0, []

        # Calculate frequency (per 100 words)
        emoji_frequency = (len(emojis) / word_count) * 100

        # Get most common emojis
        emoji_counts = Counter(emojis)
        common_emojis = [emoji for emoji, count in emoji_counts.most_common(5)]

        return emoji_frequency, common_emojis

    def _analyze_jargon(self, text: str) -> tuple[float, List[str]]:
        """
        Analyze industry jargon and technical terms

        Returns:
            Tuple of (jargon_ratio, list_of_industry_terms)
        """
        import re
        from collections import Counter

        # Common industry/technical term patterns
        # (This is a simple heuristic - could be improved with NLP)
        jargon_patterns = [
            r"\b[A-Z]{2,}\b",  # Acronyms (ROI, SEO, API)
            r"\b\w+(-\w+)+\b",  # Hyphenated terms (data-driven, real-time)
            r"\b\w+\s+\w+ing\b",  # "-ing" phrases (content marketing, lead generation)
        ]

        all_jargon = []
        for pattern in jargon_patterns:
            matches = re.findall(pattern, text)
            all_jargon.extend(matches)

        # Filter out common non-jargon
        common_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "man",
            "new",
            "now",
            "old",
            "see",
            "two",
            "way",
            "who",
            "boy",
            "did",
            "its",
            "let",
            "put",
            "say",
            "she",
            "too",
            "use",
        }
        jargon_terms = [term for term in all_jargon if term.lower() not in common_words]

        word_count = len(text.split())
        if word_count == 0:
            return 0.0, []

        # Calculate jargon ratio
        jargon_ratio = len(jargon_terms) / word_count

        # Get most common jargon terms
        jargon_counts = Counter(jargon_terms)
        top_terms = [term for term, count in jargon_counts.most_common(10) if count >= 2]

        return jargon_ratio, top_terms

    def _extract_hook(self, content: str) -> str:
        """Extract opening hook (first 1-2 sentences)"""
        sentences = content.split(". ")
        hook = ". ".join(sentences[:2])
        if not hook.endswith("."):
            hook += "."
        return hook.strip()

    def _extract_transitions(self, content: str) -> List[str]:
        """Find transitional phrases"""
        transition_markers = [
            "but here's",
            "here's why",
            "here's the thing",
            "the reality is",
            "in other words",
            "what does this mean",
            "so what",
            "bottom line",
            "that said",
            "however",
            "meanwhile",
        ]

        found = []
        content_lower = content.lower()

        for marker in transition_markers:
            if marker in content_lower:
                sentences = content.split(".")
                for sent in sentences:
                    if marker in sent.lower():
                        found.append(sent.strip())

        return found

    def _extract_cta(self, content: str) -> str:
        """Extract call-to-action"""
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        cta_indicators = ["?", "reply", "comment", "share", "thoughts", "experience", "let me know"]

        for sent in reversed(sentences[-3:]):
            if any(indicator in sent.lower() for indicator in cta_indicators):
                return sent

        return sentences[-1] if sentences else ""

    def _cluster_patterns(self, items: List[str], pattern_type: str) -> List[VoicePattern]:
        """Group similar patterns using fuzzy matching"""
        if not items:
            return []

        counter = Counter(items)
        clusters = []
        seen = set()

        for item, freq in counter.most_common():
            if item in seen or not item.strip():
                continue

            cluster = [item]
            for other_item in counter.keys():
                if other_item != item and other_item not in seen and other_item.strip():
                    similarity = SequenceMatcher(None, item.lower(), other_item.lower()).ratio()
                    if similarity > 0.7:
                        cluster.append(other_item)
                        seen.add(other_item)

            seen.add(item)
            total_freq = sum(counter[c] for c in cluster)

            clusters.append(
                VoicePattern(
                    pattern_type=pattern_type,
                    examples=cluster[:3],
                    frequency=total_freq,
                    description=self._describe_pattern(item, pattern_type),
                )
            )

        return sorted(clusters, key=lambda x: x.frequency, reverse=True)

    def _find_recurring_ngrams(self, text: str, min_freq: int = 3) -> List[str]:
        """Find phrases that appear 3+ times"""
        text = re.sub(r"[^\w\s]", "", text.lower())
        words = text.split()

        ngrams = []
        for n in range(2, 6):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i : i + n])
                ngrams.append(ngram)

        counter = Counter(ngrams)
        recurring = [phrase for phrase, count in counter.items() if count >= min_freq]

        filtered = []
        for phrase in sorted(recurring, key=len, reverse=True):
            if not any(phrase in longer for longer in filtered):
                filtered.append(phrase)

        return filtered[:10]

    def _calculate_avg_paragraphs(self, posts: List[Post]) -> float:
        """Calculate average paragraph count"""
        paragraph_counts = []
        for post in posts:
            paragraphs = [p for p in post.content.split("\n\n") if p.strip()]
            paragraph_counts.append(len(paragraphs))
        return sum(paragraph_counts) / len(paragraph_counts) if paragraph_counts else 1.0

    def _calculate_tone_consistency(self, posts: List[Post], client_brief: ClientBrief) -> float:
        """Calculate tone consistency score"""
        score = 0.0
        checks = 0

        all_content = " ".join([post.content.lower() for post in posts])

        tone_indicators = {
            "approachable": ["we", "you", "your", "us"],
            "direct": ["simple", "clear", "bottom line", "here's"],
            "authoritative": ["research shows", "data", "studies", "proven"],
            "witty": ["?", "!", "ironically"],
            "data_driven": ["statistic", "%", "number", "data", "metric"],
            "conversational": ["you know", "think about", "imagine", "ever"],
        }

        for tone in client_brief.brand_personality:
            if tone.value in tone_indicators:
                indicators = tone_indicators[tone.value]
                presence = sum(1 for ind in indicators if ind in all_content) / len(indicators)
                score += presence
                checks += 1

        if client_brief.key_phrases:
            phrases_used = sum(
                1 for phrase in client_brief.key_phrases if phrase.lower() in all_content
            )
            score += phrases_used / len(client_brief.key_phrases)
            checks += 1

        return score / checks if checks > 0 else 0.5

    def _extract_dominant_tones(self, posts: List[Post], client_brief: ClientBrief) -> List[str]:
        """Identify top 3 tones"""
        tones = [tone.value for tone in client_brief.brand_personality]
        return tones[:3] if tones else ["conversational", "professional"]

    def _generate_dos(
        self,
        hook_patterns: List[VoicePattern],
        transition_patterns: List[VoicePattern],
        cta_patterns: List[VoicePattern],
    ) -> List[str]:
        """Generate DO recommendations"""
        dos = []

        if hook_patterns:
            dos.append(
                f"DO: Start posts with {self._generalize_pattern(hook_patterns[0].examples[0])}"
            )
        if transition_patterns:
            dos.append("DO: Use clear transitions to guide readers")
        if cta_patterns:
            dos.append("DO: End with engaging questions or calls-to-action")

        dos.extend(
            [
                "DO: Maintain consistent paragraph length (2-3 sentences)",
                "DO: Use line breaks for readability",
            ]
        )

        return dos

    def _generate_donts(self, posts: List[Post], client_brief: ClientBrief) -> List[str]:
        """Generate DON'T recommendations"""
        donts = []

        if client_brief.tone_to_avoid:
            donts.append(f"DON'T: Use {client_brief.tone_to_avoid} tone")

        donts.extend(
            [
                "DON'T: Start every post the same way",
                "DON'T: Write walls of text without line breaks",
                "DON'T: End posts without a clear CTA or question",
            ]
        )

        avg_length = sum(p.word_count for p in posts) / len(posts)
        if avg_length > 250:
            donts.append("DON'T: Exceed 250-300 words")

        return donts

    def _select_best_examples(
        self, posts: List[Post], hook_patterns: List[VoicePattern]
    ) -> List[str]:
        """Select 3-5 strong post examples"""
        examples = []

        if hook_patterns:
            strong_hooks = hook_patterns[0].examples
            for hook in strong_hooks[:2]:
                for post in posts:
                    if hook in post.content:
                        excerpt = (
                            post.content[:200] + "..." if len(post.content) > 200 else post.content
                        )
                        examples.append(f'Strong hook: "{excerpt}"')
                        break

        cta_posts = [p for p in posts if p.has_cta]
        if cta_posts:
            best_cta = sorted(cta_posts, key=lambda x: x.word_count)[len(cta_posts) // 2]
            excerpt = best_cta.content[-150:]
            examples.append(f'Strong CTA: "...{excerpt}"')

        return examples[:5]

    def _describe_pattern(self, pattern: str, pattern_type: str) -> str:
        """Generate description for a pattern"""
        descriptions = {
            "opening": "Hooks reader attention immediately",
            "transition": "Guides reader through logical progression",
            "cta": "Encourages engagement and response",
        }
        return descriptions.get(pattern_type, "Common pattern in content")

    def _generalize_pattern(self, example: str) -> str:
        """Convert specific example to general pattern"""
        if any(char.isupper() for char in example):
            return "specific examples or case studies"
        elif example.lower().startswith("what if"):
            return "thought-provoking questions"
        elif example.lower().startswith("most"):
            return "statements about common challenges"
        else:
            return "concrete, relatable examples"

    def _determine_archetype(self, voice_dimensions: Dict, client_brief: ClientBrief) -> str:
        """
        Determine brand archetype based on voice dimensions.

        Args:
            voice_dimensions: Voice dimension analysis from VoiceMetrics
            client_brief: Client brief for additional context

        Returns:
            Brand archetype name
        """
        # Extract dominant dimensions
        formality = voice_dimensions.get("formality", {}).get("dominant", "conversational")
        tone = voice_dimensions.get("tone", {}).get("dominant", "friendly")
        perspective = voice_dimensions.get("perspective", {}).get("dominant", "collaborative")

        # Infer archetype from dimensions
        archetype = infer_archetype_from_voice_dimensions(formality, tone, perspective)

        logger.info(
            f"Archetype determination: formality={formality}, tone={tone}, "
            f"perspective={perspective} → {archetype}"
        )

        return archetype
