"""COLLAB-01 / GAP-UI-03 — post approval gate (submit / approve / reject, role-gated)."""

import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Post, Run, TeamMember, User
from backend.models.team import ROLE_EDITOR, ROLE_VIEWER
from backend.schemas.client import ClientCreate
from backend.schemas.project import ProjectCreate
from backend.services import crud, team_service
from backend.utils.auth import create_access_token, get_password_hash


def _mk_user(db, uid, email):
    u = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash("Password123!"),  # pragma: allowlist secret
        full_name=email,
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _add(db, team_id, user, role):
    db.add(TeamMember(team_id=team_id, user_id=user.id, role=role))
    db.commit()


def _mk_post(db, owner):
    client = crud.create_client(
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
    project = crud.create_project(
        db, ProjectCreate(name="Proj", client_id=client.id, num_posts=30), user_id=owner.id
    )
    run = Run(id=f"run-{uuid.uuid4().hex[:8]}", project_id=project.id, status="completed")
    db.add(run)
    db.commit()
    post = Post(
        id=f"post-{uuid.uuid4().hex[:8]}",
        project_id=project.id,
        run_id=run.id,
        content="A draft to approve.",
        status="approved",
    )
    db.add(post)
    db.commit()
    return post


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': uid})}"}


def test_submit_approve_flow_and_role_gates(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "ap-o", "apo@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    editor = _mk_user(db_session, "ap-e", "ape@example.com")
    _add(db_session, team.id, editor, ROLE_EDITOR)
    viewer = _mk_user(db_session, "ap-v", "apv@example.com")
    _add(db_session, team.id, viewer, ROLE_VIEWER)
    outsider = _mk_user(db_session, "ap-x", "apx@example.com")
    team_service.ensure_personal_team(db_session, outsider)
    post = _mk_post(db_session, owner)

    # No approval yet → GET returns null (any member).
    r = client.get(f"/api/posts/{post.id}/approval", headers=_hdr(viewer.id))
    assert r.status_code == 200 and r.json() is None

    # A viewer can't submit (write-gated); an outsider can't either.
    assert (
        client.post(f"/api/posts/{post.id}/approval/submit", headers=_hdr(viewer.id)).status_code
        == 403
    )
    assert (
        client.post(f"/api/posts/{post.id}/approval/submit", headers=_hdr(outsider.id)).status_code
        == 403
    )
    # An editor submits it for review.
    r = client.post(f"/api/posts/{post.id}/approval/submit", headers=_hdr(editor.id))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending" and r.json()["submitted_by_user_id"] == editor.id

    # A non-manager (editor) can't approve.
    assert (
        client.post(
            f"/api/posts/{post.id}/approval/approve", json={}, headers=_hdr(editor.id)
        ).status_code
        == 403
    )
    # The owner (manager) approves.
    r = client.post(f"/api/posts/{post.id}/approval/approve", json={}, headers=_hdr(owner.id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved" and body["decided_by_user_id"] == owner.id

    # Approving again (no longer pending) → 400.
    assert (
        client.post(
            f"/api/posts/{post.id}/approval/approve", json={}, headers=_hdr(owner.id)
        ).status_code
        == 400
    )


def test_reject_with_note_and_resubmit(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "ap-ro", "apro@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    editor = _mk_user(db_session, "ap-re", "apre@example.com")
    _add(db_session, team.id, editor, ROLE_EDITOR)
    post = _mk_post(db_session, owner)

    client.post(f"/api/posts/{post.id}/approval/submit", headers=_hdr(editor.id))
    # Owner rejects with a note.
    r = client.post(
        f"/api/posts/{post.id}/approval/reject",
        json={"note": "needs a stronger CTA"},
        headers=_hdr(owner.id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected" and r.json()["note"] == "needs a stronger CTA"

    # The editor resubmits → back to pending, decision cleared.
    r = client.post(f"/api/posts/{post.id}/approval/submit", headers=_hdr(editor.id))
    assert r.status_code == 200
    assert r.json()["status"] == "pending" and r.json()["decided_by_user_id"] is None


def test_approval_cascades_with_post_delete(db_session):
    from backend.models import PostApproval

    owner = _mk_user(db_session, "ap-c", "apc@example.com")
    team_service.ensure_personal_team(db_session, owner)
    post = _mk_post(db_session, owner)
    from backend.services import approval_service

    approval_service.submit_for_approval(db_session, post.id, owner.id)
    assert db_session.query(PostApproval).filter_by(post_id=post.id).count() == 1
    # Deleting the project cascades posts → their approval records.
    assert crud.delete_project(db_session, post.project_id) is True
    assert db_session.query(PostApproval).filter_by(post_id=post.id).count() == 0
