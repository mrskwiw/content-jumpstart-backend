"""Post-comment data operations (COLLAB-01, GAP-UI-03). Access checks live in the router."""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models import Comment


def list_comments(db: Session, post_id: str) -> List[Comment]:
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def add_comment(db: Session, post_id: str, author_user_id: str, body: str) -> Comment:
    comment = Comment(post_id=post_id, author_user_id=author_user_id, body=body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment(db: Session, comment_id: str) -> Optional[Comment]:
    return db.query(Comment).filter(Comment.id == comment_id).first()


def delete_comment(db: Session, comment: Comment) -> None:
    db.delete(comment)
    db.commit()
