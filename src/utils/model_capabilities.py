"""Model capability matrix and per-workload model routing for the Anthropic API.

Why this module exists
----------------------
The Claude 5 generation (Opus 5, Sonnet 5, Fable 5) and the Opus 4.7/4.8 line
**removed the sampling parameters**. Sending ``temperature`` to any of them is a
400. This pipeline expresses generation intent as temperature in ~117 call sites
(0.2-0.3 for extraction, 0.7-0.8 for creative generation), and that intent is
worth keeping. So rather than rewrite every call site, this module translates
temperature into ``output_config.effort`` at the moment the request is built.

It also owns per-workload model routing, so no call site needs to know which
model generation it is talking to:

===============  ==========================  ==========  =========================
Workload         Model                       Thinking    Rationale
===============  ==========================  ==========  =========================
``generation``   ``ANTHROPIC_MODEL``         disabled    Bulk post generation and
                 (default ``claude-sonnet-5``)           extraction. Cost-dominant
                                                         path; no tool use.
``research``     ``ANTHROPIC_MODEL_RESEARCH``  adaptive  $300-600/run deliverables;
                 (default ``claude-opus-5``)             quality dominates volume.
``assistant``    ``ANTHROPIC_MODEL_ASSISTANT`` adaptive  Tool-using agentic loop.
                 (default ``claude-opus-5``)             MUST NOT disable thinking.
===============  ==========================  ==========  =========================

⚠ Never disable thinking on a tool-using Opus 5 call. With thinking off, Opus 5
can emit a tool call as plain assistant text instead of a ``tool_use`` block: the
turn completes normally, the tool silently never runs, and in an agentic loop
that bogus text pollutes every later turn. :func:`resolve_thinking` enforces this.

Effort is derived from temperature rather than pinned per workload so the
existing per-agent tuning survives the migration intact. ``ANTHROPIC_EFFORT_*``
settings override it per workload once there is measured data to tune against.

Reference: ``docs/ANTHROPIC_MODEL_SDK_UPGRADE_PLAN.md``
"""

from typing import Any, Dict, Optional

# Model families that reject temperature/top_p/top_k outright (400).
# Sonnet 5 technically accepts a *default* temperature, but every call site here
# passes an explicit non-default value, so it belongs in this list.
_NO_SAMPLING_PARAMS = (
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-opus-4-8",
    "claude-opus-4-7",
)

# Models whose safety classifiers can decline a request with HTTP 200 and
# ``stop_reason == "refusal"`` instead of returning content.
_CAN_REFUSE = (
    "claude-opus-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-sonnet-5",
)

# Disabling thinking is only accepted at effort "high" or below on Opus 5.
_EFFORT_INCOMPATIBLE_WITH_DISABLED_THINKING = ("xhigh", "max")

WORKLOAD_GENERATION = "generation"
WORKLOAD_RESEARCH = "research"
WORKLOAD_ASSISTANT = "assistant"

_VALID_WORKLOADS = (WORKLOAD_GENERATION, WORKLOAD_RESEARCH, WORKLOAD_ASSISTANT)


def accepts_temperature(model: str) -> bool:
    """Whether ``model`` accepts the ``temperature`` request parameter.

    Models in the Claude 5 / Opus 4.7+ generations removed sampling parameters
    and return 400 if one is supplied.

    Args:
        model: Anthropic model ID (e.g. ``"claude-sonnet-5"``).

    Returns:
        True for legacy models that still accept ``temperature``.
    """
    return not model.startswith(_NO_SAMPLING_PARAMS)


def supports_effort(model: str) -> bool:
    """Whether ``model`` accepts ``output_config.effort``.

    Effort and sampling parameters are mutually exclusive across the model
    generations this codebase targets, so this is the inverse of
    :func:`accepts_temperature`. Kept as a separate named predicate because the
    two concepts diverge on Opus 4.6 / Sonnet 4.6, which accept both.

    Args:
        model: Anthropic model ID.

    Returns:
        True if ``output_config.effort`` may be sent.
    """
    return not accepts_temperature(model)


def can_refuse(model: str) -> bool:
    """Whether ``model`` may return ``stop_reason == "refusal"`` with no content.

    Callers must check ``stop_reason`` before indexing into ``response.content``.

    Args:
        model: Anthropic model ID.

    Returns:
        True if the model's safety classifiers can decline a request.
    """
    return model.startswith(_CAN_REFUSE)


#: Models that accept ``output_config.format`` (schema-constrained JSON output).
#: Notably excludes Sonnet 4.5 and the Claude 3 line, so a legacy pin must keep
#: using prompt-and-parse rather than silently dropping the constraint.
_STRUCTURED_OUTPUT_MODELS = (
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
    "claude-haiku-4-5",
    "claude-opus-4-5",
    "claude-opus-4-1",
)


def supports_structured_outputs(model: str) -> bool:
    """Whether ``model`` accepts ``output_config.format`` for guaranteed-valid JSON.

    Args:
        model: Anthropic model ID.

    Returns:
        True if a JSON schema may be attached to the request.
    """
    return model.startswith(_STRUCTURED_OUTPUT_MODELS)


def effort_for_temperature(temperature: float) -> str:
    """Translate a legacy sampling temperature into an effort level.

    The pipeline's temperature values encode task intent, and that mapping is
    preserved rather than discarded:

    * ``<= 0.3`` -> ``"low"``    - extraction, parsing, classification
    * ``<= 0.6`` -> ``"medium"`` - analysis, refinement
    * ``> 0.6``  -> ``"high"``   - creative generation

    ``high`` is the API default, so the top band is not an escalation. Levels
    above ``high`` (``xhigh``, ``max``) are never produced here: they are
    materially more expensive and would also conflict with disabled thinking.

    Args:
        temperature: The legacy sampling temperature, 0.0-1.0.

    Returns:
        One of ``"low"``, ``"medium"``, ``"high"``.
    """
    if temperature <= 0.3:
        return "low"
    if temperature <= 0.6:
        return "medium"
    return "high"


def _load_settings(settings_obj: Any = None) -> Any:
    """Return the settings object to read configuration from.

    Callers pass their own module-level ``settings`` reference so that a test
    patching ``<their module>.settings`` actually takes effect here — importing
    ``src.config.settings`` directly would silently bypass such a patch.
    """
    if settings_obj is not None:
        return settings_obj
    # Imported lazily: this module is imported by agent/ and backend/ code paths
    # that must not pay for settings construction at import time.
    from ..config.settings import settings

    return settings


def _configured_str(settings_obj: Any, name: str) -> Optional[str]:
    """Read a string setting, ignoring unset and non-string values.

    The isinstance guard keeps a MagicMock-based test settings object (where
    every attribute is a truthy Mock) from being mistaken for real config.
    """
    value = getattr(settings_obj, name, None)
    return value if isinstance(value, str) and value else None


def resolve_model(workload: str = WORKLOAD_GENERATION, settings_obj: Any = None) -> str:
    """Resolve the configured model ID for a workload.

    Each workload falls back to ``ANTHROPIC_MODEL`` when its specific setting is
    unset, so single-model deployments keep working unchanged.

    Args:
        workload: One of ``"generation"``, ``"research"``, ``"assistant"``.
        settings_obj: Settings object to read from. Defaults to the application
            settings; pass the caller's own reference so test patches apply.

    Returns:
        The Anthropic model ID to use.

    Raises:
        ValueError: If ``workload`` is not a recognised workload name.
    """
    if workload not in _VALID_WORKLOADS:
        raise ValueError(f"Unknown workload {workload!r}; expected one of {_VALID_WORKLOADS}")

    settings_obj = _load_settings(settings_obj)
    default = settings_obj.ANTHROPIC_MODEL

    if workload == WORKLOAD_RESEARCH:
        return _configured_str(settings_obj, "ANTHROPIC_MODEL_RESEARCH") or default
    if workload == WORKLOAD_ASSISTANT:
        return _configured_str(settings_obj, "ANTHROPIC_MODEL_ASSISTANT") or default
    return _configured_str(settings_obj, "ANTHROPIC_MODEL_GENERATION") or default


def resolve_effort(workload: str, temperature: float, settings_obj: Any = None) -> str:
    """Resolve the effort level for a workload/temperature pair.

    A configured ``ANTHROPIC_EFFORT_<WORKLOAD>`` setting wins; otherwise the
    level is derived from temperature so existing per-agent tuning carries over.

    Args:
        workload: One of ``"generation"``, ``"research"``, ``"assistant"``.
        temperature: The legacy sampling temperature.
        settings_obj: Settings object to read from; defaults to app settings.

    Returns:
        One of ``"low"``, ``"medium"``, ``"high"``, ``"xhigh"``, ``"max"``.
    """
    override = _configured_str(_load_settings(settings_obj), f"ANTHROPIC_EFFORT_{workload.upper()}")
    return override or effort_for_temperature(temperature)


def resolve_thinking(
    model: str,
    workload: str,
    effort: str,
    has_tools: bool = False,
    explicit: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve the ``thinking`` parameter for a request.

    Policy:

    * An ``explicit`` value from the caller always wins.
    * Tool-using calls get adaptive thinking, never disabled - see the module
      docstring for the silent-tool-drop hazard this prevents.
    * ``research`` and ``assistant`` get adaptive thinking (judgment work).
    * ``generation`` gets thinking disabled: bulk post generation is the
      cost-dominant path and matches the pre-migration behaviour, where
      ``max_tokens`` was consumed entirely by response text.
    * Disabling is downgraded to adaptive if effort is above ``high``, which
      Opus 5 rejects.

    Args:
        model: Anthropic model ID.
        workload: One of ``"generation"``, ``"research"``, ``"assistant"``.
        effort: The resolved effort level.
        has_tools: Whether the request declares tools.
        explicit: A caller-supplied ``thinking`` value, if any.

    Returns:
        The ``thinking`` parameter dict, or None when the model predates
        adaptive thinking and the parameter should be omitted entirely.
    """
    if explicit is not None:
        return explicit

    # Legacy models: omit the parameter rather than send an unsupported shape.
    if not supports_effort(model):
        return None

    if has_tools or workload in (WORKLOAD_RESEARCH, WORKLOAD_ASSISTANT):
        return {"type": "adaptive"}

    if effort in _EFFORT_INCOMPATIBLE_WITH_DISABLED_THINKING:
        return {"type": "adaptive"}

    return {"type": "disabled"}


#: Approximate characters per token, by tokenizer generation. The Claude 5 line
#: uses the tokenizer introduced with Opus 4.7, which produces roughly 30% more
#: tokens for the same text than every earlier model.
_CHARS_PER_TOKEN_LEGACY = 4.0
_CHARS_PER_TOKEN_CLAUDE_5 = 3.1


def estimate_tokens(text_length: int, model: str) -> int:
    """Estimate a token count from a character count.

    This is for **log lines only**. It deliberately does not call
    ``messages.count_tokens``: an extra network round-trip per request to
    produce a log field would be a poor trade. Use ``count_tokens`` directly
    wherever an accurate count actually drives a decision (budgeting, chunking).

    Args:
        text_length: Total characters in the prompt.
        model: Anthropic model ID, which selects the tokenizer ratio.

    Returns:
        An order-of-magnitude token estimate.
    """
    ratio = _CHARS_PER_TOKEN_LEGACY if accepts_temperature(model) else _CHARS_PER_TOKEN_CLAUDE_5
    return int(text_length / ratio)


#: Minimum ``max_tokens`` for a request with thinking enabled. Thinking tokens
#: and response tokens share the ``max_tokens`` budget, and thinking is spent
#: first, so a tight cap that was fine without thinking now truncates the answer.
THINKING_MAX_TOKENS_FLOOR = 16000


def enforce_token_floor(max_tokens: int, model_params: Dict[str, Any]) -> int:
    """Raise ``max_tokens`` to leave room for thinking, when thinking is on.

    Research tools cap output at 200-2000 tokens as a safety valve. Those caps
    predate adaptive thinking, which consumes the same budget before any
    response text is produced — a 200-token cap would reliably truncate, and a
    truncated response means unparseable JSON and a failed tool run.

    Raising the cap costs nothing when it is not used: ``max_tokens`` is a
    ceiling, not a reservation. Response *length* is governed by the prompt.

    Args:
        max_tokens: The caller's requested output cap.
        model_params: The fragment returned by :func:`build_model_params`.

    Returns:
        The requested cap, or :data:`THINKING_MAX_TOKENS_FLOOR` if thinking is
        enabled and the requested cap is below it.
    """
    thinking = model_params.get("thinking")
    if not thinking or thinking.get("type") == "disabled":
        return max_tokens
    return max(max_tokens, THINKING_MAX_TOKENS_FLOOR)


def build_model_params(
    model: str,
    temperature: float,
    workload: str = WORKLOAD_GENERATION,
    has_tools: bool = False,
    thinking: Optional[Dict[str, Any]] = None,
    effort: Optional[str] = None,
    settings_obj: Any = None,
) -> Dict[str, Any]:
    """Build the generation-control fragment of a Messages API request.

    This is the single place that decides between the legacy sampling-parameter
    shape and the current effort/thinking shape. Merge the result into the
    request body.

    Args:
        model: Anthropic model ID the request targets.
        temperature: The caller's temperature, used directly on legacy models
            and translated to effort on current ones.
        workload: One of ``"generation"``, ``"research"``, ``"assistant"``.
        has_tools: Whether the request declares tools.
        thinking: Explicit ``thinking`` override, if the caller has one.
        effort: Explicit effort override, bypassing the temperature mapping.
        settings_obj: Settings object to read overrides from; defaults to app
            settings. Pass the caller's own reference so test patches apply.

    Returns:
        A dict containing either ``{"temperature": ...}`` (legacy models) or
        ``{"output_config": {"effort": ...}}`` plus an optional ``"thinking"``.
    """
    if accepts_temperature(model):
        return {"temperature": temperature}

    resolved_effort = effort or resolve_effort(workload, temperature, settings_obj)
    params: Dict[str, Any] = {"output_config": {"effort": resolved_effort}}

    resolved_thinking = resolve_thinking(
        model=model,
        workload=workload,
        effort=resolved_effort,
        has_tools=has_tools,
        explicit=thinking,
    )
    if resolved_thinking is not None:
        params["thinking"] = resolved_thinking

    return params
