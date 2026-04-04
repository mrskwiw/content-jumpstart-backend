"""SEO Validator

Validates blog posts for SEO optimization.
Based on the seo_optimizer.py from content-creator skill.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models.client_brief import Platform
from ..models.post import Post
from ..models.seo_keyword import KeywordStrategy


class SEOValidator:
    """
    Validates blog posts for SEO optimization.

    Checks keyword usage, content structure, readability,
    and generates SEO improvement recommendations.
    """

    # Common stop words to filter from LSI extraction
    STOP_WORDS: Set[str] = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "shall",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
    }

    # SEO best practices - typed constants for mypy
    # Hard QA failure threshold: 800 words. Posts 800–1499 words pass validation
    # but score below optimal. Target range is 1500–2000 for best SEO performance.
    MIN_CONTENT_LENGTH: int = 800
    OPTIMAL_CONTENT_LENGTH: Tuple[int, int] = (1500, 2000)
    KEYWORD_DENSITY: Tuple[float, float] = (0.01, 0.03)  # 1-3%
    MIN_HEADINGS: int = 3
    IDEAL_PARAGRAPH_LENGTH: Tuple[int, int] = (40, 150)  # words
    MAX_SENTENCE_LENGTH: int = 20  # words

    # Keep dict for backward compatibility (tests may reference it)
    BEST_PRACTICES: Dict[str, Any] = {
        "min_content_length": 800,
        "optimal_content_length": (1500, 2000),
        "keyword_density": (0.01, 0.03),
        "min_headings": 3,
        "ideal_paragraph_length": (40, 150),
        "max_sentence_length": 20,
    }

    def __init__(
        self,
        keyword_strategy: Optional[KeywordStrategy] = None,
        min_seo_score: int = 60,
    ):
        """
        Initialize SEO validator.

        Args:
            keyword_strategy: Optional keyword strategy for keyword-aware validation
            min_seo_score: Minimum SEO score to pass validation (default 60)
        """
        self.keyword_strategy = keyword_strategy
        self.min_seo_score = min_seo_score

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate SEO optimization for blog posts.

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - seo_scores: List of individual post scores
            - average_score: float
            - issues: List of issue descriptions
            - recommendations: List of SEO recommendations
        """
        # Filter to only blog posts
        blog_posts = [p for p in posts if p.target_platform == Platform.BLOG]

        if not blog_posts:
            return {
                "passed": True,
                "seo_scores": [],
                "average_score": 0,
                "issues": [],
                "recommendations": [],
                "metric": "No blog posts to validate",
                "skipped": True,
            }

        issues = []
        recommendations: Set[str] = set()
        seo_scores = []

        for i, post in enumerate(blog_posts):
            analysis = self._analyze_post(post, i + 1)
            seo_scores.append(analysis["seo_score"])
            issues.extend(analysis["issues"])
            recommendations.update(analysis["recommendations"])

        average_score = sum(seo_scores) / len(seo_scores) if seo_scores else 0
        passed = average_score >= self.min_seo_score and len(issues) == 0

        return {
            "passed": passed,
            "seo_scores": seo_scores,
            "average_score": round(average_score, 1),
            "issues": issues,
            "recommendations": list(recommendations),
            "metric": f"Average SEO Score: {average_score:.0f}/100 ({len(blog_posts)} blog posts)",
            "skipped": False,
        }

    def _analyze_post(self, post: Post, post_num: int) -> Dict[str, Any]:
        """
        Analyze a single post for SEO optimization.

        Args:
            post: Post object to analyze
            post_num: Post number for issue reporting

        Returns:
            Dictionary with analysis results
        """
        content = post.content
        issues = []
        recommendations = []

        # Content length analysis
        word_count = post.word_count or len(content.split())
        if word_count < self.MIN_CONTENT_LENGTH:
            issues.append(
                f"Blog {post_num}: Too short for SEO ({word_count} words, "
                f"min: {self.MIN_CONTENT_LENGTH})"
            )

        # Structure analysis
        structure = self._analyze_structure(content)
        if structure["headings"]["total"] < self.MIN_HEADINGS:
            issues.append(
                f"Blog {post_num}: Needs more headings for SEO "
                f"({structure['headings']['total']} found, min: {self.MIN_HEADINGS})"
            )
            recommendations.append("Add more H2 headings to improve content structure")

        if structure["links"]["internal"] == 0 and structure["links"]["external"] == 0:
            recommendations.append("Add internal or external links to improve SEO")

        # Paragraph analysis
        if structure["avg_paragraph_length"] > self.IDEAL_PARAGRAPH_LENGTH[1]:
            recommendations.append(
                f"Break up long paragraphs (avg {structure['avg_paragraph_length']:.0f} words)"
            )

        # Readability analysis
        readability = self._analyze_readability(content)
        if readability["avg_sentence_length"] > self.MAX_SENTENCE_LENGTH:
            recommendations.append(
                f"Simplify sentences (avg {readability['avg_sentence_length']:.1f} words)"
            )

        # Keyword analysis (if keyword strategy provided)
        keyword_analysis = {}
        if self.keyword_strategy and self.keyword_strategy.primary_keywords:
            primary_keyword = self.keyword_strategy.primary_keywords[0].keyword
            keyword_analysis = self._analyze_keywords(
                content,
                primary_keyword,
                [kw.keyword for kw in (self.keyword_strategy.secondary_keywords or [])],
            )

            kw_data = keyword_analysis.get("primary_keyword", {})
            density = kw_data.get("density", 0)

            if density < self.KEYWORD_DENSITY[0]:
                recommendations.append(
                    f"Increase keyword density for '{primary_keyword}' (currently {density:.2%})"
                )
            elif density > self.KEYWORD_DENSITY[1]:
                recommendations.append(
                    f"Reduce keyword density for '{primary_keyword}' to avoid over-optimization"
                )

            if not kw_data.get("in_first_paragraph", False):
                recommendations.append("Include primary keyword in the first paragraph")

        # Calculate SEO score
        seo_score = self._calculate_seo_score(word_count, structure, readability, keyword_analysis)

        return {
            "seo_score": seo_score,
            "word_count": word_count,
            "structure": structure,
            "readability": readability,
            "keyword_analysis": keyword_analysis,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure for SEO."""
        lines = content.split("\n")

        structure = {
            "headings": {"h1": 0, "h2": 0, "h3": 0, "total": 0},
            "paragraphs": 0,
            "lists": 0,
            "links": {"internal": 0, "external": 0},
            "avg_paragraph_length": 0,
        }

        paragraphs = []
        current_para: List[str] = []

        # Access nested dicts with type hints for mypy
        headings = structure["headings"]
        links = structure["links"]

        for line in lines:
            # Count headings (markdown format)
            if line.startswith("# "):
                headings["h1"] += 1  # type: ignore[index]
                headings["total"] += 1  # type: ignore[index]
            elif line.startswith("## "):
                headings["h2"] += 1  # type: ignore[index]
                headings["total"] += 1  # type: ignore[index]
            elif line.startswith("### "):
                headings["h3"] += 1  # type: ignore[index]
                headings["total"] += 1  # type: ignore[index]

            # Count lists
            if line.strip().startswith(("- ", "* ", "1. ")):
                structure["lists"] += 1  # type: ignore[operator]

            # Count links
            internal_links = len(re.findall(r"\[.*?\]\(/.*?\)", line))
            external_links = len(re.findall(r"\[.*?\]\(https?://.*?\)", line))
            links["internal"] += internal_links  # type: ignore[index]
            links["external"] += external_links  # type: ignore[index]

            # Track paragraphs
            if line.strip() and not line.startswith("#"):
                current_para.append(line)
            elif current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []

        if current_para:
            paragraphs.append(" ".join(current_para))

        structure["paragraphs"] = len(paragraphs)

        if paragraphs:
            avg_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
            structure["avg_paragraph_length"] = round(avg_length, 1)

        return structure

    def _analyze_readability(self, content: str) -> Dict[str, Any]:
        """Analyze content readability."""
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = content.split()

        if not sentences or not words:
            return {"score": 0, "level": "Unknown", "avg_sentence_length": 0}

        avg_sentence_length = len(words) / len(sentences)

        # Simple readability scoring
        if avg_sentence_length < 15:
            level = "Easy"
            score = 90
        elif avg_sentence_length < 20:
            level = "Moderate"
            score = 70
        elif avg_sentence_length < 25:
            level = "Difficult"
            score = 50
        else:
            level = "Very Difficult"
            score = 30

        return {
            "score": score,
            "level": level,
            "avg_sentence_length": round(avg_sentence_length, 1),
        }

    def _analyze_keywords(self, content: str, primary: str, secondary: List[str]) -> Dict[str, Any]:
        """Analyze keyword usage and density."""
        content_lower = content.lower()
        word_count = len(content.split())

        results = {
            "primary_keyword": {
                "keyword": primary,
                "count": content_lower.count(primary.lower()),
                "density": 0,
                "in_first_paragraph": False,
            },
            "secondary_keywords": [],
            "lsi_keywords": [],
        }

        # Access nested dicts for mypy
        primary_kw = results["primary_keyword"]
        secondary_kws = results["secondary_keywords"]

        # Calculate primary keyword metrics
        if word_count > 0:
            primary_kw["density"] = (  # type: ignore[index]
                primary_kw["count"] / word_count  # type: ignore[index]
            )

        # Check keyword placement
        first_para = content.split("\n\n")[0] if "\n\n" in content else content[:200]
        primary_kw["in_first_paragraph"] = (  # type: ignore[index]
            primary.lower() in first_para.lower()
        )

        # Analyze secondary keywords
        for keyword in secondary:
            count = content_lower.count(keyword.lower())
            secondary_kws.append(  # type: ignore[attr-defined]
                {
                    "keyword": keyword,
                    "count": count,
                    "density": count / word_count if word_count > 0 else 0,
                }
            )

        # Extract potential LSI keywords
        results["lsi_keywords"] = self._extract_lsi_keywords(content, primary)

        return results

    def _extract_lsi_keywords(self, content: str, primary_keyword: str) -> List[str]:
        """Extract potential LSI (semantically related) keywords."""
        words = re.findall(r"\b[a-z]+\b", content.lower())
        word_freq: Dict[str, int] = {}

        # Count word frequencies
        for word in words:
            if word not in self.STOP_WORDS and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top related terms
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Filter out the primary keyword and return top 10
        lsi_keywords = []
        for word, count in sorted_words:
            if word != primary_keyword.lower() and count > 1:
                lsi_keywords.append(word)
            if len(lsi_keywords) >= 10:
                break

        return lsi_keywords

    def _calculate_seo_score(
        self,
        word_count: int,
        structure: Dict[str, Any],
        readability: Dict[str, Any],
        keyword_analysis: Dict[str, Any],
    ) -> int:
        """Calculate overall SEO optimization score."""
        score = 0

        # Content length scoring (20 points)
        opt_min, opt_max = self.OPTIMAL_CONTENT_LENGTH
        if opt_min <= word_count <= opt_max:
            score += 20
        elif word_count >= self.MIN_CONTENT_LENGTH:
            score += 15
        elif word_count >= self.MIN_CONTENT_LENGTH * 0.8:
            score += 10
        elif word_count >= 500:
            score += 5

        # Keyword optimization (30 points)
        if keyword_analysis:
            kw_data = keyword_analysis.get("primary_keyword", {})

            # Density scoring (15 points)
            density = kw_data.get("density", 0)
            min_density, max_density = self.KEYWORD_DENSITY
            if min_density <= density <= max_density:
                score += 15
            elif 0.005 <= density < min_density:
                score += 8
            elif density > 0:
                score += 4

            # Placement scoring (15 points)
            if kw_data.get("in_first_paragraph"):
                score += 15
        else:
            # No keyword strategy - give partial credit
            score += 15

        # Structure scoring (25 points)
        headings_total: int = structure["headings"]["total"]  # type: ignore[index]
        if headings_total >= self.MIN_HEADINGS:
            score += 10
        elif headings_total > 0:
            score += 5

        paragraphs: int = structure["paragraphs"]  # type: ignore[assignment]
        if paragraphs >= 3:
            score += 10
        elif paragraphs > 0:
            score += 5

        links = structure["links"]
        if links["internal"] > 0 or links["external"] > 0:  # type: ignore[index]
            score += 5

        # Readability scoring (25 points)
        readability_score = readability.get("score", 50)
        score += int(readability_score * 0.25)

        return min(score, 100)

    def generate_meta_suggestions(
        self, content: str, keyword: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate SEO meta tag suggestions.

        Args:
            content: Blog post content
            keyword: Primary keyword (optional)

        Returns:
            Dictionary with meta tag suggestions
        """
        # Extract first sentence for description base
        sentences = re.split(r"[.!?]+", content)
        first_sentence = sentences[0].strip() if sentences else content[:160]

        suggestions = {
            "title": "",
            "meta_description": "",
            "url_slug": "",
        }

        if keyword:
            # Title suggestion (50-60 chars)
            suggestions["title"] = f"{keyword.title()} - Complete Guide"
            if len(suggestions["title"]) > 60:
                suggestions["title"] = keyword.title()[:57] + "..."

            # Meta description (150-160 chars)
            desc_base = f"Learn everything about {keyword}. {first_sentence}"
            if len(desc_base) > 160:
                desc_base = desc_base[:157] + "..."
            suggestions["meta_description"] = desc_base

            # URL slug
            suggestions["url_slug"] = re.sub(r"[^a-z0-9-]+", "-", keyword.lower()).strip("-")
        else:
            # Extract from first heading if available
            heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if heading_match:
                title = heading_match.group(1).strip()
                suggestions["title"] = title[:57] + "..." if len(title) > 60 else title
                suggestions["url_slug"] = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")[:60]

            suggestions["meta_description"] = (
                first_sentence[:157] + "..." if len(first_sentence) > 160 else first_sentence
            )

        return suggestions
