"""
Tests for real (non-dry-run) Phase 11 metric collection.

Verifies the real collector path maps a platform insights response into a stored
PostMetric, and that a posted item with no connected credential is skipped rather
than faked.
"""

from datetime import datetime, timezone

from backend.models import User
from backend.models.analytics import PostMetric
from backend.models.distribution import PostedContent, ScheduledPost
from backend.services.analytics import collectors
from backend.services.distribution import orchestrator
from backend.utils.auth import get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _user(db, email, uid):
    u = User(
        id=uid, email=email, hashed_password=get_password_hash(PW), full_name="Op", is_active=True
    )
    db.add(u)
    db.commit()
    return u


def _posted_twitter(db, user_id, post_id="TID-1"):
    sp = ScheduledPost(
        id=f"sp-{post_id}",
        user_id=user_id,
        platform="twitter",
        content="hi",
        scheduled_for=datetime(2020, 1, 1, tzinfo=timezone.utc),
        status="posted",
        retry_count=0,
    )
    db.add(sp)
    db.commit()
    pc = PostedContent(
        id=f"pc-{post_id}",
        user_id=user_id,
        scheduled_post_id=sp.id,
        platform="twitter",
        platform_post_id=post_id,
    )
    db.add(pc)
    db.commit()
    return pc


def test_real_collect_maps_twitter_metrics(db_session, monkeypatch):
    monkeypatch.setenv("ANALYTICS_DRY_RUN", "false")
    u = _user(db_session, "col-tw@example.com", "user-coltw")
    _posted_twitter(db_session, u.id)
    orchestrator.save_credential(db_session, u.id, "twitter", "TOK")

    def fake_get(url, **kw):
        assert "TID-1" in url
        return _Resp(
            {
                "data": {
                    "public_metrics": {
                        "like_count": 10,
                        "reply_count": 2,
                        "retweet_count": 3,
                        "quote_count": 1,
                        "impression_count": 100,
                    }
                }
            }
        )

    monkeypatch.setattr(collectors.requests, "get", fake_get)
    res = collectors.collect_for_user(db_session, u.id)
    assert res == {"collected": 1, "skipped": 0, "dry_run": False}

    m = db_session.query(PostMetric).filter(PostMetric.user_id == u.id).first()
    assert (m.likes, m.comments, m.shares, m.impressions, m.reach) == (10, 2, 4, 100, 100)


def test_real_collect_skips_without_credential(db_session, monkeypatch):
    monkeypatch.setenv("ANALYTICS_DRY_RUN", "false")
    u = _user(db_session, "col-nocred@example.com", "user-colnocred")
    _posted_twitter(db_session, u.id)
    # No credential connected.
    res = collectors.collect_for_user(db_session, u.id)
    assert res == {"collected": 0, "skipped": 1, "dry_run": False}
    assert db_session.query(PostMetric).filter(PostMetric.user_id == u.id).count() == 0
