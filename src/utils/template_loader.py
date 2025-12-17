"""Template loader for parsing POST_TEMPLATE_LIBRARY.md"""

import random
import re
from pathlib import Path
from typing import List, Optional

from ..agents.client_classifier import ClientClassifier
from ..config.settings import settings
from ..config.template_rules import TEMPLATE_PREFERENCES, ClientType
from ..models.template import Template, TemplateDifficulty, TemplateType
from .logger import logger
from .template_cache import get_cache_manager

# Compiled regex patterns for performance
PLACEHOLDER_PATTERN = re.compile(r"\[([A-Z][A-Z\s/_-]*?)\]")
TEMPLATE_PATTERN = re.compile(r"## TEMPLATE (\d+): (.+?)(?=\n##|\Z)", re.DOTALL)
STRUCTURE_PATTERN = re.compile(r"```\n(.*?)\n```", re.DOTALL)
BEST_FOR_PATTERN = re.compile(r"\*\*Best for:\*\* (.+?)(?:\n|\*\*)")
NAME_PATTERN = re.compile(r"(.+?)\n")


class TemplateLoader:
    """Loads and parses templates from the template library file"""

    # Mapping of template names to types
    TEMPLATE_TYPE_MAP = {
        "Problem-Recognition": TemplateType.PROBLEM_RECOGNITION,
        "Statistic": TemplateType.STATISTIC,
        "Against the Grain": TemplateType.CONTRARIAN,
        "What Changed": TemplateType.EVOLUTION,
        "Question": TemplateType.QUESTION,
        "Personal Story": TemplateType.STORY,
        "Myth-Busting": TemplateType.MYTH_BUSTING,
        "Things I Got Wrong": TemplateType.VULNERABILITY,
        "How-To": TemplateType.HOW_TO,
        "Comparison": TemplateType.COMPARISON,
        "What I Learned": TemplateType.LEARNING,
        "Inside Look": TemplateType.BEHIND_SCENES,
        "Future-Thinking": TemplateType.FUTURE,
        "Reader Question": TemplateType.Q_AND_A,
        "Milestone": TemplateType.MILESTONE,
    }

    def __init__(self, template_file: Optional[Path] = None):
        """
        Initialize template loader

        Args:
            template_file: Path to template library file (defaults to settings)
        """
        if template_file is None:
            # Resolve relative path from project directory
            project_dir = Path(__file__).parent.parent.parent
            template_file = project_dir / settings.TEMPLATE_LIBRARY_PATH

        self.template_file = Path(template_file)

        if not self.template_file.exists():
            raise FileNotFoundError(f"Template library not found: {self.template_file}")

        self.templates: List[Template] = []
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the file with enhanced caching"""
        # Get cache manager instance
        cache_manager = get_cache_manager()

        # Try to load from cache
        cached_templates = cache_manager.get(self.template_file)
        if cached_templates is not None:
            self.templates = cached_templates
            logger.debug(f"Loaded {len(self.templates)} templates from cache")
            return

        logger.info(f"Parsing templates from {self.template_file}")

        # Get file modification time for cache entry
        current_mtime = self.template_file.stat().st_mtime

        content = self.template_file.read_text(encoding="utf-8")

        # Split by template headers using compiled pattern
        matches = TEMPLATE_PATTERN.finditer(content)

        for match in matches:
            template_id = int(match.group(1))
            template_section = match.group(2)

            # Extract template name from first line using compiled pattern
            name_match = NAME_PATTERN.match(template_section)
            if not name_match:
                logger.warning(f"Could not parse template {template_id}, skipping")
                continue

            full_name = name_match.group(1).strip()

            # Extract "Best for" line using compiled pattern
            best_for_match = BEST_FOR_PATTERN.search(template_section)
            best_for = best_for_match.group(1).strip() if best_for_match else "General use"

            # Extract the structure using compiled pattern
            structure_match = STRUCTURE_PATTERN.search(template_section)
            if not structure_match:
                logger.warning(f"Could not find structure for template {template_id}, skipping")
                continue

            structure = structure_match.group(1).strip()

            # Determine template type from name
            template_type = self._infer_template_type(full_name)

            # Extract placeholder fields
            placeholder_fields = self._extract_placeholders(structure)

            # Determine difficulty based on structure complexity
            difficulty = self._infer_difficulty(structure, placeholder_fields)

            # Check if template requires story or data
            requires_story = self._check_requires_story(structure, full_name)
            requires_data = self._check_requires_data(structure, full_name)

            template = Template(
                template_id=template_id,
                name=full_name,
                template_type=template_type,
                structure=structure,
                best_for=best_for,
                difficulty=difficulty,
                requires_story=requires_story,
                requires_data=requires_data,
                placeholder_fields=placeholder_fields,
            )

            self.templates.append(template)

        # Store in cache
        cache_manager.put(path=self.template_file, templates=self.templates, mtime=current_mtime)

        logger.info(f"Loaded {len(self.templates)} templates successfully")

    def _infer_template_type(self, name: str) -> TemplateType:
        """Infer template type from name"""
        for keyword, template_type in self.TEMPLATE_TYPE_MAP.items():
            if keyword.lower() in name.lower():
                return template_type

        # Default to PROBLEM_RECOGNITION
        logger.warning(f"Could not infer type for '{name}', defaulting to PROBLEM_RECOGNITION")
        return TemplateType.PROBLEM_RECOGNITION

    def _extract_placeholders(self, structure: str) -> List[str]:
        """Extract unique placeholder fields from structure"""
        # Find all [PLACEHOLDER] patterns using compiled pattern
        placeholders = PLACEHOLDER_PATTERN.findall(structure)

        # Clean and deduplicate
        unique_placeholders = []
        seen = set()

        for placeholder in placeholders:
            # Skip section headers like [HOOK], [SETUP], etc.
            if placeholder in [
                "HOOK",
                "VALIDATE",
                "REFRAME",
                "CTA",
                "STAT",
                "INTERPRETATION",
                "FLIP",
                "REAL-WORLD APPLICATION",
                "CONTRARIAN HEADLINE",
                "SETUP",
                "BUT",
                "YOUR ANGLE",
                "CAVEAT",
                "CLOSING",
                "CONTEXT",
                "TRIGGER",
                "NEW APPROACH",
                "COMPARISON",
                "WHAT WE LEARNED",
                "INVITATION",
                "QUESTION",
                "BONUS",
                "OPTIONAL SWEETENER",
                "CRISIS",
                "REALIZATION",
                "THE FEELING",
                "LESSON",
                "APPLICATION",
                "RELEVANCE TO YOUR AUDIENCE",
                "MYTH",
                "SEEMS TRUE BECAUSE",
                "THE REALITY",
                "WHY IT MATTERS",
                "EVIDENCE",
                "EXAMPLE",
                "WHAT YOU SHOULD DO INSTEAD",
            ]:
                continue

            cleaned = placeholder.strip()
            if cleaned and cleaned not in seen:
                unique_placeholders.append(cleaned)
                seen.add(cleaned)

        return unique_placeholders

    def _infer_difficulty(self, structure: str, placeholders: List[str]) -> TemplateDifficulty:
        """Infer template difficulty based on complexity"""
        # Count sections and placeholders
        section_count = len(re.findall(r"\[([A-Z][A-Z\s/-]*?)\]:", structure))
        placeholder_count = len(placeholders)
        len(structure.split())

        # Simple heuristic
        if placeholder_count <= 3 and section_count <= 4:
            return TemplateDifficulty.FAST
        elif placeholder_count <= 6 and section_count <= 6:
            return TemplateDifficulty.MEDIUM
        else:
            return TemplateDifficulty.SLOW

    def _check_requires_story(self, structure: str, name: str) -> bool:
        """Check if template requires personal story"""
        story_keywords = [
            "personal story",
            "i once",
            "we saw this",
            "example",
            "case",
            "crisis",
            "realization",
        ]
        combined = (structure + name).lower()
        return any(keyword in combined for keyword in story_keywords)

    def _check_requires_data(self, structure: str, name: str) -> bool:
        """Check if template requires data/statistics"""
        data_keywords = ["stat", "statistic", "data", "number", "%", "source"]
        combined = (structure + name).lower()
        return any(keyword in combined for keyword in data_keywords)

    def get_all_templates(self) -> List[Template]:
        """Get all loaded templates"""
        return self.templates

    def get_template_by_id(self, template_id: int) -> Optional[Template]:
        """Get a specific template by ID"""
        for template in self.templates:
            if template.template_id == template_id:
                return template
        return None

    def get_templates_by_type(self, template_type: TemplateType) -> List[Template]:
        """Get all templates of a specific type"""
        return [t for t in self.templates if t.template_type == template_type]

    def get_templates_by_difficulty(self, difficulty: TemplateDifficulty) -> List[Template]:
        """Get all templates of a specific difficulty"""
        return [t for t in self.templates if t.difficulty == difficulty]

    def select_templates_for_client(
        self,
        client_brief,
        count: int = 15,
        boost_templates: Optional[List[int]] = None,
        avoid_templates: Optional[List[int]] = None,
    ) -> List[Template]:
        """
        Intelligently select templates based on client type and brief

        Args:
            client_brief: ClientBrief instance with client information
            count: Number of templates to select (default 15)
            boost_templates: Optional list of template IDs to prioritize (from client memory)
            avoid_templates: Optional list of template IDs to deprioritize (from client memory)

        Returns:
            List of selected templates optimized for client type
        """
        # Classify client to determine template preferences
        classifier = ClientClassifier()
        client_type, confidence = classifier.classify_client(client_brief)

        logger.info(f"Client type: {client_type.value} (confidence: {confidence:.1%})")

        # Get template preferences for this client type
        preferences = TEMPLATE_PREFERENCES.get(
            client_type, TEMPLATE_PREFERENCES[ClientType.UNKNOWN]
        )
        preferred_types = set(preferences["preferred"])
        avoid_types = set(preferences["avoid"])

        # Convert boost/avoid template IDs to sets
        boost_ids = set(boost_templates or [])
        avoid_ids = set(avoid_templates or [])

        selected = []
        remaining = self.templates.copy()

        # Pass 0: Prioritize boost templates from client memory (highest priority)
        if boost_ids:
            boost_templates = [t for t in remaining if t.template_id in boost_ids]
            for template in boost_templates:
                can_fill, _ = template.can_be_filled(client_brief)
                if can_fill and len(selected) < count:
                    selected.append(template)
                    remaining.remove(template)
                    logger.debug(f"Boosted template {template.template_id} (client memory)")

        # Pass 1: Add preferred templates that can be filled (excluding memory avoids)
        preferred_templates = [
            t
            for t in remaining
            if t.template_type in preferred_types and t.template_id not in avoid_ids
        ]
        for template in preferred_templates:
            can_fill, _ = template.can_be_filled(client_brief)
            if can_fill and len(selected) < count:
                selected.append(template)
                remaining.remove(template)

        # Pass 2: Add other fillable templates (excluding avoided types and memory avoids)
        neutral_templates = [
            t
            for t in remaining
            if t.template_type not in avoid_types and t.template_id not in avoid_ids
        ]
        for template in neutral_templates:
            can_fill, _ = template.can_be_filled(client_brief)
            if can_fill and len(selected) < count:
                selected.append(template)
                remaining.remove(template)

        # Pass 3: If still need more, add remaining (excluding memory avoids, but allowing type avoids)
        available_remaining = [t for t in remaining if t.template_id not in avoid_ids]
        while len(selected) < count and available_remaining:
            selected.append(available_remaining.pop(0))

        # Pass 4: Last resort - add memory avoided templates if absolutely necessary
        while len(selected) < count and remaining:
            selected.append(remaining.pop(0))

        # Shuffle for variety in final output
        random.shuffle(selected)

        # Count boosted/avoided from memory
        boosted_count = len([t for t in selected if t.template_id in boost_ids])
        avoided_count = len([t for t in selected if t.template_id in avoid_ids])

        logger.info(
            f"Selected {len(selected)} templates for {client_brief.company_name} "
            f"({client_type.value}): "
            f"{len([t for t in selected if t.template_type in preferred_types])} preferred, "
            f"{len([t for t in selected if t.template_type in avoid_types])} avoided"
        )

        if boosted_count > 0 or avoided_count > 0:
            logger.info(
                f"Memory-aware selection: {boosted_count} boosted, "
                f"{avoided_count} avoided (from client history)"
            )

        return selected[:count]


# Create default loader instance
try:
    default_loader = TemplateLoader()
except FileNotFoundError as e:
    logger.warning(f"Could not load default templates: {e}")
    default_loader = None
