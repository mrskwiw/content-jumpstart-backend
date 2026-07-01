"""CRUD operations for ClientKeyword."""

from __future__ import annotations

from typing import List, Optional

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.client_keywords import ClientKeyword
from backend.schemas.keyword_schemas import KeywordCreate, KeywordUpdate
from backend.utils.logger import logger

_MAX_PER_TYPE = 50


def get_keywords_for_client(
    db: Session,
    client_id: str,
    keyword_type: Optional[str] = None,
    active_only: bool = True,
) -> List[ClientKeyword]:
    q = db.query(ClientKeyword).filter(ClientKeyword.client_id == client_id)
    if keyword_type:
        q = q.filter(ClientKeyword.keyword_type == keyword_type)
    if active_only:
        q = q.filter(ClientKeyword.is_active.is_(True))
    return q.order_by(ClientKeyword.keyword_type, ClientKeyword.id).all()


def get_keyword(db: Session, keyword_id: int, client_id: str) -> Optional[ClientKeyword]:
    return (
        db.query(ClientKeyword)
        .filter(ClientKeyword.id == keyword_id, ClientKeyword.client_id == client_id)
        .first()
    )


def count_active_by_type(db: Session, client_id: str, keyword_type: str) -> int:
    return (
        db.query(ClientKeyword)
        .filter(
            ClientKeyword.client_id == client_id,
            ClientKeyword.keyword_type == keyword_type,
            ClientKeyword.is_active.is_(True),
        )
        .count()
    )


def _count_and_lock_active(db: Session, client_id: str, keyword_type: str) -> int:
    """Count active keywords of a type with SELECT … FOR UPDATE row-level locks.

    PostgreSQL (READ COMMITTED): FOR UPDATE blocks T2 on the rows locked by T1;
    after T1 commits T2 re-evaluates in READ COMMITTED and sees the updated count.
    This serialises the check-then-act correctly for PostgreSQL.

    SQLite: FOR UPDATE is silently ignored and WAL mode gives each transaction a
    snapshot fixed at first read.  The cap is therefore best-effort under concurrent
    multi-process SQLite deployments.  Single-process asyncio (the default FastAPI
    deployment) is safe because the event loop serialises requests.
    """
    rows = (
        db.query(ClientKeyword.id)
        .filter(
            ClientKeyword.client_id == client_id,
            ClientKeyword.keyword_type == keyword_type,
            ClientKeyword.is_active.is_(True),
        )
        .with_for_update()
        .all()
    )
    return len(rows)


def create_keyword(
    db: Session,
    client_id: str,
    data: KeywordCreate,
    source: str = "manual",
    research_result_id: Optional[str] = None,
) -> Optional[ClientKeyword]:
    current = _count_and_lock_active(db, client_id, data.keyword_type.value)
    if current >= _MAX_PER_TYPE:
        raise ValueError(
            f"Maximum {_MAX_PER_TYPE} active {data.keyword_type} keywords allowed per client"
        )

    kw = ClientKeyword(
        client_id=client_id,
        research_result_id=research_result_id,
        keyword=data.keyword.strip().lower(),
        keyword_type=data.keyword_type,
        search_intent=data.search_intent,
        difficulty=data.difficulty,
        monthly_volume=data.monthly_volume,
        relevance_score=data.relevance_score,
        quality_score=data.quality_score,
        source=source,
        is_active=True,
        notes=data.notes,
    )
    db.add(kw)
    try:
        db.commit()
        db.refresh(kw)
        return kw
    except IntegrityError:
        db.rollback()
        # Keyword already exists for this client+type — reactivate if it was soft-deleted
        existing = (
            db.query(ClientKeyword)
            .filter(
                ClientKeyword.client_id == client_id,
                ClientKeyword.keyword == kw.keyword,
                ClientKeyword.keyword_type == data.keyword_type,
            )
            .first()
        )
        if existing and not existing.is_active:
            # Re-check cap in the new transaction started after the rollback.
            # A concurrent writer could have filled the cap between the rollback
            # and now.  In PostgreSQL, FOR UPDATE re-evaluates after unblocking;
            # in SQLite, this is best-effort (the race is extremely unlikely in
            # single-process asyncio but can occur with multiple workers).
            reactivation_count = _count_and_lock_active(db, client_id, data.keyword_type.value)
            if reactivation_count >= _MAX_PER_TYPE:
                return None  # cap reached; treat as "already exists but cannot reactivate"
            setattr(existing, "is_active", True)
            # Apply the same ownership rule as update_keyword reactivation:
            # a manual caller claims the row; never downgrade manual → research_tool.
            # Guard in bulk_upsert reads existing.source — it must be current.
            if source == "manual" or existing.source != "manual":
                setattr(existing, "source", source)
                # Apply caller-supplied metadata so the returned row matches the
                # create request.  Only set fields explicitly provided (not None),
                # preserving existing values that the caller left unspecified.
                if data.search_intent is not None:
                    setattr(existing, "search_intent", data.search_intent)
                if data.difficulty is not None:
                    setattr(existing, "difficulty", data.difficulty)
                if data.monthly_volume is not None:
                    setattr(existing, "monthly_volume", data.monthly_volume)
                if data.relevance_score is not None:
                    setattr(existing, "relevance_score", data.relevance_score)
                if data.quality_score is not None:
                    setattr(existing, "quality_score", data.quality_score)
                if data.notes is not None:
                    setattr(existing, "notes", data.notes)
            db.commit()
            db.refresh(existing)
            return existing
        return None


_CONTENT_FIELDS = frozenset(
    {"keyword", "search_intent", "difficulty", "monthly_volume", "relevance_score", "notes"}
)


def update_keyword(
    db: Session,
    keyword_id: int,
    client_id: str,
    data: KeywordUpdate,
) -> Optional[ClientKeyword]:
    kw = get_keyword(db, keyword_id, client_id)
    if not kw:
        return None
    was_inactive = not kw.is_active  # capture before applying updates
    is_reactivating = data.is_active is True and was_inactive
    if is_reactivating:
        # Enforce the same per-type cap that create_keyword and bulk_upsert honour.
        # Without this check, PUT {"is_active": true} on a soft-deleted keyword can
        # silently push a type past 50 active rows.
        current = _count_and_lock_active(db, client_id, str(kw.keyword_type))
        if current >= _MAX_PER_TYPE:
            raise ValueError(
                f"Maximum {_MAX_PER_TYPE} active {kw.keyword_type} keywords allowed per client"
            )
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "keyword" and value:
            value = value.strip().lower()
        setattr(kw, field, value)
    # Flip source to "manual" when the operator explicitly claims the keyword:
    # (a) any content-field edit — operator set or changed metadata values
    # (b) genuine reactivation (was inactive, now active) — operator brought it back;
    #     sending is_active=True to an already-active keyword is a noop on state and
    #     must NOT claim the row, otherwise research_tool keywords get locked silently.
    # Deactivation (is_active=False) does NOT claim the row.
    if updates.keys() & _CONTENT_FIELDS or is_reactivating:
        setattr(kw, "source", "manual")
    db.commit()
    db.refresh(kw)
    return kw


def soft_delete_keyword(db: Session, keyword_id: int, client_id: str) -> bool:
    kw = get_keyword(db, keyword_id, client_id)
    if not kw:
        return False
    setattr(kw, "is_active", False)
    db.commit()
    return True


def bulk_upsert_keywords(
    db: Session,
    client_id: str,
    keywords: List[KeywordCreate],
    source: str = "manual",
    research_result_id: Optional[str] = None,
    _commit: bool = True,
) -> dict:
    """Upsert a list of keywords for a client. Returns import stats.

    Pass _commit=False when the caller needs to stage additional changes before
    a single atomic commit (e.g. seed_from_research_result).
    """
    imported = 0
    skipped = 0
    # Track inserts pending flush per type so count_active_by_type stays accurate
    # (Session uses autoflush=False; unflushed adds are invisible to COUNT queries).
    in_flight: dict[str, int] = {}

    for data in keywords:  # no slice — per-type limit enforced below
        keyword_lower = data.keyword.strip().lower()
        existing = (
            db.query(ClientKeyword)
            .filter(
                ClientKeyword.client_id == client_id,
                ClientKeyword.keyword == keyword_lower,
                ClientKeyword.keyword_type == data.keyword_type,
            )
            .first()
        )
        if existing:
            if not existing.is_active:
                # Reactivating a soft-deleted row counts against the per-type cap.
                # count_active_by_type won't see unflushed reactivations (autoflush=False),
                # so we use in_flight to track them within this batch.
                ktype_r: str = data.keyword_type.value
                committed_r = _count_and_lock_active(db, client_id, ktype_r)
                pending_r = in_flight.get(ktype_r, 0)
                if committed_r + pending_r >= _MAX_PER_TYPE:
                    skipped += 1
                    continue
                in_flight[ktype_r] = pending_r + 1
                setattr(existing, "is_active", True)  # always reactivate if cap allows
            # Update metadata only when it won't overwrite human edits with research data.
            # Allow update if the caller is a manual operator OR the existing row wasn't
            # manually edited. Block when research_tool hits a manually-edited row.
            if source == "manual" or existing.source != "manual":
                setattr(
                    existing,
                    "search_intent",
                    data.search_intent or existing.search_intent,
                )
                setattr(existing, "difficulty", data.difficulty or existing.difficulty)
                setattr(
                    existing,
                    "monthly_volume",
                    data.monthly_volume or existing.monthly_volume,
                )
                setattr(
                    existing,
                    "relevance_score",
                    data.relevance_score or existing.relevance_score,
                )
                setattr(
                    existing,
                    "quality_score",
                    data.quality_score or existing.quality_score,
                )
                # A manual bulk-edit claims the row so future research re-runs won't
                # overwrite the operator's values (guard reads existing.source).
                if source == "manual":
                    setattr(existing, "source", "manual")
                elif research_result_id is not None:
                    # Keep the citation current so stale-keyword detection in
                    # seed_from_research_result can tell "refreshed this run" from
                    # "genuinely from an old run".  Only update on research_tool calls
                    # (manual upserts are not tied to a specific research run).
                    setattr(existing, "research_result_id", research_result_id)
            skipped += 1
        else:
            # Use .value to get the plain string ("primary", not "KeywordType.primary")
            # — str() on a str-Enum member changed in Python 3.12.
            ktype: str = data.keyword_type.value
            committed = _count_and_lock_active(db, client_id, ktype)
            pending = in_flight.get(ktype, 0)
            if committed + pending >= _MAX_PER_TYPE:
                skipped += 1
                continue
            kw = ClientKeyword(
                client_id=client_id,
                research_result_id=research_result_id,
                keyword=keyword_lower,
                keyword_type=data.keyword_type,
                search_intent=data.search_intent,
                difficulty=data.difficulty,
                monthly_volume=data.monthly_volume,
                relevance_score=data.relevance_score,
                quality_score=data.quality_score,
                source=source,
                is_active=True,
                notes=data.notes,
            )
            db.add(kw)
            in_flight[ktype] = pending + 1
            imported += 1

    if _commit:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"bulk_upsert_keywords failed for client {client_id}: {e}")
            raise

    return {"imported": imported, "skipped": skipped}


def seed_from_research_result(
    db: Session,
    client_id: str,
    research_result_id: str,
    data: dict,
) -> dict:
    """Unpack a KeywordStrategy JSON blob into client_keywords rows.

    Called automatically after the seo_keyword_research tool stores its result.
    Does not overwrite manual edits — uses bulk_upsert with source='research_tool'.
    """
    from backend.schemas.keyword_schemas import KeywordCreate, KeywordType

    def _kw_obj(raw, ktype: KeywordType) -> Optional[KeywordCreate]:
        if isinstance(raw, str):
            text = raw.strip()
        elif isinstance(raw, dict):
            text = (raw.get("keyword") or "").strip()
        else:
            return None
        if len(text) < 2:
            return None
        try:
            return KeywordCreate(
                keyword=text,
                keyword_type=ktype,
                search_intent=raw.get("search_intent") if isinstance(raw, dict) else None,
                difficulty=raw.get("difficulty") if isinstance(raw, dict) else None,
                monthly_volume=(
                    raw.get("monthly_volume_estimate") if isinstance(raw, dict) else None
                ),
                relevance_score=(raw.get("relevance_score") if isinstance(raw, dict) else None),
                quality_score=(raw.get("quality_score") if isinstance(raw, dict) else None),
            )
        except ValidationError:
            # e.g. keyword > 200 chars, or negative keyword > 100 chars — skip silently
            return None

    rows: List[KeywordCreate] = []
    for kw in (data.get("primary_keywords") or [])[:_MAX_PER_TYPE]:
        obj = _kw_obj(kw, KeywordType.primary)
        if obj:
            rows.append(obj)
    for kw in (data.get("secondary_keywords") or [])[:_MAX_PER_TYPE]:
        obj = _kw_obj(kw, KeywordType.secondary)
        if obj:
            rows.append(obj)
    for kw in (data.get("quick_win_keywords") or [])[:_MAX_PER_TYPE]:
        obj = _kw_obj(kw, KeywordType.quick_win)
        if obj:
            rows.append(obj)
    # Negative keywords: use _kw_obj so dict-format entries are handled consistently
    # and oversized keywords are skipped rather than raising ValidationError.
    for neg in (data.get("negative_keywords") or [])[:_MAX_PER_TYPE]:
        obj = _kw_obj(neg, KeywordType.negative)
        if obj:
            rows.append(obj)

    if not rows:
        return {"imported": 0, "skipped": 0, "deactivated": 0}

    # The entire reseed is one unit of work.  The try/except wraps ALL steps so that
    # any failure — including db.flush(), bulk_upsert_keywords, or db.commit() —
    # triggers db.rollback().  Without this, a failure inside db.flush() or inside
    # bulk_upsert_keywords (before the narrower try/except that previously only
    # wrapped db.commit()) would leave the shared session with dirty flushed state
    # that could be implicitly committed by the next operation on the same session.
    try:
        # ── Step 1: lock and deactivate stale keywords BEFORE upserting new ones ──
        #
        # Doing this first fixes two problems:
        #   (a) Atomicity — stale deactivation and new upsert share one db.commit().
        #   (b) Cap accuracy — if the old run was at cap, deactivating first frees
        #       slots so new keywords are not incorrectly blocked.
        #
        # "Stale" = source="research_tool" + is_active=True + not from this run.
        # or_(...is_(None)) catches the edge case where SQL `!= new_id` evaluates
        # to NULL (not TRUE) for rows with NULL research_result_id.
        # Manually-edited keywords (source="manual") are never touched.
        stale = (
            db.query(ClientKeyword)
            .filter(
                ClientKeyword.client_id == client_id,
                ClientKeyword.source == "research_tool",
                ClientKeyword.is_active.is_(True),
                or_(
                    ClientKeyword.research_result_id != research_result_id,
                    ClientKeyword.research_result_id.is_(None),
                ),
            )
            .with_for_update()
            .all()
        )
        stale_ids: List[int] = []
        for kw in stale:
            setattr(kw, "is_active", False)
            stale_ids.append(int(kw.id))

        # Flush deactivations so _count_and_lock_active inside bulk_upsert_keywords
        # sees the updated counts — critical when the old run filled the per-type cap.
        if stale_ids:
            db.flush()

        # ── Step 2: upsert new keywords in the same open transaction ──────────────
        upsert_result = bulk_upsert_keywords(
            db,
            client_id=client_id,
            keywords=rows,
            source="research_tool",
            research_result_id=research_result_id,
            _commit=False,  # caller owns the commit — one transaction for everything
        )

        # ── Step 3: single atomic commit ──────────────────────────────────────────
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"seed_from_research_result failed for client {client_id}: {e}")
        raise

    # Count net deactivations: stale keywords still inactive after the upsert.
    # Some stale keywords appear in the new result too — the upsert reactivated them.
    if stale_ids:
        deactivated = (
            db.query(ClientKeyword)
            .filter(
                ClientKeyword.id.in_(stale_ids),
                ClientKeyword.is_active.is_(False),
            )
            .count()
        )
    else:
        deactivated = 0

    upsert_result["deactivated"] = deactivated
    return upsert_result
