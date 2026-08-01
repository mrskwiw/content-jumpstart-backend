"""Team + membership models (COLLAB-01).

A Team is a shared workspace; resources (Client/Project) are owned by a team via
their ``team_id``, and access is governed by the caller's TeamMember role rather than
by the single ``user_id`` creator. Each user belongs to exactly one team
(``TeamMember.user_id`` is unique) — created as a personal team at registration and
backfilled for pre-existing users.

Roles (see :data:`TEAM_ROLES`):
- ``owner``  — everything, incl. delete team / manage members (the team creator);
- ``admin``  — manage members + resource read/write;
- ``editor`` — resource read/write;
- ``viewer`` — read-only (writes are 403'd).
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base

# Ordered most-privileged first. Roles that may write resources / manage members are
# derived from these tuples so the policy lives in one place.
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"
TEAM_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER)
WRITE_ROLES = frozenset({ROLE_OWNER, ROLE_ADMIN, ROLE_EDITOR})  # may mutate resources
MANAGE_ROLES = frozenset({ROLE_OWNER, ROLE_ADMIN})  # may manage members


class Team(Base):
    """A shared workspace owning clients/projects (COLLAB-01)."""

    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: f"team-{uuid.uuid4().hex[:12]}")
    name = Column(String, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """A user's membership + role in a team. One membership per user."""

    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=lambda: f"tm-{uuid.uuid4().hex[:12]}")
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    role = Column(String, nullable=False, default=ROLE_VIEWER)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    team = relationship("Team", back_populates="members")

    __table_args__ = (UniqueConstraint("user_id", name="uq_team_members_user_id"),)
