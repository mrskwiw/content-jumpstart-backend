"""Tests for the model capability matrix and per-workload routing.

The load-bearing invariant here is that a Claude 5 request never carries a
sampling parameter — that combination is a hard 400 and would take the whole
generation pipeline down.
"""

from types import SimpleNamespace

import pytest

from src.utils.model_capabilities import (
    THINKING_MAX_TOKENS_FLOOR,
    WORKLOAD_ASSISTANT,
    WORKLOAD_GENERATION,
    WORKLOAD_RESEARCH,
    accepts_temperature,
    build_model_params,
    can_refuse,
    effort_for_temperature,
    enforce_token_floor,
    estimate_tokens,
    resolve_effort,
    resolve_model,
    resolve_thinking,
    supports_effort,
    supports_structured_outputs,
)

CLAUDE_5_MODELS = [
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
]

LEGACY_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-3-5-sonnet-20241022",
    "claude-opus-4-6",
    "claude-haiku-4-5",
]


def _settings(**overrides):
    """Build a settings stub with the fields the routing code reads."""
    base = {
        "ANTHROPIC_MODEL": "claude-sonnet-5",
        "ANTHROPIC_MODEL_GENERATION": None,
        "ANTHROPIC_MODEL_RESEARCH": None,
        "ANTHROPIC_MODEL_ASSISTANT": None,
        "ANTHROPIC_EFFORT_GENERATION": None,
        "ANTHROPIC_EFFORT_RESEARCH": None,
        "ANTHROPIC_EFFORT_ASSISTANT": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestSamplingSupport:
    @pytest.mark.parametrize("model", CLAUDE_5_MODELS)
    def test_claude_5_rejects_temperature(self, model):
        assert accepts_temperature(model) is False
        assert supports_effort(model) is True

    @pytest.mark.parametrize("model", LEGACY_MODELS)
    def test_legacy_accepts_temperature(self, model):
        assert accepts_temperature(model) is True
        assert supports_effort(model) is False

    def test_refusal_capable_models(self):
        assert can_refuse("claude-opus-5") is True
        assert can_refuse("claude-fable-5") is True
        assert can_refuse("claude-sonnet-4-5-20250929") is False


class TestStructuredOutputSupport:
    @pytest.mark.parametrize(
        "model", ["claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-haiku-4-5"]
    )
    def test_current_models_support_schemas(self, model):
        assert supports_structured_outputs(model) is True

    @pytest.mark.parametrize("model", ["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-20241022"])
    def test_legacy_models_do_not(self, model):
        """A legacy pin must keep prompt-and-parse rather than silently dropping
        the schema and reporting the response as validated."""
        assert supports_structured_outputs(model) is False


class TestEffortMapping:
    @pytest.mark.parametrize(
        "temperature,expected",
        [(0.0, "low"), (0.2, "low"), (0.3, "low"), (0.4, "medium"), (0.6, "medium"), (0.7, "high")],
    )
    def test_temperature_bands(self, temperature, expected):
        assert effort_for_temperature(temperature) == expected

    def test_never_produces_expensive_levels(self):
        """xhigh/max would also conflict with disabled thinking on Opus 5."""
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            assert effort_for_temperature(t) in {"low", "medium", "high"}

    def test_setting_overrides_temperature(self):
        settings = _settings(ANTHROPIC_EFFORT_RESEARCH="max")
        assert resolve_effort(WORKLOAD_RESEARCH, 0.2, settings) == "max"

    def test_falls_back_to_temperature_when_unset(self):
        assert resolve_effort(WORKLOAD_RESEARCH, 0.2, _settings()) == "low"


class TestModelRouting:
    def test_each_workload_uses_its_own_model(self):
        settings = _settings(
            ANTHROPIC_MODEL_RESEARCH="claude-opus-5",
            ANTHROPIC_MODEL_ASSISTANT="claude-fable-5",
        )
        assert resolve_model(WORKLOAD_GENERATION, settings) == "claude-sonnet-5"
        assert resolve_model(WORKLOAD_RESEARCH, settings) == "claude-opus-5"
        assert resolve_model(WORKLOAD_ASSISTANT, settings) == "claude-fable-5"

    def test_unset_workload_falls_back_to_base_model(self):
        """Single-model deployments must keep working unchanged."""
        settings = _settings(ANTHROPIC_MODEL="claude-opus-4-8")
        for workload in (WORKLOAD_GENERATION, WORKLOAD_RESEARCH, WORKLOAD_ASSISTANT):
            assert resolve_model(workload, settings) == "claude-opus-4-8"

    def test_non_string_setting_is_ignored(self):
        """A Mock-valued attribute must not be mistaken for real config."""
        settings = _settings(ANTHROPIC_MODEL_RESEARCH=object())
        assert resolve_model(WORKLOAD_RESEARCH, settings) == "claude-sonnet-5"

    def test_unknown_workload_raises(self):
        with pytest.raises(ValueError, match="Unknown workload"):
            resolve_model("summarisation", _settings())


class TestThinkingPolicy:
    def test_generation_disables_thinking(self):
        assert resolve_thinking("claude-sonnet-5", WORKLOAD_GENERATION, "high") == {
            "type": "disabled"
        }

    @pytest.mark.parametrize("workload", [WORKLOAD_RESEARCH, WORKLOAD_ASSISTANT])
    def test_judgment_workloads_use_adaptive(self, workload):
        assert resolve_thinking("claude-opus-5", workload, "high") == {"type": "adaptive"}

    def test_tools_force_adaptive_even_for_generation(self):
        """Disabling thinking on a tool-using Opus 5 call lets it emit a tool
        call as plain text, completing the turn without running the tool."""
        assert resolve_thinking("claude-opus-5", WORKLOAD_GENERATION, "high", has_tools=True) == {
            "type": "adaptive"
        }

    @pytest.mark.parametrize("effort", ["xhigh", "max"])
    def test_high_effort_downgrades_disabled_to_adaptive(self, effort):
        """Opus 5 returns 400 for disabled thinking above `high` effort."""
        assert resolve_thinking("claude-opus-5", WORKLOAD_GENERATION, effort) == {
            "type": "adaptive"
        }

    def test_explicit_value_wins(self):
        explicit = {"type": "adaptive", "display": "summarized"}
        assert (
            resolve_thinking("claude-sonnet-5", WORKLOAD_GENERATION, "high", explicit=explicit)
            == explicit
        )

    def test_legacy_model_omits_the_parameter(self):
        assert resolve_thinking("claude-sonnet-4-5-20250929", WORKLOAD_RESEARCH, "high") is None


class TestBuildModelParams:
    @pytest.mark.parametrize("model", CLAUDE_5_MODELS)
    def test_claude_5_never_carries_temperature(self, model):
        """The regression this whole module exists to prevent."""
        params = build_model_params(model, 0.7, WORKLOAD_GENERATION, settings_obj=_settings())
        assert "temperature" not in params
        assert "top_p" not in params
        assert "top_k" not in params
        assert params["output_config"]["effort"] == "high"

    @pytest.mark.parametrize("model", LEGACY_MODELS)
    def test_legacy_keeps_temperature_and_omits_effort(self, model):
        params = build_model_params(model, 0.7, WORKLOAD_GENERATION, settings_obj=_settings())
        assert params == {"temperature": 0.7}

    def test_extraction_temperature_maps_to_low_effort(self):
        params = build_model_params(
            "claude-sonnet-5", 0.2, WORKLOAD_GENERATION, settings_obj=_settings()
        )
        assert params["output_config"]["effort"] == "low"

    def test_explicit_effort_bypasses_temperature_mapping(self):
        params = build_model_params(
            "claude-sonnet-5", 0.7, WORKLOAD_GENERATION, effort="low", settings_obj=_settings()
        )
        assert params["output_config"]["effort"] == "low"

    def test_research_call_gets_adaptive_thinking(self):
        params = build_model_params(
            "claude-opus-5", 0.4, WORKLOAD_RESEARCH, settings_obj=_settings()
        )
        assert params["thinking"] == {"type": "adaptive"}


class TestTokenFloor:
    def test_raises_tight_cap_when_thinking_enabled(self):
        """A research tool's 200-token cap would be consumed entirely by thinking."""
        params = {"thinking": {"type": "adaptive"}}
        assert enforce_token_floor(200, params) == THINKING_MAX_TOKENS_FLOOR

    def test_leaves_generous_cap_alone(self):
        params = {"thinking": {"type": "adaptive"}}
        assert enforce_token_floor(64000, params) == 64000

    def test_no_op_when_thinking_disabled(self):
        assert enforce_token_floor(200, {"thinking": {"type": "disabled"}}) == 200

    def test_no_op_on_legacy_params(self):
        assert enforce_token_floor(200, {"temperature": 0.7}) == 200


class TestTokenEstimate:
    def test_claude_5_tokenizer_estimates_higher(self):
        """The Opus 4.7 tokenizer produces ~30% more tokens for the same text."""
        legacy = estimate_tokens(10_000, "claude-sonnet-4-5-20250929")
        claude_5 = estimate_tokens(10_000, "claude-sonnet-5")
        assert claude_5 > legacy
        assert 1.2 < (claude_5 / legacy) < 1.4
