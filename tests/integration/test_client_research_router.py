"""
Integration tests for the Client Research router.

Tests:
  POST /api/client-research/brief        — returns draft without persisting
  POST /api/client-research/clients/{id}/apply — persists discovered fields to DB
  402 on insufficient credits
  401 on unauthenticated request
  400 when client has no location (apply endpoint)
  Credit refund on agent failure
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Client, User
from backend.utils.auth import get_password_hash, create_access_token

# ── Shared fake research result ────────────────────────────────────────────


def _make_fake_result():
    """Build a ClientResearchResult with known field values for assertion."""
    from src.agents.client_research_agent import ClientResearchResult
    from src.models.client_brief import ClientBrief, DataUsagePreference

    brief = ClientBrief(
        company_name="Acme Agency",
        business_description="Full-service digital marketing agency.",
        ideal_customer="Small business owners",
        main_problem_solved="Lead generation",
        industry="Marketing",
        keywords=["marketing", "leads", "digital"],
        competitors=["Rival Co", "Other Agency"],
        customer_pain_points=["Too little time", "Poor ROI"],
        location="Austin, TX",
        data_usage=DataUsagePreference.MODERATE,
    )
    return ClientResearchResult(
        brief=brief,
        confidence={
            "business_description": 0.9,
            "industry": 0.8,
            "ideal_customer": 0.7,
            "competitors": 0.6,
        },
        sources=["https://example.com/acme", "https://linkedin.com/company/acme"],
        duration_seconds=4.2,
        stub_mode=False,
        warning=None,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def user_with_credits(db_session):
    user = User(
        id="user-research-001",
        email="researcher@example.com",
        hashed_password=get_password_hash("testpass123"),  # pragma: allowlist secret
        full_name="Research User",
        is_active=True,
        is_superuser=False,
        credit_balance=500,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_no_credits(db_session):
    user = User(
        id="user-broke-001",
        email="broke@example.com",
        hashed_password=get_password_hash("testpass123"),  # pragma: allowlist secret
        full_name="Broke User",
        is_active=True,
        is_superuser=False,
        credit_balance=50,  # below 200 threshold
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client_with_location(db_session, user_with_credits):
    db_client = Client(
        id="client-research-001",
        user_id=user_with_credits.id,
        name="Acme Agency",
        location="Austin, TX",
    )
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


@pytest.fixture
def client_no_location(db_session, user_with_credits):
    db_client = Client(
        id="client-noloc-001",
        user_id=user_with_credits.id,
        name="Mystery Corp",
        location=None,
    )
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


@pytest.fixture
def auth_headers(user_with_credits):
    token = create_access_token(data={"sub": user_with_credits.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def broke_auth_headers(user_no_credits):
    token = create_access_token(data={"sub": user_no_credits.id})
    return {"Authorization": f"Bearer {token}"}


# ── /brief endpoint ────────────────────────────────────────────────────────


class TestResearchBriefEndpoint:
    def test_returns_brief_shape(self, client, auth_headers, user_with_credits):
        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme Agency", "location": "Austin, TX"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "brief" in data
        assert "confidence" in data
        assert "sources" in data
        assert data["credit_cost"] == 200
        assert data["stub_mode"] is False

    def test_brief_contains_discovered_fields(self, client, auth_headers, user_with_credits):
        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme Agency", "location": "Austin, TX"},
                headers=auth_headers,
            )

        data = resp.json()
        brief = data["brief"]
        assert brief["business_description"] == "Full-service digital marketing agency."
        assert brief["industry"] == "Marketing"
        assert "marketing" in brief["keywords"]
        assert "Rival Co" in brief["competitors"]

    def test_deducts_200_credits(self, client, auth_headers, user_with_credits, db_session):
        initial_balance = user_with_credits.credit_balance

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme Agency", "location": "Austin, TX"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        db_session.refresh(user_with_credits)
        assert user_with_credits.credit_balance == initial_balance - 200

    def test_does_not_persist_to_client_table(
        self, client, auth_headers, user_with_credits, db_session
    ):
        """The /brief endpoint is discovery-only — no Client row should be created."""
        client_count_before = (
            db_session.query(Client).filter_by(user_id=user_with_credits.id).count()
        )

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme Agency", "location": "Austin, TX"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        client_count_after = (
            db_session.query(Client).filter_by(user_id=user_with_credits.id).count()
        )
        assert client_count_after == client_count_before

    def test_402_on_insufficient_credits(self, client, broke_auth_headers, user_no_credits):
        resp = client.post(
            "/api/client-research/brief",
            json={"name": "Acme Agency", "location": "Austin, TX"},
            headers=broke_auth_headers,
        )
        assert resp.status_code == 402
        assert "Insufficient credits" in resp.json()["detail"]

    def test_401_without_auth(self, client):
        resp = client.post(
            "/api/client-research/brief",
            json={"name": "Acme Agency", "location": "Austin, TX"},
        )
        assert resp.status_code == 401

    def test_refunds_credits_on_agent_failure(
        self, client, auth_headers, user_with_credits, db_session
    ):
        initial_balance = user_with_credits.credit_balance

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(side_effect=RuntimeError("Search provider down"))

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme Agency", "location": "Austin, TX"},
                headers=auth_headers,
            )

        assert resp.status_code == 500
        db_session.refresh(user_with_credits)
        # Credits should be refunded on failure
        assert user_with_credits.credit_balance == initial_balance

    def test_includes_stub_warning_when_provider_is_stub(
        self, client, auth_headers, user_with_credits
    ):
        from src.agents.client_research_agent import ClientResearchResult
        from src.models.client_brief import ClientBrief, DataUsagePreference

        stub_result = ClientResearchResult(
            brief=ClientBrief(
                company_name="Acme",
                business_description="Test",
                ideal_customer="SMBs",
                main_problem_solved="Time",
                data_usage=DataUsagePreference.MODERATE,
            ),
            confidence={},
            sources=[],
            duration_seconds=0.5,
            stub_mode=True,
            warning="Web search is in stub mode — results are synthetic.",
        )

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=stub_result)

            resp = client.post(
                "/api/client-research/brief",
                json={"name": "Acme", "location": "Austin"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stub_mode"] is True
        assert data["warning"] is not None


# ── /clients/{id}/apply endpoint ───────────────────────────────────────────


class TestResearchApplyEndpoint:
    def test_persists_discovered_fields_to_db(
        self, client, auth_headers, client_with_location, user_with_credits, db_session
    ):
        """Core correctness test: apply endpoint writes discovered data to the Client row."""
        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                f"/api/client-research/clients/{client_with_location.id}/apply",
                headers=auth_headers,
            )

        assert resp.status_code == 200

        # Verify fields are actually persisted — reload from DB
        db_session.expire(client_with_location)
        db_session.refresh(client_with_location)

        assert client_with_location.business_description == "Full-service digital marketing agency."
        assert client_with_location.industry == "Marketing"
        assert client_with_location.ideal_customer == "Small business owners"
        assert "Rival Co" in (client_with_location.competitors or [])
        assert "marketing" in (client_with_location.keywords or [])

    def test_response_matches_updated_client(
        self, client, auth_headers, client_with_location, user_with_credits, db_session
    ):
        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                f"/api/client-research/clients/{client_with_location.id}/apply",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        # ClientResponse serializes name as companyName
        assert data["companyName"] == "Acme Agency"
        assert data["businessDescription"] == "Full-service digital marketing agency."
        assert data["industry"] == "Marketing"

    def test_deducts_200_credits(
        self, client, auth_headers, client_with_location, user_with_credits, db_session
    ):
        initial_balance = user_with_credits.credit_balance

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=_make_fake_result())

            resp = client.post(
                f"/api/client-research/clients/{client_with_location.id}/apply",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        db_session.refresh(user_with_credits)
        assert user_with_credits.credit_balance == initial_balance - 200

    def test_400_when_client_has_no_location(
        self, client, auth_headers, client_no_location, user_with_credits
    ):
        resp = client.post(
            f"/api/client-research/clients/{client_no_location.id}/apply",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "location is required" in resp.json()["detail"].lower()

    def test_403_when_other_user_owns_client(
        self, client, client_with_location, db_session, enforce_ownership
    ):
        other_user = User(
            id="user-other-001",
            email="other@example.com",
            hashed_password=get_password_hash("testpass123"),  # pragma: allowlist secret
            full_name="Other",
            is_active=True,
            is_superuser=False,
            credit_balance=500,
        )
        db_session.add(other_user)
        db_session.commit()

        other_token = create_access_token(data={"sub": other_user.id})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = client.post(
            f"/api/client-research/clients/{client_with_location.id}/apply",
            headers=other_headers,
        )
        assert resp.status_code == 403

    def test_refunds_credits_on_agent_failure(
        self, client, auth_headers, client_with_location, user_with_credits, db_session
    ):
        initial_balance = user_with_credits.credit_balance

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(side_effect=RuntimeError("Agent crashed"))

            resp = client.post(
                f"/api/client-research/clients/{client_with_location.id}/apply",
                headers=auth_headers,
            )

        assert resp.status_code == 500
        db_session.refresh(user_with_credits)
        # Credits refunded — balance should be unchanged
        assert user_with_credits.credit_balance == initial_balance

    def test_does_not_overwrite_existing_fields_when_research_finds_nothing(
        self, client, auth_headers, client_with_location, user_with_credits, db_session
    ):
        """
        Agent fallback strings ("No description provided", "Not specified") must NOT
        overwrite real existing data. This verifies the _meaningful() guard in the router.
        """
        # Pre-populate client with real data
        client_with_location.business_description = "Existing description"
        client_with_location.industry = "Existing industry"
        db_session.commit()

        from src.agents.client_research_agent import ClientResearchResult
        from src.models.client_brief import ClientBrief, DataUsagePreference

        # Simulate what the agent returns when Claude couldn't find these fields:
        # _convert_to_client_brief fills in "No description provided" / "Not specified".
        not_found_result = ClientResearchResult(
            brief=ClientBrief(
                company_name="Acme Agency",
                business_description="No description provided",  # agent fallback
                ideal_customer="Small business owners",
                main_problem_solved="Not specified",  # agent fallback
                industry=None,  # optional field — stays None
                location="Austin, TX",
                data_usage=DataUsagePreference.MODERATE,
            ),
            confidence={},
            sources=[],
            duration_seconds=2.0,
        )

        with patch("backend.routers.client_research.ClientResearchAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=not_found_result)

            resp = client.post(
                f"/api/client-research/clients/{client_with_location.id}/apply",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        db_session.expire(client_with_location)
        db_session.refresh(client_with_location)
        # Existing real data must NOT be overwritten with placeholder fallbacks
        assert client_with_location.business_description == "Existing description"
        assert client_with_location.industry == "Existing industry"
