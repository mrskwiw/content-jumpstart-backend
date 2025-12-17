"""Comprehensive API tests for Phase 12 Portal."""

from fastapi import status


class TestAuthentication:
    """Test authentication endpoints."""

    def test_register_user(self, client):
        """Test user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Registration returns TokenResponse with nested user object
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert "user_id" in data["user"]

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Different User",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "testpassword123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Login returns TokenResponse with nested user object
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid password fails."""
        response = client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, client, test_user):
        """Test token refresh."""
        # First login to get a refresh token
        login_response = client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "testpassword123"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now use refresh token to get a new access token (as query parameter)
        response = client.post(f"/api/auth/refresh?refresh_token={refresh_token}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user.email


class TestProjects:
    """Test project endpoints."""

    def test_create_project(self, client, auth_headers):
        """Test project creation."""
        response = client.post(
            "/api/projects/",
            json={
                "client_name": "Acme Corp",
                "package_tier": "Professional",
                "package_price": 1800.00,
                "posts_count": 30,
                "revision_limit": 2,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["client_name"] == "Acme Corp"
        assert data["package_tier"] == "Professional"
        assert data["status"] == "brief_submitted"

    def test_list_projects(self, client, auth_headers, test_project):
        """Test listing projects."""
        response = client.get("/api/projects/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert len(data["projects"]) >= 1

    def test_get_project(self, client, auth_headers, test_project):
        """Test getting project details."""
        response = client.get(f"/api/projects/{test_project.project_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_id"] == test_project.project_id
        assert data["client_name"] == test_project.client_name

    def test_get_project_unauthorized(self, client, auth_headers2, test_project):
        """Test that users can't access other users' projects."""
        response = client.get(f"/api/projects/{test_project.project_id}", headers=auth_headers2)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_project_status(self, client, auth_headers, test_project):
        """Test updating project status."""
        response = client.patch(
            f"/api/projects/{test_project.project_id}/status",
            json={"status": "processing"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"


class TestBriefs:
    """Test brief endpoints."""

    def test_create_brief(self, client, auth_headers, test_project):
        """Test brief creation."""
        response = client.post(
            "/api/briefs/",
            json={
                "project_id": test_project.project_id,
                "tone_descriptors": ["professional", "friendly"],
                "voice_notes": "Clear and concise",
                "audience_type": "B2B SaaS Founders",
                "audience_title": "CEO",
                "audience_industry": "Technology",
                "pain_points": ["time management", "content consistency"],
                "key_topics": ["content strategy", "SEO"],
                "target_platforms": ["LinkedIn", "Twitter"],
                "posting_frequency": "3-4 times per week",
                "conversion_goal": "Lead generation",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["project_id"] == test_project.project_id
        assert data["tone_descriptors"] == ["professional", "friendly"]
        assert data["audience_type"] == "B2B SaaS Founders"

    def test_get_brief_by_project(self, client, auth_headers, test_brief):
        """Test getting brief by project ID."""
        response = client.get(f"/api/briefs/project/{test_brief.project_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["brief_id"] == test_brief.brief_id
        assert data["project_id"] == test_brief.project_id

    def test_update_brief(self, client, auth_headers, test_brief):
        """Test updating brief."""
        response = client.patch(
            f"/api/briefs/{test_brief.brief_id}",
            json={
                "voice_notes": "Updated voice notes",
                "tone_descriptors": ["professional", "witty"],
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["voice_notes"] == "Updated voice notes"
        assert "professional" in data["tone_descriptors"]

    def test_delete_brief(self, client, auth_headers, test_brief, db_session):
        """Test deleting brief."""
        brief_id = test_brief.brief_id
        response = client.delete(f"/api/briefs/{brief_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestDeliverables:
    """Test deliverable endpoints."""

    def test_list_deliverables(self, client, auth_headers, test_deliverable):
        """Test listing deliverables for a project."""
        response = client.get(
            f"/api/deliverables/project/{test_deliverable.project_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert len(data["deliverables"]) >= 1

    def test_get_deliverable(self, client, auth_headers, test_deliverable):
        """Test getting deliverable metadata."""
        response = client.get(
            f"/api/deliverables/{test_deliverable.deliverable_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deliverable_id"] == test_deliverable.deliverable_id
        assert data["deliverable_type"] == "social_posts"

    def test_download_deliverable(self, client, auth_headers, test_deliverable):
        """Test downloading deliverable file."""
        response = client.get(
            f"/api/deliverables/{test_deliverable.deliverable_id}/download", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert b"Test deliverable content" in response.content

    def test_download_deliverable_unauthorized(self, client, auth_headers2, test_deliverable):
        """Test that users can't download other users' deliverables."""
        response = client.get(
            f"/api/deliverables/{test_deliverable.deliverable_id}/download", headers=auth_headers2
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDashboard:
    """Test dashboard endpoint."""

    def test_get_dashboard(self, client, auth_headers, test_project, test_brief, test_deliverable):
        """Test getting project dashboard."""
        response = client.get(
            f"/api/projects/{test_project.project_id}/dashboard", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify project info
        assert data["project_id"] == test_project.project_id
        assert data["client_name"] == test_project.client_name
        assert data["package_tier"] == test_project.package_tier

        # Verify stats
        stats = data["stats"]
        assert stats["brief_submitted"] is True
        assert stats["total_deliverables"] >= 1
        assert "days_since_created" in stats

        # Verify brief ID
        assert data["brief_id"] == test_brief.brief_id

    def test_get_dashboard_no_brief(self, client, auth_headers, test_project):
        """Test dashboard with no brief submitted."""
        response = client.get(
            f"/api/projects/{test_project.project_id}/dashboard", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["stats"]["brief_submitted"] is False
        assert data["brief_id"] is None


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_onboarding_flow(self, client):
        """Test complete client onboarding workflow."""
        # 1. Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "integration@example.com",
                "password": "password123",
                "full_name": "Integration Test",
            },
        )
        assert register_response.status_code == status.HTTP_201_CREATED

        # 2. Login
        login_response = client.post(
            "/api/auth/login", json={"email": "integration@example.com", "password": "password123"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create project
        project_response = client.post(
            "/api/projects/",
            json={
                "client_name": "Integration Test Client",
                "package_tier": "Professional",
                "package_price": 1800.00,
            },
            headers=headers,
        )
        assert project_response.status_code == status.HTTP_201_CREATED
        project_id = project_response.json()["project_id"]

        # 4. Submit brief
        brief_response = client.post(
            "/api/briefs/",
            json={
                "project_id": project_id,
                "tone_descriptors": ["professional"],
                "audience_type": "Test Audience",
                "key_topics": ["topic1", "topic2"],
            },
            headers=headers,
        )
        assert brief_response.status_code == status.HTTP_201_CREATED

        # 5. Check dashboard
        dashboard_response = client.get(f"/api/projects/{project_id}/dashboard", headers=headers)
        assert dashboard_response.status_code == status.HTTP_200_OK
        dashboard = dashboard_response.json()
        assert dashboard["stats"]["brief_submitted"] is True


class TestSecurity:
    """Security and permission tests."""

    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/projects/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        response = client.get("/api/projects/", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cross_user_access_denied(self, client, auth_headers, auth_headers2, test_project):
        """Test that users can't access other users' resources."""
        # User 2 tries to access User 1's project
        response = client.get(f"/api/projects/{test_project.project_id}", headers=auth_headers2)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestValidation:
    """Input validation tests."""

    def test_invalid_email_format(self, client):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "password123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_short_password(self, client):
        """Test registration with password too short."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_project_status(self, client, auth_headers, test_project):
        """Test updating project with invalid status."""
        response = client.patch(
            f"/api/projects/{test_project.project_id}/status",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
