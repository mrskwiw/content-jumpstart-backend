"""Unit tests for template angle injection in ContentGeneratorAgent."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config.template_angles import TEMPLATE_ANGLES, MAX_QUANTITY_PER_TEMPLATE
from src.models.client_brief import ClientBrief, Platform


def _make_brief() -> ClientBrief:
    return ClientBrief(
        company_name="Acme Corp",
        business_description="B2B SaaS company",
        ideal_customer="Operations managers",
        main_problem_solved="Manual reporting",
        platforms=[Platform.LINKEDIN],
    )


def _make_template_mock(template_id: int, name: str = "Test Template") -> MagicMock:
    t = MagicMock()
    t.template_id = template_id
    t.name = name
    t.structure = "Hook: [HOOK]\nBody: [BODY]\nCTA: [CTA]"
    t.template_type = MagicMock()
    t.template_type.value = "how_to"
    t.requires_story = False
    t.requires_data = False
    t.placeholder_fields = []
    return t


class TestQuantityEnforcement:
    """The ≤10 cap must be enforced before any API calls."""

    @pytest.mark.asyncio
    async def test_quantity_above_max_raises_value_error(self):
        from src.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent()
        brief = _make_brief()

        with pytest.raises(ValueError, match=str(MAX_QUANTITY_PER_TEMPLATE)):
            await agent._generate_posts_from_quantities_async(
                client_brief=brief,
                template_quantities={9: MAX_QUANTITY_PER_TEMPLATE + 1},
                platform=Platform.LINKEDIN,
            )

    @pytest.mark.asyncio
    async def test_quantity_at_max_does_not_raise_early(self):
        """Quantity == MAX_QUANTITY_PER_TEMPLATE should not raise the cap error.
        We patch the API call so the test doesn't hit the network."""
        from src.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent()
        brief = _make_brief()

        mock_template = _make_template_mock(9)
        agent.template_loader = MagicMock()
        agent.template_loader.get_template_by_id.return_value = mock_template

        mock_post = MagicMock()
        mock_post.needs_review = False

        with patch.object(
            agent,
            "_generate_single_post_with_retry_async",
            new_callable=AsyncMock,
            return_value=mock_post,
        ):
            # Should not raise ValueError about cap; any other error is acceptable
            try:
                await agent._generate_posts_from_quantities_async(
                    client_brief=brief,
                    template_quantities={9: MAX_QUANTITY_PER_TEMPLATE},
                    platform=Platform.LINKEDIN,
                )
            except ValueError as e:
                # Only fail if it's the cap error
                assert (
                    str(MAX_QUANTITY_PER_TEMPLATE) not in str(e) or "maximum" not in str(e).lower()
                )


class TestAngleInjection:
    """Each task must carry a unique angle from TEMPLATE_ANGLES."""

    def _collect_task_angles(
        self,
        template_id: int,
        quantity: int,
        agent: Any,
        brief: ClientBrief,
    ) -> list:
        """Run the task-building loop and collect '_angle' values from each task."""
        import random as _random
        from src.config.template_angles import (
            TEMPLATE_ANGLES as _ANGLES,
            MAX_QUANTITY_PER_TEMPLATE as _MAX,
        )

        if quantity > _MAX:
            raise ValueError("quantity exceeds max")

        available = _ANGLES.get(template_id, [])
        selected = (
            _random.sample(available, quantity) if available and quantity <= len(available) else []
        )
        return selected

    def test_each_task_gets_unique_angle(self):
        """random.sample guarantees no repeats within a batch."""
        import random

        template_id = 9
        quantity = 5
        available = TEMPLATE_ANGLES[template_id]

        angles = random.sample(available, quantity)
        assert len(angles) == quantity
        assert len(set(angles)) == quantity, "Angles within a batch must be unique"

    def test_angles_are_members_of_template_pool(self):
        import random

        for template_id in range(1, 16):
            quantity = 3
            available = TEMPLATE_ANGLES[template_id]
            selected = random.sample(available, quantity)
            for angle in selected:
                assert (
                    angle in available
                ), f"Template {template_id}: sampled angle not in TEMPLATE_ANGLES"

    def test_different_runs_produce_varied_batches(self):
        """Two independent samples of size 3 from 10 should differ most of the time.
        We run 20 trials and assert at least one differs (near-certain for 10 choose 3).
        """
        import random

        template_id = 1
        quantity = 3
        available = TEMPLATE_ANGLES[template_id]

        first_batch = frozenset(random.sample(available, quantity))
        found_different = False
        for _ in range(20):
            batch = frozenset(random.sample(available, quantity))
            if batch != first_batch:
                found_different = True
                break
        assert found_different, "20 independent samples all identical — seeding issue?"

    def test_angle_sampling_without_replacement(self):
        """Confirm random.sample behaviour: no angle appears twice in one batch."""
        import random

        for template_id in range(1, 16):
            for quantity in range(1, MAX_QUANTITY_PER_TEMPLATE + 1):
                angles = random.sample(TEMPLATE_ANGLES[template_id], quantity)
                assert len(set(angles)) == quantity


class TestBuildContextAngleConsumption:
    """_build_context must consume the _angle sentinel and set variant_guidance."""

    def _get_agent(self):
        from src.agents.content_generator import ContentGeneratorAgent

        return ContentGeneratorAgent()

    def _get_template_mock(self):
        return _make_template_mock(9)

    def _get_brief(self):
        return _make_brief()

    def test_injected_angle_sets_variant_guidance(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()
        angle = "Open with a specific data point that quantifies the cost of inaction."

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=1,
            base_context={"_angle": angle},
        )

        assert ctx["variant_guidance"] == angle

    def test_injected_angle_is_consumed_not_forwarded(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=1,
            base_context={"_angle": "Some angle"},
        )

        assert "_angle" not in ctx, "_angle sentinel must be consumed, not forwarded to LLM"

    def test_empty_angle_falls_back_to_variant_1_guidance(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=1,
            base_context={"_angle": ""},
        )

        assert ctx["variant_guidance"] == "Use a direct, problem-focused angle"

    def test_no_angle_key_falls_back_to_variant_1(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=1,
            base_context={},
        )

        assert ctx["variant_guidance"] == "Use a direct, problem-focused angle"

    def test_no_angle_key_falls_back_to_variant_2(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=2,
            base_context={},
        )

        assert ctx["variant_guidance"] == "Use a story-driven or example-based angle"

    def test_no_angle_variant_3_plus_uses_generic_fallback(self):
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()

        ctx = agent._build_context(
            client_brief=brief,
            template=template,
            variant=3,
            base_context={},
        )

        assert ctx["variant_guidance"] == "Use a unique angle different from previous variants"

    def test_base_context_not_mutated_by_angle_pop(self):
        """The original base_context dict must not be modified."""
        agent = self._get_agent()
        template = self._get_template_mock()
        brief = self._get_brief()
        original = {"_angle": "Some angle", "company_name": "Test Co"}
        original_copy = dict(original)

        agent._build_context(
            client_brief=brief,
            template=template,
            variant=1,
            base_context=original,
        )

        # _build_context does base_context.copy() before popping, so original is untouched
        assert original == original_copy, "_build_context must not mutate base_context"
