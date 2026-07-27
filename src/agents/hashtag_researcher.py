"""Hashtag Researcher — generation-step hashtag research (HASHTAG-02, LinkedIn + X slice).

A per-post research pass: given a post's angle/template + client context, ask the
LLM to propose tiered hashtag candidates, then DETERMINISTICALLY enforce the
platform policy (cap, tier mix, dedup, banned-filter) so output never exceeds
what the platform tolerates. Results are cached per (client, platform, topic) so
overlapping topics across a 30-post run don't re-hit the LLM.

Neither LinkedIn nor X exposes a usable hashtag API, so signals are LLM-estimated
here (``SignalSource.ESTIMATED``). External metric providers arrive in a later
slice — see docs/explore-hashtag-research.md §9 (P2).

Design split, so the risky part is unit-testable without the network:
- ``enforce_policy`` / ``build_hashtag_prompt_block`` / ``topic_key`` — pure functions.
- ``HashtagResearcher.research`` — the one async method that calls the LLM.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, List, Optional, Sequence

from ..config.platform_specs import HASHTAG_TIERS, HashtagPolicy, get_hashtag_policy
from ..models.client_brief import Platform
from ..models.hashtag_models import HashtagCandidate, HashtagSet, HashtagTier, SignalSource
from ..utils.agent_helpers import call_claude_api_async
from ..utils.logger import logger

CACHE_PREFIX = "hashtag_research"


def topic_key(client_id: str, platform_value: str, angle: str, template_name: str) -> str:
    """Stable cache key for a post's hashtag research.

    Coarser than the full post text on purpose: distinct posts on the same
    angle+template should reuse the same researched tags (see R7 in the design
    doc — granularity is tunable here).
    """
    raw = f"{client_id}|{platform_value}|{angle.strip().lower()}|{template_name.strip().lower()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{CACHE_PREFIX}:{digest}"


def enforce_policy(
    candidates: Sequence[HashtagCandidate],
    policy: HashtagPolicy,
    platform_value: str,
) -> HashtagSet:
    """Trim raw candidates down to a policy-compliant set. Pure + deterministic.

    Order of operations: drop banned → dedup (case-insensitive, keep first) →
    fill the tier mix in canonical tier order → backfill remaining slots with the
    best leftovers → hard-cap at ``policy.max_tags``. Never fabricates tags to
    reach ``min_tags`` (under-emitting beats inventing).
    """
    if not policy.enabled or policy.max_tags <= 0:
        return HashtagSet(platform=platform_value, tags=[])

    # Drop banned, then dedup case-insensitively preserving first occurrence.
    seen: set[str] = set()
    pool: List[HashtagCandidate] = []
    for c in candidates:
        if c.banned:
            continue
        key = c.tag.lower()
        if key in seen:
            continue
        seen.add(key)
        pool.append(c)

    chosen: List[HashtagCandidate] = []
    chosen_keys: set[str] = set()

    def _add(c: HashtagCandidate) -> None:
        if len(chosen) >= policy.max_tags:
            return
        k = c.tag.lower()
        if k in chosen_keys:
            return
        chosen_keys.add(k)
        chosen.append(c)

    # 1) Satisfy the desired tier mix, in canonical priority order.
    for tier in HASHTAG_TIERS:
        want = policy.tier_mix.get(tier, 0)
        if want <= 0:
            continue
        taken = 0
        for c in pool:
            if taken >= want:
                break
            if c.tier.value == tier and c.tag.lower() not in chosen_keys:
                _add(c)
                taken += 1

    # 2) Backfill any remaining slots with the best leftover candidates.
    for c in pool:
        if len(chosen) >= policy.max_tags:
            break
        _add(c)

    return HashtagSet(platform=platform_value, tags=chosen[: policy.max_tags])


def build_hashtag_prompt_block(hset: HashtagSet, policy: HashtagPolicy) -> str:
    """Render the injection block telling the generator exactly which tags to use.

    Empty string when there are no tags (disabled platform or research produced
    nothing) — the caller then adds no hashtag instruction at all.
    """
    tags = hset.display_tags
    if not tags:
        return ""
    joined = " ".join(tags)
    where = {
        "end": "at the very end of the post",
        "inline": "woven naturally into the post",
        "caption": "at the end of the caption",
        "first_comment": "in the first comment",
    }.get(policy.placement, "at the end of the post")
    note = " They count toward the character limit." if policy.counts_toward_char_limit else ""
    return (
        f"HASHTAGS FOR THIS POST — use EXACTLY these {len(tags)} and no others, "
        f"placed {where}: {joined}.{note}"
    )


# A single "real" hashtag token: '#' + word chars that contain AT LEAST ONE
# letter (anywhere). The letter requirement (lookahead ``\w*[^\W\d_]``, which is
# Unicode-aware) keeps genuine tags — including digit-led ('#5Tips', '#2024Goals')
# and non-Latin ('#日本語') — while excluding pure-numeric refs ('#1', '#42'). The
# (?<!\w) boundary excludes 'C#' (the '#' there follows a word char).
_HASHTAG_TOKEN_RE = re.compile(r"(?<!\w)#(?=\w*[^\W\d_])\w+")


def strip_all_hashtags(text: str) -> str:
    """Remove EVERY hashtag token anywhere in the text.

    This is the enforcement behind "exactly these tags and no others": before we
    append the approved set we clear any hashtag the model emitted — inline or
    trailing — then tidy the whitespace/punctuation left behind. Non-hashtag '#'
    uses are preserved: numeric refs like '#1'/'#42' (a letter must follow '#')
    and 'C#' (a word char precedes '#').
    """
    cleaned = _HASHTAG_TOKEN_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)  # collapse gaps left behind
    cleaned = re.sub(r"[ \t]+([.,!?;:])", r"\1", cleaned)  # space before punctuation
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)  # trailing spaces on a line
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # collapse blank-line runs
    return cleaned.strip()


def count_hashtags(text: str) -> int:
    """Count real hashtag tokens (letter-led), ignoring '#1'/'C#'."""
    return len(_HASHTAG_TOKEN_RE.findall(text))


def apply_hashtag_set(
    content: str,
    hset: HashtagSet,
    policy: HashtagPolicy,
    max_chars: Optional[int] = None,
) -> str:
    """Deterministically place the researched set at the end of a post (approach B).

    Strips ALL hashtags the model emitted (inline or trailing), then appends
    ``hset`` — on its own line for LinkedIn, space-joined for X — so the post ends
    up with exactly the approved tags and no others. When ``max_chars`` is given
    (any platform), keeps the FINAL post within that limit by dropping trailing
    tags that don't fit rather than overflowing; if not even one fits, emits none
    (the body is then validated for length separately).
    """
    if not policy.enabled:
        return content
    body = strip_all_hashtags(content)
    tags = hset.display_tags
    if not tags:
        return body

    sep = " " if policy.counts_toward_char_limit else "\n\n"
    if max_chars:
        base = len(body) + len(sep)
        while tags and base + len(" ".join(tags)) > max_chars:
            tags = tags[:-1]
        if not tags:
            return body

    suffix = " ".join(tags)
    return f"{body}{sep}{suffix}" if body else suffix


def keyword_fallback_candidates(
    keywords: Optional[Sequence[str]] = None,
    brand_name: Optional[str] = None,
) -> List[HashtagCandidate]:
    """Deterministic candidates from client keywords — no LLM.

    Used on the synchronous generation path (no async client for live research)
    and as a fallback when live research returns nothing, so a Twitter post is
    never left with zero hashtags when keywords exist.
    """
    out: List[HashtagCandidate] = []
    if brand_name:
        try:
            out.append(HashtagCandidate(tag=brand_name, tier=HashtagTier.BRANDED))
        except Exception:
            pass
    for kw in list(keywords or [])[:8]:
        try:
            out.append(HashtagCandidate(tag=str(kw), tier=HashtagTier.NICHE))
        except Exception:  # nosec B112 - empty/garbage keyword → skip
            continue
    return out


class HashtagResearcher:
    """Runs the per-post hashtag research pass, with a write-through cache."""

    def __init__(self, client: Any, cache: Optional[Any] = None) -> None:
        """
        Args:
            client: Async Anthropic client (same one the generator uses).
            cache: Optional cache with ``get_by_key``/``put_by_key`` (e.g.
                ``ResponseCache``). When None, every call researches live.
        """
        self.client = client
        self.cache = cache

    async def research(
        self,
        *,
        client_id: str,
        platform: Platform,
        angle: str,
        template_name: str,
        client_keywords: Optional[Sequence[str]] = None,
        industry: Optional[str] = None,
        brand_name: Optional[str] = None,
    ) -> HashtagSet:
        """Return a policy-compliant HashtagSet for one post.

        Fail-open: any error (LLM failure, bad JSON) yields an empty set so
        generation is never blocked by hashtag research.
        """
        policy = get_hashtag_policy(platform)
        if not policy.enabled:
            return HashtagSet(platform=platform.value, tags=[])

        key = topic_key(client_id, platform.value, angle, template_name)
        if self.cache is not None:
            cached = self.cache.get_by_key(key)
            if cached:
                try:
                    return HashtagSet.model_validate(cached)
                except Exception:  # corrupt cache entry → re-research
                    logger.warning("Discarding unreadable hashtag cache entry %s", key)

        candidates = await self._llm_candidates(
            policy=policy,
            platform=platform,
            angle=angle,
            template_name=template_name,
            client_keywords=client_keywords,
            industry=industry,
            brand_name=brand_name,
        )
        hset = enforce_policy(candidates, policy, platform.value)

        if self.cache is not None:
            try:
                self.cache.put_by_key(key, hset.model_dump(mode="json"))
            except Exception:  # caching is best-effort
                logger.warning("Failed to cache hashtag research %s", key)
        return hset

    async def _llm_candidates(
        self,
        *,
        policy: HashtagPolicy,
        platform: Platform,
        angle: str,
        template_name: str,
        client_keywords: Optional[Sequence[str]],
        industry: Optional[str],
        brand_name: Optional[str],
    ) -> List[HashtagCandidate]:
        """Ask the LLM for tiered candidates. Returns [] on any failure."""
        kw = ", ".join(list(client_keywords or [])[:10]) or "(none provided)"
        tiers_wanted = ", ".join(f"{t}×{n}" for t, n in policy.tier_mix.items() if n > 0)
        system = (
            "You are a social-media hashtag strategist. You recommend a SMALL, "
            "high-quality set of hashtags fitted to a specific post and brand. "
            "Tiers: broad (high-volume industry term), niche (specific, high-intent), "
            "branded (the client's own brand/campaign tag), trending (timely "
            "conversation). Prefer specificity over reach. Never invent a branded "
            "tag if no brand name is given. Output JSON only."
        )
        prompt = (
            f"Platform: {platform.value}\n"
            f"Post angle: {angle}\n"
            f"Template: {template_name}\n"
            f"Client industry: {industry or '(unspecified)'}\n"
            f"Client brand name: {brand_name or '(unspecified)'}\n"
            f"Client keywords: {kw}\n\n"
            f"Rule: {policy.guidance}\n"
            f"Aim for this tier mix (upper bound {policy.max_tags} total): "
            f"{tiers_wanted or 'niche-focused'}.\n\n"
            'Return JSON exactly: {"tags": [{"tag": "NoHashSymbol", '
            '"tier": "broad|niche|branded|trending", "rationale": "short"}]}'
        )
        result = await call_claude_api_async(
            self.client,
            prompt=prompt,
            system_prompt=system,
            max_tokens=400,
            temperature=0.4,
            extract_json=True,
            fallback_on_error={},
        )
        return self._parse_candidates(result)

    @staticmethod
    def _parse_candidates(result: Any) -> List[HashtagCandidate]:
        """Coerce raw LLM JSON into validated HashtagCandidate objects.

        Tolerant: skips malformed entries, maps unknown tiers to 'niche', accepts
        either a ``{"tags": [...]}`` object or a bare list.
        """
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (ValueError, TypeError):
                return []
        if isinstance(result, dict):
            raw = result.get("tags", [])
        elif isinstance(result, list):
            raw = result
        else:
            return []

        out: List[HashtagCandidate] = []
        for item in raw:
            if not isinstance(item, dict) or not item.get("tag"):
                continue
            tier_raw = str(item.get("tier", "niche")).lower()
            tier = tier_raw if tier_raw in {t.value for t in HashtagTier} else "niche"
            try:
                out.append(
                    HashtagCandidate(
                        tag=str(item["tag"]),
                        tier=HashtagTier(tier),
                        signal_source=SignalSource.ESTIMATED,
                        rationale=(str(item["rationale"]) if item.get("rationale") else None),
                    )
                )
            except Exception:  # nosec B112 - normalization rejected an empty/garbage tag
                continue
        return out
