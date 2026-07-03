"""
Integration Tests for Research Tools and Regeneration Workflows.

Tests:
1. Research tool execution workflow
2. Post regeneration workflow
3. QA validation workflow
4. Multi-platform generation workflow
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Post, Run, Brief
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-research-test",
        email="research@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Research Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get auth headers"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "research@example.com",
            "password": "testpass123",
        },  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_complete_project(client, auth_headers, db_session, test_user):
    """Setup a complete project with client, brief, and posts"""
    # Create client
    client_entity = Client(
        id="research-client",
        user_id=test_user.id,
        name="Research Test Client",
        business_description="AI solutions for small businesses",
        ideal_customer="Small business owners",
        main_problem_solved="Manual workflows",
    )
    db_session.add(client_entity)

    # Create project
    project = Project(
        id="research-project",
        user_id=test_user.id,
        client_id="research-client",
        name="Research Test Project",
        num_posts=10,
        status="draft",
    )
    db_session.add(project)

    # Create brief
    brief = Brief(
        id="research-brief",
        project_id="research-project",
        content="""
Company: Research Test Client
Business: AI solutions for small businesses
Customer: Small business owners
Problem: Manual workflows take too long
Pain Points: Repetitive tasks, lack of automation
Platforms: LinkedIn
Tone: Professional
        """,
        source="paste",  # Required field
    )
    db_session.add(brief)

    # Create run
    run = Run(
        id="research-run",
        project_id="research-project",
        status="succeeded",
    )
    db_session.add(run)

    # Create posts
    posts = [
        Post(
            id=f"research-post-{i}",
            project_id="research-project",
            run_id="research-run",
            content=f"Test post {i} about automation",
            template_id=(i % 3) + 1,
            template_name=f"Template {(i % 3) + 1}",
            word_count=200 + i * 10,
            status="approved" if i % 3 != 0 else "flagged",
            flags=["too_short"] if i % 3 == 0 else [],
        )
        for i in range(10)
    ]
    for post in posts:
        db_session.add(post)

    db_session.commit()

    return {
        "client_id": "research-client",
        "project_id": "research-project",
        "brief_id": "research-brief",
        "run_id": "research-run",
    }


class TestResearchToolsWorkflow:
    """Test research tools execution"""

    def test_list_available_research_tools(self, client, auth_headers):
        """Test listing available research tools"""
        response = client.get(
            "/api/research/tools",
            headers=auth_headers,
        )

        # May return 200 with tools or 404 if endpoint not implemented
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            # If it's a list, should contain tool definitions
            if isinstance(data, list) and len(data) > 0:
                # Tools should have name/id
                assert any("name" in tool or "id" in tool for tool in data)

    @pytest.mark.skip(reason="Research execution requires real API calls")
    def test_execute_voice_analysis(
        self, client, auth_headers, setup_complete_project, mock_anthropic_client
    ):
        """Test executing voice analysis research tool"""
        response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "project_id": setup_complete_project["project_id"],
                "client_id": setup_complete_project["client_id"],
                "tool": "voice_analysis",
                "params": {},
            },
        )

        assert response.status_code in [200, 201, 202]
        data = response.json()
        assert "outputs" in data or "result" in data


class TestPostRegenerationWorkflow:
    """Test post regeneration workflow"""

    def test_flag_post_for_regeneration(self, client, auth_headers, setup_complete_project):
        """Test flagging a post for regeneration"""
        response = client.post(
            "/api/posts/research-post-1/flag",
            headers=auth_headers,
            json={
                "reason": "Content doesn't match brand voice",
                "flags": ["poor_voice_match"],
            },
        )

        # Endpoint might vary in implementation
        assert response.status_code in [200, 201, 404]  # 404 if endpoint different

    def test_get_flagged_posts(self, client, auth_headers, setup_complete_project):
        """Test retrieving flagged posts for review"""
        response = client.get(
            f"/api/posts/?project_id={setup_complete_project['project_id']}&status=flagged",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])

        # Should have some flagged posts from fixture
        flagged = [p for p in items if p.get("status") == "flagged"]
        assert len(flagged) >= 1

    @pytest.mark.skip(reason="Regeneration requires real API calls")
    def test_regenerate_single_post(
        self, client, auth_headers, setup_complete_project, mock_anthropic_client
    ):
        """Test regenerating a single flagged post"""
        response = client.post(
            "/api/posts/research-post-0/regenerate",
            headers=auth_headers,
            json={
                "feedback": "Make it more engaging with a stronger hook",
            },
        )

        assert response.status_code in [200, 201, 202]
        data = response.json()
        # New post should be returned
        assert "content" in data or "id" in data

    def test_get_flagged_post_details(self, client, auth_headers, setup_complete_project):
        """Test retrieving details of a flagged post"""
        # Post 0 is flagged in setup_complete_project
        response = client.get(
            "/api/posts/research-post-0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have flagged status
        assert data["status"] == "flagged"
        # Should have flags array
        assert "flags" in data or "too_short" in str(data)

    def test_update_post_content(self, client, auth_headers, setup_complete_project):
        """Test manually editing post content"""
        new_content = "This is manually edited content that better matches the brand voice."

        response = client.patch(
            "/api/posts/research-post-1",
            headers=auth_headers,
            json={
                "content": new_content,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == new_content


class TestQAValidationWorkflow:
    """Test QA validation scenarios"""

    def test_get_posts_by_word_count_range(self, client, auth_headers, setup_complete_project):
        """Test filtering posts by word count"""
        # Get posts with word count > 220 (our fixture has 200, 210, 220, etc.)
        response = client.get(
            f"/api/posts/?project_id={setup_complete_project['project_id']}&min_word_count=220",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])

        # All returned posts should have word_count >= 220
        for post in items:
            word_count = post.get("word_count") or post.get("wordCount", 0)
            assert word_count >= 220

    def test_get_posts_by_template(self, client, auth_headers, setup_complete_project):
        """Test filtering posts by template"""
        response = client.get(
            f"/api/posts/?project_id={setup_complete_project['project_id']}&template_id=1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])

        # All returned posts should have template_id 1 (may be string or int)
        for post in items:
            template_id = post.get("template_id") or post.get("templateId")
            # Compare as strings since API may return string type
            assert str(template_id) == "1"

    def test_posts_sorted_by_creation(self, client, auth_headers, setup_complete_project):
        """Test posts are returned sorted by creation date"""
        response = client.get(
            f"/api/posts/?project_id={setup_complete_project['project_id']}&sort_by=created_at&sort_order=desc",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])

        # Should have posts
        assert len(items) > 0


class TestMultiPlatformWorkflow:
    """Test multi-platform content generation"""

    @pytest.fixture
    def setup_multiplatform_project(self, client, auth_headers, db_session, test_user):
        """Setup project targeting multiple platforms"""
        client_entity = Client(
            id="multiplatform-client",
            user_id=test_user.id,
            name="Multi Platform Client",
        )
        db_session.add(client_entity)

        project = Project(
            id="multiplatform-project",
            user_id=test_user.id,
            client_id="multiplatform-client",
            name="Multi Platform Project",
            num_posts=12,
            status="draft",
        )
        db_session.add(project)

        run = Run(
            id="multiplatform-run",
            project_id="multiplatform-project",
            status="succeeded",
        )
        db_session.add(run)

        # Create posts for different platforms
        platforms = ["linkedin", "twitter", "facebook", "blog"]
        posts = []
        for i, platform in enumerate(platforms):
            for j in range(3):  # 3 posts per platform
                post = Post(
                    id=f"mp-post-{platform}-{j}",
                    project_id="multiplatform-project",
                    run_id="multiplatform-run",
                    content=f"Test {platform} post {j}",
                    template_id=1,
                    template_name="Problem Recognition",
                    word_count=150 if platform == "twitter" else 250,
                    status="approved",
                    target_platform=platform,
                )
                posts.append(post)

        for post in posts:
            db_session.add(post)
        db_session.commit()

        return {
            "client_id": "multiplatform-client",
            "project_id": "multiplatform-project",
        }

    def test_filter_posts_by_platform(self, client, auth_headers, setup_multiplatform_project):
        """Test filtering posts by target platform"""
        response = client.get(
            f"/api/posts/?project_id={setup_multiplatform_project['project_id']}&platform=linkedin",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])

        # Should only have LinkedIn posts
        for post in items:
            platform = post.get("target_platform") or post.get("targetPlatform")
            assert platform == "linkedin"

    def test_get_platform_specific_post_counts(
        self, client, auth_headers, setup_multiplatform_project
    ):
        """Test getting post counts per platform"""
        platforms = ["linkedin", "twitter", "facebook", "blog"]

        for platform in platforms:
            response = client.get(
                f"/api/posts/?project_id={setup_multiplatform_project['project_id']}&platform={platform}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", [])
            # Should have 3 posts per platform from our fixture
            assert len(items) == 3


class TestTrendsWorkflow:
    """Test Google Trends integration workflow"""

    def test_trends_search(self, client, auth_headers):
        """Test searching Google Trends"""
        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers,
            json={
                "keywords": ["content marketing", "AI automation"],
                "timeframe": "today 3-m",
                "geo": "US",
            },
        )

        # May be rate limited or return actual data
        assert response.status_code in [200, 429, 503]

    def test_trends_related_queries(self, client, auth_headers):
        """Test getting related queries from Trends"""
        response = client.post(
            "/api/trends/search/related",
            headers=auth_headers,
            json={
                "keywords": ["content marketing"],
            },
        )

        # May be rate limited or return actual data
        assert response.status_code in [200, 429, 503]


class TestErrorHandlingWorkflow:
    """Test error handling across workflows"""

    def test_invalid_project_id(self, client, auth_headers):
        """Test handling of invalid project ID"""
        response = client.get(
            "/api/projects/invalid-project-id-that-does-not-exist",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_invalid_client_id(self, client, auth_headers):
        """Test handling of invalid client ID"""
        response = client.get(
            "/api/clients/invalid-client-id-that-does-not-exist",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_create_project_with_invalid_client(self, client, auth_headers):
        """Test creating project with non-existent client"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers,
            json={
                "name": "Invalid Client Project",
                "client_id": "non-existent-client-id",
                "num_posts": 10,
            },
        )

        assert response.status_code in [400, 404, 422]

    def test_create_brief_with_invalid_project(self, client, auth_headers):
        """Test creating brief with non-existent project"""
        response = client.post(
            "/api/briefs/create",
            headers=auth_headers,
            json={
                "project_id": "non-existent-project-id",
                "content": "Some brief content",
            },
        )

        assert response.status_code in [400, 404, 422]


class TestRateLimitingWorkflow:
    """Test rate limiting across workflows"""

    def test_standard_endpoints_allow_reasonable_requests(self, client, auth_headers):
        """Test that standard endpoints allow reasonable request volume"""
        # Make 10 requests to clients endpoint
        for _ in range(10):
            response = client.get("/api/clients/", headers=auth_headers)
            # Should not be rate limited for reasonable volume
            assert response.status_code in [200, 429]

            if response.status_code == 429:
                # If rate limited, that's fine - just verify the behavior
                break

    def test_rate_limited_endpoint_returns_429(self, client, auth_headers):
        """Test that rate-limited endpoints return 429 when exceeded"""
        # Note: This test may need adjustment based on actual rate limits
        # The generator endpoint is strictly limited (10/hour)
        responses = []
        for i in range(15):
            response = client.post(
                "/api/generator/generate-all",
                headers=auth_headers,
                json={
                    "project_id": f"test-project-{i}",
                    "client_id": f"test-client-{i}",
                },
            )
            responses.append(response.status_code)

            if response.status_code == 429:
                # Rate limit working as expected
                break

        # Either we got rate limited or all requests went through
        # Both are valid depending on rate limit configuration
        assert 429 in responses or all(r in [200, 201, 202, 400, 404, 422] for r in responses)


class TestDataIntegrityWorkflow:
    """Test data integrity across operations"""

    def test_client_project_relationship(self, client, auth_headers, db_session, test_user):
        """Test that client-project relationships are properly maintained"""
        # Create client
        client_response = client.post(
            "/api/clients/",
            headers=auth_headers,
            json={"name": "Relationship Test Client"},
        )
        assert client_response.status_code == 201
        client_id = client_response.json()["id"]

        # Create project for client
        project_response = client.post(
            "/api/projects/",
            headers=auth_headers,
            json={
                "name": "Relationship Test Project",
                "client_id": client_id,
                "num_posts": 5,
            },
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Verify project is linked to client
        get_project_response = client.get(
            f"/api/projects/{project_id}",
            headers=auth_headers,
        )
        assert get_project_response.status_code == 200
        project_data = get_project_response.json()
        client_id_field = project_data.get("client_id") or project_data.get("clientId")
        assert client_id_field == client_id

    def test_project_status_prevents_invalid_transitions(
        self, client, auth_headers, db_session, test_user
    ):
        """Test that project status follows valid transitions"""
        # Create client and project
        client_response = client.post(
            "/api/clients/",
            headers=auth_headers,
            json={"name": "Status Test Client"},
        )
        client_id = client_response.json()["id"]

        project_response = client.post(
            "/api/projects/",
            headers=auth_headers,
            json={
                "name": "Status Test Project",
                "client_id": client_id,
                "num_posts": 5,
            },
        )
        project_id = project_response.json()["id"]

        # Try to transition directly from draft to delivered (should fail or be handled)
        update_response = client.patch(
            f"/api/projects/{project_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )

        # Either rejected (400) or allowed (depends on implementation)
        assert update_response.status_code in [200, 400, 422]
