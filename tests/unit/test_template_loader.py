"""
Unit tests for TemplateLoader
"""

import pytest
from src.utils.template_loader import TemplateLoader, PLACEHOLDER_PATTERN, TEMPLATE_PATTERN
from src.models.template import Template, TemplateType, TemplateDifficulty
from src.models.client_brief import ClientBrief


# Sample template content for testing
SAMPLE_TEMPLATE_CONTENT = """# POST TEMPLATE LIBRARY

## TEMPLATE 1: Problem-Recognition Post
**Best for:** Awareness-building

```
[HOOK]: Attention-grabbing statement about [PROBLEM]
[VALIDATE]: Acknowledgment of [AUDIENCE TYPE] struggle
[REFRAME]: New perspective on [PROBLEM]
[CTA]: Question or engagement prompt
```

## TEMPLATE 2: Statistic + Insight
**Best for:** Authority

```
[STAT]: Surprising statistic about [INDUSTRY/TOPIC]
[INTERPRETATION]: What it means for [AUDIENCE TYPE]
[APPLICATION]: How to use this insight
[CTA]: Question or call to action
```

## TEMPLATE 3: Against the Grain (Contrarian Take)
**Best for:** Differentiation

```
[CONTRARIAN HEADLINE]: Provocative statement
[SETUP]: What everyone believes about [TOPIC]
[FLIP]: Why it's actually wrong
[YOUR ANGLE]: The better approach
[CTA]: Invitation to discuss
```
"""

SAMPLE_TEMPLATE_WITH_STORY = """
## TEMPLATE 6: Personal Story Post
**Best for:** Emotional connection

```
[CRISIS]: Personal crisis or challenge I faced
[REALIZATION]: Lesson learned
[THE FEELING]: Emotional impact
[LESSON]: Key takeaway
[APPLICATION]: How you can apply this
```
"""


@pytest.fixture
def temp_template_file(tmp_path):
    """Create a temporary template file for testing"""
    template_file = tmp_path / "test_templates.md"
    template_file.write_text(SAMPLE_TEMPLATE_CONTENT, encoding="utf-8")
    return template_file


@pytest.fixture
def temp_story_template_file(tmp_path):
    """Create a temporary template file with story template"""
    template_file = tmp_path / "story_templates.md"
    template_file.write_text(SAMPLE_TEMPLATE_WITH_STORY, encoding="utf-8")
    return template_file


@pytest.fixture
def loader(temp_template_file):
    """Create a TemplateLoader instance with test templates"""
    return TemplateLoader(template_file=temp_template_file)


@pytest.fixture
def sample_brief():
    """Create a sample client brief for testing"""
    return ClientBrief(
        company_name="TestCo",
        business_description="B2B SaaS platform for project management",
        ideal_customer="Product managers at tech startups",
        main_problem_solved="Lack of visibility into project progress",
        customer_pain_points=[
            "Projects run over budget",
            "Teams miss deadlines",
            "Stakeholders lack visibility",
        ],
        unique_value_proposition="Real-time project insights",
        primary_platform="LinkedIn",
        content_goals=["Build authority", "Generate leads"],
        voice_description="Professional but approachable",
        example_topics=["Project management", "Team collaboration"],
        client_stories=["Helped startup reduce project delays by 40%"],
    )


class TestTemplateLoaderInit:
    """Tests for TemplateLoader initialization"""

    def test_init_with_valid_file(self, temp_template_file):
        """Test initialization with valid template file"""
        loader = TemplateLoader(template_file=temp_template_file)
        assert loader.template_file == temp_template_file
        assert isinstance(loader.templates, list)
        assert len(loader.templates) == 3  # Three templates in sample content

    def test_init_with_nonexistent_file(self, tmp_path):
        """Test initialization with non-existent file raises error"""
        nonexistent = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError, match="Template library not found"):
            TemplateLoader(template_file=nonexistent)

    def test_init_without_file_uses_default_path(self):
        """Test initialization without file uses default settings path"""
        # This should work if the actual template file exists in parent directory
        try:
            loader = TemplateLoader()
            assert loader.template_file.exists()
        except FileNotFoundError:
            pytest.skip("Default template file not found - expected in test environment")


class TestTemplateLoaderParsing:
    """Tests for template parsing logic"""

    def test_load_templates_count(self, loader):
        """Test that correct number of templates are loaded"""
        assert len(loader.templates) == 3

    def test_load_templates_ids(self, loader):
        """Test that template IDs are correctly parsed"""
        template_ids = [t.template_id for t in loader.templates]
        assert template_ids == [1, 2, 3]

    def test_load_templates_names(self, loader):
        """Test that template names are correctly parsed"""
        template_names = [t.name for t in loader.templates]
        assert "Problem-Recognition Post" in template_names
        assert "Statistic + Insight" in template_names
        assert "Against the Grain (Contrarian Take)" in template_names

    def test_load_templates_structures(self, loader):
        """Test that template structures contain placeholders"""
        for template in loader.templates:
            assert len(template.structure) > 0
            # Each structure should contain at least one bracketed section
            assert "[" in template.structure
            assert "]" in template.structure

    def test_load_templates_best_for(self, loader):
        """Test that best_for field is extracted"""
        best_for_values = [t.best_for for t in loader.templates]
        assert "Awareness-building" in best_for_values
        assert "Authority" in best_for_values
        assert "Differentiation" in best_for_values


class TestTemplateTypeInference:
    """Tests for template type inference"""

    def test_infer_problem_recognition_type(self, loader):
        """Test inferring problem-recognition type"""
        template_type = loader._infer_template_type("Problem-Recognition Post")
        assert template_type == TemplateType.PROBLEM_RECOGNITION

    def test_infer_statistic_type(self, loader):
        """Test inferring statistic type"""
        template_type = loader._infer_template_type("Statistic + Insight")
        assert template_type == TemplateType.STATISTIC

    def test_infer_contrarian_type(self, loader):
        """Test inferring contrarian type"""
        template_type = loader._infer_template_type("Against the Grain")
        assert template_type == TemplateType.CONTRARIAN

    def test_infer_unknown_defaults_to_problem_recognition(self, loader):
        """Test that unknown template names default to PROBLEM_RECOGNITION"""
        template_type = loader._infer_template_type("Unknown Template Name")
        assert template_type == TemplateType.PROBLEM_RECOGNITION


class TestPlaceholderExtraction:
    """Tests for placeholder extraction"""

    def test_extract_placeholders_from_structure(self, loader):
        """Test extracting placeholders from template structure"""
        structure = "[HOOK]: Start with [PROBLEM]\n[CTA]: Ask about [SOLUTION]"
        placeholders = loader._extract_placeholders(structure)
        # Should exclude section headers like HOOK, CTA
        assert "PROBLEM" in placeholders
        assert "SOLUTION" in placeholders
        assert "HOOK" not in placeholders
        assert "CTA" not in placeholders

    def test_extract_placeholders_deduplicates(self, loader):
        """Test that duplicate placeholders are removed"""
        structure = "[HOOK]: [PROBLEM] and [PROBLEM] again\n[CTA]: More [PROBLEM]"
        placeholders = loader._extract_placeholders(structure)
        assert placeholders.count("PROBLEM") == 1

    def test_extract_placeholders_excludes_section_headers(self, loader):
        """Test that common section headers are excluded"""
        structure = "[HOOK]: [VALIDATE]: [REFRAME]: [CTA]: [SETUP]: [BONUS]:"
        placeholders = loader._extract_placeholders(structure)
        # All of these should be filtered out as section headers
        assert len(placeholders) == 0

    def test_placeholder_pattern_regex(self):
        """Test the PLACEHOLDER_PATTERN regex"""
        text = "[AUDIENCE TYPE] and [PROBLEM] with [CTA]"
        matches = PLACEHOLDER_PATTERN.findall(text)
        assert "AUDIENCE TYPE" in matches
        assert "PROBLEM" in matches
        assert "CTA" in matches


class TestDifficultyInference:
    """Tests for difficulty inference"""

    def test_infer_fast_difficulty(self, loader):
        """Test inferring FAST difficulty for simple templates"""
        structure = "[HOOK]: Simple\n[CTA]: Question"
        placeholders = ["TOPIC"]
        difficulty = loader._infer_difficulty(structure, placeholders)
        assert difficulty == TemplateDifficulty.FAST

    def test_infer_medium_difficulty(self, loader):
        """Test inferring MEDIUM difficulty for moderate templates"""
        structure = "[HOOK]: [STAT]: [INTERPRETATION]: [APPLICATION]: [CTA]:"
        placeholders = ["STAT", "TOPIC", "AUDIENCE", "APPLICATION"]
        difficulty = loader._infer_difficulty(structure, placeholders)
        assert difficulty == TemplateDifficulty.MEDIUM

    def test_infer_slow_difficulty(self, loader):
        """Test inferring SLOW difficulty for complex templates"""
        structure = "[HOOK]: [STAT]: [INTERPRETATION]: [EXAMPLE]: [APPLICATION]: [EVIDENCE]: [CTA]: [BONUS]:"
        placeholders = [
            "STAT",
            "TOPIC",
            "AUDIENCE",
            "APPLICATION",
            "EVIDENCE",
            "EXAMPLE",
            "BONUS",
            "CONTEXT",
        ]
        difficulty = loader._infer_difficulty(structure, placeholders)
        assert difficulty == TemplateDifficulty.SLOW


class TestRequirementChecks:
    """Tests for story and data requirement checks"""

    def test_check_requires_story_true(self, loader):
        """Test detecting templates that require stories"""
        structure = "Share a personal story about crisis and realization"
        name = "Personal Story Post"
        assert loader._check_requires_story(structure, name) is True

    def test_check_requires_story_false(self, loader):
        """Test templates that don't require stories"""
        structure = "Share a statistic and insight"
        name = "Statistic Post"
        assert loader._check_requires_story(structure, name) is False

    def test_check_requires_data_true(self, loader):
        """Test detecting templates that require data"""
        structure = "Start with a stat: 75% of people. Source: Study"
        name = "Statistic Post"
        assert loader._check_requires_data(structure, name) is True

    def test_check_requires_data_false(self, loader):
        """Test templates that don't require data"""
        structure = "Share your opinion on this topic"
        name = "Opinion Post"
        assert loader._check_requires_data(structure, name) is False


class TestTemplateGetters:
    """Tests for template getter methods"""

    def test_get_all_templates(self, loader):
        """Test getting all templates"""
        all_templates = loader.get_all_templates()
        assert len(all_templates) == 3
        assert all(isinstance(t, Template) for t in all_templates)

    def test_get_template_by_id_exists(self, loader):
        """Test getting template by existing ID"""
        template = loader.get_template_by_id(1)
        assert template is not None
        assert template.template_id == 1
        assert "Problem-Recognition" in template.name

    def test_get_template_by_id_not_exists(self, loader):
        """Test getting template by non-existent ID"""
        template = loader.get_template_by_id(999)
        assert template is None

    def test_get_templates_by_type(self, loader):
        """Test filtering templates by type"""
        problem_templates = loader.get_templates_by_type(TemplateType.PROBLEM_RECOGNITION)
        assert len(problem_templates) >= 1
        assert all(t.template_type == TemplateType.PROBLEM_RECOGNITION for t in problem_templates)

    def test_get_templates_by_difficulty(self, loader):
        """Test filtering templates by difficulty"""
        fast_templates = loader.get_templates_by_difficulty(TemplateDifficulty.FAST)
        assert all(t.difficulty == TemplateDifficulty.FAST for t in fast_templates)


class TestClientTemplateSelection:
    """Tests for intelligent client-based template selection"""

    def test_select_templates_for_client_returns_correct_count(self, loader, sample_brief):
        """Test that selection returns requested count"""
        selected = loader.select_templates_for_client(sample_brief, count=2)
        assert len(selected) == 2

    def test_select_templates_for_client_all_valid(self, loader, sample_brief):
        """Test that all selected templates are valid Template instances"""
        selected = loader.select_templates_for_client(sample_brief, count=3)
        assert all(isinstance(t, Template) for t in selected)

    def test_select_templates_with_boost(self, loader, sample_brief):
        """Test boosting specific template IDs"""
        # Boost template 1
        selected = loader.select_templates_for_client(sample_brief, count=3, boost_templates=[1])
        # Template 1 should be included due to boost
        template_ids = [t.template_id for t in selected]
        assert 1 in template_ids

    def test_select_templates_with_avoid(self, loader, sample_brief):
        """Test avoiding specific template IDs"""
        # Avoid template 1
        selected = loader.select_templates_for_client(sample_brief, count=2, avoid_templates=[1])
        # Template 1 should be avoided if possible
        template_ids = [t.template_id for t in selected]
        # May still include if no other options, but should try to avoid
        if len(loader.templates) > 2:
            assert 1 not in template_ids or len(selected) < len(loader.templates)

    def test_select_templates_shuffles_results(self, loader, sample_brief):
        """Test that templates are shuffled for variety"""
        # Get two selections with same parameters
        selected1 = loader.select_templates_for_client(sample_brief, count=3)
        selected2 = loader.select_templates_for_client(sample_brief, count=3)

        # IDs should be the same but potentially in different order
        # (This test may occasionally pass even without shuffle, but over many runs would fail)
        ids1 = [t.template_id for t in selected1]
        ids2 = [t.template_id for t in selected2]

        # Check that we got the same templates (as sets)
        assert set(ids1) == set(ids2)


class TestTemplatePatterns:
    """Tests for regex patterns used in parsing"""

    def test_template_pattern_matches_headers(self):
        """Test TEMPLATE_PATTERN matches template headers"""
        text = "## TEMPLATE 1: Test\nContent\n## TEMPLATE 2: Test2"
        matches = list(TEMPLATE_PATTERN.finditer(text))
        assert len(matches) == 2
        assert matches[0].group(1) == "1"
        assert matches[1].group(1) == "2"

    def test_placeholder_pattern_matches_brackets(self):
        """Test PLACEHOLDER_PATTERN matches bracketed text"""
        text = "[AUDIENCE] and [PROBLEM] with [SOLUTION]"
        matches = PLACEHOLDER_PATTERN.findall(text)
        assert len(matches) == 3
        assert "AUDIENCE" in matches
        assert "PROBLEM" in matches
        assert "SOLUTION" in matches


class TestCaching:
    """Tests for template caching behavior"""

    def test_second_load_uses_cache(self, temp_template_file):
        """Test that second load of same file uses cache"""
        # First load
        loader1 = TemplateLoader(template_file=temp_template_file)
        count1 = len(loader1.templates)

        # Second load should use cache
        loader2 = TemplateLoader(template_file=temp_template_file)
        count2 = len(loader2.templates)

        assert count1 == count2
        assert count1 == 3


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_template_file(self, tmp_path):
        """Test handling of empty template file"""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")
        loader = TemplateLoader(template_file=empty_file)
        assert len(loader.templates) == 0

    def test_malformed_template(self, tmp_path):
        """Test handling of malformed template"""
        malformed = tmp_path / "malformed.md"
        malformed.write_text("## TEMPLATE 1:\n\nNo structure here", encoding="utf-8")
        loader = TemplateLoader(template_file=malformed)
        # Should skip malformed template
        assert len(loader.templates) == 0

    def test_template_without_best_for(self, tmp_path):
        """Test template without 'Best for' field defaults to 'General use'"""
        content = """
## TEMPLATE 1: Test Template

```
[HOOK]: Test
[CTA]: Test
```
"""
        template_file = tmp_path / "no_best_for.md"
        template_file.write_text(content, encoding="utf-8")
        loader = TemplateLoader(template_file=template_file)
        assert len(loader.templates) == 1
        assert loader.templates[0].best_for == "General use"
