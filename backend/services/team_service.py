"""Team membership + role operations (COLLAB-01).

The single place that resolves a user's team and role, mutates membership, and creates
teams (stamping the owner's existing team-less resources into the new team). Users are
solo (team-less) until they create or join a team. Access-control decisions in
``backend/middleware/authorization.py`` read from here.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models import Client, Project, Team, TeamMember, User
from backend.models.team import MANAGE_ROLES, ROLE_ADMIN, ROLE_OWNER, TEAM_ROLES, WRITE_ROLES


class TeamError(Exception):
    """A team operation was not permitted or was invalid (surfaced as 4xx)."""


# ── read side ───────────────────────────────────────────────────────────────────


def get_membership(db: Session, user_id: str) -> Optional[TeamMember]:
    return db.query(TeamMember).filter(TeamMember.user_id == user_id).first()


def user_team_id(db: Session, user_id: str) -> Optional[str]:
    m = get_membership(db, user_id)
    return m.team_id if m else None


def user_role(db: Session, user_id: str) -> Optional[str]:
    m = get_membership(db, user_id)
    return m.role if m else None


def can_write_resources(db: Session, user_id: str) -> bool:
    """Whether the user's role allows mutating team resources (not a viewer)."""
    return (user_role(db, user_id) or "") in WRITE_ROLES


def team_member_ids(db: Session, team_id: str) -> List[str]:
    return [m.user_id for m in db.query(TeamMember).filter(TeamMember.team_id == team_id).all()]


def list_members(db: Session, team_id: str) -> List[TeamMember]:
    return db.query(TeamMember).filter(TeamMember.team_id == team_id).all()


# ── team creation ───────────────────────────────────────────────────────────────


def _stamp_user_resources(db: Session, user_id: str, team_id: str) -> None:
    """Move a user's team-less clients/projects into ``team_id`` (their solo resources
    join the team on create/join). Caller commits + invalidates caches."""
    for model in (Client, Project):
        for row in db.query(model).filter(model.user_id == user_id, model.team_id.is_(None)).all():
            row.team_id = team_id


def _invalidate_resource_caches() -> None:
    """Drop the crud read-caches for clients/projects after re-homing team_id, so
    authorization no longer sees a stale ``team_id=NULL`` and deny teammates."""
    from backend.services.crud import invalidate_related_caches

    invalidate_related_caches("project", "projects", "client", "clients")


def create_team(db: Session, owner: User, name: str, *, commit: bool = True) -> Team:
    """Create a team owned by ``owner`` and move their team-less resources into it.

    A user belongs to at most one team, so this rejects an owner who already has a
    membership. Users are otherwise team-less (solo) — their resources use the legacy
    per-user path — until they create a team here or are invited to one.
    """
    if get_membership(db, owner.id) is not None:
        raise TeamError("you already belong to a team")
    team = Team(name=name, owner_user_id=owner.id)
    db.add(team)
    db.flush()  # assign team.id
    db.add(TeamMember(team_id=team.id, user_id=owner.id, role=ROLE_OWNER))
    _stamp_user_resources(db, owner.id, team.id)
    if commit:
        db.commit()
        _invalidate_resource_caches()
    return team


def ensure_personal_team(db: Session, user: User, *, commit: bool = True) -> Team:
    """Return the user's team, creating one (they're the owner) if none. Idempotent.

    A convenience primitive (used by tests and any caller that wants a guaranteed
    team). Registration deliberately does NOT call this — new users start solo so they
    remain invitable into someone else's team.
    """
    existing = get_membership(db, user.id)
    if existing is not None:
        team = db.query(Team).filter(Team.id == existing.team_id).first()
        assert team is not None  # membership implies a team
        return team
    return create_team(db, user, f"{(user.full_name or user.email)}'s Team", commit=commit)


# ── membership management ───────────────────────────────────────────────────────


def add_member(db: Session, team_id: str, target_user: User, role: str) -> TeamMember:
    """Add an existing user to a team with a role.

    Policy (BUGS.md Decision #213): an invitee's PRE-EXISTING solo resources are NOT
    auto-migrated into the team — that would be a non-consented ownership transfer of
    another user's private work by a manager. Their old solo clients/projects stay
    private (``team_id NULL`` → per-user path); only resources they create AFTER joining
    are team-owned. Moving prior work into the team is a future explicit, consented step.
    Raises if role invalid or the user already belongs to a team.
    """
    if role not in TEAM_ROLES or role == ROLE_OWNER:
        # owner is assigned only at team creation / transfer, never via add.
        raise TeamError(f"invalid role: {role!r}")
    if get_membership(db, target_user.id) is not None:
        raise TeamError("user already belongs to a team")
    member = TeamMember(team_id=team_id, user_id=target_user.id, role=role)
    db.add(member)
    db.commit()
    return member


def change_role(db: Session, team_id: str, target_user_id: str, new_role: str) -> TeamMember:
    """Change a member's role. The owner's role can't be changed here (use transfer)."""
    if new_role not in TEAM_ROLES or new_role == ROLE_OWNER:
        raise TeamError(f"invalid role: {new_role!r}")
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == target_user_id)
        .first()
    )
    if member is None:
        raise TeamError("not a member of this team")
    if member.role == ROLE_OWNER:
        raise TeamError("cannot change the owner's role")
    member.role = new_role
    db.commit()
    return member


def remove_member(db: Session, team_id: str, target_user_id: str) -> None:
    """Remove a member from a team. The owner cannot be removed."""
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == target_user_id)
        .first()
    )
    if member is None:
        raise TeamError("not a member of this team")
    if member.role == ROLE_OWNER:
        raise TeamError("cannot remove the team owner")
    db.delete(member)
    db.commit()


def is_manager(db: Session, user_id: str) -> bool:
    """Whether the user may manage members (owner/admin)."""
    return (user_role(db, user_id) or "") in MANAGE_ROLES


def is_owner(db: Session, user_id: str) -> bool:
    return user_role(db, user_id) == ROLE_OWNER


# ── team lifecycle ───────────────────────────────────────────────────────────────


def transfer_ownership(db: Session, team_id: str, current_owner_id: str, new_owner_id: str) -> None:
    """Hand ownership to another current member. The old owner becomes an admin.

    Lets an owner subsequently leave the team (owners can't be removed while owner).
    """
    if current_owner_id == new_owner_id:
        raise TeamError("you are already the owner")
    new_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == new_owner_id)
        .first()
    )
    if new_member is None:
        raise TeamError("the new owner must be a member of this team")
    old_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == current_owner_id)
        .first()
    )
    if old_member is None or old_member.role != ROLE_OWNER:
        raise TeamError("only the current owner can transfer ownership")
    old_member.role = ROLE_ADMIN
    new_member.role = ROLE_OWNER
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is not None:
        team.owner_user_id = new_owner_id
    db.commit()


def delete_team(db: Session, team_id: str) -> None:
    """Disband a team: revert its resources to solo (creator-owned) and drop all
    memberships + the team. Each member keeps the resources they created (via the
    per-user legacy path); resources they didn't create are no longer shared.

    Concurrency-safe against a create/join that races the teardown: if the final team
    delete fails on the FK because another request attached a new client/project/member
    to the team between the sweep and the commit, we roll back and re-sweep (bounded
    retry) so the newly-attached rows are re-homed too, rather than 500-ing. The FK
    keeps this fail-safe — a stray row can never orphan a deleted team."""
    import logging

    from sqlalchemy.exc import IntegrityError

    attempts = 3
    for attempt in range(attempts):
        for model in (Client, Project):
            for row in db.query(model).filter(model.team_id == team_id).all():
                row.team_id = None
        db.query(TeamMember).filter(TeamMember.team_id == team_id).delete()
        team = db.query(Team).filter(Team.id == team_id).first()
        if team is None:  # already gone → nothing to delete; treat as success
            db.commit()
            _invalidate_resource_caches()
            return
        db.delete(team)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # We already cleared every KNOWN reference (clients/projects → NULL, members
            # deleted), so a surviving IntegrityError is either the expected concurrent-
            # attachment race (retry re-homes it) or an UNEXPECTED integrity bug. Retry
            # a bounded number of times for the race; on the last attempt, re-raise the
            # ORIGINAL error so a persistent problem surfaces as a 500 (visible) rather
            # than being masked as a retryable client conflict. Never report success.
            if attempt == attempts - 1:
                logging.getLogger(__name__).error(
                    "delete_team failed after %d attempts (persistent integrity error?) " "team=%s",
                    attempts,
                    team_id,
                )
                raise
            continue
        _invalidate_resource_caches()  # only on a CONFIRMED successful teardown
        return


def adopt_resources(db: Session, user_id: str, team_id: str) -> int:
    """Move the CALLER's own team-less resources into their team (self-consented — the
    explicit counterpart to the no-auto-migrate-on-invite policy, Decision #213).
    Returns the number of resources moved."""
    moved = 0
    for model in (Client, Project):
        rows = db.query(model).filter(model.user_id == user_id, model.team_id.is_(None)).all()
        for row in rows:
            row.team_id = team_id
            moved += 1
    if moved:
        db.commit()
        _invalidate_resource_caches()
    return moved
