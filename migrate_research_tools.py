#!/usr/bin/env python
"""Script to migrate remaining research tools to use deduplication utilities

This script automatically:
1. Adds CommonValidationMixin import and inheritance
2. Replaces validation code with mixin methods
3. Replaces API calls with _call_claude_api()
4. Removes unused imports
"""

import re
from pathlib import Path


def migrate_tool(file_path: Path) -> None:
    """Migrate a single research tool file"""
    print(f"\n{'='*60}")
    print(f"Migrating: {file_path.name}")
    print("=" * 60)

    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Step 1: Add CommonValidationMixin import if not present
    if "CommonValidationMixin" not in content:
        # Find the import section and add the mixin import
        if "from .base import ResearchTool" in content:
            content = content.replace(
                "from .base import ResearchTool",
                "from .base import ResearchTool\nfrom .validation_mixin import CommonValidationMixin",
            )
            print("[OK] Added CommonValidationMixin import")

    # Step 2: Add CommonValidationMixin to class inheritance
    # Find class declaration like: class XxxTool(ResearchTool):
    class_pattern = r"(class \w+\(ResearchTool)\):"
    if re.search(class_pattern, content) and "CommonValidationMixin" not in content:
        content = re.sub(class_pattern, r"\1, CommonValidationMixin):", content)
        print("[OK] Added CommonValidationMixin to class inheritance")

    # Step 3: Remove get_default_client import if present
    if "from ..utils.anthropic_client import get_default_client" in content:
        content = content.replace("from ..utils.anthropic_client import get_default_client\n", "")
        print("[OK] Removed get_default_client import")

    # Step 4: Replace API call patterns
    # Pattern: client = get_default_client() followed by response = client.create_message()
    api_call_pattern = re.compile(
        r"client = get_default_client\(\)\n\s+"
        r"(.*?)"  # Prompt content
        r"response = client\.create_message\(\s*"
        r'messages=\[\{"role": "user", "content": prompt\}\],?\s*'
        r"max_tokens=(\d+),?\s*"
        r"(?:temperature=([\d.]+),?\s*)?"
        r"\)",
        re.DOTALL,
    )

    def replace_api_call(match):
        prompt_section = match.group(1)
        max_tokens = match.group(2)
        temperature = match.group(3) if match.group(3) else "0.4"

        return (
            f"{prompt_section}"
            f"# Call Claude API with automatic JSON extraction (Phase 3 deduplication)\n        "
            f"data = self._call_claude_api(\n            "
            f"prompt, max_tokens={max_tokens}, temperature={temperature}, "
            f"extract_json=True, fallback_on_error={{}}\n        )"
        )

    matches = len(api_call_pattern.findall(content))
    if matches > 0:
        content = api_call_pattern.sub(replace_api_call, content)
        print(f"[OK] Replaced {matches} API call(s) with _call_claude_api()")

    # Step 5: Replace _extract_json_from_response(response) with direct use
    content = re.sub(
        r"return self\._extract_json_from_response\(response\)", "return data", content
    )

    # Step 6: Replace validation patterns with mixin methods
    # Business description
    content = re.sub(
        r'inputs\["business_description"\] = self\.validator\.validate_text\(\s*'
        r'inputs\.get\("business_description"\),\s*'
        r'field_name="business_description",\s*'
        r"min_length=\d+,\s*"
        r"max_length=\d+,\s*"
        r"required=True,\s*"
        r"sanitize=True,?\s*"
        r"\)",
        'inputs["business_description"] = self.validate_business_description(inputs)',
        content,
    )

    # Target audience
    content = re.sub(
        r'inputs\["target_audience"\] = self\.validator\.validate_text\(\s*'
        r'inputs\.get\("target_audience"\),\s*'
        r'field_name="target_audience",\s*'
        r"min_length=(\d+),\s*"
        r"max_length=\d+,\s*"
        r"required=True,\s*"
        r"sanitize=True,?\s*"
        r"\)",
        lambda m: f'inputs["target_audience"] = self.validate_target_audience(inputs, min_length={m.group(1)})'
        if m.group(1) != "10"
        else 'inputs["target_audience"] = self.validate_target_audience(inputs)',
        content,
    )

    # Optional business name
    content = re.sub(
        r'if "business_name" in inputs and inputs\["business_name"\]:\s*'
        r'inputs\["business_name"\] = self\.validator\.validate_text\(\s*'
        r'inputs\["business_name"\],\s*'
        r'field_name="business_name",\s*'
        r"min_length=\d+,\s*"
        r"max_length=\d+,\s*"
        r"required=False,\s*"
        r"sanitize=True,?\s*"
        r"\)",
        'inputs["business_name"] = self.validate_optional_business_name(inputs)',
        content,
    )

    # Optional industry
    content = re.sub(
        r'if "industry" in inputs and inputs\["industry"\]:\s*'
        r'inputs\["industry"\] = self\.validator\.validate_text\(\s*'
        r'inputs\["industry"\],\s*'
        r'field_name="industry",\s*'
        r"min_length=\d+,\s*"
        r"max_length=\d+,\s*"
        r"required=False,\s*"
        r"sanitize=True,?\s*"
        r"\)",
        'inputs["industry"] = self.validate_optional_industry(inputs)',
        content,
    )

    # Competitors
    content = re.sub(
        r'if "competitors" in inputs and inputs\["competitors"\]:\s*'
        r'inputs\["competitors"\] = validate_competitor_list\(\s*'
        r'inputs\["competitors"\],\s*'
        r"validator=self\.validator,?\s*"
        r"\)",
        'if "competitors" in inputs and inputs["competitors"]:\n        inputs["competitors"] = self.validate_competitor_list(inputs)',
        content,
    )

    # Write back if changed
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print("[OK] File updated successfully")
        return True
    else:
        print("  No changes needed")
        return False


def main():
    """Migrate all research tools"""
    project_root = Path(__file__).parent
    research_dir = project_root / "src" / "research"

    # List of tools to migrate (excluding base.py, validation_mixin.py, and already migrated)
    tools_to_migrate = [
        "market_trends_research.py",
        "content_gap_analysis.py",
        "platform_strategy.py",
        "competitive_analysis.py",
        "content_audit.py",
        "brand_archetype.py",
        "content_calendar_strategy.py",
        "voice_analysis.py",
        "story_mining.py",
        "icp_workshop.py",
    ]

    migrated = []
    for tool_file in tools_to_migrate:
        file_path = research_dir / tool_file
        if file_path.exists():
            if migrate_tool(file_path):
                migrated.append(tool_file)
        else:
            print(f"[WARNING] File not found: {tool_file}")

    print(f"\n{'='*60}")
    print(f"Migration Complete!")
    print(f"{'='*60}")
    print(f"Migrated {len(migrated)} files:")
    for f in migrated:
        print(f"  [OK] {f}")


if __name__ == "__main__":
    main()
