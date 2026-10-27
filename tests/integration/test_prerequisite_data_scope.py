"""BUGS #259: prerequisite DATA must be loaded with the same scope prerequisites are
VALIDATED with — the client, not the project.

`execute_research_tool` validates prerequisites client-wide (any completed result for the
client, in any project, counts), but `_fetch_prerequisite_data` loaded the data by
`project_id`. A prerequisite completed in another project of the same client — e.g. the
wizard's project, while the Research Library runs in the client's research project —
passed validation but injected nothing, so the dependent ran on incomplete inputs and
still reported success.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from backend.models import Client, Project, ResearchResult, User
from backend.services.research_service import ResearchService
from backend.utils.auth import get_password_hash


@pytest.fixture
def world(db_session: Session):
    """Client A with a wizard project and a research project; unrelated client B."""
    user = User(
        id="user-259",
        email="u259@example.com",
        hashed_password=get_password_hash("pw-259-test"),
        full_name="U259",
        is_active=True,
    )
    db_session.add(user)
    clients = {
        key: Client(id=f"client-259-{key}", user_id=user.id, name=f"Client {key}")
        for key in ("a", "b")
    }
    db_session.add_all(clients.values())
    projects = {
        key: Project(
            id=f"proj-259-{key}",
            user_id=user.id,
            client_id=clients[client_key].id,
            name=f"Project {key}",
            templates=["1"],
            template_quantities={"1": 1},
            num_posts=1,
            status="active",
        )
        for key, client_key in (("wizard", "a"), ("research", "a"), ("other", "b"))
    }
    db_session.add_all(projects.values())
    db_session.commit()
    return {"user": user, "clients": clients, "projects": projects}


def _seo_result(db: Session, world, *, client: str, project: str, keywords, when):
    db.add(
        ResearchResult(
            id=f"res-259-{client}-{project}-{keywords[0]}",
            user_id=world["user"].id,
            client_id=world["clients"][client].id,
            project_id=world["projects"][project].id,
            tool_name="seo_keyword_research",
            data={"primary_keywords": keywords},
            status="completed",
            created_at=when,
        )
    )
    db.commit()


def _fetch(db, world, project, client=None):
    kwargs = {"client_id": world["clients"][client].id} if client else {}
    return ResearchService()._fetch_prerequisite_data(
        db, world["projects"][project].id, "market_trends_research", **kwargs
    )


def test_prerequisite_from_another_project_of_the_same_client_is_loaded(db_session, world):
    _seo_result(
        db_session,
        world,
        client="a",
        project="wizard",
        keywords=["alpha"],
        when=datetime(2026, 10, 1),
    )
    data = _fetch(db_session, world, "research", client="a")
    assert data.get("seo_keywords") == ["alpha"]


def test_latest_result_for_the_client_wins_across_projects(db_session, world):
    _seo_result(
        db_session,
        world,
        client="a",
        project="wizard",
        keywords=["older"],
        when=datetime(2026, 10, 1),
    )
    _seo_result(
        db_session,
        world,
        client="a",
        project="research",
        keywords=["newer"],
        when=datetime(2026, 10, 20),
    )
    assert _fetch(db_session, world, "wizard", client="a").get("seo_keywords") == ["newer"]


def test_another_clients_results_never_leak(db_session, world):
    _seo_result(
        db_session,
        world,
        client="b",
        project="other",
        keywords=["leak"],
        when=datetime(2026, 10, 25),
    )
    assert "seo_keywords" not in _fetch(db_session, world, "research", client="a")


def test_without_client_id_the_lookup_stays_project_scoped(db_session, world):
    # Backward compatible for direct callers that pass only a project.
    _seo_result(
        db_session,
        world,
        client="a",
        project="wizard",
        keywords=["alpha"],
        when=datetime(2026, 10, 1),
    )
    assert "seo_keywords" not in _fetch(db_session, world, "research")


class _Stop(Exception):
    """Raised by the spy to halt execute_research_tool right after the fetch."""


@pytest.mark.asyncio
async def test_execute_research_tool_loads_prerequisite_data_client_wide():
    """The production caller must pass client_id — the scope it validated with."""
    service = ResearchService()
    project = Mock(platforms=[], user_id="user-1", client_id="client-a")
    client = Mock(business_description="", ideal_customer="")
    client.name = "Client"
    with (
        patch("backend.services.research_service.crud") as crud,
        patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True),
        patch("backend.services.research_prerequisites.get_system_prerequisites", return_value=[]),
        patch.object(service, "check_client_prerequisites", return_value=(True, [], [])),
        patch.object(service, "_prepare_inputs", return_value={}),
        patch.object(service, "_fetch_prerequisite_data", side_effect=_Stop) as fetch,
    ):
        crud.get_project.return_value = project
        crud.get_client.return_value = client
        with pytest.raises(_Stop):
            await service.execute_research_tool(
                Mock(), "proj-research", "client-a", "market_trends_research"
            )

    assert fetch.call_args.kwargs.get("client_id") == "client-a"


def test_soft_deleted_result_is_never_injected(db_session, world):
    # Codex review of cfb71f9: validation excludes soft-deleted results, so the data
    # load must too — a newer deleted row must not override the older active one.
    _seo_result(
        db_session,
        world,
        client="a",
        project="wizard",
        keywords=["active"],
        when=datetime(2026, 10, 1),
    )
    _seo_result(
        db_session,
        world,
        client="a",
        project="research",
        keywords=["deleted"],
        when=datetime(2026, 10, 20),
    )
    deleted = db_session.query(ResearchResult).filter_by(id="res-259-a-research-deleted").one()
    deleted.is_deleted = True
    db_session.commit()

    assert _fetch(db_session, world, "research", client="a").get("seo_keywords") == ["active"]
    assert "seo_keywords" not in _fetch(db_session, world, "research")  # project scope too


@pytest.mark.asyncio
async def test_execute_research_tool_rejects_a_project_of_another_client():
    # Codex review of cfb71f9: client-scoped data must never flow into a project that
    # belongs to a different client.
    service = ResearchService()
    project = Mock(platforms=[], user_id="user-1", client_id="client-a")
    client = Mock(business_description="", ideal_customer="")
    client.name = "Client B"
    with (
        patch("backend.services.research_service.crud") as crud,
        patch("backend.services.research_service.RESEARCH_TOOLS_AVAILABLE", True),
        patch.object(service, "_fetch_prerequisite_data") as fetch,
    ):
        crud.get_project.return_value = project
        crud.get_client.return_value = client
        result = await service.execute_research_tool(
            Mock(), "proj-of-a", "client-b", "market_trends_research"
        )

    assert result["success"] is False
    assert "does not belong" in result["error"]
    fetch.assert_not_called()


def _result(db: Session, world, *, rid, client, project, tool, data, when, deleted=False):
    db.add(
        ResearchResult(
            id=rid,
            user_id=world["user"].id,
            client_id=world["clients"][client].id,
            project_id=world["projects"][project].id,
            tool_name=tool,
            data=data,
            status="completed",
            created_at=when,
            is_deleted=deleted,
        )
    )
    db.commit()


def test_project_scoped_completed_tools_ignore_soft_deleted(db_session, world):
    # Codex review of a735ea6: the same soft-delete invariant at the project-scoped
    # prerequisite check — a deleted result must not satisfy a prerequisite.
    _result(
        db_session,
        world,
        rid="r-del",
        client="a",
        project="research",
        tool="seo_keyword_research",
        data={},
        when=datetime(2026, 10, 1),
        deleted=True,
    )
    _result(
        db_session,
        world,
        rid="r-live",
        client="a",
        project="research",
        tool="audience_research",
        data={},
        when=datetime(2026, 10, 1),
    )
    completed = ResearchService()._get_completed_tools(db_session, world["projects"]["research"].id)
    assert completed == {"audience_research"}


def test_avoid_platforms_ignore_a_soft_deleted_platform_strategy(db_session, world):
    # Codex review of a735ea6: content_gap_analysis gets avoid_platforms from the
    # latest platform_strategy — never from a deleted one.
    _result(
        db_session,
        world,
        rid="ps-live",
        client="a",
        project="wizard",
        tool="platform_strategy",
        data={"recommended_platform_mix": {"avoid_platforms": ["tiktok"]}},
        when=datetime(2026, 10, 1),
    )
    _result(
        db_session,
        world,
        rid="ps-del",
        client="a",
        project="research",
        tool="platform_strategy",
        data={"recommended_platform_mix": {"avoid_platforms": ["linkedin"]}},
        when=datetime(2026, 10, 20),
        deleted=True,
    )
    avoid = ResearchService()._latest_avoid_platforms(db_session, world["clients"]["a"].id)
    assert avoid == ["tiktok"]


def test_avoid_platforms_empty_without_a_strategy(db_session, world):
    assert ResearchService()._latest_avoid_platforms(db_session, world["clients"]["a"].id) == []
