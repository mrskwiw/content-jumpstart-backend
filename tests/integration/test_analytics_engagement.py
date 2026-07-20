"""
Integration tests for Phase 11 — Analytics & Engagement.

Publishes content via the Phase 10 stub, collects (stub) metrics, and checks the
overview / by-platform / by-template / top-posts aggregations and per-user
scoping.
"""

from backend.models import User
from backend.utils.auth import get_password_hash, create_access_token

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _make_user(db, email, uid):
    u = User(
        id=uid, email=email, hashed_password=get_password_hash(PW), full_name="Op", is_active=True
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def _publish_stub(client, hdr, content):
    sp = client.post(
        "/api/distribution/schedule",
        json={"platform": "stub", "content": content, "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=hdr,
    ).json()
    r = client.post(f"/api/distribution/publish/{sp['id']}", headers=hdr)
    assert r.status_code == 200 and r.json()["status"] == "posted"


def test_collect_and_aggregate(client, db_session):
    u = _make_user(db_session, "an-user@example.com", "user-an")
    hdr = _hdr(u)
    _publish_stub(client, hdr, "First post about widgets")
    _publish_stub(client, hdr, "Second post about gadgets")

    col = client.post("/api/analytics/collect", headers=hdr)
    assert col.status_code == 200, col.text
    assert col.json()["collected"] == 2

    ov = client.get("/api/analytics/overview", headers=hdr).json()
    assert ov["posts"] == 2
    assert ov["impressions"] > 0
    assert ov["engagement_rate"] >= 0

    bp = client.get("/api/analytics/by-platform", headers=hdr).json()
    assert any(row["platform"] == "stub" and row["posts"] == 2 for row in bp)

    bt = client.get("/api/analytics/by-template", headers=hdr).json()
    assert any(row["template"] == "untagged" for row in bt)

    top = client.get("/api/analytics/top-posts", headers=hdr).json()
    assert len(top) == 2
    assert all("engagement_rate" in row for row in top)


def test_collect_is_idempotent_per_day(client, db_session):
    u = _make_user(db_session, "an-idem@example.com", "user-anidem")
    hdr = _hdr(u)
    _publish_stub(client, hdr, "only post")
    client.post("/api/analytics/collect", headers=hdr)
    client.post("/api/analytics/collect", headers=hdr)  # second run, same day
    ov = client.get("/api/analytics/overview", headers=hdr).json()
    assert ov["posts"] == 1  # not duplicated


def test_overview_scoped_to_user(client, db_session):
    a = _make_user(db_session, "an-a@example.com", "user-ana")
    b = _make_user(db_session, "an-b@example.com", "user-anb")
    _publish_stub(client, _hdr(a), "a's post")
    client.post("/api/analytics/collect", headers=_hdr(a))
    ov_b = client.get("/api/analytics/overview", headers=_hdr(b)).json()
    assert ov_b["posts"] == 0
