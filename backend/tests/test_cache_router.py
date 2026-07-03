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
import backend.routers.cache as cache_mod


class _FakeCache:
    def __init__(self):
        self.cleared = False
        self.patterns = []

    def get_stats(self):
        return {"size": 3, "max_size": 10, "hits": 7, "misses": 2, "hit_rate": 0.7}

    async def clear(self):
        self.cleared = True

    async def invalidate_pattern(self, pattern):
        self.patterns.append(pattern)


def _set_user(user):
    main_mod.app.dependency_overrides[cache_mod.get_current_user] = lambda: user


def _clear_overrides():
    main_mod.app.dependency_overrides.pop(cache_mod.get_current_user, None)


def test_cache_admin_endpoints(monkeypatch):
    fake_cache = _FakeCache()
    _set_user(SimpleNamespace(is_superuser=True))
    monkeypatch.setattr(cache_mod, "get_cache", lambda: fake_cache)
    client = TestClient(main_mod.app)

    try:
        stats_response = client.get("/api/cache/cache/stats")
        clear_response = client.post("/api/cache/cache/clear")
        invalidate_response = client.delete("/api/cache/cache/pattern/research_results:*")

        assert stats_response.status_code == 200
        assert stats_response.json()["hit_rate"] == 0.7
        assert clear_response.status_code == 200
        assert clear_response.json()["message"] == "Cache cleared successfully"
        assert invalidate_response.status_code == 200
        assert fake_cache.cleared is True
        assert fake_cache.patterns == ["research_results:*"]
    finally:
        _clear_overrides()


def test_cache_rejects_non_admin(monkeypatch):
    _set_user(SimpleNamespace(is_superuser=False))
    monkeypatch.setattr(cache_mod, "get_cache", lambda: _FakeCache())
    client = TestClient(main_mod.app)

    try:
        response = client.get("/api/cache/cache/stats")
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        _clear_overrides()
