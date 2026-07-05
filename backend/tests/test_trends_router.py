import os
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20)

import backend.main as main_mod
import backend.routers.trends as trends_mod


def _make_client(monkeypatch):
    main_mod.app.dependency_overrides[trends_mod.get_db] = lambda: object()
    main_mod.app.dependency_overrides[trends_mod.get_current_user] = lambda: SimpleNamespace(
        id="user-123"
    )
    monkeypatch.setattr(main_mod.app.state.limiter, "enabled", False, raising=False)
    return TestClient(main_mod.app)


def _clear_overrides():
    main_mod.app.dependency_overrides.pop(trends_mod.get_db, None)
    main_mod.app.dependency_overrides.pop(trends_mod.get_current_user, None)


def test_trends_search_endpoints_success(monkeypatch):
    client = _make_client(monkeypatch)
    captured = {}

    def fake_search_interest_over_time(**kwargs):
        captured["interest"] = kwargs
        return {"success": True, "search_id": "s-1", "data_points": 12}

    def fake_search_related_queries(**kwargs):
        captured["related"] = kwargs
        return {"success": True, "search_id": "s-2", "total_queries": 3}

    def fake_compute_keyword_insights(**kwargs):
        captured["insight"] = kwargs
        return {"success": True, "keyword": kwargs["keyword"], "priority_score": 0.8}

    def fake_get_search_history(**kwargs):
        captured["history"] = kwargs
        return {"success": True, "count": 1, "searches": [{"id": "h-1"}]}

    def fake_get_keyword_insights(**kwargs):
        captured["insights"] = kwargs
        return {"success": True, "count": 1, "insights": [{"id": "i-1"}]}

    monkeypatch.setattr(
        trends_mod.trends_service, "search_interest_over_time", fake_search_interest_over_time
    )
    monkeypatch.setattr(
        trends_mod.trends_service, "search_related_queries", fake_search_related_queries
    )
    monkeypatch.setattr(
        trends_mod.trends_service, "compute_keyword_insights", fake_compute_keyword_insights
    )
    monkeypatch.setattr(trends_mod.trends_service, "get_search_history", fake_get_search_history)
    monkeypatch.setattr(
        trends_mod.trends_service, "get_keyword_insights", fake_get_keyword_insights
    )

    interest_response = client.post(
        "/api/trends/search/interest",
        json={
            "keywords": ["saas", "content"],
            "timeframe": "past_90_days",
            "geo": "US",
            "category": "business",
            "client_id": "client-1",
            "project_id": "project-1",
        },
    )
    related_response = client.post(
        "/api/trends/search/related",
        json={"keywords": ["saas"], "client_id": "client-1"},
    )
    insight_response = client.post(
        "/api/trends/insights/compute",
        json={"keyword": "saas", "client_id": "client-1"},
    )
    history_response = client.get(
        "/api/trends/history",
        params={"client_id": "client-1", "project_id": "project-1", "limit": 25},
    )
    insights_response = client.get(
        "/api/trends/insights",
        params={"client_id": "client-1", "project_id": "project-1", "min_priority": 0.5},
    )
    timeframes_response = client.get("/api/trends/timeframes")
    categories_response = client.get("/api/trends/categories")

    try:
        assert interest_response.status_code == 200
        assert interest_response.json()["search_id"] == "s-1"
        assert related_response.status_code == 200
        assert insight_response.status_code == 200
        assert history_response.status_code == 200
        assert insights_response.status_code == 200
        assert timeframes_response.status_code == 200
        assert categories_response.status_code == 200

        assert captured["interest"]["keywords"] == ["saas", "content"]
        assert captured["interest"]["user_id"] == "user-123"
        assert captured["related"]["keywords"] == ["saas"]
        assert captured["insight"]["keyword"] == "saas"
        assert captured["history"]["limit"] == 25
        assert captured["insights"]["min_priority"] == 0.5
    finally:
        _clear_overrides()


def test_trends_search_interest_importerror(monkeypatch):
    client = _make_client(monkeypatch)
    monkeypatch.setattr(
        trends_mod.trends_service,
        "search_interest_over_time",
        lambda **kwargs: (_ for _ in ()).throw(ImportError("missing pytrends")),
    )

    try:
        response = client.post("/api/trends/search/interest", json={"keywords": ["saas"]})
        assert response.status_code == 503
        assert "pytrends" in response.json()["detail"]
    finally:
        _clear_overrides()


def test_trends_related_queries_and_insight_errors(monkeypatch):
    client = _make_client(monkeypatch)

    def boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(trends_mod.trends_service, "search_related_queries", boom)
    monkeypatch.setattr(trends_mod.trends_service, "compute_keyword_insights", boom)
    monkeypatch.setattr(trends_mod.trends_service, "get_search_history", boom)
    monkeypatch.setattr(trends_mod.trends_service, "get_keyword_insights", boom)

    try:
        related_response = client.post("/api/trends/search/related", json={"keywords": ["saas"]})
        insight_response = client.post("/api/trends/insights/compute", json={"keyword": "saas"})
        history_response = client.get("/api/trends/history")
        insights_response = client.get("/api/trends/insights")

        assert related_response.status_code == 500
        assert "Related queries search failed" in related_response.json()["detail"]
        assert insight_response.status_code == 500
        assert "Insight computation failed" in insight_response.json()["detail"]
        assert history_response.status_code == 500
        assert "Failed to get search history" in history_response.json()["detail"]
        assert insights_response.status_code == 500
        assert "Failed to get insights" in insights_response.json()["detail"]
    finally:
        _clear_overrides()
