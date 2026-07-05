import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20)

_local_tmp_root = project_root / "data" / ".pytest-temp-priority-backlog"
_local_tmp_root.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def tmp_path():
    path = _local_tmp_root / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path


@pytest.fixture(autouse=True)
def mute_loggers(monkeypatch):
    for module in (brief_parser_mod, keyword_refiner_mod, rate_limiter_mod):
        monkeypatch.setattr(module.logger, "info", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.logger, "warning", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.logger, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(keyword_refiner_mod.console, "print", lambda *args, **kwargs: None)
    return None


from backend.schemas.client import ClientResponse
from backend.utils import rate_limiter as rate_limiter_mod
from backend.utils.rate_limiter import RateLimitTracker
from src.agents import brief_parser as brief_parser_mod
from src.agents import keyword_refiner as keyword_refiner_mod
from src.agents.brief_parser import BriefParserAgent, BriefParsingError
from src.agents.keyword_refiner import KeywordRefinementAgent
from src.models.client_brief import ClientBrief
from src.models.seo_keyword import KeywordDifficulty, KeywordIntent, KeywordStrategy, SEOKeyword
from src.utils.template_parser import TemplateParser


class DummyBriefClient:
    def create_message(self, **kwargs):
        return json.dumps({})


def build_client_brief() -> ClientBrief:
    return ClientBrief(
        company_name="Acme Analytics",
        founder_name="Jordan",
        business_description="B2B analytics platform",
        industry="SaaS",
        keywords=["analytics"],
        competitors=["Competitor"],
        location="Austin",
        ideal_customer="Ops teams",
        main_problem_solved="Saves time",
        customer_pain_points=["manual reporting"],
        customer_questions=["How do we scale?"],
        tone_preference=None,
        tone_to_avoid=None,
        brand_personality=["direct"],
        brand_voice=None,
        key_phrases=["faster reporting"],
        target_platforms=[],
        posting_frequency="3x weekly",
        data_usage=None,
        main_cta="book a call",
        measurable_results="more time",
        stories=["We grew a client"],
        misconceptions=["It's hard"],
    )


def build_keyword_strategy() -> KeywordStrategy:
    return KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="primary one",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=1,
                related_keywords=[],
                notes="seed",
            )
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword=f"secondary {i}",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=i,
                related_keywords=[],
                notes="seed",
            )
            for i in range(1, 7)
        ],
        longtail_keywords=[
            SEOKeyword(
                keyword="longtail one",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.HARD,
                priority=1,
                related_keywords=[],
                notes="seed",
            )
        ],
    )


class TestBriefParserCoverage:
    def test_parse_brief_reraises_custom_brief_parsing_error(self, monkeypatch):
        agent = BriefParserAgent(client=DummyBriefClient())

        def fake_call(*args, **kwargs):
            raise BriefParsingError("bad brief")

        monkeypatch.setattr(brief_parser_mod, "call_claude_api", fake_call)

        with pytest.raises(BriefParsingError):
            agent.parse_brief("raw text")

    def test_convert_to_client_brief_invalid_model_raises_value_error(self, monkeypatch):
        agent = BriefParserAgent(client=DummyBriefClient())

        def bad_client_brief(**kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(brief_parser_mod, "ClientBrief", bad_client_brief)

        with pytest.raises(ValueError):
            agent._convert_to_client_brief({"company_name": "Broken Co"})

    def test_enrich_brief_success_and_failure(self, monkeypatch):
        agent = BriefParserAgent(client=DummyBriefClient())
        original = build_client_brief()

        monkeypatch.setattr(
            brief_parser_mod,
            "call_claude_api",
            lambda *args, **kwargs: {
                "company_name": "Updated Co",
                "business_description": "Updated description",
                "ideal_customer": "Updated audience",
                "main_problem_solved": "Updated problem",
                "customer_questions": ["What changed?"],
                "stories": ["A new story"],
            },
        )

        updated = agent.enrich_brief(original, "new context")
        assert updated.company_name == "Updated Co"
        assert updated.business_description == "Updated description"

        monkeypatch.setattr(
            brief_parser_mod,
            "call_claude_api",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        fallback = agent.enrich_brief(original, "new context")
        assert fallback is original


class TestKeywordRefinementCoverage:
    def test_add_custom_keywords_supports_primary_and_longtail(self):
        agent = KeywordRefinementAgent()
        strategy = build_keyword_strategy()

        updated = agent.add_custom_keywords(strategy, ["primary custom"], keyword_type="primary")
        updated = agent.add_custom_keywords(updated, ["longtail custom"], keyword_type="longtail")

        assert any(kw.keyword == "primary custom" for kw in updated.primary_keywords)
        assert any(kw.keyword == "longtail custom" for kw in updated.longtail_keywords)

    def test_review_keywords_blank_feedback_keeps_strategy_and_displays_long_lists(
        self, monkeypatch
    ):
        agent = KeywordRefinementAgent()
        strategy = build_keyword_strategy()

        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")

        reviewed = agent.review_keywords_interactive(strategy)
        assert reviewed is strategy


class TestTemplateParserCoverage:
    def test_incomplete_template_sections_break_cleanly(self, tmp_path, monkeypatch):
        template_file = tmp_path / "templates.md"
        template_file.write_text("## TEMPLATE 1: Only Header\n", encoding="utf-8")

        monkeypatch.setattr(
            "src.utils.template_parser.settings.TEMPLATE_LIBRARY_PATH",
            str(template_file),
            raising=False,
        )

        parser = TemplateParser()
        templates = parser.parse_all_templates()
        assert templates == {}

    def test_missing_template_dependencies_returns_none(self, tmp_path, monkeypatch):
        template_file = tmp_path / "templates.md"
        template_file.write_text(
            """
## TEMPLATE 1: Example
**Best for:** Testing
**Format:** Simple
**Research Tools:**
**Required:** Audience Research
""".strip(),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            "src.utils.template_parser.settings.TEMPLATE_LIBRARY_PATH",
            str(template_file),
            raising=False,
        )

        parser = TemplateParser()
        assert parser.get_template_dependencies(2) is None


class TestRateLimiterCoverage:
    @pytest.mark.asyncio
    async def test_can_make_request_true_false_and_missing_queue_wait(self, monkeypatch):
        monkeypatch.setattr(
            rate_limiter_mod.settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 2, raising=False
        )
        monkeypatch.setattr(
            rate_limiter_mod.settings, "RATE_LIMIT_TOKENS_PER_MINUTE", 10, raising=False
        )

        tracker = RateLimitTracker()
        assert await tracker.can_make_request(1) is True

        await tracker.record_request(9)
        assert await tracker.can_make_request(2) is False
        assert await tracker.get_estimated_wait_time("missing") is None


class TestClientResponseCoverage:
    def test_serialize_datetime_handles_none_naive_and_aware(self):
        response = ClientResponse(
            id="1",
            name="Acme",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        )

        assert response.serialize_datetime(None, None) is None

        payload = response.model_dump(by_alias=True)
        assert payload["createdAt"].endswith("+00:00")

        aware = ClientResponse(
            id="2",
            name="Acme",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        aware_payload = aware.model_dump(by_alias=True)
        assert aware_payload["createdAt"].endswith("+00:00")
