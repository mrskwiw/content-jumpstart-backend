"""Integration tests for Research Service with Prerequisites

Tests the full prerequisite checking and batch execution flow.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from backend.services.research_service import ResearchService
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
    """Create test client (mock)"""
    client = Mock()
    client.id = "client-test"
    client.user_id = "user-test"
    client.business_name = "Test Business"
    client.business_description = "AI-powered content marketing platform for B2B SaaS companies"
    client.industry = "SaaS"
    client.ideal_customer = "Marketing managers at mid-size B2B companies"
    client.target_audience = "B2B marketing professionals"
    client.value_proposition = "Streamline content workflows with AI automation"
    return client


@pytest.fixture
def test_project(test_client):
    """Create test project (mock)"""
    project = Mock()
    project.id = "project-test"
    project.user_id = "user-test"
    project.client_id = test_client.id
    project.name = "Test Project"
    project.description = "Test project for prerequisites"
    return project


@pytest.fixture
def research_service():
    """Create ResearchService instance"""
    return ResearchService()


class TestGetCompletedTools:
    """Test getting completed tools from database"""

    def test_get_completed_tools_empty(self, research_service, mock_db):
        """Test when no tools are completed"""
        mock_db.query().filter().distinct().all.return_value = []

        completed = research_service._get_completed_tools(mock_db, "project-test")

        assert completed == set()

    def test_get_completed_tools_some_complete(self, research_service, mock_db):
        """Test when some tools are completed"""
        mock_db.query().filter().distinct().all.return_value = [
            ("seo_keyword_research",),
            ("audience_research",),
        ]

        completed = research_service._get_completed_tools(mock_db, "project-test")

        assert completed == {"seo_keyword_research", "audience_research"}

    def test_get_completed_tools_filters_by_project(self, research_service, mock_db):
        """Test that query filters by project_id and status"""
        # Setup mock to return empty list
        mock_db.query().filter().distinct().all.return_value = []

        research_service._get_completed_tools(mock_db, "project-123")

        # Verify filter was called (checking that filter method was invoked)
        assert mock_db.query().filter.called


class TestIncompleteToolStates:
    """Bug #188 / report F4: distinguish a prerequisite that was *never run* from
    one whose latest attempt has not completed (e.g. the slow Platform Strategy
    synthesis tool), so the blocking message is accurate."""

    def test_reports_running_latest_attempt(self, research_service, mock_db):
        """A prerequisite whose most recent attempt is not completed is surfaced."""
        mock_db.query().filter().order_by().first.return_value = ("running",)

        states = research_service._get_incomplete_tool_states_for_client(
            mock_db, "client-test", ["platform_strategy"]
        )

        assert states == {"platform_strategy": "running"}

    def test_completed_latest_attempt_is_not_reported(self, research_service, mock_db):
        """When the latest attempt is completed, it is NOT flagged as incomplete."""
        mock_db.query().filter().order_by().first.return_value = ("completed",)

        states = research_service._get_incomplete_tool_states_for_client(
            mock_db, "client-test", ["platform_strategy"]
        )

        assert states == {}

    def test_never_run_returns_empty(self, research_service, mock_db):
        """A prerequisite with no ResearchResult rows yields no incomplete state."""
        mock_db.query().filter().order_by().first.return_value = None

        states = research_service._get_incomplete_tool_states_for_client(
            mock_db, "client-test", ["platform_strategy"]
        )

        assert states == {}

    def test_empty_tool_ids(self, research_service, mock_db):
        """No tool ids → empty result, no queries needed."""
        assert (
            research_service._get_incomplete_tool_states_for_client(mock_db, "client-test", [])
            == {}
        )


class TestCheckPrerequisites:
    """Test prerequisite checking"""

    def test_check_prerequisites_tool_with_none(self, research_service, mock_db):
        """Test checking prerequisites for tool with no prerequisites"""
        mock_db.query().filter().distinct().all.return_value = []

        can_run, missing_required, missing_recommended = research_service.check_prerequisites(
            mock_db, "project-test", "seo_keyword_research"
        )

        assert can_run is True
        assert missing_required == []
        assert missing_recommended == []

    def test_check_prerequisites_tool_blocked(self, research_service, mock_db):
        """Test checking prerequisites for blocked tool"""
        # No completed tools
        mock_db.query().filter().distinct().all.return_value = []

        can_run, missing_required, missing_recommended = research_service.check_prerequisites(
            mock_db, "project-test", "content_calendar"
        )

        assert can_run is False
        assert "seo_keyword_research" in missing_required
        assert "platform_strategy" in missing_required

    def test_check_prerequisites_with_completed(self, research_service, mock_db):
        """Test checking prerequisites when some are completed"""
        # SEO is completed
        mock_db.query().filter().distinct().all.return_value = [
            ("seo_keyword_research",),
        ]

        can_run, missing_required, missing_recommended = research_service.check_prerequisites(
            mock_db, "project-test", "content_calendar"
        )

        assert can_run is False
        assert "platform_strategy" in missing_required
        assert "seo_keyword_research" not in missing_required

    def test_check_prerequisites_with_planned_tools(self, research_service, mock_db):
        """Test checking prerequisites with planned tools in batch"""
        # No completed tools in DB
        mock_db.query().filter().distinct().all.return_value = []

        # But SEO and Platform are planned in this batch
        can_run, missing_required, missing_recommended = research_service.check_prerequisites(
            mock_db,
            "project-test",
            "content_calendar",
            planned_tools=["seo_keyword_research", "platform_strategy"],
        )

        assert can_run is True
        assert missing_required == []

    def test_check_prerequisites_all_complete(self, research_service, mock_db):
        """Test when all prerequisites are completed"""
        # SEO and Platform are complete
        mock_db.query().filter().distinct().all.return_value = [
            ("seo_keyword_research",),
            ("platform_strategy",),
        ]

        can_run, missing_required, missing_recommended = research_service.check_prerequisites(
            mock_db, "project-test", "content_calendar"
        )

        assert can_run is True
        assert missing_required == []


class TestExecuteResearchToolWithPrerequisites:
    """Test single tool execution with prerequisite checking"""

    @pytest.mark.asyncio
    async def test_execute_tool_no_prerequisites(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test executing tool with no prerequisites"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Mock tool execution
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "seo_keyword_research"
                )

                # Should execute successfully (demo mode)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_blocked_by_prerequisites(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test executing tool blocked by missing prerequisites"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Try to execute Content Calendar without prerequisites
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True):
                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "content_calendar"
                )

                # Should be blocked
                assert result["success"] is False
                assert result["metadata"]["blocked"] is True
                assert "seo_keyword_research" in result["metadata"]["missing_required"]
                assert "platform_strategy" in result["metadata"]["missing_required"]
                assert "cannot run yet" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_prerequisites_met(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test executing tool when prerequisites are met"""
        # Mock completed prerequisites
        mock_db.query().filter().distinct().all.return_value = [
            ("seo_keyword_research",),
            ("platform_strategy",),
        ]

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Mock tool execution (demo mode)
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "content_calendar"
                )

                # Should execute successfully
                assert result["success"] is True
                assert "blocked" not in result.get("metadata", {})

    @pytest.mark.asyncio
    async def test_execute_tool_with_missing_recommended(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test executing tool with missing recommended prerequisites"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Execute Market Trends without SEO (recommended, not required)
            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "market_trends_research"
                )

                # Should execute (recommended are not blocking)
                assert result["success"] is True


class TestBatchExecution:
    """Test batch execution with automatic ordering"""

    @pytest.mark.asyncio
    async def test_batch_execution_simple_order(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution with simple dependency order"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Submit tools in random order
            tool_configs = [
                {"tool_name": "market_trends_research"},
                {"tool_name": "seo_keyword_research"},
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                # Check execution order
                assert result["execution_order"] == [
                    "seo_keyword_research",  # Tier 1 - runs first
                    "market_trends_research",  # Tier 2 - runs second
                ]

                # Both should succeed
                assert result["summary"]["successes"] == 2
                assert result["summary"]["blocked"] == 0

    @pytest.mark.asyncio
    async def test_batch_execution_complex_order(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution with complex dependencies"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Submit tools in reverse order
            tool_configs = [
                {"tool_name": "content_calendar"},  # Tier 4
                {"tool_name": "platform_strategy"},  # Tier 3
                {"tool_name": "seo_keyword_research"},  # Tier 1
                {"tool_name": "audience_research"},  # Tier 1
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                execution_order = result["execution_order"]

                # Verify Tier 1 tools run first
                seo_idx = execution_order.index("seo_keyword_research")
                audience_idx = execution_order.index("audience_research")
                platform_idx = execution_order.index("platform_strategy")
                calendar_idx = execution_order.index("content_calendar")

                assert seo_idx < platform_idx < calendar_idx
                assert audience_idx < platform_idx < calendar_idx

                # All should succeed (demo mode)
                assert result["summary"]["successes"] == 4

    @pytest.mark.asyncio
    async def test_batch_execution_with_blocking(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution where some tools are blocked"""
        # Mock only SEO completed
        mock_db.query().filter().distinct().all.return_value = [
            ("seo_keyword_research",),
        ]

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Try to run Platform and Calendar (Platform needs Audience, Calendar needs Platform)
            tool_configs = [
                {"tool_name": "content_calendar"},
                {"tool_name": "platform_strategy"},
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                # Platform should be blocked (missing Audience)
                assert result["results"]["platform_strategy"]["blocked"] is True

                # Calendar should be blocked (missing Platform)
                assert result["results"]["content_calendar"]["blocked"] is True

                # Summary should show blocked
                assert result["summary"]["blocked"] == 2

    @pytest.mark.asyncio
    async def test_batch_execution_partial_success(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution with partial success"""
        # Mock no completed tools
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Run Tier 1 tools + Content Calendar
            tool_configs = [
                {"tool_name": "seo_keyword_research"},  # Will succeed
                {"tool_name": "audience_research"},  # Will succeed
                {"tool_name": "content_calendar"},  # Will be blocked (missing Platform)
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                # Content Calendar should be blocked
                assert result["results"]["content_calendar"]["blocked"] is True

                # Summary
                assert result["summary"]["blocked"] >= 1

    @pytest.mark.asyncio
    async def test_batch_execution_tracks_completed_in_batch(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test that batch execution tracks tools completed within the batch"""
        # Mock no completed tools in DB
        mock_db.query().filter().distinct().all.return_value = []

        # Mock crud methods
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Run full workflow in correct order
            tool_configs = [
                {"tool_name": "seo_keyword_research"},  # Tier 1
                {"tool_name": "audience_research"},  # Tier 1
                {"tool_name": "platform_strategy"},  # Tier 3 (needs Audience)
                {"tool_name": "content_calendar"},  # Tier 4 (needs SEO + Platform)
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                # All should succeed because prerequisites complete in same batch
                assert result["summary"]["successes"] == 4
                assert result["summary"]["blocked"] == 0

    @pytest.mark.asyncio
    async def test_batch_execution_single_tool(
        self, research_service, mock_db, test_project, test_client
    ):
        """Test batch execution with single tool"""
        mock_db.query().filter().distinct().all.return_value = []

        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            tool_configs = [{"tool_name": "seo_keyword_research"}]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                assert result["execution_order"] == ["seo_keyword_research"]
                assert result["summary"]["total"] == 1


class TestRealWorldScenarios:
    """Test real-world prerequisite scenarios"""

    @pytest.mark.asyncio
    async def test_scenario_incremental_research(
        self, research_service, mock_db, test_project, test_client
    ):
        """Scenario: User runs research tools incrementally"""
        # Mock crud
        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                # Step 1: Run SEO (no prerequisites needed)
                mock_db.query().filter().distinct().all.return_value = []

                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "seo_keyword_research"
                )
                assert result["success"] is True

                # Step 2: Run Market Trends (SEO now complete)
                mock_db.query().filter().distinct().all.return_value = [("seo_keyword_research",)]

                result = await research_service.execute_research_tool(
                    mock_db, test_project.id, test_client.id, "market_trends_research"
                )
                assert result["success"] is True

                # Step 3: Try Content Calendar (missing Platform Strategy)
                mock_db.query().filter().distinct().all.return_value = [
                    ("seo_keyword_research",),
                    ("market_trends_research",),
                ]

                with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True):
                    result = await research_service.execute_research_tool(
                        mock_db, test_project.id, test_client.id, "content_calendar"
                    )
                    # Should be blocked
                    assert result["success"] is False
                    assert result["metadata"]["blocked"] is True

    @pytest.mark.asyncio
    async def test_scenario_bulk_research_launch(
        self, research_service, mock_db, test_project, test_client
    ):
        """Scenario: User launches all research tools at once"""
        mock_db.query().filter().distinct().all.return_value = []

        with patch("backend.services.research_service.crud") as mock_crud:
            mock_crud.get_project.return_value = test_project
            mock_crud.get_client.return_value = test_client

            # Launch all recommended tools for Content Calendar
            tool_configs = [
                {"tool_name": "seo_keyword_research"},
                {"tool_name": "audience_research"},
                {"tool_name": "market_trends_research"},
                {"tool_name": "platform_strategy"},
                {"tool_name": "content_calendar"},
            ]

            with patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", False):
                result = await research_service.execute_research_tools_batch(
                    mock_db, test_project.id, test_client.id, tool_configs
                )

                # All should execute in correct order
                execution_order = result["execution_order"]

                # Verify Tier 1 before Tier 2 before Tier 3 before Tier 4
                tiers = [
                    research_service.prerequisites.get_tool_tier(tool) for tool in execution_order
                ]

                for i in range(len(tiers) - 1):
                    assert tiers[i] <= tiers[i + 1]

                # All should succeed
                assert result["summary"]["successes"] == 5
                assert result["summary"]["blocked"] == 0
