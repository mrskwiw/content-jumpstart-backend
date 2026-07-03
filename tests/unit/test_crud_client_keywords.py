"""Unit tests for crud_client_keywords service functions.

Uses an in-memory SQLite database (same StaticPool pattern as integration conftest)
so these tests exercise real SQL without requiring a running server.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401 — registers all models before create_all
from backend.database import Base
from backend.models.client_keywords import ClientKeyword
from backend.schemas.keyword_schemas import KeywordCreate, KeywordType, KeywordUpdate
from backend.services.crud_client_keywords import (
    _count_and_lock_active,
    bulk_upsert_keywords,
    count_active_by_type,
    create_keyword,
    get_keyword,
    get_keywords_for_client,
    seed_from_research_result,
    soft_delete_keyword,
    update_keyword,
)


# ---------------------------------------------------------------------------
# Session fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


CLIENT_ID = "client-unit-001"
CLIENT_ID_2 = "client-unit-002"


def _primary(text: str) -> KeywordCreate:
    return KeywordCreate(keyword=text, keyword_type=KeywordType.primary)


def _negative(text: str) -> KeywordCreate:
    return KeywordCreate(keyword=text, keyword_type=KeywordType.negative)


# ---------------------------------------------------------------------------
# create_keyword
# ---------------------------------------------------------------------------


class TestCreateKeyword:
    def test_creates_and_returns_row(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("content strategy"))
        assert kw is not None
        assert kw.keyword == "content strategy"
        assert kw.keyword_type == KeywordType.primary
        assert kw.source == "manual"
        assert kw.is_active is True

    def test_normalises_to_lowercase(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("SEO AUDIT"))
        assert kw.keyword == "seo audit"

    def test_duplicate_returns_none(self, db):
        create_keyword(db, CLIENT_ID, _primary("duplicate kw"))
        result = create_keyword(db, CLIENT_ID, _primary("duplicate kw"))
        # Active duplicate — returns None (no reactivation needed)
        assert result is None

    def test_reactivates_soft_deleted_duplicate(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("reactivate me"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        # Row now inactive — creating same keyword should reactivate
        result = create_keyword(db, CLIENT_ID, _primary("reactivate me"))
        assert result is not None
        assert result.is_active is True

    def test_create_reactivation_applies_caller_metadata(self, db):
        """Path-1 regression: when create_keyword reactivates a soft-deleted row via the
        IntegrityError path, the caller's metadata must be applied to the returned row.
        Without this, the operator POSTs with specific metadata and gets back stale
        research data — bad output that was never gated."""
        # Seed a research_tool keyword with old metadata, then soft-delete it
        old_kw = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="overlap kw",
                keyword_type=KeywordType.primary,
                search_intent="informational",
                difficulty="medium",
            ),
            source="research_tool",
        )
        assert old_kw is not None
        soft_delete_keyword(db, old_kw.id, CLIENT_ID)

        # Operator creates the same keyword with their own metadata
        result = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="overlap kw",
                keyword_type=KeywordType.primary,
                search_intent="commercial",
                difficulty="low",
            ),
            source="manual",
        )
        assert result is not None
        assert (
            result.search_intent == "commercial"
        ), "create_keyword reactivation path must apply caller's search_intent"
        assert (
            result.difficulty == "low"
        ), "create_keyword reactivation path must apply caller's difficulty"

    def test_create_reactivation_preserves_fields_not_in_caller_data(self, db):
        """When caller doesn't supply a field (None), the existing value is preserved."""
        old_kw = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="partial update kw",
                keyword_type=KeywordType.primary,
                search_intent="informational",
                difficulty="medium",
            ),
            source="research_tool",
        )
        assert old_kw is not None
        soft_delete_keyword(db, old_kw.id, CLIENT_ID)

        # Caller only specifies difficulty; search_intent not in request
        result = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="partial update kw", keyword_type=KeywordType.primary, difficulty="high"
            ),  # search_intent intentionally omitted
            source="manual",
        )
        assert result is not None
        assert result.difficulty == "high"
        assert (
            result.search_intent == "informational"
        ), "unspecified fields in create request must preserve existing values"

    def test_manual_create_reactivation_claims_research_tool_row(self, db):
        """Guard-leak regression: create_keyword IntegrityError path must flip source to
        'manual' when a manual caller reactivates a soft-deleted research_tool row.
        Without this, existing.source stays 'research_tool' and the bulk_upsert guard
        lets a subsequent research re-run overwrite the operator's keyword."""
        # Research tool seeds the keyword, then it gets soft-deleted
        kw = create_keyword(db, CLIENT_ID, _primary("seeded kw"), source="research_tool")
        assert kw is not None
        assert kw.source == "research_tool"
        soft_delete_keyword(db, kw.id, CLIENT_ID)

        # Operator creates the same keyword via POST — hits IntegrityError, reactivates
        result = create_keyword(db, CLIENT_ID, _primary("seeded kw"), source="manual")
        assert result is not None
        assert result.is_active is True
        assert (
            result.source == "manual"
        ), "create_keyword reactivation path must flip source to 'manual' for manual callers"

        # Verify guard holds: research re-run must not overwrite
        research_kw = KeywordCreate(
            keyword="seeded kw",
            keyword_type=KeywordType.primary,
            search_intent="informational",
        )
        bulk_upsert_keywords(db, CLIENT_ID, [research_kw], source="research_tool")
        db.refresh(result)
        assert result.search_intent is None, "research re-run overwrote after manual reactivation"

    def test_research_tool_reactivation_does_not_downgrade_manual_source(self, db):
        """The IntegrityError path must never downgrade 'manual' → 'research_tool'."""
        kw = create_keyword(db, CLIENT_ID, _primary("manual kw"), source="manual")
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)

        # Research tool tries to reactivate the same keyword
        result = create_keyword(db, CLIENT_ID, _primary("manual kw"), source="research_tool")
        assert result is not None
        assert (
            result.source == "manual"
        ), "create_keyword must not downgrade source from 'manual' to 'research_tool'"

    def test_source_manual_default(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("test kw"))
        assert kw.source == "manual"

    def test_source_research_tool_override(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("researched kw"), source="research_tool")
        assert kw.source == "research_tool"

    def test_max_50_per_type_raises(self, db):
        for i in range(50):
            create_keyword(db, CLIENT_ID, _primary(f"keyword {i:03d}"))
        with pytest.raises(ValueError, match="Maximum 50"):
            create_keyword(db, CLIENT_ID, _primary("overflow kw"))

    def test_different_types_independent_limits(self, db):
        """50 primary + 1 negative should not hit the primary cap."""
        for i in range(50):
            create_keyword(db, CLIENT_ID, _primary(f"primary kw {i:03d}"))
        neg = create_keyword(db, CLIENT_ID, _negative("separate type kw"))
        assert neg is not None

    def test_different_clients_independent(self, db):
        create_keyword(db, CLIENT_ID, _primary("same keyword"))
        kw2 = create_keyword(db, CLIENT_ID_2, _primary("same keyword"))
        assert kw2 is not None  # Different client — no conflict


# ---------------------------------------------------------------------------
# get_keywords_for_client
# ---------------------------------------------------------------------------


class TestGetKeywordsForClient:
    def test_returns_all_active(self, db):
        create_keyword(db, CLIENT_ID, _primary("kw one"))
        create_keyword(db, CLIENT_ID, _negative("bad keyword"))
        rows = get_keywords_for_client(db, CLIENT_ID)
        assert len(rows) == 2

    def test_filters_inactive(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("to delete"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        rows = get_keywords_for_client(db, CLIENT_ID)
        assert len(rows) == 0

    def test_active_only_false_returns_all(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("to delete"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        rows = get_keywords_for_client(db, CLIENT_ID, active_only=False)
        assert len(rows) == 1

    def test_type_filter(self, db):
        create_keyword(db, CLIENT_ID, _primary("primary one"))
        create_keyword(db, CLIENT_ID, _negative("negative one"))
        primaries = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")
        assert len(primaries) == 1
        assert primaries[0].keyword_type == "primary"

    def test_scoped_to_client(self, db):
        create_keyword(db, CLIENT_ID, _primary("kw for client 1"))
        create_keyword(db, CLIENT_ID_2, _primary("kw for client 2"))
        rows = get_keywords_for_client(db, CLIENT_ID)
        assert all(r.client_id == CLIENT_ID for r in rows)


# ---------------------------------------------------------------------------
# get_keyword
# ---------------------------------------------------------------------------


class TestGetKeyword:
    def test_fetches_by_id_and_client(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("fetch me"))
        assert kw is not None
        found = get_keyword(db, kw.id, CLIENT_ID)
        assert found is not None
        assert found.id == kw.id

    def test_wrong_client_returns_none(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("wrong client check"))
        assert kw is not None
        found = get_keyword(db, kw.id, CLIENT_ID_2)
        assert found is None


# ---------------------------------------------------------------------------
# update_keyword
# ---------------------------------------------------------------------------


class TestUpdateKeyword:
    def test_updates_keyword_text(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("old text"))
        assert kw is not None
        updated = update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(keyword="new text"))
        assert updated is not None
        assert updated.keyword == "new text"

    def test_update_strips_whitespace(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("old"))
        assert kw is not None
        updated = update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(keyword="  trimmed  "))
        assert updated is not None
        assert updated.keyword == "trimmed"

    def test_update_notes(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("kw with notes"))
        assert kw is not None
        updated = update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(notes="Important context"))
        assert updated is not None
        assert updated.notes == "Important context"

    def test_deactivate_via_update(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("deactivate via update"))
        assert kw is not None
        updated = update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(is_active=False))
        assert updated is not None
        assert updated.is_active is False

    def test_wrong_client_returns_none(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("protected kw"))
        assert kw is not None
        result = update_keyword(db, kw.id, CLIENT_ID_2, KeywordUpdate(keyword="hacked"))
        assert result is None

    def test_content_field_edit_flips_source_to_manual(self, db):
        """Guard-leak regression: updating a content field via PUT must flip source to 'manual'
        so subsequent research_tool re-runs won't overwrite the operator's values."""
        kw = create_keyword(db, CLIENT_ID, _primary("research seeded"), source="research_tool")
        assert kw is not None
        assert kw.source == "research_tool"

        updated = update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(search_intent="commercial"))
        assert updated is not None
        assert (
            updated.source == "manual"
        ), "update_keyword must flip source to 'manual' when a content field is changed"

        # Verify: a research_tool re-run now respects the guard and does NOT overwrite
        research_kw = KeywordCreate(
            keyword="research seeded",
            keyword_type=KeywordType.primary,
            search_intent="informational",  # different from operator's "commercial"
        )
        bulk_upsert_keywords(db, CLIENT_ID, [research_kw], source="research_tool")
        db.refresh(updated)
        assert (
            updated.search_intent == "commercial"
        ), "research_tool overwrote manually-set search_intent after source was flipped"

    def test_deactivation_only_does_not_flip_source(self, db):
        """Soft-deleting via PUT (is_active=False) should NOT flip source — the operator
        is archiving the keyword, not claiming content ownership."""
        kw = create_keyword(db, CLIENT_ID, _primary("research kw"), source="research_tool")
        assert kw is not None
        update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(is_active=False))
        db.refresh(kw)
        assert kw.source == "research_tool", "deactivation must not flip source"

    def test_reactivation_flips_source_to_manual(self, db):
        """Guard-leak regression: reactivating via PUT (is_active=True) must flip source
        to 'manual'. Without this, a research re-run hits existing.source='research_tool'
        and overwrites the metadata of a keyword the operator explicitly brought back."""
        kw = create_keyword(db, CLIENT_ID, _primary("to reactivate"), source="research_tool")
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)

        # Operator reactivates — this is a deliberate ownership claim
        update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(is_active=True))
        db.refresh(kw)
        assert kw.source == "manual", "reactivation via PUT must flip source to 'manual'"

        # Verify: research re-run now respects the guard
        research_kw = KeywordCreate(
            keyword="to reactivate",
            keyword_type=KeywordType.primary,
            search_intent="informational",
            difficulty="low",
        )
        bulk_upsert_keywords(db, CLIENT_ID, [research_kw], source="research_tool")
        db.refresh(kw)
        # Metadata should be unchanged (guard blocked the overwrite)
        assert kw.search_intent is None, "research re-run overwrote after reactivation"

    def test_reactivation_at_cap_raises_value_error(self, db):
        """Cap regression: update_keyword must enforce _MAX_PER_TYPE when reactivating.
        Without this check, PUT {is_active: true} on a soft-deleted keyword bypasses
        the limit enforced by create_keyword and bulk_upsert_keywords."""
        # Create 49 active, then create the "to reactivate" keyword (50th active)
        for i in range(49):
            create_keyword(db, CLIENT_ID, _primary(f"active {i:03d}"))
        kw = create_keyword(db, CLIENT_ID, _primary("to reactivate"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)  # 49 active + 1 soft-deleted
        # Fill the 50th slot
        create_keyword(db, CLIENT_ID, _primary("slot 50 filler"))
        # Now: 50 active + 1 soft-deleted — reactivation must be rejected
        with pytest.raises(ValueError, match="Maximum 50"):
            update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(is_active=True))
        # Confirm the row is still inactive
        db.refresh(kw)
        assert kw.is_active is False

    def test_is_active_true_on_already_active_keyword_does_not_flip_source(self, db):
        """Path-2 regression: sending is_active=True to an already-active research_tool keyword
        is a noop on state; it must NOT claim the row as 'manual'. The gate should only
        fire on a genuine False→True transition, not on any is_active=True payload."""
        kw = create_keyword(db, CLIENT_ID, _primary("active rt kw"), source="research_tool")
        assert kw is not None
        assert kw.is_active is True

        # Operator sends is_active=True to an already-active keyword (e.g. defensive PUT)
        update_keyword(db, kw.id, CLIENT_ID, KeywordUpdate(is_active=True))
        db.refresh(kw)
        assert (
            kw.source == "research_tool"
        ), "is_active=True on an already-active keyword must not flip source"

    def test_nonexistent_id_returns_none(self, db):
        result = update_keyword(db, 99999, CLIENT_ID, KeywordUpdate(keyword="ghost"))
        assert result is None


# ---------------------------------------------------------------------------
# soft_delete_keyword
# ---------------------------------------------------------------------------


class TestSoftDeleteKeyword:
    def test_soft_delete_marks_inactive(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("soft delete me"))
        assert kw is not None
        result = soft_delete_keyword(db, kw.id, CLIENT_ID)
        assert result is True
        # Row should still exist but inactive
        row = db.query(ClientKeyword).filter(ClientKeyword.id == kw.id).first()
        assert row is not None
        assert row.is_active is False

    def test_wrong_client_returns_false(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("protected delete"))
        assert kw is not None
        result = soft_delete_keyword(db, kw.id, CLIENT_ID_2)
        assert result is False

    def test_nonexistent_returns_false(self, db):
        result = soft_delete_keyword(db, 99999, CLIENT_ID)
        assert result is False


# ---------------------------------------------------------------------------
# count_active_by_type
# ---------------------------------------------------------------------------


class TestCountActiveByType:
    def test_count_empty(self, db):
        assert count_active_by_type(db, CLIENT_ID, "primary") == 0

    def test_count_increases(self, db):
        create_keyword(db, CLIENT_ID, _primary("one"))
        create_keyword(db, CLIENT_ID, _primary("two"))
        assert count_active_by_type(db, CLIENT_ID, "primary") == 2

    def test_soft_deleted_not_counted(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("to delete"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        assert count_active_by_type(db, CLIENT_ID, "primary") == 0


class TestCountAndLockActive:
    """_count_and_lock_active must return the same values as count_active_by_type.
    Full concurrency serialisation is a property of FOR UPDATE locking that cannot
    be exercised in a single-threaded unit test, but we verify the count is correct
    and that the cap-enforcement call sites use the locking variant."""

    def test_empty(self, db):
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == 0

    def test_matches_plain_count(self, db):
        create_keyword(db, CLIENT_ID, _primary("kw one"))
        create_keyword(db, CLIENT_ID, _primary("kw two"))
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == 2
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == count_active_by_type(
            db, CLIENT_ID, "primary"
        )

    def test_excludes_soft_deleted(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("soft deleted"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == 0

    def test_scoped_to_client(self, db):
        create_keyword(db, CLIENT_ID, _primary("client 1 kw"))
        create_keyword(db, CLIENT_ID_2, _primary("client 2 kw"))
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == 1
        assert _count_and_lock_active(db, CLIENT_ID_2, "primary") == 1

    def test_scoped_to_type(self, db):
        create_keyword(db, CLIENT_ID, _primary("primary kw"))
        create_keyword(db, CLIENT_ID, _negative("negative kw"))
        assert _count_and_lock_active(db, CLIENT_ID, "primary") == 1
        assert _count_and_lock_active(db, CLIENT_ID, "negative") == 1


# ---------------------------------------------------------------------------
# bulk_upsert_keywords
# ---------------------------------------------------------------------------


class TestBulkUpsertKeywords:
    def test_bulk_inserts_new(self, db):
        keywords = [_primary("bulk one"), _primary("bulk two"), _negative("bad term")]
        result = bulk_upsert_keywords(db, CLIENT_ID, keywords)
        assert result["imported"] == 3
        assert result["skipped"] == 0

    def test_existing_counted_as_skipped(self, db):
        create_keyword(db, CLIENT_ID, _primary("already here"))
        result = bulk_upsert_keywords(db, CLIENT_ID, [_primary("already here")])
        assert result["skipped"] == 1
        assert result["imported"] == 0

    def test_preserves_manual_source_on_conflict(self, db):
        kw = create_keyword(db, CLIENT_ID, _primary("human edited"), source="manual")
        assert kw is not None
        # Research tool tries to overwrite the same kw
        bulk_upsert_keywords(db, CLIENT_ID, [_primary("human edited")], source="research_tool")
        db.refresh(kw)
        # Source should remain manual (not downgraded)
        assert kw.source == "manual"

    def test_manual_bulk_upsert_claims_research_tool_row(self, db):
        """Guard-leak regression: a manual bulk-edit on a research_tool row must flip
        source to 'manual' so subsequent research re-runs don't overwrite the changes."""
        kw = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="claimed kw",
                keyword_type=KeywordType.primary,
                search_intent="informational",
            ),
            source="research_tool",
        )
        assert kw is not None

        # Operator corrects the search_intent via bulk endpoint
        manual_kw = KeywordCreate(
            keyword="claimed kw",
            keyword_type=KeywordType.primary,
            search_intent="commercial",
        )
        bulk_upsert_keywords(db, CLIENT_ID, [manual_kw], source="manual")
        db.refresh(kw)
        assert kw.source == "manual", "manual bulk-edit must claim the row"
        assert kw.search_intent == "commercial"

        # Now a research re-run should NOT overwrite
        research_kw = KeywordCreate(
            keyword="claimed kw",
            keyword_type=KeywordType.primary,
            search_intent="informational",
        )
        bulk_upsert_keywords(db, CLIENT_ID, [research_kw], source="research_tool")
        db.refresh(kw)
        assert kw.search_intent == "commercial", "research re-run overwrote manual bulk edit"

    def test_research_tool_does_not_overwrite_manual_metadata(self, db):
        """Bug regression: research_tool upsert must NOT overwrite manually-set metadata."""
        kw = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="my manual kw",
                keyword_type=KeywordType.primary,
                search_intent="navigational",
                difficulty="low",
            ),
            source="manual",
        )
        assert kw is not None
        # Research tool re-runs with different metadata for the same keyword
        research_kw = KeywordCreate(
            keyword="my manual kw",
            keyword_type=KeywordType.primary,
            search_intent="commercial",  # would overwrite with bug
            difficulty="high",  # would overwrite with bug
        )
        bulk_upsert_keywords(db, CLIENT_ID, [research_kw], source="research_tool")
        db.refresh(kw)
        # Manual values must be preserved
        assert kw.search_intent == "navigational", "research_tool overwrote manual search_intent"
        assert kw.difficulty == "low", "research_tool overwrote manual difficulty"
        assert kw.source == "manual"

    def test_research_tool_updates_research_tool_metadata(self, db):
        """Bug regression: research_tool upsert SHOULD refresh metadata on research_tool rows."""
        kw = create_keyword(
            db,
            CLIENT_ID,
            KeywordCreate(
                keyword="research kw",
                keyword_type=KeywordType.primary,
                search_intent="informational",
                difficulty="medium",
            ),
            source="research_tool",
        )
        assert kw is not None
        # Research tool re-runs with updated metadata
        updated_kw = KeywordCreate(
            keyword="research kw",
            keyword_type=KeywordType.primary,
            search_intent="commercial",
            difficulty="high",
        )
        bulk_upsert_keywords(db, CLIENT_ID, [updated_kw], source="research_tool")
        db.refresh(kw)
        # Research data should be refreshed
        assert kw.search_intent == "commercial"
        assert kw.difficulty == "high"

    def test_research_tool_reactivates_soft_deleted_research_tool_keyword(self, db):
        """Bug regression: a research_tool soft-deleted keyword must be reactivated
        by a research_tool bulk_upsert (was blocked by inverted source condition)."""
        kw = create_keyword(db, CLIENT_ID, _primary("research kw"), source="research_tool")
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        # Confirm it's inactive
        assert get_keywords_for_client(db, CLIENT_ID) == []

        # Re-run research tool — must reactivate
        bulk_upsert_keywords(db, CLIENT_ID, [_primary("research kw")], source="research_tool")
        rows = get_keywords_for_client(db, CLIENT_ID)
        assert len(rows) == 1, "research_tool keyword was not reactivated"
        assert rows[0].is_active is True

    def test_research_tool_reactivation_does_not_corrupt_in_flight_count(self, db):
        """Bug regression: if the reactivation path skips setattr(is_active=True)
        but still increments in_flight, subsequent cap checks are wrong."""
        for i in range(48):
            create_keyword(db, CLIENT_ID, _primary(f"existing {i:03d}"), source="research_tool")
        kw = create_keyword(db, CLIENT_ID, _primary("to reactivate"), source="research_tool")
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        # 48 active + 1 soft-deleted

        # Re-add: reactivation (1 slot used) + 1 genuinely new (fits) + 1 that should be blocked
        result = bulk_upsert_keywords(
            db,
            CLIENT_ID,
            [
                _primary("to reactivate"),  # reactivation: committed=48, in_flight→1
                _primary("new kw one"),  # new: committed=48, in_flight=1 → 49 < 50 → OK
                _primary("new kw two"),  # new: committed=48, in_flight=2 → 50 → blocked
            ],
            source="research_tool",
        )
        assert result["imported"] == 1  # "new kw one"
        assert result["skipped"] == 2  # "to reactivate" (existing branch) + "new kw two" (blocked)
        assert count_active_by_type(db, CLIENT_ID, "primary") == 50

    def test_max_per_type_respected_in_bulk(self, db):
        for i in range(50):
            create_keyword(db, CLIENT_ID, _primary(f"existing {i:03d}"))
        overflow_kws = [_primary("overflow one"), _primary("overflow two")]
        result = bulk_upsert_keywords(db, CLIENT_ID, overflow_kws)
        assert result["skipped"] == 2
        assert result["imported"] == 0

    def test_per_type_limit_enforced_not_total_list_limit(self, db):
        """The loop no longer slices the input — per-type limit is enforced item by item."""
        keywords = [_primary(f"keyword {i:03d}") for i in range(60)]
        result = bulk_upsert_keywords(db, CLIENT_ID, keywords)
        # First 50 primaries imported; last 10 skipped because type is full
        assert result["imported"] == 50
        assert result["skipped"] == 10

    def test_cross_type_list_not_truncated(self, db):
        """Bug regression: a multi-type list must NOT be truncated to 50 total items.
        All four types must be processed even when the list exceeds 50 items total."""
        keywords = (
            [_primary(f"primary {i:03d}") for i in range(10)]
            + [
                KeywordCreate(keyword=f"secondary {i:03d}", keyword_type=KeywordType.secondary)
                for i in range(10)
            ]
            + [
                KeywordCreate(keyword=f"quick win {i:03d}", keyword_type=KeywordType.quick_win)
                for i in range(10)
            ]
            + [_negative(f"neg term {i:03d}") for i in range(10)]
        )  # 40 total, 10 per type
        result = bulk_upsert_keywords(db, CLIENT_ID, keywords)
        assert result["imported"] == 40, "All four types must be imported"
        # Verify per-type by querying directly
        for ktype in ("primary", "secondary", "quick_win", "negative"):
            rows = get_keywords_for_client(db, CLIENT_ID, keyword_type=ktype)
            assert len(rows) == 10, f"Expected 10 {ktype} keywords, got {len(rows)}"

    def test_in_flight_count_prevents_exceeding_limit(self, db):
        """Bug regression: count_active_by_type is stale under autoflush=False.
        Pending inserts in the same batch must count toward the per-type cap."""
        # Start with 48 existing primaries
        for i in range(48):
            create_keyword(db, CLIENT_ID, _primary(f"pre-existing {i:03d}"))
        # Try to add 5 more in one bulk call — only 2 should succeed
        new_kws = [_primary(f"new kw {i:03d}") for i in range(5)]
        result = bulk_upsert_keywords(db, CLIENT_ID, new_kws)
        assert result["imported"] == 2
        assert result["skipped"] == 3
        # Confirm total does not exceed 50
        total = count_active_by_type(db, CLIENT_ID, "primary")
        assert total == 50, f"Expected exactly 50, got {total}"


# ---------------------------------------------------------------------------
# seed_from_research_result
# ---------------------------------------------------------------------------


class TestSeedFromResearchResult:
    _RESEARCH_ID = "rr-unit-test-001"

    def _seo_payload(self) -> dict:
        return {
            "primary_keywords": [
                {
                    "keyword": "content marketing",
                    "search_intent": "informational",
                    "difficulty": "medium",
                },
                "seo strategy",
            ],
            "secondary_keywords": ["blog writing tips", "social media content"],
            "quick_win_keywords": ["easy seo win"],
            "negative_keywords": ["free", "cheap"],
        }

    def test_seeds_all_types(self, db):
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, self._seo_payload())
        assert result["imported"] == 7  # 2 primary + 2 secondary + 1 quick_win + 2 negative

    def test_idempotent_second_call(self, db):
        seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, self._seo_payload())
        result2 = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, self._seo_payload())
        # All already exist — should be 0 imported
        assert result2["imported"] == 0
        assert result2["skipped"] > 0

    def test_empty_payload_returns_zero(self, db):
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, {})
        assert result == {"imported": 0, "skipped": 0, "deactivated": 0}

    def test_dict_keyword_extracts_text(self, db):
        payload = {"primary_keywords": [{"keyword": "dict keyword"}]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        assert result["imported"] == 1
        row = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")[0]
        assert row.keyword == "dict keyword"

    def test_string_keyword_ingested(self, db):
        payload = {"negative_keywords": ["cheap", "free service"]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        assert result["imported"] == 2

    def test_short_keywords_skipped(self, db):
        """Keywords shorter than 2 chars are ignored."""
        payload = {"primary_keywords": ["a", "ok"]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        # "a" skipped, "ok" imported
        assert result["imported"] == 1

    def test_does_not_overwrite_manual_edits(self, db):
        create_keyword(db, CLIENT_ID, _primary("content marketing"), source="manual")
        payload = {"primary_keywords": ["content marketing"]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        # Should be skipped because it already exists (manual preserved)
        assert result["skipped"] >= 1
        row = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")[0]
        assert row.source == "manual"

    # --- Edge case regression tests ---

    def test_oversized_keyword_skipped_not_raises(self, db):
        """Edge case: keyword > 200 chars in research data must be skipped, not raise 500."""
        payload = {
            "primary_keywords": ["x" * 201, "valid keyword"],
            "negative_keywords": ["a" * 101, "cheap"],
        }
        # Must not raise ValidationError
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        # Oversized ones silently dropped; valid ones imported
        assert result["imported"] == 2  # "valid keyword" + "cheap"

    def test_dict_format_negative_keywords_not_dropped(self, db):
        """Edge case: negative keywords in dict format must be handled like other types."""
        payload = {
            "negative_keywords": [
                {"keyword": "cheap services", "reason": "low intent"},
                "free stuff",
            ]
        }
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        assert result["imported"] == 2
        rows = get_keywords_for_client(db, CLIENT_ID, keyword_type="negative")
        keywords = {r.keyword for r in rows}
        assert "cheap services" in keywords
        assert "free stuff" in keywords

    def test_negative_keyword_exactly_100_chars_accepted(self, db):
        payload = {"negative_keywords": ["b" * 100]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        assert result["imported"] == 1

    def test_negative_keyword_101_chars_skipped_not_raises(self, db):
        payload = {"negative_keywords": ["b" * 101]}
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, payload)
        assert result["imported"] == 0

    def test_research_result_id_updated_on_existing_keyword_after_rerun(self, db):
        """Citation-gate regression: when a re-run refreshes an existing research_tool keyword,
        research_result_id must be updated to the new run's ID so the stale-keyword filter
        can correctly distinguish 'refreshed this run' from 'genuinely from an old run'."""
        old_rr_id = "rr-old-001"
        new_rr_id = "rr-new-002"
        # First run seeds "content strategy"
        seed_from_research_result(
            db,
            CLIENT_ID,
            old_rr_id,
            {"primary_keywords": ["content strategy"]},
        )
        kw = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")[0]
        assert kw.research_result_id == old_rr_id

        # Re-run with same keyword — research_result_id must be updated
        seed_from_research_result(
            db,
            CLIENT_ID,
            new_rr_id,
            {"primary_keywords": ["content strategy"]},
        )
        db.refresh(kw)
        assert (
            kw.research_result_id == new_rr_id
        ), "research_result_id must be updated to new run ID after re-seed"

    def test_stale_keywords_from_old_run_deactivated_on_rerun(self, db):
        """Stale-QA regression: keywords from an old research run that the new run
        no longer includes must be deactivated, not left active indefinitely."""
        old_rr_id = "rr-old-001"
        new_rr_id = "rr-new-002"
        # First run seeds "content strategy" + "seo audit"
        seed_from_research_result(
            db,
            CLIENT_ID,
            old_rr_id,
            {"primary_keywords": ["content strategy", "seo audit"]},
        )
        assert len(get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")) == 2

        # Re-run only returns "content strategy" — "seo audit" is now stale
        result = seed_from_research_result(
            db,
            CLIENT_ID,
            new_rr_id,
            {"primary_keywords": ["content strategy"]},
        )
        assert result["deactivated"] == 1, "stale 'seo audit' must be deactivated"
        active = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")
        assert len(active) == 1
        assert active[0].keyword == "content strategy"

    def test_stale_cleanup_does_not_touch_manual_keywords(self, db):
        """Stale cleanup must never deactivate manually-edited keywords,
        even if they share a keyword_type with stale research_tool ones."""
        old_rr_id = "rr-old-001"
        new_rr_id = "rr-new-002"
        # Seed one research_tool keyword
        seed_from_research_result(
            db,
            CLIENT_ID,
            old_rr_id,
            {"primary_keywords": ["research kw"]},
        )
        # Operator adds a manual keyword of the same type
        create_keyword(db, CLIENT_ID, _primary("manual kw"), source="manual")

        # Re-run: neither keyword is in the new result
        result = seed_from_research_result(
            db,
            CLIENT_ID,
            new_rr_id,
            {"primary_keywords": ["brand new kw"]},
        )
        # "research kw" (research_tool) → deactivated
        # "manual kw" (manual) → preserved
        assert result["deactivated"] == 1
        active = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")
        active_kws = {r.keyword for r in active}
        assert "manual kw" in active_kws, "manual keyword must survive stale cleanup"
        assert "research kw" not in active_kws, "stale research keyword must be deactivated"

    def test_empty_payload_early_return_includes_deactivated_key(self, db):
        """The early-return path must include 'deactivated' in the result dict."""
        result = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, {})
        assert "deactivated" in result
        assert result["deactivated"] == 0

    def test_idempotent_rerun_does_not_deactivate_current_keywords(self, db):
        """Re-seeding with the same data and same result_id must not deactivate anything."""
        seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, self._seo_payload())
        result2 = seed_from_research_result(db, CLIENT_ID, self._RESEARCH_ID, self._seo_payload())
        assert result2["deactivated"] == 0, "idempotent re-seed must not deactivate"

    def test_rerun_at_cap_replaces_stale_keywords(self, db):
        """Cap-edge-case regression: when old run fills the cap (50), a re-run must be
        able to replace all old keywords.  Without deactivating stale rows first, the
        cap check blocks the new keywords and the type ends up nearly empty."""
        old_rr_id = "rr-old-cap"
        new_rr_id = "rr-new-cap"
        # Fill the primary cap with old research keywords
        payload_old = {"primary_keywords": [f"old kw {i:03d}" for i in range(50)]}
        seed_from_research_result(db, CLIENT_ID, old_rr_id, payload_old)
        assert count_active_by_type(db, CLIENT_ID, "primary") == 50

        # Re-run with completely different keywords (no overlap)
        payload_new = {"primary_keywords": [f"new kw {i:03d}" for i in range(30)]}
        result = seed_from_research_result(db, CLIENT_ID, new_rr_id, payload_new)

        assert (
            result["imported"] == 30
        ), "new keywords must be importable after stale rows are deactivated first"
        assert result["deactivated"] == 50, "all 50 old keywords must be deactivated"
        assert count_active_by_type(db, CLIENT_ID, "primary") == 30

    def test_session_is_clean_after_pre_commit_failure(self, db):
        """Session-leak regression: if bulk_upsert_keywords raises before db.commit(),
        the outer try/except must call db.rollback() so the shared session has no
        dirty flushed state.  Without the wider try/except, a failed flush or upsert
        would leave stale deactivations staged in the open transaction; the next
        operation on the same session could silently commit them."""
        from unittest.mock import patch

        old_rr_id = "rr-old-leak"
        new_rr_id = "rr-new-leak"
        # Seed two keywords from old run
        seed_from_research_result(
            db,
            CLIENT_ID,
            old_rr_id,
            {"primary_keywords": ["keyword a", "keyword b"]},
        )
        assert count_active_by_type(db, CLIENT_ID, "primary") == 2

        # Patch bulk_upsert_keywords to raise AFTER stale deactivations are flushed
        with patch(
            "backend.services.crud_client_keywords.bulk_upsert_keywords",
            side_effect=RuntimeError("simulated pre-commit failure"),
        ):
            with pytest.raises(RuntimeError, match="simulated pre-commit failure"):
                seed_from_research_result(
                    db,
                    CLIENT_ID,
                    new_rr_id,
                    {"primary_keywords": ["keyword a"]},
                )

        # After the rolled-back failure, BOTH keywords must still be active —
        # the stale deactivations must have been rolled back, not persisted.
        assert (
            count_active_by_type(db, CLIENT_ID, "primary") == 2
        ), "session-leaked partial deactivations were committed — rollback did not clean up"

    def test_stale_keywords_with_null_research_result_id_deactivated(self, db):
        """NULL research_result_id edge case: SQL `!= new_id` evaluates to NULL for NULL
        rows, so they would never be deactivated without the explicit or_(... .is_(None))."""
        # Manually insert a research_tool keyword with NULL research_result_id
        from backend.models.client_keywords import ClientKeyword as CKW

        null_kw = CKW(
            client_id=CLIENT_ID,
            keyword="null citation kw",
            keyword_type="primary",
            source="research_tool",
            is_active=True,
            research_result_id=None,
        )
        db.add(null_kw)
        db.commit()

        # Re-seed with a new result that doesn't include "null citation kw"
        result = seed_from_research_result(
            db,
            CLIENT_ID,
            "rr-new-001",
            {"primary_keywords": ["fresh keyword"]},
        )
        assert result["deactivated"] == 1, "NULL research_result_id keyword must be deactivated"
        rows = get_keywords_for_client(db, CLIENT_ID, keyword_type="primary")
        assert all(r.keyword != "null citation kw" for r in rows)


class TestBulkUpsertReactivationCap:
    """Edge case: reactivating soft-deleted keywords must respect the per-type cap."""

    def test_reactivation_counts_toward_cap(self, db):
        # Fill to 49 active primaries
        for i in range(49):
            create_keyword(db, CLIENT_ID, _primary(f"active {i:03d}"))
        # Add one that will be soft-deleted (50th, then removed → back to 49 active)
        kw = create_keyword(db, CLIENT_ID, _primary("will be deleted"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)
        # State: 49 active + 1 soft-deleted

        # Bulk-upsert: reactivate the deleted one + try 2 brand-new ones
        kws = [
            _primary("will be deleted"),  # reactivation: committed=49, in_flight=0 → allowed
            _primary("brand new one"),  # new: committed=49, in_flight=1 → 49+1=50 → blocked
            _primary("brand new two"),  # new: same → blocked
        ]
        result = bulk_upsert_keywords(db, CLIENT_ID, kws)

        # All three go through the existing/cap logic; reactivation is also counted as skipped
        # (existing branch always increments skipped), but it counts against in_flight.
        # "will be deleted" → existing, reactivated, skipped += 1
        # "brand new one"   → new, blocked by committed(49)+in_flight(1)=50, skipped += 1
        # "brand new two"   → new, blocked by committed(49)+in_flight(1)=50, skipped += 1
        assert result["skipped"] == 3
        assert result["imported"] == 0

        # Reactivation went through — total must be exactly 50
        total = count_active_by_type(db, CLIENT_ID, "primary")
        assert total == 50, f"Expected exactly 50, got {total}"

    def test_reactivation_beyond_cap_is_blocked(self, db):
        """If type is already at 50 active, a reactivation of a soft-deleted row is also blocked."""
        # Create 49 active, then a "placeholder" that we'll soft-delete, then fill the 50th slot.
        for i in range(49):
            create_keyword(db, CLIENT_ID, _primary(f"active {i:03d}"))
        kw = create_keyword(db, CLIENT_ID, _primary("placeholder"))
        assert kw is not None
        soft_delete_keyword(db, kw.id, CLIENT_ID)  # 49 active, 1 soft-deleted
        create_keyword(db, CLIENT_ID, _primary("filler slot 50"))  # back to 50 active
        # State: 50 active + 1 soft-deleted ("placeholder")

        result = bulk_upsert_keywords(db, CLIENT_ID, [_primary("placeholder")])
        # committed(50) + in_flight(0) = 50 >= 50 → reactivation blocked
        assert result["skipped"] == 1
        total = count_active_by_type(db, CLIENT_ID, "primary")
        assert total == 50
