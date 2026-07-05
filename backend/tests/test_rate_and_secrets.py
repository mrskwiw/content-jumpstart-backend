"""
Unit tests for rate limiting and secret rotation utilities.
"""

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.utils import cache_invalidation
from backend.utils.rate_limiter import RateLimitTracker
from backend.utils.secret_rotation import (
    Secret,
    SecretManager,
    rotate_api_key,
    rotate_jwt_secret,
)
from backend.models.mixins import SoftDeleteMixin, TimestampMixin, get_active_query


class FakeCache:
    def __init__(self):
        self.patterns = []
        self.cleared = False

    async def invalidate_pattern(self, pattern: str):
        self.patterns.append(pattern)

    async def clear(self):
        self.cleared = True


class TestRateLimitTracker:
    @pytest.mark.asyncio
    async def test_usage_and_limits(self, monkeypatch):
        from backend.utils import rate_limiter as rate_module

        monkeypatch.setattr(
            rate_module.settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 2, raising=False
        )
        monkeypatch.setattr(rate_module.settings, "RATE_LIMIT_TOKENS_PER_MINUTE", 10, raising=False)

        tracker = RateLimitTracker()
        await tracker.record_request(3)
        await tracker.record_request(4)

        assert await tracker.can_make_request(3) is False
        stats = tracker.get_usage_stats()
        assert stats["requests"] == 2
        assert stats["tokens"] == 7
        assert stats["queue_length"] == 0

    @pytest.mark.asyncio
    async def test_queue_and_wait_time(self, monkeypatch):
        from backend.utils import rate_limiter as rate_module

        monkeypatch.setattr(
            rate_module.settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 60, raising=False
        )
        monkeypatch.setattr(
            rate_module.settings, "RATE_LIMIT_TOKENS_PER_MINUTE", 1000, raising=False
        )

        tracker = RateLimitTracker()
        await tracker.add_to_queue("b", 20, priority=1)
        await tracker.add_to_queue("a", 10, priority=2)

        assert await tracker.get_queue_position("a") == 0
        assert await tracker.get_queue_position("b") == 1
        assert await tracker.get_estimated_wait_time("b") == 1

        await tracker.remove_from_queue("a")
        assert await tracker.get_queue_position("a") == -1

    def test_cleanup_old_entries(self, monkeypatch):
        from backend.utils import rate_limiter as rate_module

        monkeypatch.setattr(
            rate_module.settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 60, raising=False
        )
        monkeypatch.setattr(
            rate_module.settings, "RATE_LIMIT_TOKENS_PER_MINUTE", 1000, raising=False
        )
        tracker = RateLimitTracker()

        old_time = datetime.now() - timedelta(minutes=2)
        tracker.requests_log.append((old_time, 5))
        tracker.requests_log.append((datetime.now(), 3))

        usage = tracker._get_current_usage()
        assert usage["requests"] == 1
        assert usage["tokens"] == 3


class TestCacheInvalidation:
    @pytest.mark.asyncio
    async def test_invalidate_project_and_client(self, monkeypatch):
        fake_cache = FakeCache()
        monkeypatch.setattr(cache_invalidation, "get_cache", lambda: fake_cache)

        await cache_invalidation.invalidate_project_cache("proj-1")
        await cache_invalidation.invalidate_client_cache("client-1")

        assert any("proj-1" in pattern for pattern in fake_cache.patterns)
        assert any("client-1" in pattern for pattern in fake_cache.patterns)

    @pytest.mark.asyncio
    async def test_invalidate_research_and_cost_and_all(self, monkeypatch):
        fake_cache = FakeCache()
        monkeypatch.setattr(cache_invalidation, "get_cache", lambda: fake_cache)

        await cache_invalidation.invalidate_research_cache(client_id="c1", project_id="p1")
        await cache_invalidation.invalidate_cost_cache("u1")
        await cache_invalidation.invalidate_all_caches()

        assert fake_cache.cleared is True
        assert len(fake_cache.patterns) >= 4


class TestSecretRotation:
    def test_secret_flags(self):
        secret = Secret(
            id="1",
            value="secret",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() - timedelta(days=1)).isoformat(),
        )
        assert secret.is_expired() is True
        assert secret.is_active() is False

    def test_load_without_env_secret_and_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

        config_path = Path(tmp_path) / "secrets-empty.json"
        if config_path.exists():
            config_path.unlink()
        manager = SecretManager(config_path=config_path)
        assert manager.get_active_secrets() == []
        assert config_path.exists()

        bad_path = Path(tmp_path) / "bad-secrets.json"
        bad_path.write_text("{not-json}", encoding="utf-8")
        with pytest.raises(ValueError):
            SecretManager(config_path=bad_path)

    def test_load_add_revoke_cleanup_and_status(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "s" * 32)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        config_dir = Path(tmp_path) / "secret_rotation_case1"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "secrets.json"

        manager = SecretManager(config_path=config_path)
        assert manager.get_primary_secret() == "s" * 32

        added = manager.add_secret("t" * 32, expires_in_days=1, auto_save=False)
        duplicate = manager.add_secret("t" * 32, auto_save=False)
        assert duplicate.id == added.id
        assert "t" * 32 in manager.get_active_secrets()

        manager.revoke_secret(added.id)
        assert manager.secrets[added.id].status == "revoked"

        manager.add_secret("u" * 32, expires_in_days=-1, auto_save=False)
        pre_cleanup_status = manager.get_status()
        assert pre_cleanup_status["revoked"] >= 1

        manager.cleanup_expired()
        status = manager.get_status()
        assert status["total"] >= 1

    def test_rotate_secret(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        config_dir = Path(tmp_path) / "secret_rotation_case2"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "secrets.json"
        manager = SecretManager(config_path=config_path)
        monkeypatch.setattr(manager, "generate_secret", lambda length=32: "b" * 32)

        rotated = manager.rotate_secret(grace_period_days=0, deprecation_period_days=0)

        assert rotated.value == "b" * 32
        assert manager.get_primary_secret() == "b" * 32

    def test_rotate_secret_keeps_old_secret_active_with_grace(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "c" * 32)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        config_dir = Path(tmp_path) / "secret_rotation_case3"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "secrets.json"
        manager = SecretManager(config_path=config_path)
        old_secret = manager.get_primary_secret()
        monkeypatch.setattr(manager, "generate_secret", lambda length=32: "d" * 32)

        rotated = manager.rotate_secret(grace_period_days=3, deprecation_period_days=7)

        assert rotated.value == "d" * 32
        assert old_secret in manager.get_active_secrets()

    def test_cli_helpers_print_guidance(self, monkeypatch):
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

        class FakeManager:
            def rotate_secret(self, grace_period_days, deprecation_period_days):
                return SimpleNamespace(id="secret-1", value="new-secret")

        monkeypatch.setattr("backend.utils.secret_rotation.SecretManager", lambda: FakeManager())

        rotate_jwt_secret()
        rotate_api_key()


class TestMixins:
    def test_soft_delete_restore_and_active_query(self):
        class Dummy(SoftDeleteMixin):
            def __init__(self):
                self.is_deleted = False
                self.deleted_at = None

        dummy = Dummy()
        assert dummy.is_active is True
        dummy.soft_delete()
        assert dummy.is_deleted is True
        assert dummy.deleted_at is not None
        dummy.restore()
        assert dummy.is_deleted is False
        assert dummy.deleted_at is None

        class FilterClause:
            def __init__(self):
                self.last_value = None

            def is_(self, value):
                self.last_value = value
                return f"is-{value}"

        class DummyModel:
            is_deleted = FilterClause()

        class Query:
            def __init__(self):
                self.filtered = False

            def filter(self, *_args, **_kwargs):
                self.filtered = True
                return "filtered"

        class Session:
            def query(self, model):
                self.model = model
                return Query()

        session = Session()
        result = get_active_query(session, DummyModel)
        assert result == "filtered"
        assert DummyModel.is_deleted.last_value is False

    def test_timestamp_mixin_columns_exist(self):
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")
