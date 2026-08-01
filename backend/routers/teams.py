"""Team management endpoints (COLLAB-01).

The caller's team is resolved from their membership. Member management (add / change
role / remove) requires an owner or admin role; anyone in the team can read it.
Comments and approval gates (the rest of COLLAB-01) are separate future slices.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.models.team import ROLE_OWNER
from backend.services import crud, team_service

router = APIRouter()


class TeamMemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str


class TeamResponse(BaseModel):
    team_id: str
    name: str
    my_role: str
    members: List[TeamMemberResponse]


class MyTeamResponse(BaseModel):
    """The caller's team, or ``team: null`` when they are solo (not on a team)."""

    team: Optional[TeamResponse] = None


class CreateTeamRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class ChangeRoleRequest(BaseModel):
    role: str


class TransferOwnershipRequest(BaseModel):
    user_id: str


def _require_membership(db: Session, user: User) -> str:
    """Return the caller's team_id, or 404 if they somehow have no team."""
    team_id = team_service.user_team_id(db, user.id)
    if team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not on a team")
    return team_id


def _require_manager(db: Session, user: User) -> str:
    """Return the caller's team_id, requiring an owner/admin role (else 403)."""
    team_id = _require_membership(db, user)
    if not team_service.is_manager(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a team owner or admin can manage members",
        )
    return team_id


def _require_owner(db: Session, user: User) -> str:
    """Return the caller's team_id, requiring the owner role (else 403)."""
    team_id = _require_membership(db, user)
    if not team_service.is_owner(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team owner can do this",
        )
    return team_id


def _members_response(db: Session, team_id: str, my_role: str, name: str) -> TeamResponse:
    members = team_service.list_members(db, team_id)
    out: List[TeamMemberResponse] = []
    for m in members:
        u = crud.get_user(db, m.user_id)
        out.append(
            TeamMemberResponse(
                user_id=m.user_id,
                email=u.email if u else m.user_id,
                full_name=u.full_name if u else None,
                role=m.role,
            )
        )
    return TeamResponse(team_id=team_id, name=name, my_role=my_role, members=out)


@router.get("/me", response_model=MyTeamResponse)
def get_my_team(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """The caller's team, role, and members — or ``team: null`` if they are solo."""
    membership = team_service.get_membership(db, current_user.id)
    if membership is None:
        return MyTeamResponse(team=None)
    from backend.models import Team

    team = db.query(Team).filter(Team.id == membership.team_id).first()
    name = team.name if team else membership.team_id
    return MyTeamResponse(team=_members_response(db, membership.team_id, membership.role, name))


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team_endpoint(
    body: CreateTeamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a team (the caller becomes its owner). Rejects a caller already on a team.

    The caller's existing team-less clients/projects are moved into the new team.
    """
    try:
        team = team_service.create_team(db, current_user, body.name)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    membership = team_service.get_membership(db, current_user.id)
    return _members_response(db, team.id, membership.role, team.name)


@router.post("/members", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    body: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an existing, registered user to the caller's team (owner/admin only)."""
    team_id = _require_manager(db, current_user)
    target = crud.get_user_by_email(db, body.email)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user with that email",
        )
    try:
        team_service.add_member(db, team_id, target, body.role)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    membership = team_service.get_membership(db, current_user.id)
    from backend.models import Team

    team = db.query(Team).filter(Team.id == team_id).first()
    return _members_response(db, team_id, membership.role, team.name if team else team_id)


@router.patch("/members/{user_id}", response_model=TeamResponse)
def change_member_role(
    user_id: str,
    body: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a member's role (owner/admin only). The owner's role is immutable here."""
    team_id = _require_manager(db, current_user)
    try:
        team_service.change_role(db, team_id, user_id, body.role)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    membership = team_service.get_membership(db, current_user.id)
    from backend.models import Team

    team = db.query(Team).filter(Team.id == team_id).first()
    return _members_response(db, team_id, membership.role, team.name if team else team_id)


@router.delete("/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_member(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member (owner/admin), or leave the team yourself. Owner can't be removed."""
    team_id = _require_membership(db, current_user)
    # Managers can remove anyone (except the owner); a non-manager may only remove self.
    if user_id != current_user.id and not team_service.is_manager(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a team owner or admin can remove other members",
        )
    if user_id == current_user.id and team_service.user_role(db, current_user.id) == ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The team owner cannot leave; transfer ownership or delete the team",
        )
    try:
        team_service.remove_member(db, team_id, user_id)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "success", "message": "Member removed"}


@router.post("/transfer", status_code=status.HTTP_200_OK)
def transfer_ownership_endpoint(
    body: TransferOwnershipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transfer team ownership to another member (owner only). The caller becomes admin."""
    team_id = _require_owner(db, current_user)
    try:
        team_service.transfer_ownership(db, team_id, current_user.id, body.user_id)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "success", "message": "Ownership transferred"}


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Sustained concurrent activity prevented a clean teardown; "
            "retry (the underlying error is logged server-side — Decision #214)."
        }
    },
)
def delete_team_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disband the team (owner only). Resources revert to their creators (solo).

    If sustained concurrent activity prevents a clean teardown after bounded retries,
    returns 409 (retryable) rather than a false success — the underlying error is logged
    server-side for visibility (Decision #214).
    """
    team_id = _require_owner(db, current_user)
    try:
        team_service.delete_team(db, team_id)
    except team_service.TeamError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"status": "success", "message": "Team deleted"}


@router.post("/adopt-resources", status_code=status.HTTP_200_OK)
def adopt_resources_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move the caller's own team-less (solo) clients/projects into their team.

    The explicit, self-consented counterpart to the no-auto-migrate-on-invite policy
    (Decision #213): a member deliberately brings their prior solo work into the team.
    """
    team_id = _require_membership(db, current_user)
    moved = team_service.adopt_resources(db, current_user.id, team_id)
    return {"status": "success", "moved": moved}
