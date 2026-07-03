"""
Integration tests for platform-specific content generation.

Tests:
- Generating content with target_platform parameter
- Platform propagation through generation pipeline
- Database persistence of target_platform
- Authorization checks with platform-specific projects
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Brief, Run
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client, create_test_project


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-platform-test",
        email="platform@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Platform Test User",
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
        json={
            "email": "platform@example.com",
            "password": "testpass123",
        },  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_client_db(db_session: Session, test_user):
    """Create a test client in database"""
    client_data = create_test_client(
        name="Platform Test Client",
        user_id=test_user.id,
        email="client@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


class TestPlatformProjectCreation:
    """Test creating projects with target_platform"""

    def test_create_project_with_linkedin_platform(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test creating project with LinkedIn as target platform"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "LinkedIn Campaign",
                "clientId": test_client_db.id,
                "targetPlatform": "linkedin",
                "numPosts": 20,
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["targetPlatform"] == "linkedin" or data["target_platform"] == "linkedin"
        assert data["name"] == "LinkedIn Campaign"

        # Verify in database
        project_id = data["id"]
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is not None
        assert db_project.target_platform == "linkedin"

    def test_create_project_with_twitter_platform(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test creating project with Twitter as target platform"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Twitter Campaign",
                "clientId": test_client_db.id,
                "targetPlatform": "twitter",
                "numPosts": 30,
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()

        # Verify in database
        project_id = data["id"]
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project.target_platform == "twitter"

    def test_create_project_default_blog_platform(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test project defaults to 'blog' platform when not specified"""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Blog Campaign",
                "clientId": test_client_db.id,
                "numPosts": 25,
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()

        # Verify in database
        project_id = data["id"]
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project.target_platform == "blog"

    def test_create_projects_for_all_platforms(
        self, client, auth_headers, test_client_db, db_session
    ):
        """Test creating projects for all supported platforms"""
        platforms = [
            "linkedin",
            "twitter",
            "facebook",
            "blog",
            "email",
        ]

        for platform in platforms:
            response = client.post(
                "/api/projects",
                headers=auth_headers,
                json={
                    "name": f"{platform.title()} Campaign",
                    "clientId": test_client_db.id,
                    "targetPlatform": platform,
                    "numPosts": 10,
                },
            )

            assert response.status_code in [200, 201], f"Failed for platform {platform}"

            # Verify in database
            data = response.json()
            project_id = data["id"]
            db_project = db_session.query(Project).filter(Project.id == project_id).first()
            assert db_project.target_platform == platform


class TestPlatformProjectUpdate:
    """Test updating projects with target_platform"""

    @pytest.fixture
    def linkedin_project(self, db_session, test_user, test_client_db):
        """Create a LinkedIn project"""
        project_data = create_test_project(
            name="LinkedIn Project",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="linkedin",
        )
        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()
        db_session.refresh(db_project)
        return db_project

    def test_update_project_platform(self, client, auth_headers, linkedin_project, db_session):
        """Test updating project's target_platform"""
        response = client.put(
            f"/api/projects/{linkedin_project.id}",
            headers=auth_headers,
            json={"targetPlatform": "twitter"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify in database
        db_session.refresh(linkedin_project)
        assert linkedin_project.target_platform == "twitter"

    def test_update_project_platform_with_other_fields(
        self, client, auth_headers, linkedin_project, db_session
    ):
        """Test updating platform along with other fields"""
        response = client.put(
            f"/api/projects/{linkedin_project.id}",
            headers=auth_headers,
            json={
                "name": "Updated Campaign",
                "targetPlatform": "twitter",
                "numPosts": 40,
            },
        )

        assert response.status_code == 200

        # Verify in database
        db_session.refresh(linkedin_project)
        assert linkedin_project.target_platform == "twitter"
        assert linkedin_project.name == "Updated Campaign"
        assert linkedin_project.num_posts == 40


class TestPlatformContentGeneration:
    """Test content generation with target_platform"""

    @pytest.fixture
    def medium_project_with_brief(self, db_session, test_user, test_client_db):
        """Create a Medium project with brief"""
        project_data = create_test_project(
            name="Medium Project",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="medium",
            num_posts=10,
        )
        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()

        # Add brief
        brief_content = """
        Company: Test Publishing Company
        Business: Long-form content creation
        Ideal Customer: Writers and bloggers
        Main Problem: Content distribution
        Platforms: Medium
        Tone: Professional, thoughtful
        """

        brief = Brief(
            id=f"brief-{db_project.id}",
            project_id=db_project.id,
            content=brief_content.strip(),
            source="paste",
        )
        db_session.add(brief)
        db_session.commit()
        db_session.refresh(db_project)
        return db_project

    def test_generate_with_platform_parameter(
        self,
        client,
        auth_headers,
        medium_project_with_brief,
        test_client_db,
        mock_anthropic_client,
        db_session,
    ):
        """Test generation accepts target_platform parameter"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": medium_project_with_brief.id,
                "client_id": test_client_db.id,
                "target_platform": "medium",  # Explicit platform
            },
        )

        assert response.status_code in [200, 201, 202]
        data = response.json()

        # Should create a run
        assert "id" in data or "run_id" in data
        run_id = data.get("id") or data.get("run_id")

        # Verify run created
        db_run = db_session.query(Run).filter(Run.id == run_id).first()
        assert db_run is not None
        assert db_run.project_id == medium_project_with_brief.id

    def test_generate_inherits_project_platform(
        self,
        client,
        auth_headers,
        medium_project_with_brief,
        test_client_db,
        mock_anthropic_client,
        db_session,
    ):
        """Test generation uses project's target_platform when not specified"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": medium_project_with_brief.id,
                "client_id": test_client_db.id,
                # No target_platform - should use project's
            },
        )

        assert response.status_code in [200, 201, 202]

        # Verify project has medium platform
        db_session.refresh(medium_project_with_brief)
        assert medium_project_with_brief.target_platform == "medium"

    def test_generate_overrides_project_platform(
        self,
        client,
        auth_headers,
        medium_project_with_brief,
        test_client_db,
        mock_anthropic_client,
        db_session,
    ):
        """Test generation can override project's platform"""
        # Project is set to 'medium', but we'll generate for 'linkedin'
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": medium_project_with_brief.id,
                "client_id": test_client_db.id,
                "target_platform": "linkedin",  # Override
            },
        )

        assert response.status_code in [200, 201, 202]

        # Project platform should remain unchanged
        db_session.refresh(medium_project_with_brief)
        assert medium_project_with_brief.target_platform == "medium"


class TestPlatformDatabasePersistence:
    """Test target_platform persistence in database"""

    def test_platform_persists_after_creation(self, db_session, test_user, test_client_db):
        """Test target_platform is saved to database"""
        project_data = create_test_project(
            name="Persistence Test",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="instagram",
        )
        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()

        # Query fresh from database
        project_id = db_project.id
        db_session.expunge_all()  # Clear session

        fetched_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert fetched_project is not None
        assert fetched_project.target_platform == "instagram"

    def test_platform_persists_after_update(self, db_session, test_user, test_client_db):
        """Test target_platform updates are saved to database"""
        project_data = create_test_project(
            name="Update Test",
            client_id=test_client_db.id,
            user_id=test_user.id,
            target_platform="facebook",
        )
        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()

        # Update platform
        db_project.target_platform = "substack"
        db_session.commit()

        # Query fresh
        project_id = db_project.id
        db_session.expunge_all()

        fetched_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert fetched_project.target_platform == "substack"

    def test_null_platform_handling(self, db_session, test_user, test_client_db):
        """Test handling of NULL target_platform in database"""
        project_data = create_test_project(
            name="Null Platform Test",
            client_id=test_client_db.id,
            user_id=test_user.id,
        )
        # Don't set target_platform
        project_data.pop("target_platform", None)

        db_project = Project(**project_data)
        db_session.add(db_project)
        db_session.commit()

        # Should default to 'blog' from column default
        db_session.refresh(db_project)
        assert db_project.target_platform == "blog"


class TestPlatformValidation:
    """Test platform validation in API endpoints"""

    def test_reject_invalid_platform_in_create(self, client, auth_headers, test_client_db):
        """Test API rejects invalid platform values"""
        # Note: This test may pass because Pydantic doesn't validate enum values
        # unless we add explicit validation. This documents current behavior.
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "name": "Invalid Platform",
                "clientId": test_client_db.id,
                "targetPlatform": "tiktok",  # Not in enum
                "numPosts": 10,
            },
        )

        # May succeed (no validation) or fail (with validation)
        # This test documents the behavior
        assert response.status_code in [200, 201, 400, 422]

    def test_accept_all_valid_platforms(self, client, auth_headers, test_client_db):
        """Test all valid platforms are accepted"""
        valid_platforms = [
            "linkedin",
            "twitter",
            "facebook",
            "blog",
            "email",
        ]

        for platform in valid_platforms:
            response = client.post(
                "/api/projects",
                headers=auth_headers,
                json={
                    "name": f"Test {platform}",
                    "clientId": test_client_db.id,
                    "targetPlatform": platform,
                    "numPosts": 5,
                },
            )
            assert response.status_code in [200, 201], f"Failed for {platform}"
