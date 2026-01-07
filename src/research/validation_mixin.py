"""Common validation patterns for research tools

This mixin provides standard validation methods that are shared across
all 12 research tools, eliminating ~1,400 lines of duplicate code.

Phase 3 Performance Optimization - Research Tool Deduplication
"""

from typing import Any, Dict, List, Optional


class CommonValidationMixin:
    """Mixin providing standard validation patterns for research tools

    Usage:
        class MyResearchTool(ResearchTool, CommonValidationMixin):
            def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
                inputs["business_description"] = self.validate_business_description(inputs)
                inputs["target_audience"] = self.validate_target_audience(inputs)
                # Add tool-specific validations...
                return True
    """

    def validate_business_description(
        self,
        inputs: Dict[str, Any],
        min_length: int = 50,
        max_length: int = 5000,
    ) -> str:
        """Validate and sanitize business description

        Args:
            inputs: Input dictionary containing 'business_description'
            min_length: Minimum character length (default: 50)
            max_length: Maximum character length (default: 5000)

        Returns:
            Sanitized business description string

        Raises:
            ValueError: If validation fails
        """
        return self.validator.validate_text(  # type: ignore[attr-defined, no-any-return]
            inputs.get("business_description"),
            field_name="business_description",
            min_length=min_length,
            max_length=max_length,
            required=True,
            sanitize=True,
        )

    def validate_target_audience(
        self,
        inputs: Dict[str, Any],
        min_length: int = 10,
        max_length: int = 2000,
    ) -> str:
        """Validate and sanitize target audience description

        Args:
            inputs: Input dictionary containing 'target_audience'
            min_length: Minimum character length (default: 10)
            max_length: Maximum character length (default: 2000)

        Returns:
            Sanitized target audience string

        Raises:
            ValueError: If validation fails
        """
        return self.validator.validate_text(  # type: ignore[attr-defined, no-any-return]
            inputs.get("target_audience"),
            field_name="target_audience",
            min_length=min_length,
            max_length=max_length,
            required=True,
            sanitize=True,
        )

    def validate_optional_business_name(
        self,
        inputs: Dict[str, Any],
        min_length: int = 2,
        max_length: int = 200,
    ) -> Optional[str]:
        """Validate optional business name

        Args:
            inputs: Input dictionary potentially containing 'business_name'
            min_length: Minimum character length (default: 2)
            max_length: Maximum character length (default: 200)

        Returns:
            Sanitized business name or None if not provided
        """
        if "business_name" not in inputs or not inputs["business_name"]:
            return None

        return self.validator.validate_text(  # type: ignore[attr-defined, no-any-return]
            inputs["business_name"],
            field_name="business_name",
            min_length=min_length,
            max_length=max_length,
            required=False,
            sanitize=True,
        )

    def validate_optional_industry(
        self,
        inputs: Dict[str, Any],
        min_length: int = 2,
        max_length: int = 200,
    ) -> Optional[str]:
        """Validate optional industry

        Args:
            inputs: Input dictionary potentially containing 'industry'
            min_length: Minimum character length (default: 2)
            max_length: Maximum character length (default: 200)

        Returns:
            Sanitized industry or None if not provided
        """
        if "industry" not in inputs or not inputs["industry"]:
            return None

        return self.validator.validate_text(  # type: ignore[attr-defined, no-any-return]
            inputs["industry"],
            field_name="industry",
            min_length=min_length,
            max_length=max_length,
            required=False,
            sanitize=True,
        )

    def validate_competitor_list(
        self,
        inputs: Dict[str, Any],
    ) -> List[str]:
        """Validate list of competitors

        Args:
            inputs: Input dictionary containing 'competitors'

        Returns:
            Validated list of competitor names (max 20, enforced by validator)

        Raises:
            ValueError: If validation fails
        """
        from ..validators.research_input_validator import validate_competitor_list

        return validate_competitor_list(
            inputs.get("competitors", []),
            validator=self.validator,  # type: ignore[attr-defined, no-any-return]
        )

    def validate_optional_goals(
        self,
        inputs: Dict[str, Any],
        max_goals: int = 10,
    ) -> Optional[List[str]]:
        """Validate optional list of business goals

        Args:
            inputs: Input dictionary potentially containing 'goals'
            max_goals: Maximum number of goals (default: 10)

        Returns:
            Validated list of goals or None if not provided
        """
        if "goals" not in inputs or not inputs["goals"]:
            return None

        return self.validator.validate_list(  # type: ignore[attr-defined, no-any-return]
            inputs["goals"],
            field_name="goals",
            max_length=max_goals,
            item_type=str,
        )

    def validate_optional_url(
        self,
        inputs: Dict[str, Any],
        field_name: str = "website_url",
    ) -> Optional[str]:
        """Validate optional URL

        Args:
            inputs: Input dictionary potentially containing URL field
            field_name: Name of the URL field (default: 'website_url')

        Returns:
            Validated URL or None if not provided
        """
        if field_name not in inputs or not inputs[field_name]:
            return None

        url = inputs[field_name]

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://{url}"

        return self.validator.validate_text(  # type: ignore[attr-defined, no-any-return]
            url,
            field_name=field_name,
            min_length=10,
            max_length=500,
            required=False,
            sanitize=True,
        )
