"""Unit tests for backend/utils/web_search_validator.is_web_search_configured.

This gate decides whether web-search research tools may run at all. Every route-level
test stubs it (BUGS #256 — otherwise they depend on the developer's real keys), so
this file is where its provider/key logic is actually exercised. Hermetic: the
stored config is mocked and every key env var is cleared.
"""

from unittest.mock import patch

import pytest

from backend.utils import web_search_validator
from backend.utils.web_search_validator import is_web_search_configured

_KEY_VARS = ("BRAVE_API_KEY", "TAVILY_API_KEY", "SERPAPI_API_KEY", "WEB_SEARCH_PROVIDER")


@pytest.fixture(autouse=True)
def _no_key_env(monkeypatch):
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


def _check(config):
    with patch.object(
        web_search_validator.settings_service, "get_web_search_config", return_value=config
    ):
        return is_web_search_configured(db=None, user_id=1)


class TestSelectedProviderWithKey:
    @pytest.mark.parametrize(
        "provider,key_field",
        [("brave", "brave_api_key"), ("tavily", "tavily_api_key"), ("serpapi", "serpapi_api_key")],
    )
    def test_stored_key_configures_provider(self, provider, key_field):
        assert _check({"provider": provider, key_field: "k"}) == (True, provider)

    @pytest.mark.parametrize(
        "provider,env_var",
        [("brave", "BRAVE_API_KEY"), ("tavily", "TAVILY_API_KEY"), ("serpapi", "SERPAPI_API_KEY")],
    )
    def test_env_key_configures_provider(self, provider, env_var, monkeypatch):
        monkeypatch.setenv(env_var, "k")
        assert _check({"provider": provider}) == (True, provider)


class TestSelectedProviderWithoutKey:
    @pytest.mark.parametrize("provider", ["brave", "tavily", "serpapi"])
    def test_missing_key_is_not_configured(self, provider):
        ok, message = _check({"provider": provider})
        assert ok is False
        assert "no API key configured" in message

    def test_key_for_a_different_provider_does_not_count(self, monkeypatch):
        # The case BUGS #256's first fix missed: a Brave key does not satisfy Tavily.
        monkeypatch.setenv("BRAVE_API_KEY", "k")
        ok, message = _check({"provider": "tavily"})
        assert ok is False
        assert "Tavily" in message


class TestStubProvider:
    def test_stub_without_any_key(self):
        ok, message = _check({"provider": "stub"})
        assert ok is False
        assert "No web search API key found" in message

    def test_stub_is_not_configured_even_with_a_key(self, monkeypatch):
        monkeypatch.setenv("BRAVE_API_KEY", "k")
        ok, message = _check({"provider": "stub"})
        assert ok is False
        assert "set to 'stub'" in message


def test_unknown_provider_is_not_configured():
    ok, message = _check({"provider": "bing", "bing_api_key": "k"})
    assert ok is False
    assert "Unknown web search provider: bing" in message
