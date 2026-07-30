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


def check_compliance(text: str, platform: Platform) -> ComplianceReport:
    """Gate ``text`` for ``platform``; ``publishable`` is False on any hard violation."""
    char_count = len(text)
    word_count = len(text.split())
    hashtag_count = count_hashtags(text)

    hard: list[str] = []
    warnings: list[str] = []

    specs = PLATFORM_LENGTH_SPECS.get(platform)
    if specs:
        # Hard character ceiling — the platform API rejects/truncates past this.
        max_chars = specs["max_chars"]
        if char_count > max_chars:
            hard.append(f"{char_count} chars exceeds {platform.value} hard limit of {max_chars}")

        # Word bounds: under min_words / over max_words HARD-fail the repo's length
        # validator, so they block here too. Missing the optimal band is a warning.
        min_w, max_w = specs["min_words"], specs["max_words"]
        opt_lo, opt_hi = specs["optimal_min_words"], specs["optimal_max_words"]
        if word_count < min_w:
            hard.append(f"{word_count} words below {platform.value} minimum of {min_w}")
        elif word_count > max_w:
            hard.append(f"{word_count} words above {platform.value} maximum of {max_w}")
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
