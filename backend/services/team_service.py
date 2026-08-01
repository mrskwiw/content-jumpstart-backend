"""Team membership + role operations and the idempotent teams backfill (COLLAB-01).

The single place that resolves a user's team and role, mutates membership, and
grandfathers pre-existing users/resources onto teams. Access-control decisions in
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


# ── personal team (created at registration + backfill) ──────────────────────────


def ensure_personal_team(db: Session, user: User, *, commit: bool = True) -> Team:
    """Return the user's team, creating a personal one (they're the owner) if none.

    Idempotent: a user who already has a membership keeps it. Used at registration and
    by the backfill.
    """
    existing = get_membership(db, user.id)
    if existing is not None:
        team = db.query(Team).filter(Team.id == existing.team_id).first()
        assert team is not None  # membership implies a team
        return team

    team = Team(name=f"{(user.full_name or user.email)}'s Team", owner_user_id=user.id)
    db.add(team)
    db.flush()  # assign team.id
    db.add(TeamMember(team_id=team.id, user_id=user.id, role=ROLE_OWNER))
    if commit:
        db.commit()
    return team


def backfill_teams(db: Session) -> int:
    """Grandfather pre-existing users/resources onto teams (idempotent, every boot).

    ``team_id IS NULL`` / "user has no membership" unambiguously means "legacy" —
    every new user gets a personal team at registration and every new resource is
    stamped at create — so this only ever touches un-migrated rows and is safe to run
    on every startup. Returns the number of users given a new personal team.
    """
    created = 0
    users_without_team = (
        db.query(User)
        .outerjoin(TeamMember, TeamMember.user_id == User.id)
        .filter(TeamMember.id.is_(None))
        .all()
    )
    for user in users_without_team:
        ensure_personal_team(db, user, commit=False)
        created += 1
    if created:
        db.flush()

    # Stamp legacy clients/projects with their creator's team.
    for model in (Client, Project):
        rows = db.query(model).filter(model.team_id.is_(None)).all()
        for row in rows:
            team_id = user_team_id(db, row.user_id)
            if team_id is not None:
                row.team_id = team_id
    db.commit()
    return created


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
