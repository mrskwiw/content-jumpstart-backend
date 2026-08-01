"""COLLAB-01 — team-owned resources, roles, and management endpoints.

Covers the security core: a teammate can reach a colleague's resources, a member of
another team cannot, a viewer is read-only, list-scoping follows the team, and the
management endpoints enforce owner/admin. Also verifies the idempotent backfill.
"""

from fastapi.testclient import TestClient

from backend.main import app
from backend.middleware.authorization import (
    _check_ownership,
    filter_user_clients,
    filter_user_projects,
)
from backend.models import Client, TeamMember, User
from backend.models.team import ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER
from backend.schemas.project import ProjectCreate
from backend.schemas.client import ClientCreate
from backend.services import crud, team_service
from backend.utils.auth import create_access_token, get_password_hash


def _mk_user(db, uid, email, superuser=False):
    u = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash("Password123!"),  # pragma: allowlist secret
        full_name=email,
        is_active=True,
        is_superuser=superuser,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _add_to_team(db, team_id, user, role):
    db.add(TeamMember(team_id=team_id, user_id=user.id, role=role))
    db.commit()


def _mk_client(db, owner):
    return crud.create_client(
        db,
        ClientCreate(
            name=f"C-{owner.id}",
            email=f"c-{owner.id}@example.com",
            business_description="A sufficiently long business description for the client model.",
            ideal_customer="Customers",
            main_problem_solved="Problems",
        ),
        user_id=owner.id,
    )


def _mk_project(db, owner, client):
    return crud.create_project(
        db, ProjectCreate(name="Proj", client_id=client.id, num_posts=30), user_id=owner.id
    )


def _hdr(user_id):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user_id})}"}


# ── team creation stamps the owner's existing resources ─────────────────────────


def test_create_team_stamps_owner_resources(db_session):
    owner = _mk_user(db_session, "cb-owner", "cbowner@example.com")
    # A team-less client created while the owner was solo (team_id NULL).
    legacy = Client(id="client-legacy1", user_id=owner.id, team_id=None, name="Legacy")
    db_session.add(legacy)
    db_session.commit()

    team = team_service.create_team(db_session, owner, "Acme")
    m = team_service.get_membership(db_session, owner.id)
    assert m is not None and m.role == "owner" and m.team_id == team.id
    # The owner's pre-existing team-less client was moved into the new team.
    db_session.refresh(legacy)
    assert legacy.team_id == team.id
    # A user already on a team can't create another.
    import pytest

    with pytest.raises(team_service.TeamError):
        team_service.create_team(db_session, owner, "Other")


# ── object-level access (_check_ownership) ──────────────────────────────────────


def test_teammate_can_access_but_outsider_cannot(db_session):
    owner = _mk_user(db_session, "cb-a", "cba@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    teammate = _mk_user(db_session, "cb-c", "cbc@example.com")
    _add_to_team(db_session, team.id, teammate, ROLE_EDITOR)
    outsider = _mk_user(db_session, "cb-b", "cbb@example.com")
    team_service.ensure_personal_team(db_session, outsider)  # their own separate team

    client = _mk_client(db_session, owner)  # team_id = owner's team
    project = _mk_project(db_session, owner, client)
    assert project.team_id == team.id  # create-path stamped the team

    # Owner + teammate can access; outsider cannot.
    assert _check_ownership("Project", project, owner, db_session) is True
    assert _check_ownership("Project", project, teammate, db_session) is True
    assert _check_ownership("Project", project, outsider, db_session) is False
    assert _check_ownership("Client", client, teammate, db_session) is True
    assert _check_ownership("Client", client, outsider, db_session) is False


def test_viewer_is_read_only(db_session):
    owner = _mk_user(db_session, "cb-vo", "cbvo@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    viewer = _mk_user(db_session, "cb-v", "cbv@example.com")
    _add_to_team(db_session, team.id, viewer, ROLE_VIEWER)
    project = _mk_project(db_session, owner, _mk_client(db_session, owner))

    # Viewer can read but not write.
    assert _check_ownership("Project", project, viewer, db_session, is_write=False) is True
    assert _check_ownership("Project", project, viewer, db_session, is_write=True) is False
    # An editor can write.
    editor = _mk_user(db_session, "cb-e", "cbe@example.com")
    _add_to_team(db_session, team.id, editor, ROLE_EDITOR)
    assert _check_ownership("Project", project, editor, db_session, is_write=True) is True


def test_superuser_bypasses(db_session):
    owner = _mk_user(db_session, "cb-so", "cbso@example.com")
    team_service.ensure_personal_team(db_session, owner)
    project = _mk_project(db_session, owner, _mk_client(db_session, owner))
    su = _mk_user(db_session, "cb-su", "cbsu@example.com", superuser=True)
    assert _check_ownership("Project", project, su, db_session, is_write=True) is True


def test_legacy_resource_without_team_uses_creator_check(db_session):
    owner = _mk_user(db_session, "cb-lo", "cblo@example.com")
    other = _mk_user(db_session, "cb-lx", "cblx@example.com")
    legacy = Client(id="client-legacy2", user_id=owner.id, team_id=None, name="L")
    db_session.add(legacy)
    db_session.commit()
    # No team_id → falls back to creator ownership.
    assert _check_ownership("Client", legacy, owner, db_session) is True
    assert _check_ownership("Client", legacy, other, db_session) is False


# ── list scoping (filter_user_*) ────────────────────────────────────────────────


def test_list_scoping_follows_team(db_session):
    owner = _mk_user(db_session, "cb-lso", "cblso@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    teammate = _mk_user(db_session, "cb-lst", "cblst@example.com")
    _add_to_team(db_session, team.id, teammate, ROLE_ADMIN)
    outsider = _mk_user(db_session, "cb-lsx", "cblsx@example.com")
    team_service.ensure_personal_team(db_session, outsider)

    client = _mk_client(db_session, owner)
    project = _mk_project(db_session, owner, client)

    # Teammate's list includes the owner's project + client.
    assert project.id in {p.id for p in filter_user_projects(db_session, teammate).all()}
    assert client.id in {c.id for c in filter_user_clients(db_session, teammate).all()}
    # Outsider sees neither.
    assert project.id not in {p.id for p in filter_user_projects(db_session, outsider).all()}
    assert client.id not in {c.id for c in filter_user_clients(db_session, outsider).all()}


# ── management endpoints ─────────────────────────────────────────────────────────


def test_team_endpoints_flow(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cb-eo", "cbeo@example.com")
    team_service.ensure_personal_team(db_session, owner)
    member = _mk_user(db_session, "cb-em", "cbem@example.com")  # registered, no team yet

    # GET /me shows the owner alone (wrapped in {"team": ...}).
    r = client.get("/api/teams/me", headers=_hdr(owner.id))
    assert r.status_code == 200, r.text
    body = r.json()["team"]
    assert body["my_role"] == "owner" and len(body["members"]) == 1

    # Owner adds the member as editor.
    r = client.post(
        "/api/teams/members",
        json={"email": member.email, "role": "editor"},
        headers=_hdr(owner.id),
    )
    assert r.status_code == 201, r.text
    assert any(m["user_id"] == member.id and m["role"] == "editor" for m in r.json()["members"])

    # Owner changes their role to viewer.
    r = client.patch(
        f"/api/teams/members/{member.id}", json={"role": "viewer"}, headers=_hdr(owner.id)
    )
    assert r.status_code == 200
    assert any(m["user_id"] == member.id and m["role"] == "viewer" for m in r.json()["members"])

    # A viewer cannot manage members (add someone) → 403.
    stranger = _mk_user(db_session, "cb-str", "cbstr@example.com")
    r = client.post(
        "/api/teams/members",
        json={"email": stranger.email, "role": "editor"},
        headers=_hdr(member.id),
    )
    assert r.status_code == 403

    # Owner removes the member.
    r = client.delete(f"/api/teams/members/{member.id}", headers=_hdr(owner.id))
    assert r.status_code == 200
    assert team_service.get_membership(db_session, member.id) is None

    # The owner cannot leave their own team.
    r = client.delete(f"/api/teams/members/{owner.id}", headers=_hdr(owner.id))
    assert r.status_code == 400


def test_create_team_endpoint_and_solo_me(db_session):
    client = TestClient(app)
    user = _mk_user(db_session, "cb-solo", "cbsolo@example.com")
    # A solo (team-less) user: /me returns team: null (200, not 404).
    r = client.get("/api/teams/me", headers=_hdr(user.id))
    assert r.status_code == 200 and r.json()["team"] is None
    # Create a team → the caller becomes owner.
    r = client.post("/api/teams", json={"name": "Acme"}, headers=_hdr(user.id))
    assert r.status_code == 201, r.text
    assert r.json()["my_role"] == "owner"
    # /me now reflects the team.
    assert client.get("/api/teams/me", headers=_hdr(user.id)).json()["team"]["name"] == "Acme"
    # Creating a second team is rejected.
    assert (
        client.post("/api/teams", json={"name": "Other"}, headers=_hdr(user.id)).status_code == 400
    )


def test_solo_user_can_be_invited(db_session):
    # The finding-1 fix: a normal (solo) registered user CAN be added to a team.
    client = TestClient(app)
    owner = _mk_user(db_session, "cb-io", "cbio@example.com")
    team_service.ensure_personal_team(db_session, owner)
    invitee = _mk_user(db_session, "cb-inv", "cbinv@example.com")  # solo, invitable
    r = client.post(
        "/api/teams/members",
        json={"email": invitee.email, "role": "editor"},
        headers=_hdr(owner.id),
    )
    assert r.status_code == 201, r.text
    assert team_service.user_team_id(db_session, invitee.id) == team_service.user_team_id(
        db_session, owner.id
    )


def test_add_member_rejects_user_already_on_a_team(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cb-do", "cbdo@example.com")
    team_service.ensure_personal_team(db_session, owner)
    other_owner = _mk_user(db_session, "cb-doo", "cbdoo@example.com")
    team_service.ensure_personal_team(db_session, other_owner)  # already owns a team

    r = client.post(
        "/api/teams/members",
        json={"email": other_owner.email, "role": "editor"},
        headers=_hdr(owner.id),
    )
    assert r.status_code == 400
    assert "already belongs" in r.json()["detail"]
