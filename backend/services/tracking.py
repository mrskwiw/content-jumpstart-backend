"""Trackable-link builder (attribution / ROI measurement).

2026 buyers demand measurable ROI + attribution. This appends consistent UTM
parameters to published links so distribution analytics can attribute traffic per
platform / campaign — and lets LLM-referral traffic be treated as its own channel
(the fastest-growing referral source). Pure + deterministic; URL-safe via urllib,
preserving any query params already on the URL.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def build_tracked_url(
    base_url: str,
    *,
    source: str,
    campaign: str,
    medium: str = "social",
    content: str | None = None,
    term: str | None = None,
) -> str:
    """Return ``base_url`` with UTM params merged in (existing UTMs overridden).

    Args:
        source: ``utm_source`` — the platform/origin (e.g. ``linkedin``, ``chatgpt``).
        campaign: ``utm_campaign`` — the campaign/run identifier.
        medium: ``utm_medium`` — default ``social``.
        content/term: optional ``utm_content`` / ``utm_term``.
    """
    if not source or not campaign:
        raise ValueError("source and campaign are required")

    parsed = urlparse(base_url)
    # Preserve non-UTM query params; our UTMs win over any pre-existing ones.
    params = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.startswith("utm_")
    ]
    params.append(("utm_source", source))
    params.append(("utm_medium", medium))
    params.append(("utm_campaign", campaign))
    if content:
        params.append(("utm_content", content))
    if term:
        params.append(("utm_term", term))

    return urlunparse(parsed._replace(query=urlencode(params)))
