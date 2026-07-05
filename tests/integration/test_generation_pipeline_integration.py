"""
Integration tests for POST /api/generator/generate-all.

Coverage scope
--------------
Validation (HTTP 422)
  - Empty template_quantities dict
  - Zero or negative template_quantities values
  - num_posts <= 0

IDOR / Authorization
  - Client owned by a different user → 403
  - Project owned by a different user → 403
  - No auth header → 401

Happy path (HTTP 200, background task queued)
  - Valid template_quantities creates a Run record in "running" or "pending" status
  - target_platform omitted — generation still accepted

Credit deduction
  - User with zero credit balance → 402 Payment Required

All tests rely on the integration conftest.py fixtures:
  client            FastAPI TestClient(app) with DB overridden to in-memory SQLite
  db_session        Function-scoped SQLAlchemy session (in-memory SQLite)
  test_user         User model pre-saved to DB (credit_balance=1000 by default)
  test_user_headers {"Authorization": "Bearer <token>"} for test_user
  test_project      Project model owned by test_user
  test_client       Client model owned by test_user

The autouse mock_background_tasks fixture (conftest.py) patches
fastapi.BackgroundTasks.add_task so no real Anthropic calls are made.
"""

import pytest
from fastapi.testclient import TestClient

from backend.models import User, Client, Project, Run
from backend.utils.auth import create_access_token, get_password_hash

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GENERATE_URL = "/api/generator/generate-all"


def _valid_payload(project_id: str, client_id: str, **overrides) -> dict:
    """Return a minimal valid GenerateAllInput payload."""
    payload = {
        "project_id": project_id,
        "client_id": client_id,
        "template_quantities": {"1": 2},
        "target_platform": "linkedin",
    }
    payload.update(overrides)
    return payload


def _make_second_user(db_session) -> User:
    """Create and persist a second user that is *not* test_user."""
    user = User(
        id="user-other-abc99",
        email="other@example.com",
        hashed_password=get_password_hash("otherpass123"),
        full_name="Other User",
        is_active=True,
        is_superuser=False,
        credit_balance=1000,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _headers_for(user: User) -> dict:
    """Return Authorization headers for *user*."""
    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Validation tests — all expect HTTP 422
# ---------------------------------------------------------------------------


class TestValidation:
    """Pydantic-level validation enforced by GenerateAllInput."""

    def test_template_quantities_empty_dict_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
    ):
        """Empty template_quantities must be rejected (validator: must not be empty)."""
        payload = _valid_payload(test_project.id, test_client.id, template_quantities={})
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "bad_qty",
        [
            {"1": 0},  # zero — boundary
            {"1": -1},  # negative — one below boundary
        ],
        ids=["zero_value", "negative_value"],
    )
    def test_template_quantities_non_positive_value_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
        bad_qty: dict,
    ):
        """template_quantities values < 1 must be rejected."""
        payload = _valid_payload(test_project.id, test_client.id, template_quantities=bad_qty)
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422

    # Kept as explicit named tests to satisfy the specified test-function inventory.

    def test_template_quantities_zero_value_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
    ):
        """template_quantities: {'1': 0} must return 422."""
        payload = _valid_payload(test_project.id, test_client.id, template_quantities={"1": 0})
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422

    def test_template_quantities_negative_value_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
    ):
        """template_quantities: {'1': -3} must return 422."""
        payload = _valid_payload(test_project.id, test_client.id, template_quantities={"1": -3})
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422

    def test_num_posts_zero_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
    ):
        """num_posts=0 with template_quantities=null must return 422."""
        payload = {
            "project_id": test_project.id,
            "client_id": test_client.id,
            "num_posts": 0,
            "template_quantities": None,
        }
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422

    def test_num_posts_negative_rejected(
        self,
        client: TestClient,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
    ):
        """num_posts=-5 must return 422."""
        payload = {
            "project_id": test_project.id,
            "client_id": test_client.id,
            "num_posts": -5,
            "template_quantities": None,
        }
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# IDOR / Authorization tests
# ---------------------------------------------------------------------------


class TestAuthorization:
    """Ensure TR-021 IDOR checks reject cross-user access and unauthenticated requests."""

    def test_generate_with_unowned_client_rejected(
        self,
        client: TestClient,
        db_session,
        test_project: Project,
        test_user_headers: dict,
    ):
        """
        test_user calls generate-all with a client_id owned by a different user.
        Expect 403 — the authorization check on client ownership must fire.
        """
        other_user = _make_second_user(db_session)

        # Create a client belonging exclusively to other_user.
        other_client = Client(
            id="client-other-abc01",
            user_id=other_user.id,
            name="Other Client",
            business_description=(
                "Competitor business providing analytics dashboards to enterprise clients."
            ),
            ideal_customer="Enterprise data teams",
            main_problem_solved="Fragmented data insights",
        )
        db_session.add(other_client)
        db_session.commit()

        payload = _valid_payload(test_project.id, other_client.id)
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 403

    def test_generate_with_unowned_project_rejected(
        self,
        client: TestClient,
        db_session,
        test_client: Client,
        test_user_headers: dict,
    ):
        """
        test_user calls generate-all with a project_id owned by a different user.
        Expect 403 — the authorization check on project ownership must fire.
        """
        other_user = _make_second_user(db_session)

        # Create a project belonging exclusively to other_user.
        other_project = Project(
            id="proj-other-abc01",
            user_id=other_user.id,
            client_id=test_client.id,
            name="Other Project",
            num_posts=5,
            status="draft",
        )
        db_session.add(other_project)
        db_session.commit()

        payload = _valid_payload(other_project.id, test_client.id)
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)
        assert response.status_code == 403

    def test_generate_unauthenticated_rejected(
        self, client: TestClient, test_project: Project, test_client: Client
    ):
        """No Authorization header must return 401."""
        payload = _valid_payload(test_project.id, test_client.id)
        response = client.post(GENERATE_URL, json=payload)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Valid requests that should create a Run record and queue the background task."""

    def test_valid_template_quantities_creates_run(
        self,
        client: TestClient,
        db_session,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
        test_user: User,
    ):
        """
        Valid template_quantities should return 200 with a Run record.

        The response body must contain:
          - "id": the Run record's primary key
          - "status": "running" or "pending" (endpoint updates to "running" before returning)

        The Run record must also exist in the database.
        """
        # Give test_user ample credits so the credit-deduction step succeeds.
        test_user.credit_balance = 10_000
        db_session.add(test_user)
        db_session.commit()

        payload = _valid_payload(test_project.id, test_client.id, template_quantities={"1": 2})
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)

        assert response.status_code == 200
        data = response.json()

        # Must return a Run id.
        assert "id" in data, f"Response missing 'id' field: {data}"

        # Status must be one of the accepted active states.
        assert data["status"] in ("running", "pending"), f"Unexpected run status '{data['status']}'"

        # Verify the Run record was persisted.
        run_in_db = db_session.query(Run).filter(Run.id == data["id"]).first()
        assert run_in_db is not None, "Run record not found in database after create"

    def test_target_platform_default_when_omitted(
        self,
        client: TestClient,
        db_session,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
        test_user: User,
    ):
        """
        Omitting target_platform entirely must still succeed (200).

        The router falls back to project.target_platform or 'blog' when
        the field is absent from the request.
        """
        test_user.credit_balance = 10_000
        db_session.add(test_user)
        db_session.commit()

        # Explicitly exclude target_platform from the payload.
        payload = {
            "project_id": test_project.id,
            "client_id": test_client.id,
            "template_quantities": {"1": 1},
        }
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data, f"Response missing 'id' field: {data}"


# ---------------------------------------------------------------------------
# Credit deduction tests
# ---------------------------------------------------------------------------


class TestCreditDeduction:
    """Ensure the credit gate blocks generation when the user is out of credits."""

    def test_insufficient_credits_returns_402(
        self,
        client: TestClient,
        db_session,
        test_project: Project,
        test_client: Client,
        test_user_headers: dict,
        test_user: User,
    ):
        """
        A user with credit_balance=0 must receive HTTP 402 Payment Required.

        The credit deduction in the router (credit_service.deduct_credits) raises
        InsufficientCreditsError when balance < required_amount, which the router
        catches and re-raises as HTTP 402.
        """
        # Drive the balance to zero.
        test_user.credit_balance = 0
        db_session.add(test_user)
        db_session.commit()

        # Expire the cached instance so the router's session sees the updated value.
        db_session.expire(test_user)

        payload = _valid_payload(test_project.id, test_client.id, template_quantities={"1": 2})
        response = client.post(GENERATE_URL, json=payload, headers=test_user_headers)

        assert (
            response.status_code == 402
        ), f"Expected 402 for zero-credit user, got {response.status_code}: {response.text}"
