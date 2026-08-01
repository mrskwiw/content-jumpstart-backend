"""COLLAB-01 / GAP-UI-03 — post comments (team review feedback)."""

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
        content="A draft post to review.",
        status="approved",
    )
    db.add(post)
    db.commit()
    return post


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': uid})}"}


def test_teammates_can_comment_outsider_cannot(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cm-o", "cmo@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    viewer = _mk_user(db_session, "cm-v", "cmv@example.com")
    _add(db_session, team.id, viewer, ROLE_VIEWER)
    outsider = _mk_user(db_session, "cm-x", "cmx@example.com")
    team_service.ensure_personal_team(db_session, outsider)

    post = _mk_post(db_session, owner)

    # A teammate (even a viewer — review feedback is read-level) can comment.
    r = client.post(
        f"/api/posts/{post.id}/comments", json={"body": "looks good"}, headers=_hdr(viewer.id)
    )
    assert r.status_code == 201, r.text
    # The owner can comment too.
    assert (
        client.post(
            f"/api/posts/{post.id}/comments", json={"body": "ship it"}, headers=_hdr(owner.id)
        ).status_code
        == 201
    )
    # An outsider (different team) cannot see or add comments.
    assert (
        client.get(f"/api/posts/{post.id}/comments", headers=_hdr(outsider.id)).status_code == 403
    )
    assert (
        client.post(
            f"/api/posts/{post.id}/comments", json={"body": "nope"}, headers=_hdr(outsider.id)
        ).status_code
        == 403
    )
    # Teammates see both comments in order.
    listed = client.get(f"/api/posts/{post.id}/comments", headers=_hdr(owner.id))
    assert listed.status_code == 200
    bodies = [c["body"] for c in listed.json()]
    assert bodies == ["looks good", "ship it"]


def test_comment_delete_permissions(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cm-do", "cmdo@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    editor = _mk_user(db_session, "cm-de", "cmde@example.com")
    _add(db_session, team.id, editor, ROLE_EDITOR)
    post = _mk_post(db_session, owner)

    # Editor comments.
    r = client.post(
        f"/api/posts/{post.id}/comments", json={"body": "editor note"}, headers=_hdr(editor.id)
    )
    comment_id = r.json()["id"]

    # A different non-manager member (another editor) cannot delete it.
    other = _mk_user(db_session, "cm-d2", "cmd2@example.com")
    _add(db_session, team.id, other, ROLE_EDITOR)
    assert client.delete(f"/api/comments/{comment_id}", headers=_hdr(other.id)).status_code == 403
    # The author can delete their own.
    assert client.delete(f"/api/comments/{comment_id}", headers=_hdr(editor.id)).status_code == 200

    # A manager (owner) can delete another member's comment.
    r = client.post(
        f"/api/posts/{post.id}/comments", json={"body": "editor note 2"}, headers=_hdr(editor.id)
    )
    cid2 = r.json()["id"]
    assert client.delete(f"/api/comments/{cid2}", headers=_hdr(owner.id)).status_code == 200


def test_deleting_project_cascades_comments(db_session):
    # A commented post/project must remain deletable — comments cascade with the post.
    from backend.models import Comment
    from backend.services import comment_service

    owner = _mk_user(db_session, "cm-c1", "cmc1@example.com")
    team_service.ensure_personal_team(db_session, owner)
    post = _mk_post(db_session, owner)
    comment_service.add_comment(db_session, post.id, owner.id, "review note")
    assert db_session.query(Comment).filter_by(post_id=post.id).count() == 1

    assert crud.delete_project(db_session, post.project_id) is True
    # The post's comments were removed by the ORM cascade (no FK integrity error).
    assert db_session.query(Comment).filter_by(post_id=post.id).count() == 0


def test_soft_deleted_post_not_commentable(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cm-sd", "cmsd@example.com")
    team_service.ensure_personal_team(db_session, owner)
    post = _mk_post(db_session, owner)
    post.is_deleted = True
    db_session.commit()

    # A soft-deleted post is treated as gone: cannot list or add comments.
    assert client.get(f"/api/posts/{post.id}/comments", headers=_hdr(owner.id)).status_code == 404
    assert (
        client.post(
            f"/api/posts/{post.id}/comments", json={"body": "x"}, headers=_hdr(owner.id)
        ).status_code
        == 404
    )


def test_comment_deletable_after_post_soft_deleted(db_session):
    # Cleanup must still work: the privacy flow soft-deletes posts but leaves comments;
    # the author/manager must be able to remove them (an outsider still cannot).
    from backend.services import comment_service

    client = TestClient(app)
    owner = _mk_user(db_session, "cm-cl", "cmcl@example.com")
    team = team_service.ensure_personal_team(db_session, owner)
    editor = _mk_user(db_session, "cm-cle", "cmcle@example.com")
    _add(db_session, team.id, editor, ROLE_EDITOR)
    post = _mk_post(db_session, owner)
    c1 = comment_service.add_comment(db_session, post.id, editor.id, "n1")
    c2 = comment_service.add_comment(db_session, post.id, editor.id, "n2")
    post.is_deleted = True
    db_session.commit()

    # An outsider still cannot delete a comment on the (soft-deleted) post.
    outsider = _mk_user(db_session, "cm-clx", "cmclx@example.com")
    team_service.ensure_personal_team(db_session, outsider)
    assert client.delete(f"/api/comments/{c1.id}", headers=_hdr(outsider.id)).status_code == 403
    # The author can clean up their comment even though the post is soft-deleted.
    assert client.delete(f"/api/comments/{c1.id}", headers=_hdr(editor.id)).status_code == 200
    # A team manager (owner) can clean up the other one.
    assert client.delete(f"/api/comments/{c2.id}", headers=_hdr(owner.id)).status_code == 200


def test_comment_body_validation_and_missing_post(db_session):
    client = TestClient(app)
    owner = _mk_user(db_session, "cm-vo", "cmvo@example.com")
    team_service.ensure_personal_team(db_session, owner)
    post = _mk_post(db_session, owner)

    # Empty body rejected (422 validation).
    assert (
        client.post(
            f"/api/posts/{post.id}/comments", json={"body": ""}, headers=_hdr(owner.id)
        ).status_code
        == 422
    )
    # Unknown post → 404.
    assert (
        client.post(
            "/api/posts/post-missing/comments", json={"body": "x"}, headers=_hdr(owner.id)
        ).status_code
        == 404
    )
