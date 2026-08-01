"""Post comments — team review feedback endpoints (COLLAB-01, GAP-UI-03).

Access is team-scoped through the post's project: any member of the post's team (any
role, incl. viewer — leaving review feedback is a read-level collaboration action) may
read and add comments; a comment can be deleted by its author or a team manager
(owner/admin), or a superuser.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import _check_ownership
from backend.models import Post, User
from backend.services import comment_service, crud, team_service

router = APIRouter()


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_user_id: str
    author_email: Optional[str] = None
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


def _post_with_read_access(post_id: str, db: Session, user: User) -> Post:
    """Load a post the caller can READ (a member of its team, its creator, or a
    superuser); 404 if missing, 403 if not permitted."""
    post = crud.get_post(db, post_id)
    # A soft-deleted post (or its soft-deleted project) is treated as gone — deleted
    # content isn't commentable, matching the deleted-row filtering on other read paths.
    if not post or getattr(post, "is_deleted", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    project = crud.get_project(db, post.project_id)
    if not project or getattr(project, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post's project not found"
        )
    # is_write=False → read-level: any team member (incl. viewer) may see + comment.
    if not _check_ownership("Project", project, user, db, is_write=False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this post"
        )
    return post


def _to_response(db: Session, comment) -> CommentResponse:
    author = crud.get_user(db, comment.author_user_id)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author_user_id=comment.author_user_id,
        author_email=author.email if author else None,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def list_post_comments(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List a post's comments (any member of the post's team)."""
    _post_with_read_access(post_id, db, current_user)
    return [_to_response(db, c) for c in comment_service.list_comments(db, post_id)]


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_post_comment(
    post_id: str,
    body: CreateCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a post (any member of the post's team)."""
    _post_with_read_access(post_id, db, current_user)
    comment = comment_service.add_comment(db, post_id, current_user.id, body.body)
    return _to_response(db, comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_200_OK)
def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment (its author, a team manager, or a superuser)."""
    comment = comment_service.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    # The caller must at least be able to read the post (team member of its team).
    post = _post_with_read_access(comment.post_id, db, current_user)
    project = crud.get_project(db, post.project_id)
    # Manager check is scoped to the POST'S team explicitly (not the caller's own team),
    # so it's correct even if a user could ever belong to more than one team.
    is_team_manager = team_service.is_manager(
        db, current_user.id, project.team_id if project else None
    )
    is_author = comment.author_user_id == current_user.id
    if not (is_author or current_user.is_superuser or is_team_manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment's author or a team owner/admin can delete it",
        )
    comment_service.delete_comment(db, comment)
    return {"status": "success", "message": "Comment deleted"}
