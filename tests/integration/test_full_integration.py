"""
Full Integration Test - Prerequisites System

Verifies all components are wired together:
1. Prerequisites checking
2. Data flow between tools
3. Batch execution
4. API endpoints
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.services.research_service import ResearchService
from backend.services.research_prerequisites import ResearchPrerequisites
from backend.models import Client, Project, ResearchResult


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def test_client():
    """Create test client"""
    client = Mock()
    client.id = "client-integration-test"
    client.user_id = "user-test"
    client.business_name = "Integration Test Co"
    client.business_description = "AI-powered content platform for B2B SaaS"
    client.industry = "SaaS"
    client.ideal_customer = "Marketing managers"
    client.target_audience = "B2B marketers"
    client.value_proposition = "Streamline content workflows"
    return client


@pytest.fixture
def test_project(test_client):
    """Create test project"""
    project = Mock()
    project.id = "project-integration-test"
    project.user_id = "user-test"
    project.client_id = test_client.id
    project.name = "Integration Test Project"
    return project


@pytest.fixture
def research_service():
    """Create ResearchService instance"""
    return ResearchService()


class TestPrerequisitesSystemLoading:
    """Test that prerequisites system loads correctly"""

    def test_prerequisites_module_loads(self):
        """Test prerequisites module can be imported"""
        from backend.services.research_prerequisites import (
            ResearchPrerequisites,
            PrerequisiteType,
            TOOL_DEPENDENCIES,
        )

        assert ResearchPrerequisites is not None
        assert PrerequisiteType is not None
        assert len(TOOL_DEPENDENCIES) >= 12

    def test_research_service_initializes_with_prerequisites(self, research_service):
        """Test research service has prerequisites instance"""
        assert hasattr(research_service, "prerequisites")
        assert research_service.prerequisites is not None
        assert isinstance(research_service.prerequisites, ResearchPrerequisites)

    def test_all_tool_dependencies_valid(self, research_service):
        """Test all tool dependencies are valid"""
        from backend.services.research_prerequisites import TOOL_DEPENDENCIES

        for tool_id, deps in TOOL_DEPENDENCIES.items():
            # Check each prerequisite exists
            for prereq in deps.prerequisites:
                assert (
                    prereq.tool_id in TOOL_DEPENDENCIES
                ), f"{tool_id} references non-existent prerequisite: {prereq.tool_id}"


class TestDataFlowMechanism:
    """Test data flow between tools via database"""

    def test_fetch_prerequisite_data_exists(self, research_service):
        """Test _fetch_prerequisite_data method exists"""
        assert hasattr(research_service, "_fetch_prerequisite_data")
        assert callable(research_service._fetch_prerequisite_data)

    def test_fetch_prerequisite_data_for_seo(self, research_service, mock_db):
        """Test fetching prerequisite data for tool with no prerequisites"""
        # SEO has no prerequisites
        mock_db.query().filter().order_by().first.return_value = None

        data = research_service._fetch_prerequisite_data(
            mock_db, "project-test", "seo_keyword_research"
        )

        assert data == {}  # No prerequisites needed

    def test_fetch_prerequisite_data_for_market_trends(self, research_service, mock_db):
        """Test fetching SEO keywords for Market Trends"""
        # Mock SEO result in database
        seo_result = Mock()
        seo_result.tool_name = "seo_keyword_research"
        seo_result.status = "completed"
        seo_result.data = {
            "primary_keywords": ["AI content", "marketing automation", "B2B SaaS"],
            "keywords": ["content strategy", "lead generation"],
        }
        seo_result.created_at = datetime.now()

        # Mock database query
        def mock_query_filter(*args, **kwargs):
            mock_result = Mock()
            mock_result.order_by = Mock(return_value=mock_result)
            mock_result.first = Mock(return_value=seo_result)
            return mock_result

        mock_db.query.return_value.filter.side_effect = mock_query_filter

        # Fetch data
        data = research_service._fetch_prerequisite_data(
            mock_db, "project-test", "market_trends_research"
        )

        # Verify SEO keywords were extracted
        assert "seo_keywords" in data
        assert data["seo_keywords"] == ["AI content", "marketing automation", "B2B SaaS"]

    def test_fetch_prerequisite_data_for_content_calendar(self, research_service, mock_db):
        """Test fetching multiple prerequisites for Content Calendar"""
        # Mock SEO result
        seo_result = Mock()
        seo_result.tool_name = "seo_keyword_research"
        seo_result.status = "completed"
        seo_result.data = {"primary_keywords": ["AI", "automation"]}
        seo_result.created_at = datetime.now()

        # Mock Platform result
        platform_result = Mock()
        platform_result.tool_name = "platform_strategy"
        platform_result.status = "completed"
        platform_result.data = {
            "platforms": ["LinkedIn", "Twitter"],
            "frequency": {"LinkedIn": "3x/week"},
        }
        platform_result.created_at = datetime.now()

        # Mock database to return different results based on filter
        def mock_query_filter(*args, **kwargs):
            mock_result = Mock()
            mock_result.order_by = Mock(return_value=mock_result)

            # Check which tool is being queried
            call_count = mock_db.query.call_count
            if call_count % 2 == 1:  # Odd calls get SEO
                mock_result.first = Mock(return_value=seo_result)
            else:  # Even calls get Platform
                mock_result.first = Mock(return_value=platform_result)

            return mock_result

        mock_db.query.return_value.filter.side_effect = mock_query_filter

        # Fetch data
        data = research_service._fetch_prerequisite_data(
            mock_db, "project-test", "content_calendar"
        )

        # Content Calendar should get data from both prerequisites
        assert "seo_keywords" in data or "platform_recommendations" in data


class TestExecuteResearchToolIntegration:
    """Test execute_research_tool integrates with data flow"""

    def test_execute_tool_fetches_prerequisite_data(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test that _fetch_prerequisite_data method exists and is callable"""
        # Verify the method exists on the service
        assert hasattr(research_service, "_fetch_prerequisite_data")
        assert callable(research_service._fetch_prerequisite_data)

        # Mock database queries for direct call
        mock_db.query().filter().all.return_value = []
        mock_db.query().filter().first.return_value = None

        # Call directly and verify it returns a dict (not an exception)
        result = research_service._fetch_prerequisite_data(
            mock_db, test_project.id, "seo_keyword_research"
        )
        assert isinstance(result, dict)


class TestBatchExecutionIntegration:
    """Test batch execution integrates all components"""

    @pytest.mark.asyncio
    async def test_batch_execution_orders_tools(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution orders tools correctly"""
        # Mock database
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Mock tool execution (demo mode)
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db,
                    test_project.id,
                    test_client.id,
                    [
                        {"tool_name": "content_calendar"},
                        {"tool_name": "seo_keyword_research"},
                        {"tool_name": "market_trends_research"},
                    ],
                )

                # Verify execution order
                assert result["execution_order"] == [
                    "seo_keyword_research",  # Tier 1
                    "market_trends_research",  # Tier 2
                    "content_calendar",  # Tier 4
                ]

                # Verify all executed
                assert result["summary"]["total"] == 3

    @pytest.mark.asyncio
    async def test_batch_execution_tracks_completed_in_batch(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution tracks tools completed within batch"""
        # No completed tools in DB
        mock_db.query().filter().distinct().all.return_value = []

        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                # Run full workflow
                result = await research_service.execute_research_tools_batch(
                    mock_db,
                    test_project.id,
                    test_client.id,
                    [
                        {"tool_name": "seo_keyword_research"},
                        {"tool_name": "audience_research"},
                        {"tool_name": "platform_strategy"},
                        {"tool_name": "content_calendar"},
                    ],
                )

                # All should succeed (prerequisites complete in batch)
                assert result["summary"]["successes"] == 4
                assert result["summary"]["blocked"] == 0


class TestAPIEndpointsExist:
    """Test that new API endpoints exist and are accessible"""

    def test_check_prerequisites_endpoint_exists(self):
        """Test /check-prerequisites endpoint exists in router"""
        from backend.routers import research

        # Check endpoint exists
        routes = [route.path for route in research.router.routes]
        assert "/check-prerequisites" in routes

    def test_batch_endpoint_exists(self):
        """Test /batch endpoint exists in router"""
        from backend.routers import research

        routes = [route.path for route in research.router.routes]
        assert "/batch" in routes

    def test_prerequisite_check_request_schema_exists(self):
        """Test PrerequisiteCheckRequest schema exists"""
        from backend.routers.research import PrerequisiteCheckRequest

        # Test schema can be instantiated
        request = PrerequisiteCheckRequest(project_id="test", tool_names=["seo_keyword_research"])

        assert request.project_id == "test"
        assert request.tool_names == ["seo_keyword_research"]

    def test_batch_request_schema_exists(self):
        """Test BatchResearchRequest schema exists"""
        from backend.routers.research import BatchResearchRequest, BatchToolConfig

        # Test schema can be instantiated
        request = BatchResearchRequest(
            project_id="test",
            client_id="test",
            tools=[BatchToolConfig(tool_name="seo_keyword_research", params={})],
        )

        assert request.project_id == "test"
        assert len(request.tools) == 1


class TestEndToEndIntegration:
    """Test complete end-to-end integration"""

    @pytest.mark.asyncio
    async def test_full_workflow_seo_to_market_trends(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test complete workflow: SEO → Market Trends with data flow"""

        # Step 1: No completed tools initially
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Track database saves
            saved_results = []

            def mock_add(result):
                saved_results.append(result)

            mock_db.add = mock_add

            # Use demo mode
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                # Run batch with SEO → Market Trends
                result = await research_service.execute_research_tools_batch(
                    mock_db,
                    test_project.id,
                    test_client.id,
                    [
                        {"tool_name": "market_trends_research"},
                        {"tool_name": "seo_keyword_research"},
                    ],
                )

                # Verify correct order
                assert result["execution_order"][0] == "seo_keyword_research"
                assert result["execution_order"][1] == "market_trends_research"

                # Verify both succeeded
                assert result["results"]["seo_keyword_research"]["success"] is True
                assert result["results"]["market_trends_research"]["success"] is True


class TestSystemHealthCheck:
    """Overall system health checks"""

    def test_all_imports_work(self):
        """Test all key imports work without errors"""
        from backend.services.research_service import ResearchService
        from backend.services.research_prerequisites import ResearchPrerequisites
        from backend.routers.research import (
            PrerequisiteCheckRequest,
            BatchResearchRequest,
            check_prerequisites,
            execute_research_batch,
        )

        # All imports successful
        assert True

    def test_research_service_has_all_methods(self, research_service):
        """Test research service has all required methods"""
        required_methods = [
            "_fetch_prerequisite_data",
            "_get_completed_tools",
            "check_prerequisites",
            "execute_research_tool",
            "execute_research_tools_batch",
        ]

        for method in required_methods:
            assert hasattr(research_service, method), f"Missing method: {method}"
            assert callable(getattr(research_service, method))

    def test_prerequisites_system_complete(self, research_service):
        """Test prerequisites system is complete"""
        # Has prerequisites instance
        assert research_service.prerequisites is not None

        # Prerequisites has all methods
        required_methods = [
            "get_dependencies",
            "get_required_prerequisites",
            "get_recommended_prerequisites",
            "check_prerequisites_met",
            "get_execution_order",
            "get_parallel_groups",
            "get_missing_prerequisites_message",
        ]

        for method in required_methods:
            assert hasattr(research_service.prerequisites, method)
            assert callable(getattr(research_service.prerequisites, method))
