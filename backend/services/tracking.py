"""Trackable-link builder (attribution / ROI measurement).

2026 buyers demand measurable ROI + attribution. This appends consistent UTM
parameters to published links so distribution analytics can attribute traffic per
platform / campaign — and lets LLM-referral traffic be treated as its own channel
(the fastest-growing referral source). Pure + deterministic; URL-safe via urllib,
preserving any query params already on the URL.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse, urlunparse

# http(s) URLs in free text. Stops at whitespace and quote/angle delimiters.
_URL_RE = re.compile(r"https?://[^\s<>\"']+")
# Sentence punctuation that commonly trails a URL — peeled off before tagging so it
# stays in the prose. Parens/brackets are intentionally NOT peeled (they can be part
# of a real URL, e.g. a Wikipedia article path).
_TRAILING_PUNCT = ".,;:!?\"'"


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
    # Keep existing non-UTM query pairs BYTE-EXACT — do not round-trip them through
    # parse/re-encode, so a signed or opaque query string is never mutated. Only
    # utm_* keys are ours to own, so we drop any stale ones and append fresh.
    kept = [p for p in parsed.query.split("&") if p and not p.lower().startswith("utm_")]

    utm = [("utm_source", source), ("utm_medium", medium), ("utm_campaign", campaign)]
    if content:
        utm.append(("utm_content", content))
    if term:
        utm.append(("utm_term", term))
    kept.append(urlencode(utm))

    return urlunparse(parsed._replace(query="&".join(kept)))


def tag_urls_in_text(text: str, *, source: str, campaign: str, medium: str = "social") -> str:
    """Append UTM params to every http(s) URL in ``text``, leaving the prose intact.

    Used at publish time so links in a post are attributable per platform/campaign.
    Idempotent — a URL that already carries ``utm_source`` is left untouched, so
    re-publishing or double-application never stacks parameters. Trailing sentence
    punctuation is preserved outside the tagged URL.
    """

    def _tag(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = ""
        while url and url[-1] in _TRAILING_PUNCT:
            trailing = url[-1] + trailing
            url = url[:-1]
        if not url or "utm_source=" in url.lower():
            return url + trailing
        return build_tracked_url(url, source=source, campaign=campaign, medium=medium) + trailing

    return _URL_RE.sub(_tag, text)
