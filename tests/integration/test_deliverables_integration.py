"""
Integration tests for the deliverables router.

Coverage
--------
List endpoint (GET /api/deliverables/)
    - Ownership isolation: test_user sees only their own deliverables
    - Filter by client_id: returns only matching records
    - Filter by project_id: returns only matching records
    - Filter by status: returns only matching records
    - Unauthenticated request: 401

Download endpoint (GET /api/deliverables/{id}/download)
    - Non-existent id: 404
    - IDOR (TR-021): downloading another user's deliverable: 403
    - Missing file triggers regeneration attempt: response is NOT 200 application/json

From-research endpoint (POST /api/deliverables/from-research)
    - Unauthenticated request: 401
    - Wrong-user client_id (TR-021): 403
    - Happy path with mocked generate_export_file: 200, deliverable_id in body
"""

import uuid
import pytest
from pathlib import Path

from backend.models import Deliverable, User, Client, Project
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client, create_test_project


# ---------------------------------------------------------------------------
# Helper: build a minimal Deliverable row bound to an existing project/client
# ---------------------------------------------------------------------------


def _make_deliverable(
    db_session,
    project_id: str,
    client_id: str,
    *,
    status: str = "ready",
    path: str | None = None,
    format: str = "md",
) -> Deliverable:
    """
    Insert a Deliverable into the test database and return the refreshed instance.

    The path defaults to a syntactically valid but non-existent file location so
    that download tests can exercise the missing-file code path without touching
    the real filesystem.
    """
    if path is None:
        path = f"TestClient/report_{uuid.uuid4().hex[:8]}.{format}"

    deliverable = Deliverable(
        id=f"del-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        client_id=client_id,
        path=path,
        format=format,
        status=status,
        file_size_bytes=1024,
    )
    db_session.add(deliverable)
    db_session.commit()
    db_session.refresh(deliverable)
    return deliverable


# ---------------------------------------------------------------------------
# Helper: build a second user with their own client and project
# ---------------------------------------------------------------------------


def _make_other_user(db_session, suffix: str = "other") -> tuple[User, Client, Project]:
    """
    Create a secondary user, client, and project and return all three.

    Returns (other_user, other_client, other_project).
    """
    other_user = User(
        id=f"user-{suffix}-{uuid.uuid4().hex[:8]}",
        email=f"{suffix}@test.com",
        hashed_password=get_password_hash("otherpass123"),  # pragma: allowlist secret
        full_name="Other User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(other_user)
    db_session.flush()

    client_data = create_test_client(name=f"{suffix} Client", user_id=other_user.id)
    other_client = Client(**client_data)
    db_session.add(other_client)
    db_session.flush()

    project_data = create_test_project(
        name=f"{suffix} Project",
        client_id=other_client.id,
        user_id=other_user.id,
    )
    other_project = Project(**project_data)
    db_session.add(other_project)
    db_session.commit()
    db_session.refresh(other_user)
    db_session.refresh(other_client)
    db_session.refresh(other_project)
    return other_user, other_client, other_project


# ===========================================================================
# List filtering tests
# ===========================================================================


def test_list_returns_only_own_deliverables(
    client, db_session, test_user, test_user_headers, test_project, test_client, enforce_ownership
):
    """
    GET /api/deliverables/ — ownership isolation (TR-021).

    A deliverable owned by another user must not appear in test_user's list.
    """
    # Deliverable belonging to test_user
    own_deliverable = _make_deliverable(db_session, test_project.id, test_client.id)

    # Deliverable belonging to a different user
    _, other_client, other_project = _make_other_user(db_session, suffix="isolated")
    other_deliverable = _make_deliverable(db_session, other_project.id, other_client.id)

    response = client.get("/api/deliverables/", headers=test_user_headers)

    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)

    returned_ids = {item["id"] for item in items}
    assert own_deliverable.id in returned_ids, "Own deliverable must appear in list"
    assert (
        other_deliverable.id not in returned_ids
    ), "Another user's deliverable must not appear in list (TR-021 IDOR)"


def test_list_filter_by_client_id(
    client, db_session, test_user, test_user_headers, test_project, test_client
):
    """
    GET /api/deliverables/?client_id=... — only matching client's deliverables returned.

    Two deliverables for two different clients are created; the filter must
    return exclusively the one whose client_id matches the query parameter.
    """
    # Primary deliverable for test_client
    target_deliverable = _make_deliverable(db_session, test_project.id, test_client.id)

    # A second client/project under the same user so both pass ownership check
    second_client_data = create_test_client(name="Second Client", user_id=test_user.id)
    second_client = Client(**second_client_data)
    db_session.add(second_client)
    db_session.flush()

    second_project_data = create_test_project(
        name="Second Project", client_id=second_client.id, user_id=test_user.id
    )
    second_project = Project(**second_project_data)
    db_session.add(second_project)
    db_session.commit()
    db_session.refresh(second_client)
    db_session.refresh(second_project)

    other_deliverable = _make_deliverable(db_session, second_project.id, second_client.id)

    response = client.get(
        f"/api/deliverables/?client_id={test_client.id}", headers=test_user_headers
    )

    assert response.status_code == 200
    items = response.json()
    returned_ids = {item["id"] for item in items}

    assert (
        target_deliverable.id in returned_ids
    ), "Deliverable for the requested client must be returned"
    assert (
        other_deliverable.id not in returned_ids
    ), "Deliverable for a different client must not be returned when filtering by client_id"


def test_list_filter_by_project_id(
    client, db_session, test_user, test_user_headers, test_project, test_client
):
    """
    GET /api/deliverables/?project_id=... — only matching project's deliverables returned.
    """
    target_deliverable = _make_deliverable(db_session, test_project.id, test_client.id)

    # Second project under the same user
    second_client_data = create_test_client(name="Proj Filter Client", user_id=test_user.id)
    second_client = Client(**second_client_data)
    db_session.add(second_client)
    db_session.flush()

    second_project_data = create_test_project(
        name="Proj Filter Project", client_id=second_client.id, user_id=test_user.id
    )
    second_project = Project(**second_project_data)
    db_session.add(second_project)
    db_session.commit()
    db_session.refresh(second_project)

    other_deliverable = _make_deliverable(db_session, second_project.id, second_client.id)

    response = client.get(
        f"/api/deliverables/?project_id={test_project.id}", headers=test_user_headers
    )

    assert response.status_code == 200
    items = response.json()
    returned_ids = {item["id"] for item in items}

    assert (
        target_deliverable.id in returned_ids
    ), "Deliverable for the requested project must be returned"
    assert (
        other_deliverable.id not in returned_ids
    ), "Deliverable for a different project must not be returned when filtering by project_id"


def test_list_filter_by_status(client, db_session, test_user_headers, test_project, test_client):
    """
    GET /api/deliverables/?status=delivered — only status-matching records returned.

    A ready deliverable and a delivered deliverable are both created; only the
    delivered one must appear when the status filter is applied.
    """
    ready_deliverable = _make_deliverable(
        db_session, test_project.id, test_client.id, status="ready"
    )
    delivered_deliverable = _make_deliverable(
        db_session, test_project.id, test_client.id, status="delivered"
    )

    response = client.get("/api/deliverables/?status=delivered", headers=test_user_headers)

    assert response.status_code == 200
    items = response.json()
    returned_ids = {item["id"] for item in items}

    assert (
        delivered_deliverable.id in returned_ids
    ), "Delivered deliverable must be present when filtering status=delivered"
    assert (
        ready_deliverable.id not in returned_ids
    ), "Ready deliverable must be absent when filtering status=delivered"

    # Every item in the result must carry the requested status
    for item in items:
        assert item["status"] == "delivered", (
            f"Item {item['id']} has unexpected status {item['status']!r} "
            "when status=delivered filter is active"
        )


def test_list_no_auth_returns_401(client):
    """
    GET /api/deliverables/ without Authorization header must return HTTP 401.
    """
    response = client.get("/api/deliverables/")
    assert (
        response.status_code == 401
    ), f"Expected 401 for unauthenticated list request, got {response.status_code}"


# ===========================================================================
# Download tests
# ===========================================================================


def test_download_nonexistent_deliverable_returns_404(client, test_user_headers):
    """
    GET /api/deliverables/{unknown_id}/download — 404 for unknown id.

    The authorization dependency resolves the deliverable from the database
    before the handler runs, so an unknown id is rejected with 404.
    """
    unknown_id = f"del-{uuid.uuid4().hex[:12]}"
    response = client.get(f"/api/deliverables/{unknown_id}/download", headers=test_user_headers)
    assert (
        response.status_code == 404
    ), f"Expected 404 for non-existent deliverable id, got {response.status_code}"


def test_download_other_users_deliverable_returns_403(
    client, db_session, test_user_headers, test_project, test_client, enforce_ownership
):
    """
    GET /api/deliverables/{id}/download — IDOR protection (TR-021).

    A deliverable owned by another user must not be downloadable by test_user,
    even when the deliverable id is known.
    """
    _, other_client, other_project = _make_other_user(db_session, suffix="download-idor")
    other_deliverable = _make_deliverable(db_session, other_project.id, other_client.id)

    response = client.get(
        f"/api/deliverables/{other_deliverable.id}/download",
        headers=test_user_headers,
    )
    assert response.status_code == 403, (
        f"Expected 403 when test_user downloads another user's deliverable, "
        f"got {response.status_code}"
    )


def test_download_own_deliverable_missing_file_triggers_regeneration(
    client, db_session, test_user_headers, test_project, test_client
):
    """
    GET /api/deliverables/{id}/download — file-not-found path triggers regeneration.

    The deliverable row exists in the database but its path points to a file
    that does not exist on disk.  The endpoint must attempt regeneration and
    must NOT return HTTP 200 with a JSON body (which would indicate the handler
    accidentally serialised the Deliverable ORM object instead of a file).

    Acceptable outcomes are: any non-200 response, OR a 200 that carries a
    binary/text file content-type (not application/json).
    """
    # Path that is syntactically safe but guaranteed non-existent
    deliverable = _make_deliverable(
        db_session,
        test_project.id,
        test_client.id,
        path="TestClient/definitely_does_not_exist_abc123.md",
        format="md",
    )

    response = client.get(
        f"/api/deliverables/{deliverable.id}/download",
        headers=test_user_headers,
    )

    content_type = response.headers.get("content-type", "")

    # The endpoint must not silently return a 200 JSON blob instead of a file.
    if response.status_code == 200:
        assert "application/json" not in content_type, (
            "Endpoint returned 200 application/json for a missing file — "
            "the handler likely returned the ORM object rather than a FileResponse. "
            f"Content-Type: {content_type!r}"
        )
    else:
        # Any non-200 status is acceptable (404 if regeneration fails, 500 on
        # unexpected error, etc.).  The critical invariant is the one above.
        assert response.status_code in {
            400,
            404,
            500,
        }, f"Unexpected status code {response.status_code} for missing-file download"


# ===========================================================================
# From-research endpoint tests
# ===========================================================================


def test_from_research_requires_auth(client, test_client):
    """
    POST /api/deliverables/from-research — unauthenticated request returns 401.
    """
    response = client.post(
        f"/api/deliverables/from-research?client_id={test_client.id}&tools=voice_analysis&format=md"
    )
    assert (
        response.status_code == 401
    ), f"Expected 401 for unauthenticated from-research request, got {response.status_code}"


def test_from_research_wrong_client_returns_403(client, db_session, test_user_headers):
    """
    POST /api/deliverables/from-research — client_id owned by another user returns 403 (TR-021).

    test_user attempts to generate a report for a client that belongs to
    other_user.  The router verifies ownership before generating anything, so
    the request must be rejected with 403.
    """
    _, other_client, _ = _make_other_user(db_session, suffix="research-idor")

    response = client.post(
        f"/api/deliverables/from-research"
        f"?client_id={other_client.id}&tools=voice_analysis&format=md",
        headers=test_user_headers,
    )
    assert response.status_code == 403, (
        f"Expected 403 when generating report for another user's client, "
        f"got {response.status_code}"
    )


def test_from_research_valid_client_creates_deliverable(
    client, test_user_headers, test_client, monkeypatch
):
    """
    POST /api/deliverables/from-research — happy path with mocked file generation.

    generate_export_file is replaced with a coroutine that creates a real file
    under data/outputs/ so the router's relative_to(Path("data/outputs")) call
    succeeds.  The endpoint must return HTTP 200 with a deliverable_id field.
    """
    import uuid, shutil
    from pathlib import Path

    # File must live under data/outputs/ because the router computes
    # actual_path = file_path.relative_to(Path("data/outputs"))
    base = Path("data/outputs")
    test_dir = base / f"test_from_research_{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    fake_file = test_dir / "report.md"
    fake_file.write_text("# Research Report\n\nMocked content for integration test.")

    async def mock_generate(*args, **kwargs):
        """Drop-in replacement for generate_export_file."""
        return fake_file, fake_file.stat().st_size

    monkeypatch.setattr(
        "backend.routers.deliverables.generate_export_file",
        mock_generate,
    )

    try:
        response = client.post(
            f"/api/deliverables/from-research"
            f"?client_id={test_client.id}&tools=voice_analysis&format=md",
            headers=test_user_headers,
        )

        assert response.status_code == 200, (
            f"Expected 200 from from-research with mocked generator, got {response.status_code}. "
            f"Body: {response.text!r}"
        )

        data = response.json()
        assert (
            "deliverable_id" in data
        ), f"Response body must contain 'deliverable_id'. Got keys: {list(data.keys())}"
        assert (
            isinstance(data["deliverable_id"], str) and data["deliverable_id"]
        ), f"deliverable_id must be a non-empty string, got {data['deliverable_id']!r}"
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
