"""
Integration tests for the research prerequisites system.

Covers:
- POST /api/research/execution-order: topological ordering, dependency maps,
  parallel groups, auth enforcement, edge cases.
- POST /api/research/run: unknown tool rejection, auth enforcement, schema
  coercion of empty lists (must not 422), and prerequisite blocking when a
  required predecessor has never been executed for the client.

All tests that touch /api/research/run use monkeypatch to avoid making real
Anthropic API calls.  The execution-order tests are computation-only and need
no external services.
"""

import pytest
from fastapi.testclient import TestClient

from backend.models import ResearchResult
from backend.services import crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXECUTION_ORDER_URL = "/api/research/execution-order"
_RUN_URL = "/api/research/run"


def _order_index(execution_order: list, tool: str) -> int:
    """Return the position of *tool* in *execution_order*, raising if absent."""
    return execution_order.index(tool)


def _tools_in_parallel_groups(parallel_groups: list) -> set:
    """Flatten parallel_groups into a single set of tool names."""
    return {tool for group in parallel_groups for tool in group}


# ---------------------------------------------------------------------------
# POST /api/research/execution-order
# ---------------------------------------------------------------------------


class TestExecutionOrderSingleTool:
    """Test #1 — single tool with no dependencies."""

    def test_execution_order_single_tool(self, client, test_user_headers):
        """Single tool batch: order is the tool itself, count is 1."""
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": ["seo_keyword_research"], "project_id": None, "client_id": None},
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["execution_order"] == ["seo_keyword_research"]
        assert data["tool_count"] == 1
        # Single tool with no deps lives alone in one parallel group
        assert len(data["parallel_groups"]) == 1
        assert data["parallel_groups"][0] == ["seo_keyword_research"]


class TestExecutionOrderDependencyChain:
    """Test #2 — three-tool chain: determine_competitors → competitive_analysis → content_gap_analysis."""

    def test_execution_order_dependency_chain(self, client, test_user_headers):
        """
        competitive_analysis REQUIRES determine_competitors (REQUIRED edge).
        content_gap_analysis REQUIRES competitive_analysis (REQUIRED edge).
        So the topological order must honour: det_comp < comp_anal < gap_anal.
        """
        tools = [
            "determine_competitors",
            "competitive_analysis",
            "content_gap_analysis",
        ]
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": tools, "project_id": None, "client_id": None},
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        order = data["execution_order"]

        # All three must appear
        assert set(order) == set(tools)
        assert data["tool_count"] == 3

        det_idx = _order_index(order, "determine_competitors")
        comp_idx = _order_index(order, "competitive_analysis")
        gap_idx = _order_index(order, "content_gap_analysis")

        # Strict ordering requirements from the REQUIRED edges
        assert det_idx < comp_idx, "determine_competitors must precede competitive_analysis"
        assert comp_idx < gap_idx, "competitive_analysis must precede content_gap_analysis"

        # parallel_groups must account for all tools
        assert _tools_in_parallel_groups(data["parallel_groups"]) == set(tools)

        # Each of the three tools has at least one REQUIRED predecessor in the batch,
        # so they must occupy at least three sequential groups (no two can run in parallel).
        assert len(data["parallel_groups"]) == 3


class TestExecutionOrderIndependentToolsInSameGroup:
    """Test #3 — three Tier-1 tools with no inter-dependencies share one parallel group."""

    def test_execution_order_independent_tools_in_same_group(self, client, test_user_headers):
        """
        brand_archetype, seo_keyword_research, and audience_research are all
        Tier-1 tools with no REQUIRED prerequisites in the registry.
        They must all land in parallel_groups[0].
        """
        tools = ["brand_archetype", "seo_keyword_research", "audience_research"]
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": tools, "project_id": None, "client_id": None},
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        order = data["execution_order"]

        assert set(order) == set(tools)
        assert data["tool_count"] == 3

        # All three are independent — exactly one parallel group
        assert (
            len(data["parallel_groups"]) == 1
        ), "Three independent Tier-1 tools must occupy a single parallel group"
        assert set(data["parallel_groups"][0]) == set(tools)


class TestExecutionOrderDependencyMap:
    """Test #4 — dependency_map reflects in-batch REQUIRED edges."""

    def test_execution_order_competitive_analysis_requires_determine_competitors(
        self, client, test_user_headers
    ):
        """
        When both tools are in the batch, competitive_analysis.dependency_map
        must list determine_competitors as a REQUIRED predecessor.
        """
        tools = ["determine_competitors", "competitive_analysis"]
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": tools, "project_id": None, "client_id": None},
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        dep_map = data["dependency_map"]

        # determine_competitors has no in-batch prerequisites
        assert dep_map["determine_competitors"] == []

        # competitive_analysis must list determine_competitors as a dependency
        assert "determine_competitors" in dep_map["competitive_analysis"], (
            "dependency_map must record the REQUIRED edge "
            "competitive_analysis → determine_competitors"
        )


class TestExecutionOrderOutOfBatchDepNotInMap:
    """Test #5 — prerequisite absent from batch is excluded from dependency_map."""

    def test_execution_order_out_of_batch_dep_not_in_map(self, client, test_user_headers):
        """
        When competitive_analysis is run alone (determine_competitors absent),
        its dependency_map entry must be an empty list — the backend will read
        the completed result from the DB rather than blocking the batch.
        """
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={
                "tool_names": ["competitive_analysis"],
                "project_id": None,
                "client_id": None,
            },
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # determine_competitors is NOT in the batch so must be absent from the map
        assert (
            data["dependency_map"]["competitive_analysis"] == []
        ), "Out-of-batch prerequisites must not appear in dependency_map"


class TestExecutionOrderEmptyList:
    """Test #6 — empty tool_names list is valid and returns empty structures."""

    def test_execution_order_empty_list(self, client, test_user_headers):
        """Empty batch: 200 with zero tools and empty structures."""
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": [], "project_id": None, "client_id": None},
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["execution_order"] == []
        assert data["tool_count"] == 0
        assert data["parallel_groups"] == []
        assert data["dependency_map"] == {}


class TestExecutionOrderReservedParams:
    """Test #7 — project_id and client_id are accepted without triggering 422."""

    def test_execution_order_accepts_project_client_id_reserved(self, client, test_user_headers):
        """
        project_id and client_id are reserved for future use; passing them must
        not cause a 422 Unprocessable Entity — they should be silently ignored.
        """
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={
                "tool_names": ["seo_keyword_research"],
                "project_id": "proj-some-future-id",
                "client_id": "client-some-future-id",
            },
            headers=test_user_headers,
        )

        assert (
            response.status_code == 200
        ), f"Reserved params must not cause 422; got {response.status_code}: {response.text}"
        data = response.json()
        assert data["tool_count"] == 1


class TestExecutionOrderRequiresAuth:
    """Test #8 — unauthenticated requests are rejected."""

    def test_execution_order_requires_auth(self, client):
        """No Authorization header → 401."""
        response = client.post(
            _EXECUTION_ORDER_URL,
            json={"tool_names": ["seo_keyword_research"]},
        )

        assert (
            response.status_code == 401
        ), f"Expected 401 for unauthenticated request, got {response.status_code}"


# ---------------------------------------------------------------------------
# POST /api/research/run — validation tests (no real API calls)
# ---------------------------------------------------------------------------


class TestRunUnknownTool:
    """Test #9 — unknown tool names are rejected."""

    def test_run_unknown_tool_returns_error(
        self, client, test_user_headers, test_project, test_client
    ):
        """
        A tool name that does not exist in RESEARCH_TOOLS must not return 200.
        The router checks the tool catalogue and raises 404.
        """
        response = client.post(
            _RUN_URL,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "nonexistent_tool_xyz",
                "params": {},
            },
            headers=test_user_headers,
        )

        assert response.status_code not in (
            200,
        ), f"Unknown tool must not return 200; got {response.status_code}"
        # The router returns 404 for an unknown tool name
        assert response.status_code in (
            404,
            422,
        ), f"Expected 404 or 422 for unknown tool, got {response.status_code}: {response.text}"


class TestRunRequiresAuth:
    """Test #10 — run endpoint requires authentication."""

    def test_run_requires_auth(self, client, test_project, test_client):
        """No Authorization header → 401."""
        response = client.post(
            _RUN_URL,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "seo_keyword_research",
                "params": {},
            },
        )

        assert (
            response.status_code == 401
        ), f"Expected 401 for unauthenticated request, got {response.status_code}"


# ---------------------------------------------------------------------------
# POST /api/research/run — schema coercion tests (monkeypatched execution)
# ---------------------------------------------------------------------------


class TestSchemaCoercion:
    """Tests #11-12 — empty list params are coerced to None and must not raise 422."""

    def test_seo_run_empty_main_topics_not_422(
        self,
        client,
        test_user_headers,
        test_project,
        test_client,
        monkeypatch,
    ):
        """
        SEOKeywordParams.validate_topics coerces [] → None (auto-generate mode).
        Passing an empty main_topics list must NOT return 422.
        The call may fail at tool execution (e.g. credit deduction, DB write,
        or the monkeypatched service), but the schema layer must pass cleanly.
        """

        async def mock_execute(*args, **kwargs):
            return {"success": True, "outputs": {}, "data": {}, "metadata": {}}

        monkeypatch.setattr(
            "backend.services.research_service.ResearchService.execute_research_tool",
            mock_execute,
        )

        response = client.post(
            _RUN_URL,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "seo_keyword_research",
                "params": {"main_topics": []},
            },
            headers=test_user_headers,
        )

        assert response.status_code != 422, (
            "Empty main_topics list must be coerced to None by SEOKeywordParams "
            f"and must not produce a 422; got {response.status_code}: {response.text}"
        )

    def test_competitive_analysis_empty_competitors_not_422(
        self,
        client,
        test_user_headers,
        test_project,
        test_client,
        monkeypatch,
    ):
        """
        CompetitiveAnalysisParams.validate_competitors coerces [] → None
        (auto-populate from client profile).  Passing an empty competitors list
        must NOT return 422.
        """

        async def mock_execute(*args, **kwargs):
            return {"success": True, "outputs": {}, "data": {}, "metadata": {}}

        monkeypatch.setattr(
            "backend.services.research_service.ResearchService.execute_research_tool",
            mock_execute,
        )

        response = client.post(
            _RUN_URL,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "competitive_analysis",
                "params": {"competitors": []},
            },
            headers=test_user_headers,
        )

        assert response.status_code != 422, (
            "Empty competitors list must be coerced to None by CompetitiveAnalysisParams "
            f"and must not produce a 422; got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# POST /api/research/run — prerequisite enforcement test
# ---------------------------------------------------------------------------


class TestPrerequisiteEnforcement:
    """Test #13 — competitive_analysis is blocked without determine_competitors."""

    def test_competitive_analysis_blocked_without_determine_competitors(
        self,
        test_client,
        db_session,
    ):
        """
        competitive_analysis declares determine_competitors as a REQUIRED
        prerequisite.  check_client_prerequisites is tested directly at the
        service layer — no HTTP call, no Anthropic mock needed.

        The prerequisite check lives INSIDE execute_research_tool, so going
        through the HTTP endpoint and mocking execute_research_tool would
        bypass the check entirely.  Testing the service method directly is
        the correct isolation level for this logic.
        """
        from backend.services.research_service import research_service

        # Confirm no determine_competitors result exists for this client
        existing = (
            db_session.query(ResearchResult)
            .filter(
                ResearchResult.client_id == test_client.id,
                ResearchResult.tool_name == "determine_competitors",
                ResearchResult.status == "completed",
            )
            .first()
        )
        assert existing is None, (
            "Precondition failed: test client must not have a completed "
            "determine_competitors result"
        )

        can_run, missing_required, _ = research_service.check_client_prerequisites(
            db_session, test_client.id, "competitive_analysis"
        )

        assert not can_run, (
            "competitive_analysis must be blocked when determine_competitors "
            "has not been run for the client"
        )
        assert (
            "determine_competitors" in missing_required
        ), f"Expected 'determine_competitors' in missing_required, got: {missing_required}"

    # Keep a placeholder so the class has >1 method and the structure is clear
    def test_fulfilled_prerequisite_allows_run_check(
        self,
        test_user,
        test_client,
        db_session,
    ):
        """
        When determine_competitors IS completed for the client, competitive_analysis
        should report can_run=True from check_client_prerequisites.
        """
        import uuid
        from datetime import datetime
        from backend.services.research_service import research_service

        # Insert a completed determine_competitors result for this client
        result = ResearchResult(
            id=f"res-prereq-{uuid.uuid4().hex[:8]}",
            tool_name="determine_competitors",
            project_id=None,
            client_id=test_client.id,
            user_id=test_user.id,
            status="completed",
            data={"competitors": ["Acme Corp"]},
            created_at=datetime.utcnow(),
            is_deleted=False,
        )
        db_session.add(result)
        db_session.commit()

        can_run, missing_required, _ = research_service.check_client_prerequisites(
            db_session, test_client.id, "competitive_analysis"
        )

        assert can_run, (
            "competitive_analysis must be allowed when determine_competitors is completed. "
            f"Missing required: {missing_required}"
        )
        assert missing_required == [], f"No missing required deps expected, got: {missing_required}"
