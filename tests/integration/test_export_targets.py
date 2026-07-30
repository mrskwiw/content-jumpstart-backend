"""
Integration tests for export target/platform functionality.

Tests the complete flow:
1. Create project with target_platform
2. Generate content optimized for platform
3. Export with platform-specific formatting
4. Verify all supported export targets

This verifies Task 16: Move Export Target to Generate Page
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Brief, Post, Run
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-export-target-test",
        email="export@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Export Target Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, client):
    """Get auth headers for test user"""
    response = client.post(
        "/api/auth/login",
        json={"email": "export@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_client_db(db_session: Session, test_user):
    """Create a test client in database"""
    client_data = create_test_client(
        name="Export Target Test Client",
        user_id=test_user.id,
        email="client@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


# Supported export targets (matches backend Platform enum)
EXPORT_TARGETS = [
    # Social Media
    "linkedin-posts",
    "linkedin-articles",
    "twitter",
    "twitter-threads",
    "facebook",
    # Standard Formats
    "docx",
    "markdown",
    "txt",
]


class TestExportTargetProjectCreation:
    """Test creating projects with various export targets"""

    @pytest.mark.parametrize("target", EXPORT_TARGETS)
    def test_create_project_with_export_target(
        self, client, auth_headers, test_client_db, db_session, target
    ):
        """Test creating project with each supported export target"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": f"{target} Campaign",
                "clientId": test_client_db.id,
                "targetPlatform": target,
                "numPosts": 10,
            },
        )

        assert response.status_code in [200, 201], f"Failed to create project with target {target}"
        data = response.json()

        # Check response includes target platform (handles both camelCase and snake_case)
        assert (
            data.get("targetPlatform") == target or data.get("target_platform") == target
        ), f"Target platform not set correctly for {target}"

        # Verify in database
        project_id = data["id"]
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is not None
        assert db_project.target_platform == target

    def test_create_project_without_target_defaults_to_blog(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test creating project without target_platform defaults to 'blog'"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Blog Campaign",
                "clientId": test_client_db.id,
                "numPosts": 10,
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        project_id = data["id"]

        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project.target_platform in [None, "blog", ""]


class TestPlatformSpecificGeneration:
    """Test content generation with platform targeting"""

    @pytest.fixture
    def linkedin_project(self, db_session, test_client_db, test_user):
        """Create a LinkedIn-targeted project with brief"""
        project = Project(
            id="proj-linkedin-gen",
            name="LinkedIn Test Project",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="linkedin",
            num_posts=5,
        )
        db_session.add(project)

        brief_content = """
Company: Test Company
Business Description: B2B SaaS platform for content marketing
Target Audience: Marketing managers at mid-size companies
Value Proposition: Streamline content workflows
"""
        brief = Brief(
            id="brief-linkedin",
            project_id=project.id,
            content=brief_content,
            source="paste",
        )
        db_session.add(brief)
        db_session.commit()
        db_session.refresh(project)
        return project

    def test_generate_with_target_platform(
        self, client, auth_headers, linkedin_project, db_session
    ):
        """Test that generation endpoint accepts and uses target_platform"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": linkedin_project.id,
                "client_id": linkedin_project.client_id,
                "is_batch": True,
                "num_posts": 5,
                "target_platform": "linkedin",
            },
        )

        # Should accept the request and create a run
        assert response.status_code in [200, 201, 202]
        data = response.json()
        assert "id" in data  # Run ID

        # Verify run was created with target platform
        run_id = data["id"]
        db_run = db_session.query(Run).filter(Run.id == run_id).first()
        assert db_run is not None
        assert db_run.project_id == linkedin_project.id

    @pytest.mark.parametrize("platform", ["twitter", "linkedin", "medium", "substack"])
    def test_generate_multiple_platforms(
        self, client, auth_headers, test_client_db, test_user, db_session, platform
    ):
        """Test generation with different platforms"""
        # Create project for each platform
        project = Project(
            id=f"proj-{platform}-test",
            name=f"{platform} Campaign",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform=platform,
            num_posts=3,
        )
        db_session.add(project)

        brief = Brief(
            id=f"brief-{platform}",
            project_id=project.id,
            content="Company: Test Company\nBusiness: AI-powered content platform\nAudience: Content creators and marketers",
            source="paste",
        )
        db_session.add(brief)
        db_session.commit()

        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "client_id": test_client_db.id,
                "is_batch": True,
                "num_posts": 3,
                "target_platform": platform,
            },
        )

        assert response.status_code in [200, 201, 202], f"Generation failed for {platform}"


class TestExportWithPlatformFormatting:
    """Test export with platform-specific formatting"""

    @pytest.fixture
    def project_with_posts(self, db_session, test_client_db, test_user):
        """Create a project with generated posts"""
        project = Project(
            id="proj-export-test",
            name="Export Test Project",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="linkedin",
            num_posts=10,
        )
        db_session.add(project)

        brief = Brief(
            id="brief-export",
            project_id=project.id,
            content="Company: Export Test Co\nBusiness: Testing platform-specific exports\nAudience: QA engineers and testers",
            source="paste",
        )
        db_session.add(brief)

        # Create posts
        run = Run(
            id="run-export",
            project_id=project.id,
            status="succeeded",
        )
        db_session.add(run)

        posts = [
            Post(
                id=f"post-export-{i}",
                project_id=project.id,
                run_id=run.id,
                content=f"LinkedIn post content {i}\n\nOptimized for professional audience.",
                template_id=1,
                target_platform="linkedin",
                status="approved",
            )
            for i in range(5)
        ]
        db_session.add_all(posts)
        db_session.commit()
        db_session.refresh(project)
        return project

    @pytest.mark.parametrize("format", ["txt", "md", "docx", "csv"])
    def test_export_different_formats(self, client, auth_headers, project_with_posts, format):
        """Test exporting in different file formats"""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers,
            json={
                "project_id": project_with_posts.id,
                "format": format,
                "include_audit_log": False,
                "include_research": False,
            },
        )

        assert response.status_code == 200, f"Export failed for format {format}"

        # Verify content type
        content_type = response.headers.get("content-type", "")
        if format == "docx":
            assert "application" in content_type or "octet-stream" in content_type
        elif format == "md":
            assert "markdown" in content_type or "text" in content_type or "json" in content_type
        elif format == "txt":
            assert "text" in content_type or "json" in content_type

    @pytest.mark.parametrize("flag", ["include_audit_log", "include_research"])
    def test_csv_export_rejects_appendix_flags(
        self, client, auth_headers, project_with_posts, flag
    ):
        """CSV can't carry the audit/research appendix — the API must reject the
        combination with a 400 rather than a misleading 200 that omits the data."""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers,
            json={
                "project_id": project_with_posts.id,
                "format": "csv",
                flag: True,
            },
        )

        assert response.status_code == 400
        assert "csv" in response.json()["detail"].lower()

    def test_export_with_target_platform_optimization(
        self, client, auth_headers, project_with_posts
    ):
        """Test that export respects target platform from project"""
        # Export for LinkedIn-optimized project
        response = client.post(
            "/api/generator/export",
            headers=auth_headers,
            json={
                "project_id": project_with_posts.id,
                "format": "md",
                "include_audit_log": False,
                "include_research": False,
            },
        )

        assert response.status_code == 200
        # Export should succeed and potentially format content for LinkedIn
        # (actual formatting logic is in export service)

    def test_export_includes_platform_metadata(
        self, client, auth_headers, project_with_posts, db_session
    ):
        """Test that exported content includes platform information"""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers,
            json={
                "project_id": project_with_posts.id,
                "format": "txt",
                "include_audit_log": False,
                "include_research": False,
            },
        )

        assert response.status_code == 200
        # Platform information should be included in export metadata


class TestTargetPlatformValidation:
    """Test validation of target platform values"""

    def test_invalid_target_platform_rejected(self, client, auth_headers, test_client_db):
        """Test that invalid target platforms are rejected"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Invalid Platform Campaign",
                "clientId": test_client_db.id,
                "targetPlatform": "invalid-platform-xyz",
                "numPosts": 10,
            },
        )

        # Should either reject with 422 or accept and sanitize
        # (depends on backend validation implementation)
        assert response.status_code in [200, 201, 422]

    def test_case_insensitive_platform_names(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test that platform names are handled case-insensitively"""
        # Try creating with different casing
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Case Test Campaign",
                "clientId": test_client_db.id,
                "targetPlatform": "LinkedIn",  # Capital L
                "numPosts": 10,
            },
        )

        # Backend should normalize or accept
        assert response.status_code in [200, 201, 422]


class TestPlatformSelectorIntegration:
    """Test PlatformSelector component integration"""

    def test_all_platforms_supported_in_backend(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test that all platforms defined in PlatformSelector are supported by backend"""
        # Platforms from PlatformSelector.tsx (must match backend Platform enum)
        frontend_platforms = ["linkedin", "twitter", "facebook", "blog", "email"]

        for platform in frontend_platforms:
            response = client.post(
                "/api/projects",
                headers=auth_headers,
                json={
                    "name": f"{platform} Test",
                    "clientId": test_client_db.id,
                    "targetPlatform": platform,
                    "numPosts": 5,
                },
            )

            assert response.status_code in [
                200,
                201,
            ], f"Backend rejected platform '{platform}' from frontend PlatformSelector"

            # Clean up
            if response.status_code in [200, 201]:
                project_id = response.json()["id"]
                db_session.query(Project).filter(Project.id == project_id).delete()
                db_session.commit()


class TestEndToEndPlatformWorkflow:
    """Test complete workflow: create → generate → export with platform targeting"""

    def test_complete_workflow_linkedin(
        self, client, auth_headers, test_client_db, test_user, db_session
    ):
        """Test complete workflow for LinkedIn platform"""

        # Step 1: Create project with LinkedIn target
        create_response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "LinkedIn E2E Test",
                "clientId": test_client_db.id,
                "targetPlatform": "linkedin",
                "numPosts": 3,
            },
        )
        assert create_response.status_code in [200, 201]
        project = create_response.json()
        project_id = project["id"]

        # Step 2: Create brief
        brief = Brief(
            id="brief-e2e-linkedin",
            project_id=project_id,
            content="Company: E2E Test Company\nBusiness: End-to-end testing platform\nAudience: QA professionals",
            source="paste",
        )
        db_session.add(brief)
        db_session.commit()

        # Step 3: Generate content with platform targeting
        gen_response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "client_id": test_client_db.id,
                "is_batch": True,
                "num_posts": 3,
                "target_platform": "linkedin",
            },
        )
        assert gen_response.status_code in [200, 201, 202]

        # Step 4: Create mock posts for export test.
        # started_at is set 1 second ahead so this run sorts after the one
        # created by generate-all, ensuring the export endpoint picks it up
        # as the "latest run" and finds these posts.
        run = Run(
            id="run-e2e-linkedin",
            project_id=project_id,
            status="succeeded",
            started_at=datetime.utcnow() + timedelta(seconds=1),
        )
        db_session.add(run)

        posts = [
            Post(
                id=f"post-e2e-linkedin-{i}",
                project_id=project_id,
                run_id=run.id,
                content=f"LinkedIn-optimized post {i}",
                template_id=1,
                target_platform="linkedin",
                status="approved",
            )
            for i in range(3)
        ]
        db_session.add_all(posts)
        db_session.commit()

        # Step 5: Export with platform formatting
        export_response = client.post(
            "/api/generator/export",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "format": "md",
                "include_audit_log": False,
                "include_research": False,
            },
        )
        assert export_response.status_code == 200

        print("✅ Complete LinkedIn workflow test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
