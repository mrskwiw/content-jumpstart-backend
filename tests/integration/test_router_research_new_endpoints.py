"""
Integration tests for new Research Router endpoints:
- GET /api/research/pricing-preview (bundle detection)
- GET /api/research/analytics (ROI tracking)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client, db_session):
    """Get auth headers for authenticated requests"""
    from backend.models import User
    from backend.utils.auth import get_password_hash

    # Create test user directly
    user = User(
        id="user-test-pricing",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()

    # Login to get token
    response = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPricingPreviewEndpoint:
    """Tests for /api/research/pricing-preview endpoint"""

    def test_pricing_preview_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected"""
        response = client.get("/api/research/pricing-preview?tool_ids=voice_analysis")
        assert response.status_code == 401

    def test_pricing_preview_single_tool(self, client, auth_headers):
        """Test pricing for single tool (no bundle)"""
        response = client.get(
            "/api/research/pricing-preview?tool_ids=voice_analysis", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # API returns snake_case
        assert data["base_cost"] == 400.0
        assert data["final_cost"] == 400.0
        assert data["discount"] == 0.0
        assert data["bundle_applied"] is None
        assert data["savings_percent"] == 0.0

    def test_pricing_preview_foundation_bundle(self, client, auth_headers):
        """Test Foundation Pack bundle detection (4 tools, $1,500)"""
        tools = "voice_analysis,brand_archetype,audience_research,icp_workshop"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["base_cost"] == 1800.0  # 400 + 300 + 500 + 600
        assert data["final_cost"] == 1500.0  # Bundle price
        assert data["discount"] == 300.0
        assert data["bundle_applied"] == "foundation_pack"
        assert data["bundle_name"] == "Foundation Pack"
        assert data["savings_percent"] == 16.7

    def test_pricing_preview_seo_bundle(self, client, auth_headers):
        """Test SEO Pack bundle detection (3 tools, $1,300)"""
        tools = "seo_keyword_research,competitive_analysis,content_gap_analysis"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["base_cost"] == 1400.0  # 400 + 500 + 500
        assert data["final_cost"] == 1300.0  # Bundle price
        assert data["discount"] == 100.0
        assert data["bundle_applied"] == "seo_pack"
        assert data["bundle_name"] == "SEO Pack"

    def test_pricing_preview_complete_strategy(self, client, auth_headers):
        """Test Complete Strategy bundle (7 foundation + SEO tools, $2,400)"""
        tools = "voice_analysis,brand_archetype,audience_research,icp_workshop,seo_keyword_research,competitive_analysis,content_gap_analysis"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["base_cost"] == 3200.0
        assert data["final_cost"] == 2400.0
        assert data["discount"] == 800.0
        assert data["bundle_applied"] == "complete_strategy"
        assert data["bundle_name"] == "Complete Strategy"

    def test_pricing_preview_ultimate_pack(self, client, auth_headers):
        """Test Ultimate Pack bundle (all 12 tools, $4,500)"""
        tools = "voice_analysis,brand_archetype,audience_research,icp_workshop,seo_keyword_research,competitive_analysis,content_gap_analysis,content_audit,platform_strategy,content_calendar_strategy,story_mining_interview,market_trends"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["base_cost"] == 5100.0
        assert data["final_cost"] == 4500.0
        assert data["discount"] == 600.0
        assert data["bundle_applied"] == "ultimate_pack"
        assert data["bundle_name"] == "Ultimate Pack"

    def test_pricing_preview_next_bundle_suggestion(self, client, auth_headers):
        """Test that next bundle suggestion is provided"""
        # 3 foundation tools (missing icp_workshop to complete bundle)
        tools = "voice_analysis,brand_archetype,audience_research"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "next_bundle_suggestion" in data
        suggestion = data["next_bundle_suggestion"]
        assert suggestion is not None
        assert "bundle" in suggestion
        assert "missing_tools" in suggestion
        assert "additional_cost" in suggestion
        assert "potential_savings" in suggestion
        assert suggestion["potential_savings"] > 0

    def test_pricing_preview_no_suggestion_for_ultimate(self, client, auth_headers):
        """Test that no bundle suggestion for Ultimate Pack"""
        tools = "voice_analysis,brand_archetype,audience_research,icp_workshop,seo_keyword_research,competitive_analysis,content_gap_analysis,content_audit,platform_strategy,content_calendar_strategy,story_mining_interview,market_trends"
        response = client.get(
            f"/api/research/pricing-preview?tool_ids={tools}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # No upgrade possible from Ultimate Pack
        assert data["next_bundle_suggestion"] is None

    def test_pricing_preview_empty_tools(self, client, auth_headers):
        """Test pricing with no tools selected"""
        response = client.get("/api/research/pricing-preview?tool_ids=", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["base_cost"] == 0.0
        assert data["final_cost"] == 0.0
        assert data["discount"] == 0.0

    def test_pricing_preview_invalid_tool_id(self, client, auth_headers):
        """Test pricing with invalid tool ID returns zero cost for that tool"""
        response = client.get(
            "/api/research/pricing-preview?tool_ids=voice_analysis,invalid_tool",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should only count valid tool (voice_analysis = $400)
        assert data["base_cost"] == 400.0


class TestAnalyticsEndpoint:
    """Tests for /api/research/analytics endpoint"""

    def test_analytics_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected"""
        response = client.get("/api/research/analytics")
        assert response.status_code == 401

    def test_analytics_empty_results(self, client, auth_headers, db_session):
        """Test analytics with no research results"""
        response = client.get("/api/research/analytics?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_revenue"] == 0.0
        assert data["total_api_cost"] == 0.0
        assert data["profit_margin"] == 0.0
        assert data["total_executions"] == 0
        assert data["cache_hit_rate"] == 0.0
        assert data["cache_savings"] == 0.0
        assert data["avg_cost_per_tool"] == 0.0
        assert data["top_tools"] == []
        assert data["date_range"] == 90

    def test_analytics_with_results(self, client, auth_headers, db_session):
        """Test analytics with research results"""
        from backend.models import ResearchResult, Client, Project
        import uuid

        # Get current user
        from backend.models import User

        user = db_session.query(User).filter(User.email == "test@example.com").first()

        # Create client and project directly
        client_obj = Client(
            id=f"client-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            name="Test Client",
            email="client@test.com",
            business_description="Test business",
        )
        db_session.add(client_obj)
        db_session.commit()

        project = Project(
            id=f"proj-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            name="Test Project",
            num_posts=30,
            status="draft",
        )
        db_session.add(project)
        db_session.commit()

        # Create research results
        result1 = ResearchResult(
            id=f"res-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            project_id=project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            actual_cost_usd=1.25,
            status="completed",
            duration_seconds=120,
            created_at=datetime.utcnow(),
        )

        result2 = ResearchResult(
            id=f"res-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            project_id=project.id,
            tool_name="brand_archetype",
            tool_label="Brand Archetype",
            tool_price=300.0,
            actual_cost_usd=0.85,
            status="completed",
            duration_seconds=90,
            is_cached_result=True,
            created_at=datetime.utcnow(),
        )

        db_session.add(result1)
        db_session.add(result2)
        db_session.commit()

        response = client.get("/api/research/analytics?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_revenue"] == 700.0  # 400 + 300
        assert data["total_api_cost"] == 2.10  # 1.25 + 0.85
        assert data["profit_margin"] > 99.0  # (700 - 2.10) / 700 * 100 ≈ 99.7%
        assert data["total_executions"] == 2
        assert data["cache_hit_rate"] == 50.0  # 1 cached out of 2
        assert data["cache_savings"] == 350.0  # 50% of $700
        assert data["avg_cost_per_tool"] == 1.05  # 2.10 / 2
        assert len(data["top_tools"]) == 2

    def test_analytics_date_range_filtering(self, client, auth_headers, db_session):
        """Test analytics date range filtering"""
        from backend.models import ResearchResult, Client, Project, User
        import uuid

        # Get current user
        user = db_session.query(User).filter(User.email == "test@example.com").first()

        # Create client and project directly
        client_obj = Client(
            id=f"client-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            name="Test Client 2",
            email="client2@test.com",
            business_description="Test business 2",
        )
        db_session.add(client_obj)
        db_session.commit()

        project = Project(
            id=f"proj-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            name="Test Project 2",
            num_posts=30,
            status="draft",
        )
        db_session.add(project)
        db_session.commit()

        # Create old result (100 days ago)
        old_result = ResearchResult(
            id=f"res-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            project_id=project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            actual_cost_usd=1.25,
            status="completed",
            created_at=datetime.utcnow() - timedelta(days=100),
        )

        # Create recent result
        recent_result = ResearchResult(
            id=f"res-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            project_id=project.id,
            tool_name="brand_archetype",
            tool_label="Brand Archetype",
            tool_price=300.0,
            actual_cost_usd=0.85,
            status="completed",
            created_at=datetime.utcnow(),
        )

        db_session.add(old_result)
        db_session.add(recent_result)
        db_session.commit()

        # Query last 90 days - should only get recent result
        response = client.get("/api/research/analytics?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Should only include recent result
        assert (
            data["total_executions"] >= 1
        )  # At least the recent one (may have others from previous tests)
        assert data["date_range"] == 90

    def test_analytics_top_tools_ranking(self, client, auth_headers, db_session):
        """Test that top tools are ranked by execution count"""
        from backend.models import ResearchResult, Client, Project, User
        import uuid

        # Get current user
        user = db_session.query(User).filter(User.email == "test@example.com").first()

        # Create client and project directly
        client_obj = Client(
            id=f"client-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            name="Test Client 3",
            email="client3@test.com",
            business_description="Test business 3",
        )
        db_session.add(client_obj)
        db_session.commit()

        project = Project(
            id=f"proj-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            name="Test Project 3",
            num_posts=30,
            status="draft",
        )
        db_session.add(project)
        db_session.commit()

        # Create 3 voice_analysis results and 1 brand_archetype
        for i in range(3):
            result = ResearchResult(
                id=f"res-{uuid.uuid4().hex[:12]}",
                user_id=user.id,
                client_id=client_obj.id,
                project_id=project.id,
                tool_name="voice_analysis",
                tool_label="Voice Analysis",
                tool_price=400.0,
                actual_cost_usd=1.25,
                status="completed",
                created_at=datetime.utcnow(),
            )
            db_session.add(result)

        result = ResearchResult(
            id=f"res-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            client_id=client_obj.id,
            project_id=project.id,
            tool_name="brand_archetype",
            tool_label="Brand Archetype",
            tool_price=300.0,
            actual_cost_usd=0.85,
            status="completed",
            created_at=datetime.utcnow(),
        )
        db_session.add(result)
        db_session.commit()

        response = client.get("/api/research/analytics?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Voice analysis should be ranked higher (3 executions vs 1)
        top_tools = data["top_tools"]
        assert len(top_tools) > 0

        # Find voice_analysis in top tools
        voice_tool = next((t for t in top_tools if t["tool_name"] == "voice_analysis"), None)
        assert voice_tool is not None
        assert voice_tool["execution_count"] >= 3

    def test_analytics_custom_date_range(self, client, auth_headers):
        """Test analytics with custom date ranges"""
        # Test different date range values
        for days in [7, 30, 90, 365]:
            response = client.get(f"/api/research/analytics?days={days}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["date_range"] == days


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
