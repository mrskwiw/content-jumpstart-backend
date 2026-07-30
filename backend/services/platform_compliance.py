"""Pre-publish platform compliance gate (distribution go-live).

Distinct from the word-count *optimizer* in ``src/config/platform_specs.py``: this
is the hard gate a post must pass before we hand it to a platform's publish API, so
a post the platform API *or* our own length validator would reject (an X post over
280 chars, under the word floor, over the word ceiling, too many hashtags) is caught
here instead of failing mid-distribution. Composes the existing char/length specs and
hashtag policy — no new platform constants. Pure/deterministic.

``hard`` violations block publishing: the char ceiling (API truncates/rejects) and
the min/max word bounds (the repo's length validator FAILS these — see the "will fail
validation" notes in ``platform_specs.py``). ``warnings`` are sub-optimal but
publishable — misses of the *optimal* word band only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config.platform_specs import (
    PLATFORM_LENGTH_SPECS,
    get_hashtag_policy,
)
from src.models.client_brief import Platform

_HASHTAG_RE = re.compile(r"(?<!\w)#\w+")

# True platform-API hard character limits — a post over these is actually
# rejected/truncated by the platform. Deliberately NARROWER than
# PLATFORM_LENGTH_SPECS' ``max_chars`` (a quality ceiling: LinkedIn 1800 vs the real
# ~3000 API limit, Facebook 650 vs ~63k). Only limits that are both well-established
# AND realistically reachable by short-form posts are listed; in api_only mode a
# platform absent here is not char-gated, so legitimate longer posts are never
# blocked. Twitter/X's 280 is the one commonly-hit real limit.
_API_HARD_CHAR_LIMITS: dict[Platform, int] = {Platform.TWITTER: 280}


def count_hashtags(text: str) -> int:
    """Number of ``#tag`` tokens (word-boundary anchored; ignores ``a#b``)."""
    return len(_HASHTAG_RE.findall(text))


@dataclass
class ComplianceReport:
    platform: str
    publishable: bool
    char_count: int
    word_count: int
    hashtag_count: int
    hard: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_compliance(text: str, platform: Platform, *, api_only: bool = False) -> ComplianceReport:
    """Gate ``text`` for ``platform``; ``publishable`` is False on any hard violation.

    ``api_only=True`` restricts hard failures to what the platform *API* actually
    rejects — the character ceiling and hashtag over-cap — and demotes the word-count
    floor/ceiling to warnings. Use it for the distribution pre-publish gate, where a
    deliberately short scheduled post must not be blocked; leave it False for the
    generation QA context, where the repo's length validator treats word bounds as
    hard failures.
    """
    char_count = len(text)
    word_count = len(text.split())
    hashtag_count = count_hashtags(text)

    hard: list[str] = []
    warnings: list[str] = []

    # Empty / whitespace-only content is never publishable — platforms reject it,
    # and in api_only mode the word-floor demotion would otherwise let it pass.
    if not text.strip():
        hard.append(f"empty content — nothing to publish on {platform.value}")

    specs = PLATFORM_LENGTH_SPECS.get(platform)
    if specs:
        # Character ceiling. In api_only mode use the TRUE API limit (only a few
        # platforms; absent → not char-gated) so we never block a legitimately long
        # post; otherwise use the spec's quality ceiling (the QA-context behaviour).
        if api_only:
            api_limit = _API_HARD_CHAR_LIMITS.get(platform)
            if api_limit is not None and char_count > api_limit:
                hard.append(f"{char_count} chars exceeds {platform.value} API limit of {api_limit}")
        else:
            max_chars = specs["max_chars"]
            if char_count > max_chars:
                hard.append(
                    f"{char_count} chars exceeds {platform.value} hard limit of {max_chars}"
                )

        # Word bounds: under min_words / over max_words HARD-fail the repo's length
        # validator, so they block here too — UNLESS api_only, since a word count is
        # not something the platform API rejects. Missing the optimal band is a warning.
        min_w, max_w = specs["min_words"], specs["max_words"]
        opt_lo, opt_hi = specs["optimal_min_words"], specs["optimal_max_words"]
        word_bound = warnings if api_only else hard
        if word_count < min_w:
            word_bound.append(f"{word_count} words below {platform.value} minimum of {min_w}")
        elif word_count > max_w:
            word_bound.append(f"{word_count} words above {platform.value} maximum of {max_w}")
        elif word_count < opt_lo or word_count > opt_hi:
            warnings.append(
                f"{word_count} words outside optimal {opt_lo}-{opt_hi} for {platform.value}"
            )

    # Hashtag count vs the platform's policy cap.
    policy = get_hashtag_policy(platform)
    if not policy.enabled and hashtag_count > 0:
        warnings.append(f"{platform.value} should not use hashtags ({hashtag_count} present)")
    elif policy.enabled and hashtag_count > policy.max_tags:
        hard.append(f"{hashtag_count} hashtags exceeds {platform.value} max of {policy.max_tags}")

    return ComplianceReport(
        platform=platform.value,
        publishable=not hard,
        char_count=char_count,
        word_count=word_count,
        hashtag_count=hashtag_count,
        hard=hard,
        warnings=warnings,
    )
