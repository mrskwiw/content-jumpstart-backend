"""Tests for the business-summary aggregation (GAP-UI-01, internal-ops Analytics).

Covers the real project/post/client/template counts, the time-window filter, and
per-user scoping. Revenue/quality are intentionally absent from the output.
"""

from datetime import datetime, timedelta

from backend.models import Client, Post, Project, User
from backend.services.analytics import business
from backend.utils.auth import get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _user(db, uid):
    db.add(
        User(id=uid, email=f"{uid}@x.com", hashed_password=get_password_hash(PW), is_active=True)
    )
    db.commit()


def _client(db, cid, uid, name):
    db.add(Client(id=cid, user_id=uid, name=name))
    db.commit()


def _project(db, pid, uid, cid, when):
    db.add(Project(id=pid, user_id=uid, client_id=cid, name="Proj", created_at=when))
    db.commit()


def _post(db, pid, project_id, template, when):
    db.add(
        Post(
            id=pid,
            project_id=project_id,
            run_id="run-x",
            content="body",
            template_name=template,
            created_at=when,
        )
    )
    db.commit()


def test_business_summary_counts_and_grouping(db_session):
    now = datetime.utcnow()
    _user(db_session, "u1")
    _client(db_session, "c1", "u1", "Acme")
    _client(db_session, "c2", "u1", "Globex")
    _project(db_session, "p1", "u1", "c1", now)
    _project(db_session, "p2", "u1", "c2", now)
    for i in range(3):
        _post(db_session, f"a{i}", "p1", "How-To", now)
    _post(db_session, "b0", "p2", "Question", now)

    s = business.business_summary(db_session, "u1", days=90)

    assert s["totals"] == {"projects": 2, "posts": 4, "clients": 2}
    # by_client sorted by posts desc → Acme (3) before Globex (1).
    assert [c["client_name"] for c in s["by_client"]] == ["Acme", "Globex"]
    assert s["by_client"][0]["posts"] == 3
    tpl = {t["template_name"]: t["usage_count"] for t in s["by_template"]}
    assert tpl == {"How-To": 3, "Question": 1}
    # No fabricated revenue/quality fields leak into the payload.
    assert "revenue" not in s["totals"]
    assert all("revenue" not in c and "avgQualityScore" not in c for c in s["by_client"])


def test_business_summary_excludes_rows_outside_window(db_session):
    now = datetime.utcnow()
    old = now - timedelta(days=200)
    _user(db_session, "u1")
    _client(db_session, "c1", "u1", "Acme")
    _project(db_session, "p_recent", "u1", "c1", now)
    _project(db_session, "p_old", "u1", "c1", old)
    _post(db_session, "recent", "p_recent", "How-To", now)
    _post(db_session, "old", "p_old", "How-To", old)

    s = business.business_summary(db_session, "u1", days=90)

    # Only the in-window project/post are counted.
    assert s["totals"]["projects"] == 1
    assert s["totals"]["posts"] == 1


def test_business_summary_excludes_soft_deleted(db_session):
    now = datetime.utcnow()
    _user(db_session, "u1")
    _client(db_session, "c1", "u1", "Acme")
    _project(db_session, "p_live", "u1", "c1", now)
    _post(db_session, "live", "p_live", "How-To", now)
    # A soft-deleted project (its post must be excluded transitively), an individually
    # soft-deleted post on the live project, and a live post inside the deleted project.
    db_session.add(
        Project(
            id="p_del", user_id="u1", client_id="c1", name="Proj", created_at=now, is_deleted=True
        )
    )
    db_session.add(
        Post(
            id="del_in_live",
            project_id="p_live",
            run_id="run-x",
            content="b",
            template_name="How-To",
            created_at=now,
            is_deleted=True,
        )
    )
    db_session.add(
        Post(
            id="post_in_del",
            project_id="p_del",
            run_id="run-x",
            content="b",
            template_name="How-To",
            created_at=now,
        )
    )
    db_session.commit()

    s = business.business_summary(db_session, "u1", days=90)

    # Only the live project and its single non-deleted post are counted.
    assert s["totals"]["projects"] == 1
    assert s["totals"]["posts"] == 1
    assert s["by_template"] == [{"template_name": "How-To", "usage_count": 1}]


def test_business_summary_is_scoped_to_the_user(db_session):
    now = datetime.utcnow()
    _user(db_session, "u1")
    _user(db_session, "u2")
    _client(db_session, "c1", "u1", "Mine")
    _client(db_session, "c2", "u2", "Theirs")
    _project(db_session, "p1", "u1", "c1", now)
    _project(db_session, "p2", "u2", "c2", now)
    _post(db_session, "mine", "p1", "How-To", now)
    _post(db_session, "theirs", "p2", "How-To", now)

    s = business.business_summary(db_session, "u1", days=90)

    assert s["totals"]["projects"] == 1
    assert s["totals"]["posts"] == 1
    assert [c["client_name"] for c in s["by_client"]] == ["Mine"]
