"""Unit tests for backend.services.web_search_factory."""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.web_search_factory import get_user_search_client


def _db():
    return MagicMock()


class TestGetUserSearchClient:
    def _mock_config(self, provider="stub", brave="", tavily="", serpapi=""):
        return {
            "provider": provider,
            "brave_api_key": brave,
            "tavily_api_key": tavily,
            "serpapi_api_key": serpapi,
        }

    def test_brave_provider_uses_brave_key(self):
        db = _db()
        config = self._mock_config(provider="brave", brave="brave-key-123")
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            client = get_user_search_client(db, "user-1")
        assert client.provider == "brave"

    def test_tavily_provider_uses_tavily_key(self):
        db = _db()
        config = self._mock_config(provider="tavily", tavily="tvly-abc")
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            client = get_user_search_client(db, "user-1")
        assert client.provider == "tavily"

    def test_serpapi_provider_uses_serpapi_key(self):
        db = _db()
        config = self._mock_config(provider="serpapi", serpapi="serp-xyz")
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            client = get_user_search_client(db, "user-1")
        assert client.provider == "serpapi"

    def test_falls_back_to_stub_when_no_key(self):
        db = _db()
        config = self._mock_config(provider="brave", brave="")  # empty key
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            with patch.dict("os.environ", {}, clear=True):
                # No env var either
                import os

                os.environ.pop("BRAVE_API_KEY", None)
                client = get_user_search_client(db, "user-1")
        assert client.provider == "stub"

    def test_stub_provider_returned_as_is(self):
        db = _db()
        config = self._mock_config(provider="stub")
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            client = get_user_search_client(db, "user-1")
        assert client.provider == "stub"

    def test_env_var_fallback_for_brave(self):
        db = _db()
        config = self._mock_config(provider="brave", brave="")
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            with patch.dict("os.environ", {"BRAVE_API_KEY": "env-brave-key"}):
                client = get_user_search_client(db, "user-1")
        assert client.provider == "brave"

    def test_returns_web_search_client(self):
        from src.utils.web_search import WebSearchClient

        db = _db()
        config = self._mock_config()
        with patch(
            "backend.services.web_search_factory.settings_service.get_web_search_config",
            return_value=config,
        ):
            client = get_user_search_client(db, "user-1")
        assert isinstance(client, WebSearchClient)
