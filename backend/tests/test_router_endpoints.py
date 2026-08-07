"""
Unit tests for lightweight backend routers.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.routers import metrics as metrics_router
from backend.routers import pricing as pricing_router
from backend.routers import privacy as privacy_router
from backend.models import Client


class TestPricingRouter:
    @pytest.mark.asyncio
    async def test_get_pricing_config(self):
        result = await pricing_router.get_pricing_config.__wrapped__(request=SimpleNamespace())

        assert result.minPosts == 1
        assert result.maxPosts == 100
        assert result.unlimitedRevisions is True

    @pytest.mark.asyncio
    async def test_calculate_custom_price_get(self, monkeypatch):
        monkeypatch.setattr(pricing_router, "calculate_price", lambda **kwargs: 1200.0)

        result = await pricing_router.calculate_custom_price.__wrapped__(
            request=SimpleNamespace(),
            num_posts=30,
            research=True,
            body=None,
        )

        assert result.numPosts == 30
        assert result.researchIncluded is True
        assert result.totalPrice == 1200.0
        assert result.pricePerPost == 40.0

    @pytest.mark.asyncio
    async def test_calculate_custom_price_from_body(self, monkeypatch):
        monkeypatch.setattr(pricing_router, "calculate_price", lambda **kwargs: 450.0)

        result = await pricing_router.calculate_custom_price.__wrapped__(
            request=SimpleNamespace(),
            num_posts=None,
            research=False,
            body={"template_quantities": {"1": 2, "2": 3}, "research": True},
        )

        assert result.numPosts == 5
        assert result.researchIncluded is True
        assert result.totalPrice == 450.0

    @pytest.mark.asyncio
    async def test_calculate_custom_price_requires_num_posts_for_get(self):
        with pytest.raises(HTTPException) as exc:
            await pricing_router.calculate_custom_price.__wrapped__(
                request=SimpleNamespace(),
                num_posts=None,
                research=False,
                body=None,
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_calculate_price_from_template_quantities(self, monkeypatch):
        monkeypatch.setattr(
            pricing_router, "calculate_price_from_quantities", lambda **kwargs: 600.0
        )

        result = await pricing_router.calculate_price_from_template_quantities.__wrapped__(
            request=SimpleNamespace(),
            template_quantities={"1": 2, "2": 4},
            research=False,
        )

        assert result.numPosts == 6
        assert result.totalPrice == 600.0
        assert result.pricePerPost == 100.0


class TestMetricsRouter:
    @pytest.mark.asyncio
    async def test_metrics_summary(self, monkeypatch):
        fake_metrics = SimpleNamespace(
            get_summary=lambda: {
                "uptime_seconds": 10,
                "total_requests": 5,
                "total_errors": 1,
                "error_rate": 20.0,
                "endpoints_tracked": 2,
            }
        )
        monkeypatch.setattr(metrics_router, "get_metrics", lambda: fake_metrics)

        result = await metrics_router.get_metrics_summary(current_user=SimpleNamespace(id=1))

        assert result.total_requests == 5
        assert result.error_rate == 20.0

    @pytest.mark.asyncio
    async def test_endpoint_metrics(self, monkeypatch):
        fake_metrics = SimpleNamespace(
            get_endpoint_stats=lambda: {"GET /api/clients": {"total_requests": 1}}
        )
        monkeypatch.setattr(metrics_router, "get_metrics", lambda: fake_metrics)

        result = await metrics_router.get_endpoint_metrics(current_user=SimpleNamespace(id=1))

        assert result["GET /api/clients"]["total_requests"] == 1

    @pytest.mark.asyncio
    async def test_all_metrics(self, monkeypatch):
        fake_metrics = SimpleNamespace(
            get_summary=lambda: {
                "uptime_seconds": 10,
                "total_requests": 5,
                "total_errors": 1,
                "error_rate": 20.0,
                "endpoints_tracked": 2,
            },
            get_endpoint_stats=lambda: {
                "GET /api/clients": {
                    "total_requests": 1,
                    "successful_requests": 1,
                    "failed_requests": 0,
                    "success_rate": 100.0,
                    "avg_duration_ms": 1.5,
                    "min_duration_ms": 1.0,
                    "max_duration_ms": 2.0,
                    "p95_duration_ms": 2.0,
                }
            },
            get_error_summary=lambda: {"500_/api/clients": 1},
        )
        fake_cache = SimpleNamespace(
            get_stats=lambda: {"size": 2, "max_size": 10, "hits": 1, "misses": 1, "hit_rate": 50.0}
        )
        monkeypatch.setattr(metrics_router, "get_metrics", lambda: fake_metrics)
        monkeypatch.setattr(metrics_router, "get_cache", lambda: fake_cache)

        result = await metrics_router.get_all_metrics(current_user=SimpleNamespace(id=1))

        assert result.summary.total_requests == 5
        assert result.cache.size == 2
        assert result.errors["500_/api/clients"] == 1

    @pytest.mark.asyncio
    async def test_prometheus_metrics(self, monkeypatch):
        fake_metrics = SimpleNamespace(
            get_summary=lambda: {
                "uptime_seconds": 10,
                "total_requests": 5,
                "total_errors": 1,
                "error_rate": 20.0,
                "endpoints_tracked": 1,
            },
            get_endpoint_stats=lambda: {
                "GET /api/clients": {
                    "total_requests": 1,
                    "avg_duration_ms": 2.5,
                    "p95_duration_ms": 3.0,
                }
            },
        )
        fake_cache = SimpleNamespace(
            get_stats=lambda: {"size": 2, "max_size": 10, "hits": 1, "misses": 1, "hit_rate": 50.0}
        )
        monkeypatch.setattr(metrics_router, "get_metrics", lambda: fake_metrics)
        monkeypatch.setattr(metrics_router, "get_cache", lambda: fake_cache)

        result = await metrics_router.get_prometheus_metrics()

        assert "app_uptime_seconds 10" in result
        assert 'http_requests_total{endpoint="GET /api/clients"} 1' in result


def _user(uid=1, superuser=False):
    """Caller stand-in for the privacy handlers' authorization check."""
    return SimpleNamespace(id=uid, is_superuser=superuser)


def _client_db(owner_id=1, client_id="abc", exists=True):
    """Session double for `_require_client_access`, the privacy handlers' IDOR guard.

    It answers the one query the guard makes, but only for the row that was actually
    asked for: it checks that the query targets `Client` and reads the id out of the
    filter predicate, returning the stored row only on a match. A permissive stub that
    returned the same client whatever was queried would keep passing if the router
    stopped filtering by id — i.e. it would leave the guard untested.
    """
    stored = SimpleNamespace(id=client_id, user_id=owner_id) if exists else None

    def _query(model):
        assert model is Client, f"privacy guard queried {model!r}, expected Client"

        def _filter(predicate, *rest):
            # `Client.id == <value>` — pull the bound value off the comparison.
            requested = predicate.right.value
            # (identity fails here — SQLAlchemy hands back an annotated copy of the column)
            column = predicate.left
            assert (column.name, column.table.name) == (
                "id",
                Client.__tablename__,
            ), f"privacy guard filtered on {column!r}, expected clients.id"
            matched = stored if (stored is not None and requested == stored.id) else None
            return SimpleNamespace(first=lambda: matched)

        return SimpleNamespace(filter=_filter)

    return SimpleNamespace(query=_query)


class TestPrivacyRouter:
    def test_delete_client(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "soft_delete_client",
            lambda client_id, db, cascade: {"client_id": client_id, "cascade": cascade},
        )

        result = privacy_router.delete_client(
            client_id="abc",
            cascade=True,
            db=_client_db(),
            current_user=_user(),
        )

        assert result["client_id"] == "abc"
        assert result["cascade"] is True

    def test_delete_client_not_found(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "soft_delete_client",
            lambda client_id, db, cascade: (_ for _ in ()).throw(ValueError("missing")),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.delete_client(
                client_id="abc",
                cascade=True,
                db=_client_db(),
                current_user=_user(),
            )

        assert exc.value.status_code == 404

    def test_anonymize_client(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "anonymize_client",
            lambda client_id, db: {"client_id": client_id, "anonymized": True},
        )

        result = privacy_router.anonymize_client(
            client_id="abc",
            db=_client_db(),
            current_user=_user(),
        )

        assert result["anonymized"] is True

    def test_anonymize_client_not_found(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "anonymize_client",
            lambda client_id, db: (_ for _ in ()).throw(ValueError("missing")),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.anonymize_client(
                client_id="abc",
                db=_client_db(),
                current_user=_user(),
            )

        assert exc.value.status_code == 404

    def test_export_client(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "export_client_data",
            lambda client_id, db: {"client_id": client_id, "exported": True},
        )

        result = privacy_router.export_client(
            client_id="abc",
            db=_client_db(),
            current_user=_user(),
        )

        assert result["exported"] is True

    def test_export_client_not_found(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "export_client_data",
            lambda client_id, db: (_ for _ in ()).throw(ValueError("missing")),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.export_client(
                client_id="abc",
                db=_client_db(),
                current_user=_user(),
            )

        assert exc.value.status_code == 404

    def test_restore_client(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "restore_soft_deleted_client",
            lambda client_id, db: {"client_id": client_id, "restored": True},
        )

        result = privacy_router.restore_client(
            client_id="abc",
            db=_client_db(),
            current_user=_user(),
        )

        assert result["restored"] is True

    def test_restore_client_not_found(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "restore_soft_deleted_client",
            lambda client_id, db: (_ for _ in ()).throw(ValueError("missing")),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.restore_client(
                client_id="abc",
                db=_client_db(),
                current_user=_user(),
            )

        assert exc.value.status_code == 404

    # The authorization guard itself. These tests exist because the handlers' unit
    # tests silently rotted when `_require_client_access` was added: a bare
    # SimpleNamespace() session has no .query, so every case above failed on the guard
    # rather than on the behaviour it was checking.
    def test_unknown_client_is_404(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "soft_delete_client",
            lambda client_id, db, cascade: called.append(client_id),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.delete_client(
                client_id="nope",
                cascade=False,
                db=_client_db(exists=False),
                current_user=_user(),
            )

        assert exc.value.status_code == 404
        assert called == []  # refused before the service ran

    def test_another_users_client_is_403(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "export_client_data",
            lambda client_id, db: called.append(client_id),
        )

        with pytest.raises(HTTPException) as exc:
            privacy_router.export_client(
                client_id="abc",
                db=_client_db(owner_id=999),
                current_user=_user(uid=1),
            )

        assert exc.value.status_code == 403
        assert called == []  # no data left the building

    def test_superuser_may_act_on_another_users_client(self, monkeypatch):
        monkeypatch.setattr(
            privacy_router.data_privacy_service,
            "export_client_data",
            lambda client_id, db: {"client_id": client_id, "exported": True},
        )

        result = privacy_router.export_client(
            client_id="abc",
            db=_client_db(owner_id=999),
            current_user=_user(uid=1, superuser=True),
        )

        assert result["exported"] is True
