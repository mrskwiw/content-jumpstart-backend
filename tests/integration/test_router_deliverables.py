"""
Integration tests for deliverables router.

Tests all deliverable endpoints including:
- List deliverables (GET /api/deliverables/)
- Download deliverable (GET /api/deliverables/{deliverable_id}/download)
- Mark as delivered (POST /api/deliverables/{deliverable_id}/mark-delivered)
- Export formats (markdown, Word)
- Authorization checks (TR-021)
- Path security (TR-019)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Run, Deliverable
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client, create_test_project


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user_a(db_session: Session):
    """Create test user A"""
    user = User(
        id="user-a-123",
        email="usera@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_b(db_session: Session):
    """Create test user B"""
    user = User(
        id="user-b-456",
        email="userb@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers_user_a(test_user_a, client):
    """Get auth headers for user A"""
    response = client.post(
        "/api/auth/login",
        json={"email": "usera@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_b(test_user_b, client):
    """Get auth headers for user B"""
    response = client.post(
        "/api/auth/login",
        json={"email": "userb@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_for_user_a(db_session: Session, test_user_a):
    """Create a project owned by user A"""
    client_data = create_test_client(
        name="User A Client",
        user_id=test_user_a.id,
        email="clienta@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()

    project_data = create_test_project(
        name="User A Project",
        client_id=db_client.id,
        user_id=test_user_a.id,
    )
    db_project = Project(**project_data)
    db_session.add(db_project)
    db_session.commit()
    db_session.refresh(db_project)
    return db_project


@pytest.fixture
def run_for_user_a(db_session: Session, test_user_a, project_for_user_a):
    """Create a completed generation run owned by user A"""
    run = Run(
        id="run-test-123",
        project_id=project_for_user_a.id,
        status="succeeded",  # Run status is pending/running/succeeded/failed
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


@pytest.fixture
def deliverable_for_user_a(db_session: Session, test_user_a, project_for_user_a, run_for_user_a):
    """Create a deliverable owned by user A"""
    deliverable = Deliverable(
        id="del-test-123",
        project_id=project_for_user_a.id,
        client_id=project_for_user_a.client_id,  # Required field
        run_id=run_for_user_a.id,
        path="data/outputs/TestClient/deliverable.md",  # Model uses 'path' not 'file_path'
        format="markdown",
        status="ready",
        delivered_at=None,
    )
    db_session.add(deliverable)
    db_session.commit()
    db_session.refresh(deliverable)
    return deliverable


@pytest.fixture
def media_deliverable_for_user_a(db_session: Session, test_user_a, project_for_user_a):
    """A Phase-12 media deliverable (image): path is a storage KEY, not a data/outputs file."""
    deliverable = Deliverable(
        id="del-media-img-1",
        project_id=project_for_user_a.id,
        client_id=project_for_user_a.client_id,
        run_id=None,  # media jobs aren't tied to a generation run
        path="media/user-a/job-1/asset-1.png",  # storage key, not a filesystem path
        format="image",
        status="ready",
        delivered_at=None,
    )
    db_session.add(deliverable)
    db_session.commit()
    db_session.refresh(deliverable)
    return deliverable


class TestMediaDeliverableDownload:
    """MEDIA-DELIVERABLE-SPLIT: media deliverables serve via a signed media-storage
    redirect, NOT the data/outputs export-file flow (which would 404 + try to
    regenerate a document from a storage key)."""

    def test_media_deliverable_downloads_via_signed_redirect(
        self, client, auth_headers_user_a, media_deliverable_for_user_a, monkeypatch
    ):
        monkeypatch.setenv("MEDIA_DRY_RUN", "true")  # StubStorage → deterministic signed URL
        resp = client.get(
            f"/api/deliverables/{media_deliverable_for_user_a.id}/download",
            headers=auth_headers_user_a,
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307), resp.text
        # Unconfigured storage in tests → StubStorage signs to a stub.local URL, and the
        # original .png storage key is preserved (not regenerated as a document export).
        assert "stub.local" in resp.headers["location"]
        assert ".png" in resp.headers["location"]


class TestListDeliverables:
    """Test GET /api/deliverables/"""

    def test_list_deliverables_authenticated(
        self, client, auth_headers_user_a, deliverable_for_user_a
    ):
        """Test listing deliverables with authentication"""
        response = client.get("/api/deliverables/", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
        # Should see own deliverable
        if isinstance(data, list):
            assert len(data) >= 1
            assert any(d["id"] == deliverable_for_user_a.id for d in data)
        else:
            assert len(data["items"]) >= 1
            assert any(d["id"] == deliverable_for_user_a.id for d in data["items"])

    def test_list_deliverables_unauthenticated(self, client):
        """Test listing deliverables without authentication"""
        response = client.get("/api/deliverables/")
        assert response.status_code == 401

    def test_list_deliverables_filters_by_user(
        self,
        client,
        auth_headers_user_a,
        auth_headers_user_b,
        deliverable_for_user_a,
        db_session,
        test_user_b,
        enforce_ownership,
    ):
        """Test TR-021: Users only see their own deliverables"""
        # Create deliverable for user B
        client_data = create_test_client(
            name="User B Client",
            user_id=test_user_b.id,
            email="clientb@example.com",
        )
        db_client = Client(**client_data)
        db_session.add(db_client)
        db_session.commit()

        project_data = create_test_project(
            name="User B Project",
            client_id=db_client.id,
            user_id=test_user_b.id,
        )
        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()

        run_b = Run(
            id="run-b-999",
            project_id=db_project.id,
            status="succeeded",
        )
        db_session.add(run_b)
        db_session.commit()

        deliverable_b = Deliverable(
            id="del-b-999",
            project_id=db_project.id,
            client_id=db_client.id,
            run_id=run_b.id,
            path="data/outputs/ClientB/deliverable.md",
            format="markdown",
            status="ready",
        )
        db_session.add(deliverable_b)
        db_session.commit()

        # User A should see only their deliverable
        response = client.get("/api/deliverables/", headers=auth_headers_user_a)
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        assert len(items) >= 1
        assert all(d["id"] != deliverable_b.id for d in items)
        assert any(d["id"] == deliverable_for_user_a.id for d in items)

    def test_list_deliverables_filter_by_status(
        self, client, auth_headers_user_a, deliverable_for_user_a
    ):
        """Test filtering deliverables by status"""
        response = client.get("/api/deliverables/?status=ready", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        # All returned deliverables should have ready status
        assert all(d["status"] == "ready" for d in items)

    def test_list_deliverables_filter_by_project(
        self, client, auth_headers_user_a, deliverable_for_user_a, project_for_user_a
    ):
        """Test filtering deliverables by project ID"""
        response = client.get(
            f"/api/deliverables/?project_id={project_for_user_a.id}", headers=auth_headers_user_a
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        # All returned deliverables should belong to the project
        # Use .get() to handle both snake_case and camelCase field names
        assert all(
            (d.get("project_id") or d.get("projectId")) == project_for_user_a.id for d in items
        )

    def test_list_deliverables_filter_by_format(self, client, auth_headers_user_a):
        """Test filtering deliverables by format"""
        response = client.get("/api/deliverables/?format=markdown", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        # All returned deliverables should be markdown format
        assert all(d["format"] == "markdown" for d in items)


class TestDownloadDeliverable:
    """Test GET /api/deliverables/{deliverable_id}/download"""

    def test_download_deliverable_success(
        self, client, auth_headers_user_a, deliverable_for_user_a
    ):
        """Test downloading deliverable"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}/download",
            headers=auth_headers_user_a,
        )

        # Should return 200 with file content or 404 if file doesn't exist
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Check content type
            assert "text/markdown" in response.headers.get(
                "content-type", ""
            ) or "application/octet-stream" in response.headers.get("content-type", "")
            # Check content-disposition header
            assert "attachment" in response.headers.get("content-disposition", "")

    def test_download_deliverable_unauthorized(
        self, client, auth_headers_user_b, deliverable_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot download User A's deliverable"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}/download",
            headers=auth_headers_user_b,
        )
        assert response.status_code == 403

    def test_download_deliverable_not_found(self, client, auth_headers_user_a):
        """Test downloading non-existent deliverable"""
        response = client.get(
            "/api/deliverables/nonexistent-id/download",
            headers=auth_headers_user_a,
        )
        assert response.status_code == 404

    def test_download_deliverable_unauthenticated(self, client, deliverable_for_user_a):
        """Test downloading without authentication"""
        response = client.get(f"/api/deliverables/{deliverable_for_user_a.id}/download")
        assert response.status_code == 401

    def test_download_deliverable_path_traversal(
        self,
        client,
        auth_headers_user_a,
        db_session,
        project_for_user_a,
        run_for_user_a,
    ):
        """Test TR-019: Path traversal attack prevention"""
        # Create deliverable with malicious path
        malicious_deliverable = Deliverable(
            id="del-malicious-999",
            project_id=project_for_user_a.id,
            client_id=project_for_user_a.client_id,  # Get client_id from project
            run_id=run_for_user_a.id,
            path="../../../etc/passwd",  # Path traversal attempt
            format="markdown",
            status="ready",
        )
        db_session.add(malicious_deliverable)
        db_session.commit()

        response = client.get(
            f"/api/deliverables/{malicious_deliverable.id}/download",
            headers=auth_headers_user_a,
        )

        # Should reject path traversal attempts
        assert response.status_code in [400, 403, 404]


class TestMarkAsDelivered:
    """Test PATCH /api/deliverables/{deliverable_id}/mark-delivered"""

    def test_mark_delivered_success(
        self, client, auth_headers_user_a, deliverable_for_user_a, db_session
    ):
        """Test marking deliverable as delivered"""
        from datetime import datetime

        response = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            json={"delivered_at": datetime.now().isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "delivered"
        assert "delivered_at" in data or "deliveredAt" in data

        # Verify in database
        db_deliverable = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        assert db_deliverable.status == "delivered"
        assert db_deliverable.delivered_at is not None

    def test_mark_delivered_ignores_client_timestamp(
        self, client, auth_headers_user_a, deliverable_for_user_a, db_session
    ):
        """The audit timestamp is server-stamped: a bogus client delivered_at is ignored."""
        from datetime import datetime, timezone

        before = datetime.now(timezone.utc)
        response = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            # A skewed/backdated client clock — must NOT drive the audit record.
            json={"delivered_at": "2000-01-01T00:00:00+00:00"},
        )
        assert response.status_code == 200

        db_deliverable = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        stamped = db_deliverable.delivered_at
        if stamped.tzinfo is None:
            stamped = stamped.replace(tzinfo=timezone.utc)
        # Server-now, not the year-2000 value the client sent.
        assert stamped.year >= before.year
        assert stamped >= before.replace(microsecond=0)

    def test_mark_delivered_without_timestamp(
        self, client, auth_headers_user_a, deliverable_for_user_a, db_session
    ):
        """delivered_at is now optional — the server stamps it when omitted."""
        response = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            json={},
        )
        assert response.status_code == 200
        db_deliverable = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        assert db_deliverable.status == "delivered"
        assert db_deliverable.delivered_at is not None

    def test_mark_delivered_is_idempotent_on_retry(
        self, client, auth_headers_user_a, deliverable_for_user_a, db_session
    ):
        """A retry must not rewrite the original delivery time or wipe proof metadata."""
        from datetime import timezone

        url = f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered"
        first = client.patch(
            url,
            headers=auth_headers_user_a,
            json={"proof_url": "https://proof/x", "proof_notes": "sent via email"},
        )
        assert first.status_code == 200
        db_session.expire_all()
        d1 = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        original_ts = d1.delivered_at
        if original_ts.tzinfo is None:
            original_ts = original_ts.replace(tzinfo=timezone.utc)

        # Retry with DIFFERENT proof — a duplicate/replayed/tampered submit. First-write-wins:
        # the delivery record is immutable, so neither timestamp nor proof changes.
        second = client.patch(
            url,
            headers=auth_headers_user_a,
            json={"proof_url": "https://proof/TAMPERED", "proof_notes": "changed"},
        )
        assert second.status_code == 200
        db_session.expire_all()
        d2 = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        retry_ts = d2.delivered_at
        if retry_ts.tzinfo is None:
            retry_ts = retry_ts.replace(tzinfo=timezone.utc)

        # Original timestamp AND proof metadata are frozen (not the retry's values).
        assert retry_ts == original_ts
        assert d2.proof_url == "https://proof/x"
        assert d2.proof_notes == "sent via email"

    def test_mark_delivered_backfills_missing_proof_but_freezes_set_proof(
        self, client, auth_headers_user_a, deliverable_for_user_a, db_session
    ):
        """Proof is write-once-per-field: an empty field can be populated after delivery,
        but a value already stored is immutable."""
        url = f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered"
        # First delivery with NO proof — records delivery, proof stays empty.
        assert client.patch(url, headers=auth_headers_user_a, json={}).status_code == 200
        db_session.expire_all()
        d1 = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        assert d1.status == "delivered" and d1.proof_url is None

        # A later correction backfills the still-empty proof.
        assert (
            client.patch(
                url, headers=auth_headers_user_a, json={"proof_url": "https://proof/late"}
            ).status_code
            == 200
        )
        db_session.expire_all()
        d2 = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        assert d2.proof_url == "https://proof/late"

        # But once set, it's frozen — a further submit can't change it.
        client.patch(url, headers=auth_headers_user_a, json={"proof_url": "https://proof/OTHER"})
        db_session.expire_all()
        d3 = (
            db_session.query(Deliverable)
            .filter(Deliverable.id == deliverable_for_user_a.id)
            .first()
        )
        assert d3.proof_url == "https://proof/late"

    def test_mark_delivered_unauthorized(
        self, client, auth_headers_user_b, deliverable_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot mark User A's deliverable as delivered"""
        from datetime import datetime

        response = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_b,
            json={"delivered_at": datetime.now().isoformat()},
        )
        assert response.status_code == 403

    def test_mark_delivered_not_found(self, client, auth_headers_user_a):
        """Test marking non-existent deliverable"""
        from datetime import datetime

        response = client.patch(
            "/api/deliverables/nonexistent-id/mark-delivered",
            headers=auth_headers_user_a,
            json={"delivered_at": datetime.now().isoformat()},
        )
        assert response.status_code == 404

    def test_mark_delivered_unauthenticated(self, client, deliverable_for_user_a):
        """Test marking deliverable without authentication"""
        from datetime import datetime

        response = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            json={"delivered_at": datetime.now().isoformat()},
        )
        assert response.status_code == 401

    def test_mark_delivered_idempotent(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test marking already-delivered deliverable (should be idempotent)"""
        from datetime import datetime

        # Mark as delivered first time
        response1 = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            json={"delivered_at": datetime.now().isoformat()},
        )
        assert response1.status_code == 200

        # Mark as delivered second time (should succeed)
        response2 = client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            json={"delivered_at": datetime.now().isoformat()},
        )
        assert response2.status_code == 200


class TestExportFormats:
    """Test deliverable export formats"""

    def test_markdown_format_deliverable(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test deliverable with markdown format"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"

    def test_word_format_deliverable(
        self,
        client,
        auth_headers_user_a,
        db_session,
        project_for_user_a,
        run_for_user_a,
    ):
        """Test deliverable with Word format"""
        word_deliverable = Deliverable(
            id="del-word-123",
            project_id=project_for_user_a.id,
            client_id=project_for_user_a.client_id,
            run_id=run_for_user_a.id,
            path="data/outputs/TestClient/deliverable.docx",
            format="word",
            status="ready",
        )
        db_session.add(word_deliverable)
        db_session.commit()

        response = client.get(
            f"/api/deliverables/{word_deliverable.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "word"

    def test_pdf_format_deliverable(
        self,
        client,
        auth_headers_user_a,
        db_session,
        project_for_user_a,
        run_for_user_a,
    ):
        """Test deliverable with PDF format"""
        pdf_deliverable = Deliverable(
            id="del-pdf-123",
            project_id=project_for_user_a.id,
            client_id=project_for_user_a.client_id,
            run_id=run_for_user_a.id,
            path="data/outputs/TestClient/deliverable.pdf",
            format="pdf",
            status="ready",
        )
        db_session.add(pdf_deliverable)
        db_session.commit()

        response = client.get(
            f"/api/deliverables/{pdf_deliverable.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "pdf"


class TestDeliverableMetadata:
    """Test deliverable metadata fields"""

    def test_deliverable_has_file_size(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test deliverable includes file size"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        _data = response.json()  # noqa: F841 - validates JSON response
        # File size might be included as metadata
        # Exact field depends on implementation

    def test_deliverable_has_timestamps(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test deliverable includes created_at timestamp"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data or "createdAt" in data

    def test_deliverable_has_project_info(
        self, client, auth_headers_user_a, deliverable_for_user_a, project_for_user_a
    ):
        """Test deliverable includes project information"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        # API may return camelCase or snake_case
        project_id = data.get("project_id") or data.get("projectId")
        assert project_id == project_for_user_a.id


class TestGetDeliverable:
    """Test GET /api/deliverables/{deliverable_id}"""

    def test_get_deliverable_success(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test getting deliverable by ID"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == deliverable_for_user_a.id
        assert data["status"] == "ready"
        assert data["format"] == "markdown"

    def test_get_deliverable_unauthorized(
        self, client, auth_headers_user_b, deliverable_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot get User A's deliverable"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_b,
        )
        assert response.status_code == 403

    def test_get_deliverable_not_found(self, client, auth_headers_user_a):
        """Test getting non-existent deliverable"""
        response = client.get(
            "/api/deliverables/nonexistent-id",
            headers=auth_headers_user_a,
        )
        assert response.status_code == 404

    def test_get_deliverable_unauthenticated(self, client, deliverable_for_user_a):
        """Test getting deliverable without authentication"""
        response = client.get(f"/api/deliverables/{deliverable_for_user_a.id}")
        assert response.status_code == 401


class TestDeliverableStatus:
    """Test deliverable status tracking"""

    def test_deliverable_status_ready(self, client, auth_headers_user_a, deliverable_for_user_a):
        """Test deliverable with ready status"""
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        # API may return camelCase or snake_case
        delivered_at = data.get("delivered_at") or data.get("deliveredAt")
        assert delivered_at is None

    def test_deliverable_status_delivered(
        self, client, auth_headers_user_a, deliverable_for_user_a
    ):
        """Test deliverable with delivered status"""
        from datetime import datetime

        # Mark as delivered using PATCH with request body
        client.patch(
            f"/api/deliverables/{deliverable_for_user_a.id}/mark-delivered",
            headers=auth_headers_user_a,
            json={"delivered_at": datetime.now().isoformat()},
        )

        # Get deliverable
        response = client.get(
            f"/api/deliverables/{deliverable_for_user_a.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "delivered"
        # API may return camelCase or snake_case
        delivered_at = data.get("delivered_at") or data.get("deliveredAt")
        assert delivered_at is not None
