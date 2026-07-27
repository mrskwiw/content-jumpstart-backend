"""Unit tests for the generation-step hashtag research (HASHTAG-02, LinkedIn + X).

Covers the deterministic core (policy enforcement, injection, cache key, JSON
parsing) plus the async research pass with a mocked LLM + cache.
"""

import pytest

from src.config.platform_specs import get_hashtag_policy
from src.models.client_brief import Platform
from src.models.hashtag_models import HashtagCandidate, HashtagSet, HashtagTier, SignalSource
from src.agents.hashtag_researcher import (
    HashtagResearcher,
    apply_hashtag_set,
    build_hashtag_prompt_block,
    count_hashtags,
    enforce_policy,
    keyword_fallback_candidates,
    strip_all_hashtags,
    topic_key,
)

LI = get_hashtag_policy(Platform.LINKEDIN)
TW = get_hashtag_policy(Platform.TWITTER)
FB = get_hashtag_policy(Platform.FACEBOOK)


def _c(tag: str, tier: str = "niche", banned: bool = False) -> HashtagCandidate:
    return HashtagCandidate(tag=tag, tier=HashtagTier(tier), banned=banned)


# --------------------------------------------------------------------------- #
# enforce_policy — the deterministic heart
# --------------------------------------------------------------------------- #


def test_disabled_platform_emits_nothing():
    cands = [_c("Marketing", "broad"), _c("Sales", "niche")]
    assert enforce_policy(cands, FB, "facebook").tags == []


def test_linkedin_caps_at_three_and_honors_tier_mix():
    cands = [
        _c("Marketing", "broad"),
        _c("B2BContentMarketing", "niche"),
        _c("DemandGen", "niche"),
        _c("AcmeInsights", "branded"),
        _c("Extra", "broad"),
    ]
    hset = enforce_policy(cands, LI, "linkedin")
    assert len(hset.tags) == 3
    tiers = {c.tier.value for c in hset.tags}
    # One of each requested tier should be present (broad, niche, branded).
    assert tiers == {"broad", "niche", "branded"}


def test_twitter_caps_at_two():
    cands = [_c("GrowthMarketing", "niche"), _c("SaaS", "trending"), _c("Extra", "broad")]
    hset = enforce_policy(cands, TW, "twitter")
    assert len(hset.tags) == 2


def test_banned_tags_dropped():
    cands = [_c("Bad", "niche", banned=True), _c("Good", "niche")]
    hset = enforce_policy(cands, LI, "linkedin")
    assert [c.tag for c in hset.tags] == ["Good"]


def test_case_insensitive_dedup():
    cands = [_c("Marketing", "broad"), _c("marketing", "niche"), _c("MARKETING", "branded")]
    hset = enforce_policy(cands, LI, "linkedin")
    assert len(hset.tags) == 1


def test_backfill_when_tier_mix_underfilled():
    # No branded/broad available — should still fill to max from niche pool.
    cands = [_c("A", "niche"), _c("B", "niche"), _c("C", "niche"), _c("D", "niche")]
    hset = enforce_policy(cands, LI, "linkedin")
    assert len(hset.tags) == 3


def test_never_fabricates_to_reach_min():
    # Only one candidate; min_tags is 2 for LinkedIn — we return the one we have.
    hset = enforce_policy([_c("Solo", "niche")], LI, "linkedin")
    assert len(hset.tags) == 1


# --------------------------------------------------------------------------- #
# injection block
# --------------------------------------------------------------------------- #


def test_injection_empty_when_no_tags():
    assert build_hashtag_prompt_block(HashtagSet(platform="linkedin", tags=[]), LI) == ""


def test_injection_lists_exact_tags_and_placement():
    hset = HashtagSet(platform="linkedin", tags=[_c("A", "broad"), _c("B", "niche")])
    block = build_hashtag_prompt_block(hset, LI)
    assert "#A #B" in block
    assert "very end" in block
    assert "character limit" not in block  # LinkedIn tags don't count toward a limit


def test_injection_twitter_notes_char_limit():
    hset = HashtagSet(platform="twitter", tags=[_c("Growth", "niche")])
    block = build_hashtag_prompt_block(hset, TW)
    assert "character limit" in block


# --------------------------------------------------------------------------- #
# topic_key
# --------------------------------------------------------------------------- #


def test_topic_key_stable_and_case_insensitive():
    a = topic_key("c1", "linkedin", "Scaling B2B", "Personal Story")
    b = topic_key("c1", "linkedin", "  scaling b2b ", "personal story")
    assert a == b


def test_topic_key_varies_by_platform_and_client():
    base = topic_key("c1", "linkedin", "x", "t")
    assert base != topic_key("c1", "twitter", "x", "t")
    assert base != topic_key("c2", "linkedin", "x", "t")


# --------------------------------------------------------------------------- #
# JSON parsing tolerance
# --------------------------------------------------------------------------- #


def test_parse_handles_object_list_and_junk():
    parse = HashtagResearcher._parse_candidates
    obj = parse({"tags": [{"tag": "#Foo", "tier": "niche"}]})
    assert obj[0].tag == "Foo" and obj[0].signal_source == SignalSource.ESTIMATED
    assert parse([{"tag": "Bar", "tier": "weird"}])[0].tier == HashtagTier.NICHE  # unknown→niche
    assert parse("not json") == []
    assert parse({"tags": [{"no_tag": 1}, {"tag": ""}]}) == []  # skips malformed/empty


# --------------------------------------------------------------------------- #
# async research pass (mocked LLM + cache)
# --------------------------------------------------------------------------- #


class _FakeCache:
    def __init__(self):
        self.store = {}

    def get_by_key(self, k):
        return self.store.get(k)

    def put_by_key(self, k, v):
        self.store[k] = v


@pytest.mark.asyncio
async def test_research_disabled_platform_skips_llm():
    calls = []

    class _Client:  # should never be called
        async def create_message_async(self, **kw):
            calls.append(kw)
            return "{}"

    r = HashtagResearcher(_Client())
    hset = await r.research(
        client_id="c1", platform=Platform.FACEBOOK, angle="a", template_name="t"
    )
    assert hset.tags == [] and calls == []


@pytest.mark.asyncio
async def test_research_caches_and_reuses(monkeypatch):
    payload = (
        '{"tags": [{"tag": "B2BContentMarketing", "tier": "niche"}, '
        '{"tag": "Marketing", "tier": "broad"}, {"tag": "AcmeCo", "tier": "branded"}]}'
    )
    n = {"calls": 0}

    class _Client:
        async def create_message_async(self, **kw):
            n["calls"] += 1
            return payload

    cache = _FakeCache()
    r = HashtagResearcher(_Client(), cache=cache)
    first = await r.research(
        client_id="c1",
        platform=Platform.LINKEDIN,
        angle="Scaling B2B",
        template_name="Personal Story",
        client_keywords=["b2b", "content"],
        brand_name="AcmeCo",
    )
    assert len(first.tags) == 3
    assert n["calls"] == 1
    # Second identical call hits cache — no new LLM call.
    second = await r.research(
        client_id="c1",
        platform=Platform.LINKEDIN,
        angle="Scaling B2B",
        template_name="Personal Story",
        client_keywords=["b2b", "content"],
        brand_name="AcmeCo",
    )
    assert second.display_tags == first.display_tags
    assert n["calls"] == 1


@pytest.mark.asyncio
async def test_research_fails_open_on_llm_error():
    class _Client:
        async def create_message_async(self, **kw):
            raise RuntimeError("boom")

    r = HashtagResearcher(_Client())
    hset = await r.research(
        client_id="c1", platform=Platform.LINKEDIN, angle="a", template_name="t"
    )
    assert hset.tags == []  # fail-open: no tags, no crash


# --------------------------------------------------------------------------- #
# strip_all_hashtags / count_hashtags (single Unicode-aware sanitizer)
# --------------------------------------------------------------------------- #


def test_strip_all_hashtags_removes_inline_and_trailing():
    # Inline AND trailing hashtags all go; whitespace/punctuation tidied.
    assert strip_all_hashtags("Check out #Marketing today. #Foo #Bar") == "Check out today."
    assert strip_all_hashtags("#Leading tag then text") == "tag then text"
    # Preserves non-hashtag '#': numeric refs and 'C#'.
    assert strip_all_hashtags("My #1 tip: learn C#") == "My #1 tip: learn C#"
    assert strip_all_hashtags("Issue #42 is fixed") == "Issue #42 is fixed"


def test_count_hashtags_ignores_numeric_and_csharp():
    assert count_hashtags("#A #B #C") == 3
    assert count_hashtags("My #1 tip in C# is #Clean") == 1  # only #Clean


def test_sanitizer_catches_digit_led_and_nonlatin_real_tags():
    # Real tags that start with a digit or use non-Latin scripts must be treated
    # as hashtags (they have letters) — not slip through.
    assert count_hashtags("#5Tips #2024Goals #100DaysOfCode") == 3
    assert count_hashtags("grow fast #日本語 today") == 1
    assert strip_all_hashtags("Read #5Tips now") == "Read now"
    assert strip_all_hashtags("投稿 #日本語 テスト") == "投稿 テスト"
    # ...but pure-numeric refs and 'C#' still survive.
    assert count_hashtags("item #42 in C#") == 0
    assert strip_all_hashtags("item #42 in C#") == "item #42 in C#"


def test_apply_strips_digit_led_inline_model_tag():
    content = "Our #5SecretTips really work.\n\nBook a demo."
    hset = HashtagSet(platform="linkedin", tags=[_c("A", "broad")])
    out = apply_hashtag_set(content, hset, LI)
    assert "#5SecretTips" not in out
    assert count_hashtags(out) == 1  # only the approved tag


def test_apply_strips_inline_model_hashtags_guaranteeing_exact_set():
    # A model that sneaks an INLINE hashtag into the body must not ship it — the
    # final post carries exactly the approved set.
    content = "Our #SecretTag platform helps teams.\n\nBook a demo."
    hset = HashtagSet(platform="linkedin", tags=[_c("A", "broad"), _c("B", "niche")])
    out = apply_hashtag_set(content, hset, LI)
    assert "#SecretTag" not in out  # inline model tag stripped
    assert out.endswith("#A #B")
    assert count_hashtags(out) == 2  # exactly the approved set


# --------------------------------------------------------------------------- #
# apply_hashtag_set — deterministic placement (approach B)
# --------------------------------------------------------------------------- #


def test_apply_linkedin_appends_on_new_line_and_replaces_model_tags():
    content = "Here is a strong take.\n\n#ModelAdded #Junk"
    hset = HashtagSet(platform="linkedin", tags=[_c("A", "broad"), _c("B", "niche")])
    out = apply_hashtag_set(content, hset, LI)
    assert out == "Here is a strong take.\n\n#A #B"  # model's tags stripped, ours appended


def test_apply_disabled_platform_leaves_content_untouched():
    content = "A facebook post #WithTags"
    out = apply_hashtag_set(content, HashtagSet(platform="facebook", tags=[]), FB)
    assert out == content


def test_apply_twitter_respects_280_budget():
    body = "x" * 275  # only ~5 chars of headroom
    hset = HashtagSet(platform="twitter", tags=[_c("Growth", "niche"), _c("SaaS", "trending")])
    out = apply_hashtag_set(body, hset, TW, max_chars=280)
    assert len(out) <= 280
    assert out == body  # no tag fits → none appended, body preserved


def test_apply_twitter_keeps_tags_that_fit():
    body = "Ship fast."
    hset = HashtagSet(platform="twitter", tags=[_c("Growth", "niche")])
    out = apply_hashtag_set(body, hset, TW, max_chars=280)
    assert out == "Ship fast. #Growth"


def test_apply_linkedin_drops_tags_that_would_exceed_char_limit():
    # LinkedIn tags don't "count toward" the visible limit, but the final post
    # must still respect max_chars — near-limit bodies drop tags instead of overflowing.
    body = "x" * 1798  # LinkedIn max_chars = 1800; almost no room
    hset = HashtagSet(platform="linkedin", tags=[_c("A", "broad"), _c("B", "niche")])
    out = apply_hashtag_set(body, hset, LI, max_chars=1800)
    assert len(out) <= 1800


# --------------------------------------------------------------------------- #
# keyword_fallback_candidates
# --------------------------------------------------------------------------- #


def test_keyword_fallback_builds_branded_and_niche():
    cands = keyword_fallback_candidates(["content marketing", "b2b saas"], brand_name="Acme Co")
    tiers = [c.tier.value for c in cands]
    assert tiers[0] == "branded"  # brand first
    # spaces stripped by normalization
    assert cands[0].tag == "AcmeCo"
    assert "contentmarketing" in [c.tag.lower() for c in cands]


def test_keyword_fallback_empty_when_nothing_provided():
    assert keyword_fallback_candidates([], None) == []


# --------------------------------------------------------------------------- #
# Generator integration (wiring seam) — approach B
# --------------------------------------------------------------------------- #

from unittest.mock import Mock  # noqa: E402

from src.agents.content_generator import ContentGeneratorAgent  # noqa: E402
from src.models.client_brief import ClientBrief  # noqa: E402
from src.models.post import Post  # noqa: E402
from src.models.template import Template, TemplateType, TemplateDifficulty  # noqa: E402


def _agent():
    return ContentGeneratorAgent(client=Mock(), template_loader=Mock(), use_content_skill=False)


def _brief():
    return ClientBrief(
        company_name="Acme Co",
        business_description="Analytics SaaS",
        ideal_customer="Data teams",
        main_problem_solved="Slow insights",
    )


def _template():
    return Template(
        template_id=1,
        name="Personal Story",
        structure="[HOOK]\n\n[BODY]",
        template_type=TemplateType.PROBLEM_RECOGNITION,
        difficulty=TemplateDifficulty.FAST,
        best_for="Test",
    )


def test_sync_apply_appends_brand_tag_without_hiding_cta():
    agent = _agent()
    body = "Great insight about analytics.\n\nBook a demo today."
    out = agent._apply_hashtags_sync(body, Platform.LINKEDIN, _brief(), _template())
    # Brand-derived tag appended on its own line...
    assert out.endswith("#AcmeCo")
    # ...and the CTA line is still present in the body (detection runs pre-append).
    assert "Book a demo today." in out


def test_wiring_refreshes_length_metadata_after_append():
    # Simulate the generator seam: append tags to a post, then refresh length.
    agent = _agent()
    post = Post(
        content="Ship analytics faster.\n\nBook a demo today.",
        template_id=1,
        template_name="T",
        variant=1,
        client_name="Acme Co",
    )
    before_chars = post.character_count
    post.content = agent._apply_hashtags_sync(
        post.content, Platform.LINKEDIN, _brief(), _template()
    )
    post.recompute_length()
    # Both counts reflect the FULL content (incl. appended tags) and grew.
    assert post.character_count == len(post.content)
    assert post.word_count == len(post.content.split())
    assert post.character_count > before_chars
    assert "#" in post.content  # a tag was actually appended
    # CTA detected on the body is preserved (not re-detected on final content).
    assert post.has_cta is True


def test_sync_apply_noop_for_disabled_platform():
    agent = _agent()
    body = "A facebook post."
    assert agent._apply_hashtags_sync(body, Platform.FACEBOOK, _brief(), _template()) == body


def test_apply_skips_placeholder_content():
    agent = _agent()
    ph = "[ERROR: Failed to generate post - boom]"
    assert agent._apply_hashtags_sync(ph, Platform.LINKEDIN, _brief(), _template()) == ph


def test_check_hashtag_flags_flags_overflow():
    agent = _agent()
    post = Post(
        content="Body here.\n\n#A #B #C #D #E",
        template_id=1,
        template_name="T",
        variant=1,
        client_name="C",
    )
    agent._check_hashtag_flags(post, Platform.LINKEDIN)  # max 3, has 5
    assert post.needs_review is True


def test_near_word_cap_body_not_churned_by_appended_hashtags():
    # Decision #198: word_count reflects actual content (may exceed the cap once a
    # hashtag is appended), but the component that REGENERATES (PostRegenerator)
    # evaluates the prose body, so a near-cap post is not churned by its hashtags.
    from src.agents.post_regenerator import PostRegenerator
    from src.models.quality_profile import get_default_profile

    body = " ".join(["ok"] * 280)  # within the LinkedIn cap as prose
    post = Post(content=body, template_id=1, template_name="T", variant=1, client_name="C")
    agent = _agent()
    post.content = agent._apply_hashtags_sync(
        post.content, Platform.LINKEDIN, _brief(), _template()
    )
    post.recompute_length()
    assert "#" in post.content and post.word_count > 280  # tags counted in word_count

    profile = get_default_profile("professional_linkedin")
    profile.max_words = 300  # ensure the prose body (280) is within cap
    regen = PostRegenerator(client=Mock(), quality_profile=profile)
    should, reasons = regen.should_regenerate(post)
    assert not any(r.reason_type == "too_long" for r in reasons)  # tags don't trip length
    assert not any(r.reason_type == "cta_not_last" for r in reasons)  # nor CTA placement


def test_check_hashtag_flags_flags_missing_microblog_tag():
    agent = _agent()
    post = Post(
        content="Just a tweet with no tags.",
        template_id=1,
        template_name="T",
        variant=1,
        client_name="C",
    )
    agent._check_hashtag_flags(post, Platform.TWITTER)  # min 1, has 0
    assert post.needs_review is True


def test_check_hashtag_flags_flags_underfilled_linkedin():
    # LinkedIn min is 2 — a single-tag post must be flagged, not shipped silently.
    agent = _agent()
    post = Post(
        content="A solid LinkedIn take.\n\n#OnlyOne",
        template_id=1,
        template_name="T",
        variant=1,
        client_name="C",
    )
    agent._check_hashtag_flags(post, Platform.LINKEDIN)
    assert post.needs_review is True
    assert "Too few hashtags" in (post.review_reason or "")


def test_check_hashtag_flags_passes_linkedin_within_bounds():
    agent = _agent()
    post = Post(
        content="A solid LinkedIn take.\n\n#Alpha #Beta #Gamma",
        template_id=1,
        template_name="T",
        variant=1,
        client_name="C",
    )
    agent._check_hashtag_flags(post, Platform.LINKEDIN)  # 3 tags: within [2, 3]
    assert post.needs_review is False


@pytest.mark.asyncio
async def test_underfill_flags_settled_post_without_prose_retry_churn():
    # A prose-clean LinkedIn post that can only muster 1 tag (brand only, research
    # unavailable) must be RETURNED on the first attempt (regen can't add tags) but
    # flagged for review — min is enforced, not silently shipped, and not churned.
    good = (
        " ".join(["insight"] * 210) + "\n\nBook a personalized demo today and see the difference."
    )
    n = {"gen": 0}

    async def _gen(**kw):
        n["gen"] += 1
        return good

    class _Client:
        async def create_message_async(self, **kw):  # research yields nothing
            raise RuntimeError("no research")

    agent = _agent()
    agent.client = _Client()
    agent.client.generate_post_content_async = _gen
    brief = _brief()  # brand "Acme Co", no keywords → 1 fallback tag

    post = await agent._generate_single_post_with_retry_async(
        template=_template(),
        client_brief=brief,
        variant=1,
        post_number=1,
        platform=Platform.LINKEDIN,
        max_attempts=5,
    )
    assert n["gen"] == 1  # returned on attempt 1 — underfill did NOT trigger retries
    assert post.needs_review is True
    assert "Too few hashtags" in (post.review_reason or "")


@pytest.mark.asyncio
async def test_async_keys_research_on_real_angle_not_template():
    # Same template, DIFFERENT angle → separate research (no cache collision); the
    # actual angle reaches the prompt. Same angle → cache hit (no extra call).
    n = {"calls": 0}
    prompts = []

    class _Client:
        async def create_message_async(self, **kw):
            n["calls"] += 1
            prompts.append(kw["messages"][0]["content"])
            return '{"tags":[{"tag":"Ship","tier":"niche"}]}'

    agent = _agent()
    agent._hashtag_researcher = HashtagResearcher(_Client(), cache=_FakeCache())
    tmpl = _template()  # one template, name "Personal Story"

    await agent._apply_hashtags_async(
        "Body one.", Platform.LINKEDIN, _brief(), tmpl, angle="scaling teams"
    )
    await agent._apply_hashtags_async(
        "Body two.", Platform.LINKEDIN, _brief(), tmpl, angle="hiring mistakes"
    )
    assert n["calls"] == 2  # distinct angles → distinct cache keys, no sharing

    # Repeat an angle → served from cache, no new research call.
    await agent._apply_hashtags_async(
        "Body three.", Platform.LINKEDIN, _brief(), tmpl, angle="scaling teams"
    )
    assert n["calls"] == 2

    # The real angle (not the template name) steered the prompt.
    assert any("scaling teams" in p for p in prompts)
    assert any("hiring mistakes" in p for p in prompts)
    assert all("Personal Story" in p for p in prompts)  # template name still present
