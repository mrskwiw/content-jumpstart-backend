"""
Data Privacy Service - GDPR & CCPA Compliance
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session
from backend.models.client import Client
from backend.models.project import Project
from backend.models.post import Post
from backend.models.research_result import ResearchResult


def soft_delete_client(client_id: str, db: Session, cascade: bool = True) -> Dict:
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise ValueError(f"Client {client_id} not found")
    client.soft_delete()
    deleted_counts = {"client": 1, "projects": 0, "posts": 0, "research_results": 0}
    if cascade:
        for project in (
            db.query(Project)
            .filter(Project.client_id == client_id, Project.is_deleted.is_(False))
            .all()
        ):
            project.soft_delete()
            deleted_counts["projects"] += 1
            for post in (
                db.query(Post)
                .filter(Post.project_id == project.id, Post.is_deleted.is_(False))
                .all()
            ):
                post.soft_delete()
                deleted_counts["posts"] += 1
        for result in (
            db.query(ResearchResult)
            .filter(ResearchResult.client_id == client_id, ResearchResult.is_deleted.is_(False))
            .all()
        ):
            result.soft_delete()
            deleted_counts["research_results"] += 1
    db.commit()
    return {
        "status": "success",
        "client_id": client_id,
        "deleted_at": client.deleted_at.isoformat(),
        "deleted_counts": deleted_counts,
        "recovery_period_days": 30,
    }


def anonymize_client(client_id: str, db: Session) -> Dict:
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise ValueError(f"Client {client_id} not found")
    anon_id = uuid.uuid4().hex[:8]
    client.name = f"ANONYMIZED_USER_{anon_id}"
    client.email = f"deleted_{anon_id}@anonymized.local"
    client.business_description = None
    client.ideal_customer = None
    client.main_problem_solved = None
    client.is_deleted = True
    client.deleted_at = datetime.utcnow()
    db.commit()
    return {
        "status": "success",
        "client_id": client_id,
        "anonymized_at": client.deleted_at.isoformat(),
    }


def export_client_data(client_id: str, db: Session) -> Dict:
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise ValueError(f"Client {client_id} not found")
    projects = (
        db.query(Project)
        .filter(Project.client_id == client_id, Project.is_deleted.is_(False))
        .all()
    )
    export_data = {
        "client": {"id": client.id, "name": client.name, "email": client.email},
        "projects": [],
        "export_metadata": {
            "client_id": client_id,
            "exported_at": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "1.0",
        },
    }
    for p in projects:
        export_data["projects"].append({"id": p.id, "name": p.name, "status": p.status})
    return export_data


def restore_soft_deleted_client(client_id: str, db: Session) -> Dict:
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(True)).first()
    if not client:
        raise ValueError(f"Client {client_id} not in deleted records")
    if client.deleted_at and (datetime.utcnow() - client.deleted_at).days > 90:
        raise ValueError(
            f"Client {client_id} was deleted more than 90 days ago and cannot be restored"
        )
    client.restore()
    for p in (
        db.query(Project).filter(Project.client_id == client_id, Project.is_deleted.is_(True)).all()
    ):
        p.restore()
    db.commit()
    return {"status": "success", "client_id": client_id}


def purge_soft_deleted_records(days_old: int, db: Session, dry_run: bool = True) -> Dict:
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    clients = db.query(Client).filter(Client.is_deleted.is_(True), Client.deleted_at < cutoff).all()
    summary = {"dry_run": dry_run, "deleted": {"clients": len(clients)}}
    if not dry_run:
        for c in clients:
            db.delete(c)
        db.commit()
    return summary
