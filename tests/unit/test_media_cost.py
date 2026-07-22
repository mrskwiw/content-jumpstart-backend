"""
Unit tests for Phase 12 media cost estimation and the budget gate.

These are pure-function / small-DB tests: the projected-cost table, the per-job
and monthly ceilings, and the month-to-date sum. No provider or app involved.
"""

import pytest

from backend.services.media import cost
from backend.services.media.providers import MediaKind


def test_estimate_cost_uses_rate_table():
    # kling ≈ 12¢/s; an 8s clip ≈ 96¢.
    assert cost.estimate_cost(MediaKind.GEN_CLIP, "kling", seconds=8) == 96
    # stub is always free.
    assert cost.estimate_cost(MediaKind.TTS, "stub", seconds=30) == 0


def test_estimate_cost_defaults_seconds_by_kind():
    # No seconds → the kind's default (avatar_video = 60s) at heygen's 3¢/s = 180¢.
    assert cost.estimate_cost(MediaKind.AVATAR_VIDEO, "heygen") == 180


def test_estimate_cost_unknown_provider_is_not_free():
    # An unmapped provider must fall back to a premium rate, never silently $0.
    assert cost.estimate_cost(MediaKind.GEN_CLIP, "mystery", seconds=10) > 0


def test_enforce_budget_disabled_by_default(db_session):
    # With no caps configured, any spend is allowed.
    cost.enforce_budget(db_session, "u1", None, 999_999)


def test_enforce_budget_per_job_cap(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "100")
    cost.enforce_budget(db_session, "u1", None, 100)  # at the cap is OK
    with pytest.raises(cost.BudgetExceededError):
        cost.enforce_budget(db_session, "u1", None, 101)


def test_enforce_budget_monthly_cap(db_session, monkeypatch):
    from backend.models import User
    from backend.models.media import MediaJob
    from backend.utils.auth import get_password_hash

    u = User(
        id="u-month",
        email="month@example.com",
        hashed_password=get_password_hash("Zx9!qWmp7Kt#"),  # pragma: allowlist secret
        is_active=True,
    )
    db_session.add(u)
    # Already spent 80¢ this month.
    db_session.add(
        MediaJob(
            id="j-spent",
            user_id="u-month",
            kind="tts",
            provider="kling",
            status="done",
            cost_cents=80,
        )
    )
    db_session.commit()

    monkeypatch.setenv("MEDIA_MAX_MONTHLY_COST_CENTS", "100")
    assert cost.month_to_date_cents(db_session, "u-month") == 80
    cost.enforce_budget(db_session, "u-month", None, 20)  # 80 + 20 = 100, at cap
    with pytest.raises(cost.BudgetExceededError):
        cost.enforce_budget(db_session, "u-month", None, 21)  # 80 + 21 = 101, over
