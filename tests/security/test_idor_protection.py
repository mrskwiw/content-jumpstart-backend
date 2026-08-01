"""P0 Security Tests — IDOR Protection (OWASP A01:2021)

Tests for backend/middleware/authorization.py

Verifies that:
- Users can only access resources they own
- Superusers bypass ownership checks
- Resources without user_id fields are denied (fail-closed)
- Cross-user resource access raises 403
- Missing resources raise 404
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.middleware.authorization import (
    _check_ownership,
    filter_user_clients,
    filter_user_deliverables,
    filter_user_posts,
    filter_user_projects,
    filter_user_runs,
    verify_client_ownership,
    verify_deliverable_ownership,
    verify_post_ownership,
    verify_project_ownership,
    verify_run_ownership,
)


# NOTE: ownership enforcement is now UNCONDITIONAL in
# backend/middleware/authorization.py (`_check_ownership` always runs). The old
# `_ownership_enforcement_enabled()` feature flag was removed, so the autouse
# monkeypatch that used to force it on is gone — these tests exercise the
# always-on behavior directly.


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _user(id: str = "user-1", is_superuser: bool = False):
    u = MagicMock()
    u.id = id
    u.email = f"{id}@example.com"
    u.is_superuser = is_superuser
    return u


def _resource_with_owner(user_id: str):
    r = MagicMock()
    r.user_id = user_id
    # COLLAB-01: team_id=None → _check_ownership uses the legacy creator-based path,
    # which is exactly the owner-vs-non-owner behavior these unit tests assert. Team-
    # aware access is covered end-to-end in tests/integration/test_collab_teams.py.
    r.team_id = None
    return r


def _resource_no_user_id():
    r = MagicMock(spec=[])  # No attributes — simulates missing user_id
    return r


# ---------------------------------------------------------------------------
# _check_ownership — unit tests
# ---------------------------------------------------------------------------


class TestCheckOwnership:
    def test_owner_can_access_own_resource(self):
        user = _user("u1")
        resource = _resource_with_owner("u1")
        assert _check_ownership("Project", resource, user) is True

    def test_non_owner_denied(self):
        user = _user("u1")
        resource = _resource_with_owner("u2")
        assert _check_ownership("Project", resource, user) is False

    def test_superuser_bypasses_ownership(self):
        superuser = _user("admin", is_superuser=True)
        resource = _resource_with_owner("u2")  # owned by someone else
        assert _check_ownership("Project", resource, superuser) is True

    def test_missing_user_id_field_denied(self):
        """Fail-closed: resource without user_id must be denied."""
        user = _user("u1")
        resource = _resource_no_user_id()
        assert _check_ownership("Project", resource, user) is False

    def test_missing_user_id_superuser_still_allowed(self):
        """Superusers bypass even when user_id field is absent."""
        superuser = _user("admin", is_superuser=True)
        resource = _resource_no_user_id()
        assert _check_ownership("Project", resource, superuser) is True

    def test_different_resource_types_use_same_logic(self):
        """Ownership logic is resource-type-agnostic."""
        user = _user("u1")
        for rtype in ("Client", "Post", "Deliverable", "Run", "Brief"):
            owned = _resource_with_owner("u1")
            not_owned = _resource_with_owner("u2")
            assert _check_ownership(rtype, owned, user) is True
            assert _check_ownership(rtype, not_owned, user) is False


# ---------------------------------------------------------------------------
# verify_project_ownership — async integration-level
# ---------------------------------------------------------------------------


class TestVerifyProjectOwnership:
    # crud is imported locally inside each verify_* function as
    # `from backend.services import crud`, so we patch backend.services.crud.
    _PATCH = "backend.services.crud"

    @pytest.mark.asyncio
    async def test_returns_project_when_owner(self):
        user = _user("u1")
        project = _resource_with_owner("u1")
        project.id = "proj-1"

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_project.return_value = project
            result = await verify_project_ownership(
                project_id="proj-1",
                request=MagicMock(method="GET"),
                db=MagicMock(),
                current_user=user,
            )
        assert result is project

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        user = _user("u1")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_project.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_project_ownership(
                    project_id="nonexistent",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_wrong_user(self):
        """IDOR: user B cannot access user A's project."""
        attacker = _user("attacker")
        project = _resource_with_owner("victim")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_project.return_value = project
            with pytest.raises(HTTPException) as exc:
                await verify_project_ownership(
                    project_id="proj-victim",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=attacker,
                )
        assert exc.value.status_code == 403
        assert "Access denied" in exc.value.detail

    @pytest.mark.asyncio
    async def test_superuser_can_access_any_project(self):
        superuser = _user("admin", is_superuser=True)
        project = _resource_with_owner("some-other-user")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_project.return_value = project
            result = await verify_project_ownership(
                project_id="proj-1",
                request=MagicMock(method="GET"),
                db=MagicMock(),
                current_user=superuser,
            )
        assert result is project


# ---------------------------------------------------------------------------
# verify_client_ownership
# ---------------------------------------------------------------------------


class TestVerifyClientOwnership:
    _PATCH = "backend.services.crud"

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        user = _user("u1")
        with patch(self._PATCH) as mock_crud:
            mock_crud.get_client.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_client_ownership(
                    client_id="c-999",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_client(self):
        """IDOR: attacker cannot read victim's client record."""
        attacker = _user("attacker")
        client = _resource_with_owner("victim")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_client.return_value = client
            with pytest.raises(HTTPException) as exc:
                await verify_client_ownership(
                    client_id="c-victim",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=attacker,
                )
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# verify_post_ownership — indirect via project
# ---------------------------------------------------------------------------


class TestVerifyPostOwnership:
    _PATCH = "backend.services.crud"

    @pytest.mark.asyncio
    async def test_raises_404_when_post_not_found(self):
        user = _user("u1")
        with patch(self._PATCH) as mock_crud:
            mock_crud.get_post.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_post_ownership(
                    post_id="p-999",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_parent_project_missing(self):
        user = _user("u1")
        post = MagicMock()
        post.project_id = "proj-deleted"

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_post.return_value = post
            mock_crud.get_project.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_post_ownership(
                    post_id="p-1",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_project_owned_by_other(self):
        """IDOR: attacker cannot read posts from victim's project."""
        attacker = _user("attacker")
        post = MagicMock()
        post.project_id = "proj-victim"
        project = _resource_with_owner("victim")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_post.return_value = post
            mock_crud.get_project.return_value = project
            with pytest.raises(HTTPException) as exc:
                await verify_post_ownership(
                    post_id="p-victim-post",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=attacker,
                )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_post_for_owner(self):
        user = _user("u1")
        post = MagicMock()
        post.project_id = "proj-1"
        project = _resource_with_owner("u1")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_post.return_value = post
            mock_crud.get_project.return_value = project
            result = await verify_post_ownership(
                post_id="p-1", request=MagicMock(method="GET"), db=MagicMock(), current_user=user
            )
        assert result is post


# ---------------------------------------------------------------------------
# verify_deliverable_ownership
# ---------------------------------------------------------------------------


class TestVerifyDeliverableOwnership:
    _PATCH = "backend.services.crud"

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_deliverable(self):
        attacker = _user("attacker")
        deliverable = MagicMock()
        deliverable.project_id = "proj-victim"
        project = _resource_with_owner("victim")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_deliverable.return_value = deliverable
            mock_crud.get_project.return_value = project
            with pytest.raises(HTTPException) as exc:
                await verify_deliverable_ownership(
                    deliverable_id="d-victim",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=attacker,
                )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_raises_404_when_deliverable_missing(self):
        user = _user("u1")
        with patch(self._PATCH) as mock_crud:
            mock_crud.get_deliverable.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_deliverable_ownership(
                    deliverable_id="d-999",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# verify_run_ownership
# ---------------------------------------------------------------------------


class TestVerifyRunOwnership:
    _PATCH = "backend.services.crud"

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_run(self):
        attacker = _user("attacker")
        run = MagicMock()
        run.project_id = "proj-victim"
        project = _resource_with_owner("victim")

        with patch(self._PATCH) as mock_crud:
            mock_crud.get_run.return_value = run
            mock_crud.get_project.return_value = project
            with pytest.raises(HTTPException) as exc:
                await verify_run_ownership(
                    run_id="run-victim",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=attacker,
                )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_raises_404_when_run_missing(self):
        user = _user("u1")
        with patch(self._PATCH) as mock_crud:
            mock_crud.get_run.return_value = None
            with pytest.raises(HTTPException) as exc:
                await verify_run_ownership(
                    run_id="run-999",
                    request=MagicMock(method="GET"),
                    db=MagicMock(),
                    current_user=user,
                )
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# filter_user_* list operations
# ---------------------------------------------------------------------------


class TestFilterUserResources:
    """Verify list queries are scoped to the current user."""

    def _mock_db_with_model(self, model_cls, has_user_id: bool = True):
        """Return a mock db whose query().filter() chain is inspectable.

        NOTE: this no longer mutates ``model_cls.user_id`` — the real models already
        have the column, and permanently replacing it with a MagicMock leaked across
        tests (corrupting later real-DB suites). The mock db below is all that's needed.
        """
        db = MagicMock()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.join.return_value = query_mock
        return db, query_mock

    def test_filter_projects_superuser_gets_all(self):
        from backend.models import Project

        superuser = _user("admin", is_superuser=True)
        db, query_mock = self._mock_db_with_model(Project)
        filter_user_projects(db, superuser)
        # Superuser: query returned directly without filter()
        db.query.assert_called_once_with(Project)
        query_mock.filter.assert_not_called()

    def test_filter_clients_regular_user_filtered(self):
        from backend.models import Client

        user = _user("u1")
        db, query_mock = self._mock_db_with_model(Client)
        filter_user_clients(db, user)
        query_mock.filter.assert_called()

    def test_filter_projects_regular_user_filtered(self):
        from backend.models import Project

        user = _user("u1")
        db, query_mock = self._mock_db_with_model(Project)
        filter_user_projects(db, user)
        query_mock.filter.assert_called()

    def test_filter_posts_regular_user_filtered(self):
        from backend.models import Project

        user = _user("u1")
        db, query_mock = self._mock_db_with_model(Project)
        filter_user_posts(db, user)
        query_mock.filter.assert_called()

    def test_filter_runs_regular_user_filtered(self):
        from backend.models import Project

        user = _user("u1")
        db, query_mock = self._mock_db_with_model(Project)
        filter_user_runs(db, user)
        query_mock.filter.assert_called()

    def test_filter_deliverables_regular_user_filtered(self):
        from backend.models import Project

        user = _user("u1")
        db, query_mock = self._mock_db_with_model(Project)
        filter_user_deliverables(db, user)
        query_mock.filter.assert_called()
