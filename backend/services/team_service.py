"""Team membership + role operations (COLLAB-01).

The single place that resolves a user's team and role, mutates membership, and creates
teams (stamping the owner's existing team-less resources into the new team). Users are
solo (team-less) until they create or join a team. Access-control decisions in
``backend/middleware/authorization.py`` read from here.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models import Client, Project, Team, TeamMember, User
from backend.models.team import MANAGE_ROLES, ROLE_OWNER, TEAM_ROLES, WRITE_ROLES


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


def _stamp_owner_resources(db: Session, owner_id: str, team_id: str) -> None:
    """Assign the owner's team-less clients/projects to ``team_id`` (their existing
    solo resources join the team they just created)."""
    for model in (Client, Project):
        for row in db.query(model).filter(model.user_id == owner_id, model.team_id.is_(None)).all():
            row.team_id = team_id


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
    _stamp_owner_resources(db, owner.id, team.id)
    if commit:
        db.commit()
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
    """Add an existing user to a team with a role. Raises if role invalid or the user
    already belongs to a team (one membership per user)."""
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
