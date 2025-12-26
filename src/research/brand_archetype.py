"""Brand Archetype Assessment Tool - Identifies brand personality archetype

This tool analyzes business description and brand positioning to determine which
of the 12 brand archetypes best fits the client's brand personality.

The 12 Brand Archetypes (based on Carl Jung's psychology):
1. The Innocent - Optimistic, pure, simple (Dove, Coca-Cola)
2. The Sage - Knowledgeable, thoughtful, analytical (Google, PBS)
3. The Explorer - Freedom-seeking, adventurous (Jeep, Patagonia)
4. The Outlaw - Rebellious, rule-breaking (Harley-Davidson, Virgin)
5. The Magician - Transformative, visionary (Disney, Apple)
6. The Hero - Courageous, bold, inspiring (Nike, FedEx)
7. The Lover - Passionate, intimate, sensual (Chanel, Godiva)
8. The Jester - Fun, playful, humorous (Old Spice, M&Ms)
9. The Everyman - Down-to-earth, reliable, supportive (IKEA, Home Depot)
10. The Caregiver - Nurturing, compassionate, selfless (Johnson & Johnson, Campbell's)
11. The Ruler - Powerful, authoritative, leader (Mercedes-Benz, Microsoft)
12. The Creator - Innovative, artistic, imaginative (Lego, Adobe)

Price: $300
Automation Level: 90%
Time: 1-2 minutes automated + 15 min review
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
from .base import ResearchTool


class BrandArchetype:
    """Brand archetype definition"""

    def __init__(
        self,
        name: str,
        description: str,
        traits: List[str],
        keywords: List[str],
        voice_characteristics: List[str],
        content_themes: List[str],
        examples: List[str],
    ):
        self.name = name
        self.description = description
        self.traits = traits
        self.keywords = keywords
        self.voice_characteristics = voice_characteristics
        self.content_themes = content_themes
        self.examples = examples


# Define all 12 archetypes
ARCHETYPES = {
    "innocent": BrandArchetype(
        name="The Innocent",
        description="Optimistic, pure, and simple. Focuses on happiness, simplicity, and virtue.",
        traits=["Optimistic", "Honest", "Pure", "Simple", "Trusting"],
        keywords=["simple", "pure", "honest", "happy", "natural", "clean", "fresh", "wholesome"],
        voice_characteristics=["Positive", "Simple language", "Reassuring", "Trustworthy"],
        content_themes=[
            "Simplicity",
            "Goodness",
            "Nostalgia",
            "Family values",
            "Natural solutions",
        ],
        examples=["Dove", "Coca-Cola", "Aveeno", "Simple"],
    ),
    "sage": BrandArchetype(
        name="The Sage",
        description="Knowledgeable, thoughtful, and analytical. Values truth and wisdom.",
        traits=["Knowledgeable", "Thoughtful", "Analytical", "Wise", "Mentor"],
        keywords=["knowledge", "wisdom", "research", "data", "insight", "expert", "truth", "learn"],
        voice_characteristics=["Authoritative", "Educational", "Data-driven", "Precise"],
        content_themes=[
            "Education",
            "Research",
            "Analysis",
            "Best practices",
            "Thought leadership",
        ],
        examples=["Google", "PBS", "Harvard", "TED"],
    ),
    "explorer": BrandArchetype(
        name="The Explorer",
        description="Freedom-seeking and adventurous. Values individuality and discovery.",
        traits=["Adventurous", "Independent", "Ambitious", "Free-spirited", "Pioneering"],
        keywords=[
            "explore",
            "adventure",
            "freedom",
            "discover",
            "journey",
            "new",
            "bold",
            "different",
        ],
        voice_characteristics=["Inspirational", "Bold", "Exciting", "Authentic"],
        content_themes=[
            "Discovery",
            "Adventure",
            "Self-discovery",
            "Breaking boundaries",
            "Innovation",
        ],
        examples=["Jeep", "Patagonia", "Red Bull", "The North Face"],
    ),
    "outlaw": BrandArchetype(
        name="The Outlaw",
        description="Rebellious and rule-breaking. Challenges the status quo.",
        traits=["Rebellious", "Disruptive", "Revolutionary", "Bold", "Provocative"],
        keywords=[
            "rebel",
            "disrupt",
            "revolution",
            "challenge",
            "break",
            "radical",
            "rethink",
            "change",
        ],
        voice_characteristics=["Provocative", "Edgy", "Direct", "Controversial"],
        content_themes=[
            "Disruption",
            "Revolution",
            "Questioning norms",
            "Breaking rules",
            "Liberation",
        ],
        examples=["Harley-Davidson", "Virgin", "Diesel", "PayPal"],
    ),
    "magician": BrandArchetype(
        name="The Magician",
        description="Transformative and visionary. Makes dreams come true.",
        traits=["Visionary", "Imaginative", "Transformative", "Charismatic", "Inspirational"],
        keywords=[
            "transform",
            "magic",
            "vision",
            "imagine",
            "possible",
            "dream",
            "create",
            "extraordinary",
        ],
        voice_characteristics=["Inspirational", "Visionary", "Wonder-filled", "Transformative"],
        content_themes=["Transformation", "Vision", "Possibilities", "Dreams", "Special moments"],
        examples=["Disney", "Apple", "Tesla", "MasterCard"],
    ),
    "hero": BrandArchetype(
        name="The Hero",
        description="Courageous, bold, and inspiring. Overcomes challenges.",
        traits=["Courageous", "Bold", "Inspiring", "Strong", "Determined"],
        keywords=[
            "achieve",
            "win",
            "strong",
            "courage",
            "champion",
            "overcome",
            "power",
            "succeed",
        ],
        voice_characteristics=["Motivational", "Confident", "Empowering", "Direct"],
        content_themes=[
            "Achievement",
            "Overcoming obstacles",
            "Performance",
            "Excellence",
            "Victory",
        ],
        examples=["Nike", "FedEx", "BMW", "Duracell"],
    ),
    "lover": BrandArchetype(
        name="The Lover",
        description="Passionate, intimate, and sensual. Creates emotional connections.",
        traits=["Passionate", "Intimate", "Sensual", "Romantic", "Elegant"],
        keywords=[
            "love",
            "passion",
            "beauty",
            "desire",
            "intimate",
            "elegant",
            "luxury",
            "indulge",
        ],
        voice_characteristics=["Sensual", "Elegant", "Warm", "Personal"],
        content_themes=["Beauty", "Intimacy", "Passion", "Pleasure", "Relationships"],
        examples=["Chanel", "Godiva", "Victoria's Secret", "Alfa Romeo"],
    ),
    "jester": BrandArchetype(
        name="The Jester",
        description="Fun, playful, and humorous. Brings joy and entertainment.",
        traits=["Playful", "Humorous", "Fun-loving", "Spontaneous", "Lighthearted"],
        keywords=["fun", "enjoy", "play", "laugh", "surprise", "humor", "delight", "entertaining"],
        voice_characteristics=["Humorous", "Playful", "Casual", "Entertaining"],
        content_themes=["Fun", "Entertainment", "Joy", "Playfulness", "Living in the moment"],
        examples=["Old Spice", "M&Ms", "Ben & Jerry's", "GEICO"],
    ),
    "everyman": BrandArchetype(
        name="The Everyman",
        description="Down-to-earth, reliable, and supportive. Belongs and connects.",
        traits=["Relatable", "Honest", "Supportive", "Friendly", "Down-to-earth"],
        keywords=[
            "everyday",
            "real",
            "honest",
            "reliable",
            "friendly",
            "together",
            "community",
            "simple",
        ],
        voice_characteristics=["Conversational", "Friendly", "Accessible", "Authentic"],
        content_themes=["Belonging", "Community", "Authenticity", "Everyday life", "Connection"],
        examples=["IKEA", "Home Depot", "eBay", "Target"],
    ),
    "caregiver": BrandArchetype(
        name="The Caregiver",
        description="Nurturing, compassionate, and selfless. Protects and cares for others.",
        traits=["Nurturing", "Compassionate", "Selfless", "Generous", "Protective"],
        keywords=["care", "protect", "nurture", "support", "help", "comfort", "safe", "compassion"],
        voice_characteristics=["Warm", "Reassuring", "Supportive", "Empathetic"],
        content_themes=["Care", "Protection", "Support", "Wellness", "Family"],
        examples=["Johnson & Johnson", "Campbell's", "Volvo", "UNICEF"],
    ),
    "ruler": BrandArchetype(
        name="The Ruler",
        description="Powerful, authoritative, and leader. Creates order and success.",
        traits=["Authoritative", "Confident", "Powerful", "Leader", "Organized"],
        keywords=[
            "power",
            "control",
            "leader",
            "success",
            "prestige",
            "authority",
            "premium",
            "exclusive",
        ],
        voice_characteristics=["Authoritative", "Confident", "Premium", "Sophisticated"],
        content_themes=["Leadership", "Success", "Control", "Status", "Excellence"],
        examples=["Mercedes-Benz", "Microsoft", "Rolex", "American Express"],
    ),
    "creator": BrandArchetype(
        name="The Creator",
        description="Innovative, artistic, and imaginative. Builds and creates.",
        traits=["Innovative", "Imaginative", "Artistic", "Entrepreneurial", "Visionary"],
        keywords=["create", "build", "design", "innovate", "imagine", "craft", "make", "original"],
        voice_characteristics=["Creative", "Inspiring", "Original", "Expressive"],
        content_themes=[
            "Creativity",
            "Innovation",
            "Self-expression",
            "Craftsmanship",
            "Imagination",
        ],
        examples=["Lego", "Adobe", "Crayola", "Moleskine"],
    ),
}


class BrandArchetypeAnalyzer(ResearchTool):
    """Analyzes brand positioning to determine primary and secondary archetypes"""

    def tool_name(self) -> str:
        return "brand_archetype"

    def price(self) -> int:
        return 300

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs

        Required:
        - business_description: str (min 100 chars)
        - brand_positioning: Optional[str]
        - target_audience: Optional[str]
        - core_values: Optional[List[str]]
        """
        if "business_description" not in inputs:
            raise ValueError("Missing required input: business_description")

        if len(inputs["business_description"]) < 70:
            raise ValueError("business_description too short (minimum 70 characters)")

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute brand archetype analysis

        Returns dict with:
        - primary_archetype: str
        - secondary_archetype: str
        - confidence_score: float
        - trait_matches: Dict
        - recommendations: List[str]
        """
        business_desc = inputs["business_description"]
        brand_positioning = inputs.get("brand_positioning", "")
        target_audience = inputs.get("target_audience", "")
        core_values = inputs.get("core_values", [])

        logger.info("Running brand archetype analysis")

        # Step 1: Keyword-based scoring
        keyword_scores = self._score_by_keywords(business_desc, brand_positioning)

        # Step 2: Claude-based analysis for context
        claude_analysis = self._analyze_with_claude(
            business_desc, brand_positioning, target_audience, core_values
        )

        # Step 3: Combine scores
        final_scores = self._combine_scores(keyword_scores, claude_analysis)

        # Step 4: Select primary and secondary
        sorted_archetypes = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_archetypes[0][0]
        secondary = sorted_archetypes[1][0] if len(sorted_archetypes) > 1 else None

        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(primary, secondary)

        return {
            "primary_archetype": primary,
            "secondary_archetype": secondary,
            "confidence_score": sorted_archetypes[0][1],
            "archetype_scores": dict(sorted_archetypes[:5]),  # Top 5
            "trait_matches": self._analyze_traits(business_desc, primary, secondary),
            "recommendations": recommendations,
        }

    def _score_by_keywords(self, business_desc: str, positioning: str) -> Dict[str, float]:
        """Score archetypes based on keyword matches"""
        text = f"{business_desc} {positioning}".lower()
        scores = {}

        for archetype_id, archetype in ARCHETYPES.items():
            # Count keyword matches
            matches = sum(1 for keyword in archetype.keywords if keyword in text)
            # Normalize by number of keywords
            scores[archetype_id] = matches / len(archetype.keywords)

        return scores

    def _analyze_with_claude(
        self, business_desc: str, positioning: str, audience: str, values: List[str]
    ) -> Dict[str, float]:
        """Use Claude to analyze brand archetype fit"""

        # Build archetype list for prompt
        archetype_list = "\n".join(
            [
                f"{i+1}. {arch.name} - {arch.description}"
                for i, arch in enumerate(ARCHETYPES.values())
            ]
        )

        prompt = f"""Analyze this brand and rate how well it fits each of the 12 brand archetypes.

**Business:** {business_desc}

**Positioning:** {positioning or "Not provided"}

**Target Audience:** {audience or "Not provided"}

**Core Values:** {', '.join(values) if values else "Not provided"}

**The 12 Brand Archetypes:**
{archetype_list}

Please respond with JSON only (no markdown):
{{
    "innocent": 0.0-1.0,
    "sage": 0.0-1.0,
    "explorer": 0.0-1.0,
    "outlaw": 0.0-1.0,
    "magician": 0.0-1.0,
    "hero": 0.0-1.0,
    "lover": 0.0-1.0,
    "jester": 0.0-1.0,
    "everyman": 0.0-1.0,
    "caregiver": 0.0-1.0,
    "ruler": 0.0-1.0,
    "creator": 0.0-1.0
}}

Rate each archetype 0.0 (no fit) to 1.0 (perfect fit) based on the brand's personality, values, and positioning."""

        try:
            client = get_default_client()
            content = client.create_message(
                messages=[{"role": "user", "content": prompt}], max_tokens=500, temperature=0.3
            )

            # Extract JSON
            import re

            json_match = re.search(r"\{[^}]+\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning("Claude didn't return valid JSON, using fallback")
                return {}

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {}

    def _combine_scores(
        self, keyword_scores: Dict[str, float], claude_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Combine keyword and Claude scores (60% Claude, 40% keywords)"""
        combined = {}

        for archetype_id in ARCHETYPES.keys():
            keyword_score = keyword_scores.get(archetype_id, 0.0)
            claude_score = claude_scores.get(archetype_id, 0.0)

            # Weight: 60% Claude (more nuanced), 40% keywords (objective)
            if claude_score > 0:
                combined[archetype_id] = (0.6 * claude_score) + (0.4 * keyword_score)
            else:
                # If Claude failed, use keyword score only
                combined[archetype_id] = keyword_score

        return combined

    def _analyze_traits(
        self, business_desc: str, primary: str, secondary: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze which traits are present"""
        text = business_desc.lower()

        primary_arch = ARCHETYPES[primary]
        trait_matches = {
            "primary": {
                "archetype": primary_arch.name,
                "matched_traits": [
                    trait
                    for trait in primary_arch.traits
                    if any(word in text for word in trait.lower().split())
                ],
            }
        }

        if secondary:
            secondary_arch = ARCHETYPES[secondary]
            trait_matches["secondary"] = {
                "archetype": secondary_arch.name,
                "matched_traits": [
                    trait
                    for trait in secondary_arch.traits
                    if any(word in text for word in trait.lower().split())
                ],
            }

        return trait_matches

    def _generate_recommendations(self, primary: str, secondary: Optional[str]) -> List[str]:
        """Generate actionable recommendations"""
        primary_arch = ARCHETYPES[primary]
        recommendations = []

        # Voice recommendations
        recommendations.append(
            f"**Voice:** Adopt a {', '.join(primary_arch.voice_characteristics[:2]).lower()} tone"
        )

        # Content themes
        recommendations.append(
            f"**Content Themes:** Focus on {', '.join(primary_arch.content_themes[:3]).lower()}"
        )

        # Examples
        recommendations.append(
            f"**Study These Brands:** {', '.join(primary_arch.examples[:2])} (they share your archetype)"
        )

        if secondary:
            secondary_arch = ARCHETYPES[secondary]
            recommendations.append(
                f"**Secondary Influence:** Blend in {secondary_arch.name.lower()} elements like {secondary_arch.voice_characteristics[0].lower()}"
            )

        return recommendations

    def generate_reports(self, analysis: Dict[str, Any]) -> Dict[str, Path]:
        """Generate archetype assessment reports"""

        # 1. JSON report
        json_path = self._save_json(analysis, "brand_archetype.json")

        # 2. Markdown report
        markdown_content = self._create_markdown_report(analysis)
        markdown_path = self._save_markdown(markdown_content, "brand_archetype_report.md")

        # 3. Simple guide
        guide_content = self._create_guide(analysis)
        guide_path = self._save_text(guide_content, "archetype_guide.txt")

        return {"json": json_path, "markdown": markdown_path, "text": guide_path}

    def _create_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """Create comprehensive markdown report"""
        primary = analysis["primary_archetype"]
        secondary = analysis["secondary_archetype"]
        primary_arch = ARCHETYPES[primary]

        lines = [
            "# Brand Archetype Assessment Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## Your Brand Archetype",
            "",
            f"### Primary: {primary_arch.name}",
            "",
            f"**Confidence Score:** {analysis['confidence_score']:.1%}",
            "",
            f"{primary_arch.description}",
            "",
            "**Key Traits:**",
        ]

        for trait in primary_arch.traits:
            lines.append(f"- {trait}")

        if secondary:
            secondary_arch = ARCHETYPES[secondary]
            lines.extend(
                [
                    "",
                    f"### Secondary: {secondary_arch.name}",
                    "",
                    f"{secondary_arch.description}",
                    "",
                    "**Key Traits:**",
                ]
            )
            for trait in secondary_arch.traits:
                lines.append(f"- {trait}")

        # Archetype scores
        lines.extend(
            [
                "",
                "---",
                "",
                "## Archetype Fit Scores",
                "",
            ]
        )

        for archetype_id, score in analysis["archetype_scores"].items():
            arch = ARCHETYPES[archetype_id]
            lines.append(f"- **{arch.name}:** {score:.1%}")

        # Recommendations
        lines.extend(
            [
                "",
                "---",
                "",
                "## Recommendations",
                "",
            ]
        )

        for rec in analysis["recommendations"]:
            lines.append(f"{rec}")
            lines.append("")

        # Voice characteristics
        lines.extend(
            [
                "---",
                "",
                "## Voice Characteristics",
                "",
                "Your brand voice should be:",
            ]
        )

        for char in primary_arch.voice_characteristics:
            lines.append(f"- {char}")

        # Content themes
        lines.extend(
            [
                "",
                "## Content Themes",
                "",
                "Focus your content on these themes:",
            ]
        )

        for theme in primary_arch.content_themes:
            lines.append(f"- {theme}")

        # Examples
        lines.extend(
            [
                "",
                "## Brand Examples",
                "",
                "Brands that share your archetype:",
            ]
        )

        for example in primary_arch.examples:
            lines.append(f"- {example}")

        return "\n".join(lines)

    def _create_guide(self, analysis: Dict[str, Any]) -> str:
        """Create simple text guide"""
        primary = analysis["primary_archetype"]
        primary_arch = ARCHETYPES[primary]

        lines = [
            "BRAND ARCHETYPE GUIDE",
            "=" * 50,
            "",
            f"Your Primary Archetype: {primary_arch.name}",
            f"Confidence: {analysis['confidence_score']:.1%}",
            "",
            "DESCRIPTION:",
            primary_arch.description,
            "",
            "KEY TRAITS:",
        ]

        for trait in primary_arch.traits:
            lines.append(f"  • {trait}")

        lines.extend(
            [
                "",
                "VOICE CHARACTERISTICS:",
            ]
        )

        for char in primary_arch.voice_characteristics:
            lines.append(f"  • {char}")

        lines.extend(
            [
                "",
                "CONTENT THEMES:",
            ]
        )

        for theme in primary_arch.content_themes:
            lines.append(f"  • {theme}")

        lines.extend(
            [
                "",
                "RECOMMENDATIONS:",
            ]
        )

        for rec in analysis["recommendations"]:
            # Strip markdown formatting for text file
            clean_rec = rec.replace("**", "").replace("*", "")
            lines.append(f"  • {clean_rec}")

        return "\n".join(lines)
