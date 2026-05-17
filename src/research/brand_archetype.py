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

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import logger
from ..validators.research_input_validator import ResearchInputValidator
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin


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


class BrandArchetypeAnalyzer(ResearchTool, CommonValidationMixin):
    """Analyzes brand positioning to determine primary and secondary archetypes"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize brand archetype analyzer with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "brand_archetype"

    @property
    def price(self) -> int:
        return 300

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate required inputs with comprehensive security checks (TR-019)

        Security Features:
        - Max length checks (prevent DOS attacks)
        - Prompt injection sanitization
        - Type validation
        - Field presence validation

        Required:
        - business_description: str (min 70 chars)
        - brand_positioning: Optional[str]
        - target_audience: Optional[str]
        - core_values: Optional[List[str]]
        """
        # SECURITY: Validate business description with sanitization
        inputs["business_description"] = self.validate_business_description(inputs)

        # SECURITY: Validate optional brand positioning
        if "brand_positioning" in inputs and inputs["brand_positioning"]:
            inputs["brand_positioning"] = self.validator.validate_text(
                inputs["brand_positioning"],
                field_name="brand_positioning",
                min_length=10,
                max_length=2000,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional target audience
        if "target_audience" in inputs and inputs["target_audience"]:
            inputs["target_audience"] = self.validator.validate_text(
                inputs["target_audience"],
                field_name="target_audience",
                min_length=10,
                max_length=2000,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional core values list
        if "core_values" in inputs and inputs["core_values"]:
            inputs["core_values"] = self.validator.validate_list(
                inputs["core_values"],
                field_name="core_values",
                min_items=1,
                max_items=20,
                required=False,
                item_validator=lambda v: self.validator.validate_text(
                    v,
                    field_name="core_value",
                    min_length=2,
                    max_length=100,
                    required=True,
                    sanitize=True,
                ),
            )

        # Optional client brand direction fields
        if "brand_personality" in inputs and inputs["brand_personality"]:
            bp = inputs["brand_personality"]
            if isinstance(bp, list):
                inputs["brand_personality"] = [
                    self.validator.validate_text(
                        t,
                        field_name="brand_personality_item",
                        min_length=1,
                        max_length=100,
                        required=False,
                        sanitize=True,
                    )
                    for t in bp
                    if t
                ]
            else:
                inputs["brand_personality"] = self.validator.validate_text(
                    bp,
                    field_name="brand_personality",
                    min_length=2,
                    max_length=500,
                    required=False,
                    sanitize=True,
                )
        if "tone_to_avoid" in inputs and inputs["tone_to_avoid"]:
            inputs["tone_to_avoid"] = self.validator.validate_text(
                inputs.get("tone_to_avoid"),
                field_name="tone_to_avoid",
                min_length=2,
                max_length=500,
                required=False,
                sanitize=True,
            )

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
        brand_personality = inputs.get("brand_personality", "")
        tone_to_avoid = inputs.get("tone_to_avoid", "")

        logger.info("Running brand archetype analysis")

        # Step 1: Keyword-based scoring
        keyword_scores = self._score_by_keywords(business_desc, brand_positioning)

        # Step 2: Claude-based analysis for context
        claude_analysis = self._analyze_with_claude(
            business_desc,
            brand_positioning,
            target_audience,
            core_values,
            brand_personality=brand_personality,
            tone_to_avoid=tone_to_avoid,
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
        self,
        business_desc: str,
        positioning: str,
        audience: str,
        values: List[str],
        brand_personality: "Any" = "",
        tone_to_avoid: str = "",
    ) -> Dict[str, float]:
        """Use Claude to analyze brand archetype fit"""

        # Build archetype list for prompt
        archetype_list = "\n".join(
            [
                f"{i+1}. {arch.name} - {arch.description}"
                for i, arch in enumerate(ARCHETYPES.values())
            ]
        )

        direction_lines = []
        if brand_personality:
            traits = (
                ", ".join(brand_personality)
                if isinstance(brand_personality, list)
                else brand_personality
            )
            direction_lines.append(
                f"Declared Brand Personality: {traits} — weight these traits heavily when scoring archetype fit"
            )
        if tone_to_avoid:
            direction_lines.append(
                f"Tone to Avoid: {tone_to_avoid} — lower scores for archetypes that embody this tone"
            )
        brand_direction = (
            "\n\n**Declared Brand Direction (client-stated — use as primary signal):**\n"
            + "\n".join(direction_lines)
            if direction_lines
            else ""
        )

        prompt = f"""Analyze this brand and rate how well it fits each of the 12 brand archetypes.

**Business:** {business_desc}

**Positioning:** {positioning or "Not provided"}

**Target Audience:** {audience or "Not provided"}

**Core Values:** {', '.join(values) if values else "Not provided"}{brand_direction}

**The 12 Brand Archetypes:**
{archetype_list}

CRITICAL: Rate ALL 12 archetypes. Search ENTIRE input for personality traits, values, and positioning signals.

EXAMPLE INPUT/OUTPUT:

Input: "We're a sustainable outdoor gear company empowering adventurers to explore responsibly.
We believe in freedom, environmental stewardship, and pushing boundaries while protecting nature."

Output:
{{
    "innocent": 0.2,
    "sage": 0.3,
    "explorer": 0.9,
    "outlaw": 0.4,
    "magician": 0.2,
    "hero": 0.5,
    "lover": 0.3,
    "jester": 0.1,
    "everyman": 0.4,
    "caregiver": 0.6,
    "ruler": 0.2,
    "creator": 0.5
}}

RATING CRITERIA (0.0-1.0):

**0.9-1.0 (Dominant fit):** Brand strongly embodies this archetype's core traits, values, and voice
- Example: "empowering adventurers to explore" + "freedom" + "pushing boundaries" = 0.9 Explorer

**0.6-0.8 (Strong secondary):** Brand exhibits multiple traits but not the primary identity
- Example: "environmental stewardship" + "protecting nature" = 0.6 Caregiver (secondary to Explorer)

**0.3-0.5 (Moderate influence):** Some traits present but not defining characteristics
- Example: "pushing boundaries" shows Hero courage (0.5) but Explorer is stronger

**0.1-0.2 (Minimal presence):** Very weak or absent traits
- Example: No humor/playfulness = 0.1 Jester

**0.0 (No fit):** Archetype contradicts brand personality
- Use sparingly - most brands have traces of multiple archetypes

ARCHETYPE-SPECIFIC SIGNALS:

1. **Innocent (0.0-1.0):** Look for: optimism, simplicity, purity, nostalgia, wholesome, natural, clean, happy, trust
   - Keywords: "simple", "pure", "honest", "natural", "wholesome"
   - Values: goodness, family, virtue, simplicity

2. **Sage (0.0-1.0):** Look for: knowledge, wisdom, analysis, research, expertise, thought leadership, truth
   - Keywords: "expert", "research", "data", "insight", "wisdom", "learn"
   - Values: truth, knowledge, understanding, education

3. **Explorer (0.0-1.0):** Look for: adventure, freedom, discovery, independence, pioneering, bold, new experiences
   - Keywords: "explore", "adventure", "freedom", "discover", "journey", "bold"
   - Values: independence, self-discovery, authenticity, breaking boundaries

4. **Outlaw (0.0-1.0):** Look for: rebellion, disruption, challenging norms, radical change, provocative, rule-breaking
   - Keywords: "disrupt", "rebel", "revolution", "challenge", "break", "radical"
   - Values: liberation, disruption, questioning status quo

5. **Magician (0.0-1.0):** Look for: transformation, vision, making dreams real, extraordinary, wonder, possibility
   - Keywords: "transform", "vision", "imagine", "possible", "dream", "extraordinary"
   - Values: transformation, vision, special moments, making impossible possible

6. **Hero (0.0-1.0):** Look for: courage, achievement, overcoming obstacles, strength, determination, winning, excellence
   - Keywords: "achieve", "win", "courage", "overcome", "champion", "power"
   - Values: mastery, courage, performance, overcoming challenges

7. **Lover (0.0-1.0):** Look for: passion, beauty, intimacy, elegance, sensuality, luxury, emotional connection
   - Keywords: "passion", "beauty", "luxury", "intimate", "elegant", "indulge"
   - Values: intimacy, passion, pleasure, aesthetics, relationships

8. **Jester (0.0-1.0):** Look for: fun, humor, playfulness, entertainment, spontaneity, joy, lighthearted
   - Keywords: "fun", "enjoy", "play", "laugh", "humor", "delight", "entertaining"
   - Values: living in the moment, joy, playfulness, not taking life too seriously

9. **Everyman (0.0-1.0):** Look for: down-to-earth, relatable, community, belonging, honest, friendly, accessible
   - Keywords: "everyday", "real", "honest", "reliable", "community", "together"
   - Values: belonging, connection, authenticity, equality, common sense

10. **Caregiver (0.0-1.0):** Look for: nurturing, compassion, protection, support, care, wellness, safety, generosity
    - Keywords: "care", "protect", "nurture", "support", "help", "safe", "comfort"
    - Values: service, compassion, caring for others, protection

11. **Ruler (0.0-1.0):** Look for: power, authority, leadership, control, success, prestige, premium, exclusive
    - Keywords: "leader", "power", "success", "prestige", "authority", "premium"
    - Values: control, status, leadership, order, stability

12. **Creator (0.0-1.0):** Look for: innovation, creativity, craftsmanship, imagination, building, originality, design
    - Keywords: "create", "build", "design", "innovate", "craft", "make", "original"
    - Values: self-expression, innovation, creativity, vision, craftsmanship

ANALYSIS STRATEGY:

1. Read ENTIRE business description, positioning, audience, and values
2. Identify explicit traits: What words/phrases directly match archetype keywords?
3. Infer personality: What does their tone/style suggest about brand personality?
4. Weigh values: What core values align with which archetypes?
5. Consider audience: Who are they trying to attract? (Explorers attract Explorers, etc.)
6. Rank archetypes: Primary (0.8-1.0), Secondary (0.5-0.7), Influences (0.2-0.4), Minimal (0.0-0.1)
7. Rate ALL 12: Every archetype gets a score, even if 0.1

Return ONLY the JSON object with all 12 archetype scores (0.0-1.0). No markdown, no explanation."""

        result = self._call_claude_api(
            prompt, max_tokens=500, temperature=0.3, extract_json=True, fallback_on_error={}
        )
        return dict(result) if isinstance(result, dict) else {}

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
            # Bug #167: secondary_arch.voice_characteristics[0] may overlap with the
            # primary archetype's traits (e.g., both Ruler and Sage lead with
            # "Authoritative"), making the blend-in suggestion indistinguishable.
            # Use the first voice trait unique to the secondary archetype instead.
            primary_voices = {v.lower() for v in ARCHETYPES[primary].voice_characteristics}
            unique_voices = [
                v for v in secondary_arch.voice_characteristics if v.lower() not in primary_voices
            ]
            blend_voice = (
                unique_voices[0] if unique_voices else secondary_arch.voice_characteristics[0]
            )
            recommendations.append(
                f"**Secondary Influence:** Blend in {secondary_arch.name.lower()} elements like {blend_voice.lower()}"
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
