"""
Unit tests for the skill loader utility.

Tests the SkillLoader class and related utility functions for loading
external skill definitions from SKILL.md files.
"""

from pathlib import Path

import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from src.utils.skill_loader import (
    SkillLoader,
    Skill,
    SkillMetadata,
    SkillReference,
    load_skill,
    list_skills,
    get_skill_reference,
    get_skill_loader,
)


def _skills_present() -> bool:
    """True only when the real skill packages are on disk.

    The skill packages (content-creator, marketing-strategy-pmm) live OUTSIDE the
    git repo (workspace root, the parent of project/), so they're present locally
    but NOT in CI's project-only checkout. Integration tests that load them are
    guarded to skip when absent.
    """
    try:
        return (get_skill_loader().skills_base / "content-creator").exists()
    except Exception:
        return False


_requires_skills = pytest.mark.skipif(
    not _skills_present(), reason="external skill packages not present (not in CI)"
)


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""

    def test_metadata_defaults(self):
        """Test default values for metadata fields."""
        metadata = SkillMetadata(name="test", description="Test skill")

        assert metadata.name == "test"
        assert metadata.description == "Test skill"
        assert metadata.version == "1.0.0"
        assert metadata.author == ""
        assert metadata.license == "MIT"
        assert metadata.category == ""
        assert metadata.domain == ""
        assert metadata.python_tools == []
        assert metadata.tech_stack == []
        assert metadata.keywords == []

    def test_metadata_with_values(self):
        """Test metadata with explicit values."""
        metadata = SkillMetadata(
            name="content-creator",
            description="Content creation skill",
            version="2.0.0",
            author="Test Author",
            category="marketing",
            domain="content",
            python_tools=["tool1", "tool2"],
            tech_stack=["python", "react"],
        )

        assert metadata.name == "content-creator"
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.category == "marketing"
        assert len(metadata.python_tools) == 2
        assert len(metadata.tech_stack) == 2


class TestSkill:
    """Tests for Skill dataclass."""

    def test_skill_get_reference(self):
        """Test getting a reference by name."""
        ref = SkillReference(name="test_ref", path=Path("/fake/path"), content="Test content")
        skill = Skill(
            metadata=SkillMetadata(name="test", description="Test"),
            path=Path("/fake/skill"),
            documentation="# Test Skill",
            references={"test_ref": ref},
        )

        assert skill.get_reference("test_ref") == "Test content"
        assert skill.get_reference("nonexistent") is None

    def test_skill_get_all_references(self):
        """Test getting all references."""
        skill = Skill(
            metadata=SkillMetadata(name="test", description="Test"),
            path=Path("/fake/skill"),
            documentation="# Test",
            references={
                "ref1": SkillReference(name="ref1", path=Path("/a"), content="Content 1"),
                "ref2": SkillReference(name="ref2", path=Path("/b"), content="Content 2"),
            },
        )

        refs = skill.get_all_references()
        assert len(refs) == 2
        assert refs["ref1"] == "Content 1"
        assert refs["ref2"] == "Content 2"

    def test_skill_get_script_module_exists(self):
        """Test getting a script module that exists (lines 78-79)."""
        from src.utils.skill_loader import SkillScript
        import types

        # Create a mock module
        mock_module = types.ModuleType("test_module")

        skill = Skill(
            metadata=SkillMetadata(name="test", description="Test"),
            path=Path("/fake/skill"),
            documentation="# Test",
            references={},
            scripts={
                "test_script": SkillScript(
                    name="test_script",
                    path=Path("/fake/script.py"),
                    module=mock_module,
                )
            },
        )

        result = skill.get_script_module("test_script")
        assert result is mock_module

    def test_skill_get_script_module_not_exists(self):
        """Test getting a script module that doesn't exist (lines 78-79)."""
        skill = Skill(
            metadata=SkillMetadata(name="test", description="Test"),
            path=Path("/fake/skill"),
            documentation="# Test",
            references={},
            scripts={},
        )

        result = skill.get_script_module("nonexistent")
        assert result is None

    def test_skill_get_script_module_no_module_loaded(self):
        """Test getting a script where module is None (lines 78-79)."""
        from src.utils.skill_loader import SkillScript

        skill = Skill(
            metadata=SkillMetadata(name="test", description="Test"),
            path=Path("/fake/skill"),
            documentation="# Test",
            references={},
            scripts={
                "test_script": SkillScript(
                    name="test_script",
                    path=Path("/fake/script.py"),
                    module=None,  # Module not loaded
                )
            },
        )

        result = skill.get_script_module("test_script")
        assert result is None


class TestSkillLoader:
    """Tests for SkillLoader class."""

    def test_parse_yaml_frontmatter_valid(self):
        """Test parsing valid YAML frontmatter."""
        loader = SkillLoader(skills_base_path=Path("/fake"))
        content = """---
name: test-skill
description: A test skill
metadata:
  version: "1.0.0"
  category: testing
---
# Test Skill Documentation

This is the skill documentation.
"""
        frontmatter, documentation = loader._parse_yaml_frontmatter(content)

        assert frontmatter["name"] == "test-skill"
        assert frontmatter["description"] == "A test skill"
        assert frontmatter["metadata"]["version"] == "1.0.0"
        assert "Test Skill Documentation" in documentation

    def test_parse_yaml_frontmatter_no_yaml(self):
        """Test parsing content without YAML frontmatter."""
        loader = SkillLoader(skills_base_path=Path("/fake"))
        content = "# Just Markdown\n\nNo frontmatter here."

        frontmatter, documentation = loader._parse_yaml_frontmatter(content)

        assert frontmatter == {}
        assert documentation == content

    def test_parse_yaml_frontmatter_invalid_yaml(self):
        """Test parsing content with invalid YAML frontmatter (lines 129-130)."""
        loader = SkillLoader(skills_base_path=Path("/fake"))
        # Invalid YAML - unquoted colon in value and bad indentation
        content = """---
name: test
invalid: [unclosed bracket
  bad: indentation
---
# Documentation"""

        frontmatter, documentation = loader._parse_yaml_frontmatter(content)

        # Should return empty frontmatter and full content on YAML error
        assert frontmatter == {}
        assert "---" in documentation  # Returns original content

    def test_parse_metadata(self):
        """Test parsing metadata from frontmatter."""
        loader = SkillLoader(skills_base_path=Path("/fake"))
        frontmatter = {
            "name": "test-skill",
            "description": "Test description",
            "metadata": {
                "version": "2.0.0",
                "author": "Test Author",
                "category": "testing",
                "python-tools": "tool1, tool2",
                "tech-stack": ["python", "nodejs"],
            },
        }

        metadata = loader._parse_metadata(frontmatter)

        assert metadata.name == "test-skill"
        assert metadata.description == "Test description"
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.category == "testing"
        assert metadata.python_tools == ["tool1", "tool2"]
        assert metadata.tech_stack == ["python", "nodejs"]


@_requires_skills
class TestIntegration:
    """Integration tests with actual skill directories."""

    def test_list_available_skills(self):
        """Test listing available skills (requires actual skill directories)."""
        # Use the actual skills base path
        # Skills are in repository root: content-creator/, marketing-strategy-pmm/
        project_root = Path(__file__).parent.parent.parent
        skills_base = (
            project_root.parent
        )  # skills live in repo root (parent of project/) after Phase 5 test relocation

        loader = SkillLoader(skills_base_path=skills_base)
        skills = loader.list_available_skills()

        # Should find content-creator and marketing-strategy-pmm
        assert "content-creator" in skills
        assert "marketing-strategy-pmm" in skills

    def test_load_content_creator_skill(self):
        """Test loading the content-creator skill."""
        project_root = Path(__file__).parent.parent.parent
        skills_base = (
            project_root.parent
        )  # skills live in repo root (parent of project/) after Phase 5 test relocation

        loader = SkillLoader(skills_base_path=skills_base)
        skill = loader.load_skill("content-creator")

        assert skill is not None
        assert skill.metadata.name == "content-creator"
        assert skill.metadata.category == "marketing"
        assert len(skill.references) > 0

    def test_load_marketing_pmm_skill(self):
        """Test loading the marketing-strategy-pmm skill."""
        project_root = Path(__file__).parent.parent.parent
        skills_base = (
            project_root.parent
        )  # skills live in repo root (parent of project/) after Phase 5 test relocation

        loader = SkillLoader(skills_base_path=skills_base)
        skill = loader.load_skill("marketing-strategy-pmm")

        assert skill is not None
        assert skill.metadata.name == "marketing-strategy-pmm"

    def test_load_nonexistent_skill(self):
        """Test loading a skill that doesn't exist."""
        project_root = Path(__file__).parent.parent.parent
        skills_base = (
            project_root.parent
        )  # skills live in repo root (parent of project/) after Phase 5 test relocation

        loader = SkillLoader(skills_base_path=skills_base)
        skill = loader.load_skill("nonexistent-skill")

        assert skill is None

    def test_skill_caching(self):
        """Test that skills are cached after loading."""
        project_root = Path(__file__).parent.parent.parent
        skills_base = project_root.parent

        loader = SkillLoader(skills_base_path=skills_base)

        # Load skill twice
        skill1 = loader.load_skill("content-creator")
        skill2 = loader.load_skill("content-creator")

        # Should be the same object (cached)
        assert skill1 is skill2


@_requires_skills
class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_load_skill_function(self):
        """Test the load_skill convenience function."""
        skill = load_skill("content-creator")
        assert skill is not None
        assert skill.metadata.name == "content-creator"

    def test_list_skills_function(self):
        """Test the list_skills convenience function."""
        skills = list_skills()
        assert isinstance(skills, list)
        assert "content-creator" in skills

    def test_get_skill_reference_function(self):
        """Test the get_skill_reference convenience function."""
        # Get an actual reference
        skill = load_skill("content-creator")
        if skill and skill.references:
            ref_name = list(skill.references.keys())[0]
            content = get_skill_reference("content-creator", ref_name)
            assert content is not None
            assert len(content) > 0

    def test_get_skill_loader_singleton(self):
        """Test the singleton skill loader."""
        loader1 = get_skill_loader()
        loader2 = get_skill_loader()

        assert loader1 is loader2


@_requires_skills
class TestAgentToolsIntegration:
    """Tests for AgentTools skill integration."""

    def test_agent_tools_skill_methods(self):
        """Test that AgentTools has skill-related methods."""
        from agent.tools import AgentTools

        tools = AgentTools()

        # Check methods exist
        assert hasattr(tools, "get_available_skills")
        assert hasattr(tools, "get_skill_info")
        assert hasattr(tools, "get_skill_reference")
        assert hasattr(tools, "get_all_skill_references")

    def test_agent_tools_get_available_skills(self):
        """Test getting available skills through AgentTools."""
        from agent.tools import AgentTools

        tools = AgentTools()
        result = tools.get_available_skills()

        assert result["success"] is True
        assert result["count"] >= 2

        skill_names = [s["name"] for s in result["skills"]]
        assert "content-creator" in skill_names
        assert "marketing-strategy-pmm" in skill_names

    def test_agent_tools_get_skill_info(self):
        """Test getting skill info through AgentTools."""
        from agent.tools import AgentTools

        tools = AgentTools()
        result = tools.get_skill_info("content-creator")

        assert result["success"] is True
        assert result["name"] == "content-creator"
        assert result["category"] == "marketing"
        assert isinstance(result["references"], list)

    def test_agent_tools_skill_in_available_tools(self):
        """Test that skill tools appear in available tools list."""
        from agent.tools import AgentTools

        tools = AgentTools()
        available = tools.get_available_tools()

        tool_names = [t["name"] for t in available]

        assert "get_available_skills" in tool_names
        assert "get_skill_info" in tool_names
        assert "get_skill_reference" in tool_names
        assert "get_all_skill_references" in tool_names
