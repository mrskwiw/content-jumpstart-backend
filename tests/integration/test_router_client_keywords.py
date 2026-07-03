"""Integration tests for client keyword router.

Covers:
- All 6 endpoints (list, add, update, delete, bulk, import)
- Authentication (401 for missing token)
- Ownership isolation: user B cannot access user A's client keywords
- Superuser bypass
- Input validation (400 on bad payload)
- Soft-delete semantics
- Bulk upsert and import from research result
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import Client, User
from backend.models.client_keywords import ClientKeyword
from backend.models.research_result import ResearchResult
from backend.utils.auth import get_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def user_a(db_session: Session):
    user = User(
        id="kw-user-a",
        email="kw_usera@example.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="KW User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session: Session):
    user = User(
        id="kw-user-b",
        email="kw_userb@example.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="KW User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superuser(db_session: Session):
    user = User(
        id="kw-superuser",
        email="kw_super@example.com",
        hashed_password=get_password_hash("Super123!"),
        full_name="KW Superuser",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client_a(db_session: Session, user_a):
    c = Client(
        id="client-kw-a",
        user_id=user_a.id,
        name="KW Client A",
        business_description="Business description for KW client A that is long enough to pass validation requirements",
        ideal_customer="Tech professionals",
        main_problem_solved="Content creation",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def client_b(db_session: Session, user_b):
    c = Client(
        id="client-kw-b",
        user_id=user_b.id,
        name="KW Client B",
        business_description="Business description for KW client B that is long enough to pass validation requirements",
        ideal_customer="Marketers",
        main_problem_solved="SEO",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def auth_a(user_a, client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "kw_usera@example.com", "password": "Pass123!"},  # pragma: allowlist secret
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth_b(user_b, client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "kw_userb@example.com", "password": "Pass123!"},  # pragma: allowlist secret
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth_super(superuser, client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "kw_super@example.com", "password": "Super123!"},  # pragma: allowlist secret
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def seeded_keyword(db_session: Session, client_a: Client):
    """A single active keyword owned by client_a."""
    kw = ClientKeyword(
        client_id=client_a.id,
        keyword="content marketing",
        keyword_type="primary",
        source="manual",
        is_active=True,
    )
    db_session.add(kw)
    db_session.commit()
    db_session.refresh(kw)
    return kw


@pytest.fixture
def seeded_research_result(db_session: Session, client_a: Client, user_a):
    """A minimal SEO research result linked to client_a."""
    rr = ResearchResult(
        id="rr-kw-test-001",
        user_id=user_a.id,
        client_id=client_a.id,
        tool_name="seo_keyword_research",
        status="completed",
        data={
            "primary_keywords": ["content strategy", "seo audit"],
            "secondary_keywords": ["blog writing"],
            "quick_win_keywords": [],
            "negative_keywords": ["cheap", "free"],
        },
    )
    db_session.add(rr)
    db_session.commit()
    db_session.refresh(rr)
    return rr


# ---------------------------------------------------------------------------
# GET /{client_id}/keywords
# ---------------------------------------------------------------------------


class TestListKeywords:
    def test_returns_empty_grouped_structure(self, client, client_a, auth_a):
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) >= {"primary", "secondary", "negative", "quick_win", "total"}
        assert data["total"] == 0

    def test_returns_seeded_keywords(self, client, client_a, auth_a, seeded_keyword):
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert len(resp.json()["primary"]) == 1
        assert resp.json()["primary"][0]["keyword"] == "content marketing"

    def test_type_filter(self, client, client_a, auth_a, db_session):
        # Add a negative kw
        db_session.add(
            ClientKeyword(
                client_id=client_a.id,
                keyword="bad term",
                keyword_type="negative",
                source="manual",
                is_active=True,
            )
        )
        db_session.commit()
        resp = client.get(f"/api/clients/{client_a.id}/keywords?type=negative", headers=auth_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["negative"]) == 1

    def test_unauthenticated_returns_401(self, client, client_a):
        resp = client.get(f"/api/clients/{client_a.id}/keywords")
        assert resp.status_code == 401

    def test_cross_user_access_denied(self, client, client_a, auth_b, client_b):
        """User B cannot list keywords for user A's client."""
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_b)
        assert resp.status_code == 403

    def test_superuser_can_access_any_client(self, client, client_a, auth_super):
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_super)
        assert resp.status_code == 200

    def test_nonexistent_client_returns_404(self, client, auth_a):
        resp = client.get("/api/clients/client-does-not-exist/keywords", headers=auth_a)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /{client_id}/keywords
# ---------------------------------------------------------------------------


class TestAddKeyword:
    def test_creates_keyword_returns_201(self, client, client_a, auth_a):
        payload = {"keyword": "email marketing", "keyword_type": "primary"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["keyword"] == "email marketing"
        assert data["keyword_type"] == "primary"
        assert data["source"] == "manual"
        assert data["is_active"] is True

    def test_strips_whitespace(self, client, client_a, auth_a):
        payload = {"keyword": "  seo tips  ", "keyword_type": "secondary"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 201
        assert resp.json()["keyword"] == "seo tips"

    def test_invalid_keyword_type_returns_422(self, client, client_a, auth_a):
        payload = {"keyword": "test kw", "keyword_type": "invalid_type"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 422

    def test_too_short_keyword_returns_422(self, client, client_a, auth_a):
        payload = {"keyword": "x", "keyword_type": "primary"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 422

    def test_duplicate_active_returns_409(self, client, client_a, auth_a, seeded_keyword):
        payload = {"keyword": "content marketing", "keyword_type": "primary"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 409

    def test_unauthenticated_returns_401(self, client, client_a):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords",
            json={"keyword": "test", "keyword_type": "primary"},
        )
        assert resp.status_code == 401

    def test_cross_user_returns_403(self, client, client_a, auth_b):
        payload = {"keyword": "cross user kw", "keyword_type": "primary"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_b)
        assert resp.status_code == 403

    def test_negative_keyword_over_100_chars_returns_422(self, client, client_a, auth_a):
        payload = {"keyword": "a" * 101, "keyword_type": "negative"}
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 422

    def test_with_optional_metadata(self, client, client_a, auth_a):
        payload = {
            "keyword": "meta keyword",
            "keyword_type": "primary",
            "search_intent": "informational",
            "difficulty": "low",
            "notes": "Watch this one",
        }
        resp = client.post(f"/api/clients/{client_a.id}/keywords", json=payload, headers=auth_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["search_intent"] == "informational"
        assert data["notes"] == "Watch this one"


# ---------------------------------------------------------------------------
# PUT /{client_id}/keywords/{keyword_id}
# ---------------------------------------------------------------------------


class TestUpdateKeyword:
    def test_updates_keyword_text(self, client, client_a, auth_a, seeded_keyword):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            json={"keyword": "updated content marketing"},
            headers=auth_a,
        )
        assert resp.status_code == 200
        assert resp.json()["keyword"] == "updated content marketing"

    def test_updates_notes(self, client, client_a, auth_a, seeded_keyword):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            json={"notes": "Priority keyword"},
            headers=auth_a,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Priority keyword"

    def test_deactivates_via_update(self, client, client_a, auth_a, seeded_keyword):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            json={"is_active": False},
            headers=auth_a,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_wrong_client_returns_404(self, client, client_b, auth_b, seeded_keyword):
        """seeded_keyword belongs to client_a; user_b tries to update via client_b."""
        resp = client.put(
            f"/api/clients/{client_b.id}/keywords/{seeded_keyword.id}",
            json={"keyword": "hacked"},
            headers=auth_b,
        )
        assert resp.status_code == 404

    def test_cross_user_returns_403(self, client, client_a, auth_b, seeded_keyword):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            json={"keyword": "injected"},
            headers=auth_b,
        )
        assert resp.status_code == 403

    def test_reactivation_at_cap_returns_400(self, client, client_a, auth_a, db_session):
        """Cap regression: PUT {is_active: true} on a soft-deleted keyword must return 400
        when the type is already at the 50-keyword limit."""
        from backend.models.client_keywords import ClientKeyword

        # Fill to 50 active primaries
        for i in range(50):
            db_session.add(
                ClientKeyword(
                    client_id=client_a.id,
                    keyword=f"filler {i:03d}",
                    keyword_type="primary",
                    source="manual",
                    is_active=True,
                )
            )
        # Add one soft-deleted primary to attempt reactivation
        soft_kw = ClientKeyword(
            client_id=client_a.id,
            keyword="soft deleted kw",
            keyword_type="primary",
            source="manual",
            is_active=False,
        )
        db_session.add(soft_kw)
        db_session.commit()
        db_session.refresh(soft_kw)

        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{soft_kw.id}",
            json={"is_active": True},
            headers=auth_a,
        )
        assert resp.status_code == 400
        assert "Maximum" in resp.json()["detail"]

    def test_nonexistent_keyword_returns_404(self, client, client_a, auth_a):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/99999",
            json={"notes": "ghost"},
            headers=auth_a,
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client, client_a, seeded_keyword):
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            json={"keyword": "no auth"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /{client_id}/keywords/{keyword_id}
# ---------------------------------------------------------------------------


class TestDeleteKeyword:
    def test_soft_delete_returns_204(self, client, client_a, auth_a, seeded_keyword):
        resp = client.delete(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            headers=auth_a,
        )
        assert resp.status_code == 204

    def test_deleted_keyword_excluded_from_list(
        self, client, client_a, auth_a, seeded_keyword, db_session
    ):
        client.delete(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            headers=auth_a,
        )
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.json()["total"] == 0

    def test_deleted_keyword_row_still_exists_inactive(
        self, client, client_a, auth_a, seeded_keyword, db_session
    ):
        client.delete(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            headers=auth_a,
        )
        row = db_session.query(ClientKeyword).filter(ClientKeyword.id == seeded_keyword.id).first()
        assert row is not None
        assert row.is_active is False

    def test_wrong_client_returns_404(self, client, client_b, auth_b, seeded_keyword):
        resp = client.delete(
            f"/api/clients/{client_b.id}/keywords/{seeded_keyword.id}",
            headers=auth_b,
        )
        assert resp.status_code == 404

    def test_cross_user_returns_403(self, client, client_a, auth_b, seeded_keyword):
        resp = client.delete(
            f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}",
            headers=auth_b,
        )
        assert resp.status_code == 403

    def test_nonexistent_returns_404(self, client, client_a, auth_a):
        resp = client.delete(
            f"/api/clients/{client_a.id}/keywords/99999",
            headers=auth_a,
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client, client_a, seeded_keyword):
        resp = client.delete(f"/api/clients/{client_a.id}/keywords/{seeded_keyword.id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /{client_id}/keywords/bulk
# ---------------------------------------------------------------------------


class TestBulkUpsert:
    def _payload(self, *keywords, ktype: str = "primary") -> dict:
        return {"keywords": [{"keyword": kw, "keyword_type": ktype} for kw in keywords]}

    def test_bulk_creates_keywords(self, client, client_a, auth_a):
        payload = self._payload("bulk one", "bulk two", "bulk three")
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=payload,
            headers=auth_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 3
        assert data["skipped"] == 0

    def test_bulk_deduplicates(self, client, client_a, auth_a, seeded_keyword):
        payload = self._payload("content marketing", "brand new kw")
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=payload,
            headers=auth_a,
        )
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_over_50_items_rejected(self, client, client_a, auth_a):
        payload = {
            "keywords": [
                {"keyword": f"keyword {i:03d}", "keyword_type": "primary"} for i in range(51)
            ]
        }
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=payload,
            headers=auth_a,
        )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self, client, client_a):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=self._payload("kw one"),
        )
        assert resp.status_code == 401

    def test_cross_user_returns_403(self, client, client_a, auth_b):
        payload = self._payload("injected kw")
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=payload,
            headers=auth_b,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /{client_id}/keywords/import/{result_id}
# ---------------------------------------------------------------------------


class TestImportFromResearch:
    def test_imports_from_research_result(self, client, client_a, auth_a, seeded_research_result):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] > 0
        assert "message" in data

    def test_imported_keywords_visible_in_list(
        self, client, client_a, auth_a, seeded_research_result
    ):
        client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_a,
        )
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.json()["total"] > 0

    def test_nonexistent_result_returns_404(self, client, client_a, auth_a):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/rr-does-not-exist",
            headers=auth_a,
        )
        assert resp.status_code == 404

    def test_wrong_tool_name_returns_404(self, client, client_a, user_a, auth_a, db_session):
        """Research result with wrong tool_name is rejected."""
        rr = ResearchResult(
            id="rr-wrong-tool",
            user_id=user_a.id,
            client_id=client_a.id,
            tool_name="audience_research",  # not seo_keyword_research
            status="completed",
            data={"primary_keywords": ["something"]},
        )
        db_session.add(rr)
        db_session.commit()
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/rr-wrong-tool",
            headers=auth_a,
        )
        assert resp.status_code == 404

    def test_idempotent_double_import(self, client, client_a, auth_a, seeded_research_result):
        resp1 = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_a,
        )
        resp2 = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_a,
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Second import: 0 new, all skipped
        assert resp2.json()["imported"] == 0
        assert resp2.json()["skipped"] > 0

    def test_cross_user_returns_403(self, client, client_a, auth_b, seeded_research_result):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_b,
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, client_a, seeded_research_result):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}"
        )
        assert resp.status_code == 401

    def test_superuser_can_import_any_client(
        self, client, client_a, auth_super, seeded_research_result
    ):
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/{seeded_research_result.id}",
            headers=auth_super,
        )
        assert resp.status_code == 200

    def test_oversized_keyword_in_research_data_does_not_cause_500(
        self, client, client_a, user_a, auth_a, db_session
    ):
        """Edge case regression: a keyword >200 chars or negative >100 chars in the
        research result JSON must be silently skipped, not cause a 500."""
        rr = ResearchResult(
            id="rr-oversized",
            user_id=user_a.id,
            client_id=client_a.id,
            tool_name="seo_keyword_research",
            status="completed",
            data={
                "primary_keywords": ["x" * 201, "valid primary"],
                "secondary_keywords": [],
                "quick_win_keywords": [],
                "negative_keywords": ["b" * 101, "cheap"],
            },
        )
        db_session.add(rr)
        db_session.commit()
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/rr-oversized",
            headers=auth_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        # "x"*201 and "b"*101 are silently dropped; "valid primary" and "cheap" are imported
        assert data["imported"] == 2

    def test_dict_format_negative_keywords_imported(
        self, client, client_a, user_a, auth_a, db_session
    ):
        """Edge case regression: negative keywords as dicts must be imported, not silently dropped."""
        rr = ResearchResult(
            id="rr-dict-neg",
            user_id=user_a.id,
            client_id=client_a.id,
            tool_name="seo_keyword_research",
            status="completed",
            data={
                "primary_keywords": [],
                "secondary_keywords": [],
                "quick_win_keywords": [],
                "negative_keywords": [
                    {"keyword": "cheap services", "reason": "low intent"},
                    "free stuff",
                ],
            },
        )
        db_session.add(rr)
        db_session.commit()
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/import/rr-dict-neg",
            headers=auth_a,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 2


# ---------------------------------------------------------------------------
# End-to-end workflow
# ---------------------------------------------------------------------------


class TestKeywordEditorE2E:
    """Full CRUD lifecycle: add → list → edit → delete → confirm gone."""

    def test_full_lifecycle(self, client, client_a, auth_a):
        # 1. Add three keywords
        kws = ["email strategy", "content calendar", "seo basics"]
        ids = []
        for kw in kws:
            resp = client.post(
                f"/api/clients/{client_a.id}/keywords",
                json={"keyword": kw, "keyword_type": "primary"},
                headers=auth_a,
            )
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        # 2. List — all 3 present
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.json()["total"] == 3

        # 3. Edit first
        resp = client.put(
            f"/api/clients/{client_a.id}/keywords/{ids[0]}",
            json={"notes": "Top priority"},
            headers=auth_a,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Top priority"

        # 4. Delete second
        resp = client.delete(
            f"/api/clients/{client_a.id}/keywords/{ids[1]}",
            headers=auth_a,
        )
        assert resp.status_code == 204

        # 5. List — 2 remain
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.json()["total"] == 2

        # 6. Bulk add 2 more with different types
        payload = {
            "keywords": [
                {"keyword": "bulk negative one", "keyword_type": "negative"},
                {"keyword": "bulk negative two", "keyword_type": "negative"},
            ]
        }
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords/bulk",
            json=payload,
            headers=auth_a,
        )
        assert resp.json()["imported"] == 2

        # 7. Final count: 2 primary + 2 negative = 4
        resp = client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_a)
        assert resp.json()["total"] == 4
        assert len(resp.json()["negative"]) == 2

    def test_ownership_isolation_is_complete(self, client, client_a, client_b, auth_a, auth_b):
        """User A's keywords are never accessible to user B even when guessing IDs."""
        # A adds a keyword
        resp = client.post(
            f"/api/clients/{client_a.id}/keywords",
            json={"keyword": "private keyword", "keyword_type": "primary"},
            headers=auth_a,
        )
        kw_id = resp.json()["id"]

        # B tries all operations on A's client
        assert client.get(f"/api/clients/{client_a.id}/keywords", headers=auth_b).status_code == 403
        assert (
            client.post(
                f"/api/clients/{client_a.id}/keywords",
                json={"keyword": "injected", "keyword_type": "primary"},
                headers=auth_b,
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/clients/{client_a.id}/keywords/{kw_id}",
                json={"notes": "compromised"},
                headers=auth_b,
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/api/clients/{client_a.id}/keywords/{kw_id}",
                headers=auth_b,
            ).status_code
            == 403
        )
