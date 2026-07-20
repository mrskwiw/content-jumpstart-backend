"""
Data Privacy Service - GDPR & CCPA Compliance
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from backend.models.client import Client
from backend.models.project import Project
from backend.models.post import Post
from backend.models.research_result import ResearchResult

logger = logging.getLogger(__name__)

# Column names redacted from any export — secrets that must never leave the DB,
# even in an owner-initiated migration bundle.
_REDACTED_COLUMNS = {
    "hashed_password",
    "mfa_secret",
    "mfa_backup_codes",
    "access_token",  # platform_credentials — encrypted OAuth tokens
    "refresh_token",
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


def _raw_rows(
    db: Session, table: str, id_column: str = None, ids=None, missing: list = None
) -> List[Dict[str, Any]]:
    """Export rows from a table with NO ORM model (raw-SQL-managed cost tracking,
    e.g. api_calls / budget_alerts).

    ``table`` and ``id_column`` are internal constants, never user input. If the
    table is absent (e.g. schema drift or a test DB that never created it) the
    table name is appended to ``missing`` (when provided) so the caller can flag
    the export as partial rather than silently returning empty. Values are
    JSON-normalized like the ORM path.
    """
    from sqlalchemy import inspect as sqla_inspect, text, bindparam

    if table not in sqla_inspect(db.bind).get_table_names():
        if missing is not None:
            missing.append(table)
        return []
    if id_column is not None:
        if not ids:
            return []
        stmt = text(f"SELECT * FROM {table} WHERE {id_column} IN :ids").bindparams(  # nosec B608
            bindparam("ids", expanding=True)
        )
        result = db.execute(stmt, {"ids": list(ids)})
    else:
        result = db.execute(text(f"SELECT * FROM {table}"))  # nosec B608
    return [{k: _json_safe(v) for k, v in dict(r).items()} for r in result.mappings().all()]


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

    from backend.models import (
        PlatformCredential,
        PostMetric,
        PostedContent,
        ScheduledPost,
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
        ("platform_credentials", PlatformCredential),
        ("scheduled_posts", ScheduledPost),
        ("posted_content", PostedContent),
        ("post_metrics", PostMetric),
    ]

    data: Dict[str, Any] = {}
    counts: Dict[str, int] = {}
    for key, model in tables:
        rows = _rows_to_list(db.query(model).all())
        data[key] = rows
        counts[key] = len(rows)

    # Raw-SQL cost-tracking tables (no ORM model) — full dump for migration.
    missing_tables: List[str] = []
    for raw_table in ("api_calls", "budget_alerts"):
        rows = _raw_rows(db, raw_table, missing=missing_tables)
        data[raw_table] = rows
        counts[raw_table] = len(rows)
    if missing_tables:
        logger.warning("Instance export is PARTIAL — missing raw tables: %s", missing_tables)

    return {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "1.0",
            "scope": "instance",
            "partial": bool(missing_tables),
            "missing_tables": missing_tables,
            "row_counts": counts,
            "redacted_columns": sorted(_REDACTED_COLUMNS) + ["settings.value (when encrypted)"],
        },
        "data": data,
    }


def export_user_data(user_id: str, db: Session) -> Dict:
    """Export ALL data associated with a single user account (GDPR Article 15).

    Comprehensive subject-access export: the user's account record, every row
    keyed directly to their ``user_id`` (settings, credits, billing,
    communications, audit, assistant conversations), and the full content tree
    they generated — reached through the clients/projects they created (posts,
    briefs, runs, deliverables, keywords, trends detail, story usage, messages).
    Secret columns are redacted by ``_row_to_dict``.
    """
    from backend.models import (
        AuditLog,
        Brief,
        Client,
        ClientKeyword,
        Communication,
        Conversation,
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

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    def by_user(model):
        return _rows_to_list(db.query(model).filter(model.user_id == user_id).all())

    def by_ids(model, column, ids):
        if not ids:
            return []
        return _rows_to_list(db.query(model).filter(column.in_(ids)).all())

    from sqlalchemy import or_

    def or_rows(model, *pairs):
        """Serialize rows of `model` matching ANY (column, ids) with non-empty ids.

        Used so records that carry no user_id (only client_id/project_id, e.g.
        trends_keyword_insights) or that may be scoped to the user's client OR
        project are still captured exhaustively.
        """
        conds = [col.in_(ids) for col, ids in pairs if ids]
        return _rows_to_list(db.query(model).filter(or_(*conds)).all()) if conds else []

    def or_objs(model, base_cond, *pairs):
        conds = [base_cond] + [col.in_(ids) for col, ids in pairs if ids]
        return db.query(model).filter(or_(*conds)).all()

    # Resolve the id sets the child records hang off.
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
    client_ids = [c.id for c in clients]
    project_ids = [p.id for p in projects]
    conversation_ids = [c.id for c in conversations]

    # Stories & trends: user-owned OR scoped to the user's clients/projects.
    mined_stories = or_objs(
        MinedStory,
        MinedStory.user_id == user_id,
        (MinedStory.project_id, project_ids),
        (MinedStory.client_id, client_ids),
    )
    story_ids = [s.id for s in mined_stories]
    trends_searches = or_objs(
        TrendsSearch,
        TrendsSearch.user_id == user_id,
        (TrendsSearch.project_id, project_ids),
        (TrendsSearch.client_id, client_ids),
    )
    search_ids = [t.id for t in trends_searches]

    # Cost-tracking tables (raw SQL, no ORM). The project_id column may hold a
    # client_id as a fallback (token_sync_service), so query BOTH id sets.
    cost_ids = project_ids + client_ids
    missing_tables: List[str] = []
    api_calls = _raw_rows(db, "api_calls", "project_id", cost_ids, missing_tables)
    budget_alerts = _raw_rows(db, "budget_alerts", "project_id", cost_ids, missing_tables)
    if missing_tables:
        logger.warning(
            "User export for %s is PARTIAL — missing raw tables: %s", user_id, missing_tables
        )

    from backend.models import (
        PlatformCredential,
        PostMetric,
        PostedContent,
        ScheduledPost,
    )

    return {
        "export_metadata": {
            "partial": bool(missing_tables),
            "missing_tables": missing_tables,
            "user_id": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "2.0",
            "scope": "user",
        },
        "account": _row_to_dict(user),
        # Account-level records keyed directly to the user.
        "settings": by_user(Setting),
        "credit_transactions": by_user(CreditTransaction),
        "stripe_customers": by_user(StripeCustomer),
        "stripe_payments": by_user(StripePayment),
        "communications": by_user(Communication),
        "audit_log": _rows_to_list(db.query(AuditLog).filter(AuditLog.user_id == user_id).all()),
        "deletion_audit_log": _rows_to_list(
            db.query(DeletionAuditLog).filter(DeletionAuditLog.deleted_by_user_id == user_id).all()
        ),
        # Assistant history (user-owned).
        "conversations": _rows_to_list(conversations),
        "messages": by_ids(Message, Message.conversation_id, conversation_ids),
        # Clients + their full content tree.
        "clients": _rows_to_list(clients),
        "client_keywords": by_ids(ClientKeyword, ClientKeyword.client_id, client_ids),
        "projects": _rows_to_list(projects),
        "briefs": by_ids(Brief, Brief.project_id, project_ids),
        "runs": by_ids(Run, Run.project_id, project_ids),
        "posts": by_ids(Post, Post.project_id, project_ids),
        "deliverables": or_rows(
            Deliverable,
            (Deliverable.client_id, client_ids),
            (Deliverable.project_id, project_ids),
        ),
        "research_results": by_user(ResearchResult),
        "trends_searches": _rows_to_list(trends_searches),
        "trends_interest_data": by_ids(
            TrendsInterestData, TrendsInterestData.search_id, search_ids
        ),
        "trends_related_queries": by_ids(
            TrendsRelatedQuery, TrendsRelatedQuery.search_id, search_ids
        ),
        "trends_keyword_insights": or_rows(
            TrendsKeywordInsight,
            (TrendsKeywordInsight.client_id, client_ids),
            (TrendsKeywordInsight.project_id, project_ids),
        ),
        "mined_stories": _rows_to_list(mined_stories),
        "story_usage": or_rows(
            StoryUsage,
            (StoryUsage.story_id, story_ids),
            (StoryUsage.project_id, project_ids),
        ),
        # Raw-SQL cost-tracking tables (no ORM model), project/client-scoped.
        "api_calls": api_calls,
        "budget_alerts": budget_alerts,
        # Phase 10/11 — distribution + analytics (tokens redacted).
        "platform_credentials": by_user(PlatformCredential),
        "scheduled_posts": by_user(ScheduledPost),
        "posted_content": by_user(PostedContent),
        "post_metrics": by_user(PostMetric),
    }


def delete_user_account(user_id: str, db: Session) -> Dict:
    """Soft-delete and deactivate a user account, revoking its sessions.

    Operators have no stake in the data, so this does NOT cascade to the
    clients/projects they created (those belong to the instance). Refuses to
    delete the last active superuser to avoid locking out the instance. Raises
    PermissionError for that guard, ValueError for not-found / already-deleted.
    """
    from datetime import timezone
    from backend.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    if user.is_deleted:
        raise ValueError(f"User {user_id} is already deleted")

    if user.is_superuser:
        remaining_admins = (
            db.query(User)
            .filter(
                User.is_superuser.is_(True),
                User.is_active.is_(True),
                User.is_deleted.is_(False),
                User.id != user_id,
            )
            .count()
        )
        if remaining_admins == 0:
            raise PermissionError("Cannot delete the last active administrator")

    now = datetime.now(timezone.utc)
    user.is_active = False
    user.is_deleted = True
    user.deleted_at = now
    user.password_changed_at = now  # revoke all of this user's sessions
    db.commit()
    return {
        "status": "success",
        "user_id": user_id,
        "deleted_at": now.isoformat(),
        "recovery_period_days": 30,
    }


def restore_user_account(user_id: str, db: Session) -> Dict:
    """Restore a soft-deleted user account (superuser-gated at the router).

    Sessions stay revoked (password_changed_at unchanged) — the user signs in
    again after restore.
    """
    from backend.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    if not user.is_deleted:
        raise ValueError(f"User {user_id} is not deleted")

    user.is_deleted = False
    user.deleted_at = None
    user.is_active = True
    db.commit()
    return {"status": "success", "user_id": user_id, "restored": True}


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
