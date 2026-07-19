"""
Data Privacy Service - GDPR & CCPA Compliance
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from backend.models.client import Client
from backend.models.project import Project
from backend.models.post import Post
from backend.models.research_result import ResearchResult

# Column names redacted from any export — secrets that must never leave the DB,
# even in an owner-initiated migration bundle.
_REDACTED_COLUMNS = {
    "hashed_password",
    "mfa_secret",
    "mfa_backup_codes",
}


def _json_safe(value: Any) -> Any:
    """Convert a SQLAlchemy column value into a JSON-serializable primitive."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    # JSONB/JSON columns already arrive as dict/list/str/int/float/bool/None.
    return value


def _row_to_dict(obj: Any) -> Dict[str, Any]:
    """Serialize an ORM row to a dict, redacting secret columns."""
    out: Dict[str, Any] = {}
    for column in obj.__table__.columns:
        name = column.name
        if name in _REDACTED_COLUMNS:
            out[name] = "[REDACTED]"
            continue
        value = getattr(obj, name)
        # Redact the value of encrypted settings rows while keeping the key/metadata.
        if name == "value" and getattr(obj, "is_encrypted", False):
            out[name] = "[ENCRYPTED]"
            continue
        out[name] = _json_safe(value)
    return out


def _rows_to_list(objs: Any) -> List[Dict[str, Any]]:
    return [_row_to_dict(o) for o in objs]


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
            .filter(
                ResearchResult.client_id == client_id,
                ResearchResult.is_deleted.is_(False),
            )
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
    """Package ALL data owned by a client into a JSON-serializable bundle.

    GDPR Article 15 / CCPA Right to Know. Includes the client record and every
    related row across projects, posts, briefs, runs, research, keywords,
    stories, trends, deliverables and communications. Secret columns are redacted
    by ``_row_to_dict``.
    """
    from backend.models import (
        Brief,
        ClientKeyword,
        Communication,
        Deliverable,
        MinedStory,
        Run,
        TrendsKeywordInsight,
        TrendsSearch,
    )

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ValueError(f"Client {client_id} not found")

    projects = db.query(Project).filter(Project.client_id == client_id).all()
    project_ids = [p.id for p in projects]

    posts = db.query(Post).filter(Post.project_id.in_(project_ids)).all() if project_ids else []
    briefs = db.query(Brief).filter(Brief.project_id.in_(project_ids)).all() if project_ids else []
    runs = db.query(Run).filter(Run.project_id.in_(project_ids)).all() if project_ids else []

    return {
        "export_metadata": {
            "client_id": client_id,
            "exported_at": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "2.0",
            "scope": "client",
        },
        "client": _row_to_dict(client),
        "projects": _rows_to_list(projects),
        "briefs": _rows_to_list(briefs),
        "runs": _rows_to_list(runs),
        "posts": _rows_to_list(posts),
        "deliverables": _rows_to_list(
            db.query(Deliverable).filter(Deliverable.client_id == client_id).all()
        ),
        "research_results": _rows_to_list(
            db.query(ResearchResult).filter(ResearchResult.client_id == client_id).all()
        ),
        "client_keywords": _rows_to_list(
            db.query(ClientKeyword).filter(ClientKeyword.client_id == client_id).all()
        ),
        "mined_stories": _rows_to_list(
            db.query(MinedStory).filter(MinedStory.client_id == client_id).all()
        ),
        "trends_searches": _rows_to_list(
            db.query(TrendsSearch).filter(TrendsSearch.client_id == client_id).all()
        ),
        "trends_keyword_insights": _rows_to_list(
            db.query(TrendsKeywordInsight).filter(TrendsKeywordInsight.client_id == client_id).all()
        ),
        "communications": _rows_to_list(
            db.query(Communication).filter(Communication.client_id == client_id).all()
        ),
    }


def export_full_instance(db: Session) -> Dict:
    """Dump the entire instance database into one JSON bundle for migration.

    Superuser-only (enforced at the router). Every table is included so the
    customer can migrate elsewhere; secret columns (password hashes, MFA secrets,
    encrypted setting values) are redacted by ``_row_to_dict``.
    """
    from backend.models import (
        AuditLog,
        Brief,
        Client,
        ClientKeyword,
        Communication,
        Conversation,
        CreditPackage,
        CreditTransaction,
        DeletionAuditLog,
        Deliverable,
        Message,
        MinedStory,
        Post,
        Project,
        ResearchResult,
        Run,
        Setting,
        StoryUsage,
        StripeCustomer,
        StripePayment,
        TrendsInterestData,
        TrendsKeywordInsight,
        TrendsRelatedQuery,
        TrendsSearch,
        User,
    )

    # (json key, model) — order roughly follows dependency order for readability.
    tables = [
        ("users", User),
        ("credit_packages", CreditPackage),
        ("credit_transactions", CreditTransaction),
        ("clients", Client),
        ("client_keywords", ClientKeyword),
        ("projects", Project),
        ("briefs", Brief),
        ("runs", Run),
        ("posts", Post),
        ("deliverables", Deliverable),
        ("research_results", ResearchResult),
        ("trends_searches", TrendsSearch),
        ("trends_interest_data", TrendsInterestData),
        ("trends_related_queries", TrendsRelatedQuery),
        ("trends_keyword_insights", TrendsKeywordInsight),
        ("mined_stories", MinedStory),
        ("story_usage", StoryUsage),
        ("stripe_customers", StripeCustomer),
        ("stripe_payments", StripePayment),
        ("communications", Communication),
        ("settings", Setting),
        ("audit_log", AuditLog),
        ("deletion_audit_log", DeletionAuditLog),
        ("conversations", Conversation),
        ("messages", Message),
    ]

    data: Dict[str, Any] = {}
    counts: Dict[str, int] = {}
    for key, model in tables:
        rows = _rows_to_list(db.query(model).all())
        data[key] = rows
        counts[key] = len(rows)

    return {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "1.0",
            "scope": "instance",
            "row_counts": counts,
            "redacted_columns": sorted(_REDACTED_COLUMNS) + ["settings.value (when encrypted)"],
        },
        "data": data,
    }


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
