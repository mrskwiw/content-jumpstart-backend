"""
Tests for the Phase 11 analytics "full build" additions: benchmark tiers, daily
series, trend detection, auto-insights, and the PDF report endpoint.
"""

import uuid
from datetime import date, timedelta

import pytest

from backend.models import User
from backend.models.analytics import PostMetric
from backend.services.analytics import engine
from backend.utils.auth import create_access_token, get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _user(db, email, uid):
    u = User(
        id=uid, email=email, hashed_password=get_password_hash(PW), full_name="Op", is_active=True
    )
    db.add(u)
    db.commit()
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def _metric(db, user_id, d, likes, impressions, platform="twitter"):
    db.add(
        PostMetric(
            id=str(uuid.uuid4()),
            user_id=user_id,
            posted_content_id=None,
            platform=platform,
            metric_date=d,
            likes=likes,
            comments=0,
            shares=0,
            impressions=impressions,
            reach=impressions,
        )
    )
    db.commit()


def _metric_with_template(db, user_id, template_name, platform="stub"):
    db.add(
        PostMetric(
            id=str(uuid.uuid4()),
            user_id=user_id,
            posted_content_id=None,
            platform=platform,
            template_name=template_name,
            metric_date=date.today(),
            likes=20,
            comments=2,
            shares=1,
            impressions=500,
            reach=400,
        )
    )
    db.commit()


def test_benchmark_tier_bands():
    assert engine.benchmark_tier("twitter", 0.001) == "poor"
    assert engine.benchmark_tier("twitter", 0.005) == "average"
    assert engine.benchmark_tier("twitter", 0.015) == "good"
    assert engine.benchmark_tier("twitter", 0.030) == "excellent"
    # Unknown platform falls back to the default band.
    assert engine.benchmark_tier("myspace", 0.0001) == "poor"


def test_insights_empty_when_no_data(db_session):
    u = _user(db_session, "eng-empty@example.com", "user-engempty")
    lines = engine.insights(db_session, u.id)
    assert len(lines) == 1 and "No published content" in lines[0]


def test_daily_series_and_upward_trend(db_session):
    u = _user(db_session, "eng-trend@example.com", "user-engtrend")
    today = date.today()  # daily_series filters by a cutoff off the real date
    _metric(db_session, u.id, today - timedelta(days=3), likes=1, impressions=100)  # 1%
    _metric(db_session, u.id, today - timedelta(days=2), likes=1, impressions=100)  # 1%
    _metric(db_session, u.id, today - timedelta(days=1), likes=5, impressions=100)  # 5%
    _metric(db_session, u.id, today, likes=5, impressions=100)  # 5%

    series = engine.daily_series(db_session, u.id)
    assert len(series) == 4
    assert series[0]["date"] < series[-1]["date"]

    tr = engine.trend(db_session, u.id)
    assert tr["direction"] == "up"
    assert tr["change_pct"] > 0


def test_trend_is_volume_weighted_not_daily_average(db_session):
    """A tiny high-rate spike day must not flip the trend when the high-volume
    days dominate. Unweighted daily averaging would call this 'up'; the
    volume-weighted rate correctly calls it 'down'."""
    u = _user(db_session, "eng-weight@example.com", "user-engweight")
    today = date.today()
    # Prior window: solid 1% on real volume.
    _metric(db_session, u.id, today - timedelta(days=3), likes=10, impressions=1000)  # 1%
    _metric(db_session, u.id, today - timedelta(days=2), likes=10, impressions=1000)  # 1%
    # Recent window: a big-volume low day + a 1-impression 100% spike.
    _metric(db_session, u.id, today - timedelta(days=1), likes=5, impressions=1000)  # 0.5%
    _metric(db_session, u.id, today, likes=1, impressions=1)  # 100% but 1 impression

    tr = engine.trend(db_session, u.id, window_days=2)
    assert tr["direction"] == "down"  # weighted recent (~0.6%) < prior (1%)


def test_report_pdf_survives_xml_special_template_name(db_session):
    reportlab = pytest.importorskip("reportlab")  # noqa: F841
    from backend.services.analytics import report

    u = _user(db_session, "eng-xml@example.com", "user-engxml")
    # A template name with XML-special chars would break ReportLab if unescaped.
    _metric_with_template(db_session, u.id, "Tips & Tricks <b> / A>B")
    pdf = report.build_pdf(db_session, u.id)
    assert pdf[:4] == b"%PDF"


def test_benchmarks_and_insights_endpoints(client, db_session):
    u = _user(db_session, "eng-ep@example.com", "user-engep")
    hdr = _hdr(u)
    sp = client.post(
        "/api/distribution/schedule",
        json={
            "platform": "stub",
            "content": "hello widgets",
            "scheduled_for": "2020-01-01T00:00:00Z",
        },
        headers=hdr,
    ).json()
    client.post(f"/api/distribution/publish/{sp['id']}", headers=hdr)
    client.post("/api/analytics/collect", headers=hdr)

    bm = client.get("/api/analytics/benchmarks", headers=hdr).json()
    assert bm and all("benchmark_tier" in row for row in bm)

    ins = client.get("/api/analytics/insights", headers=hdr).json()
    assert "insights" in ins and len(ins["insights"]) >= 1


def test_report_pdf_endpoint(client, db_session):
    pytest.importorskip("reportlab")
    u = _user(db_session, "eng-pdf@example.com", "user-engpdf")
    hdr = _hdr(u)
    sp = client.post(
        "/api/distribution/schedule",
        json={"platform": "stub", "content": "pdf post", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=hdr,
    ).json()
    client.post(f"/api/distribution/publish/{sp['id']}", headers=hdr)
    client.post("/api/analytics/collect", headers=hdr)

    r = client.get("/api/analytics/report.pdf", headers=hdr)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
