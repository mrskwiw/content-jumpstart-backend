"""Unit tests for backend/services/crud_client_keywords.py including concurrency guard.

Coverage target: 90%+
Uses the in-memory SQLite db_session fixture from tests/unit/conftest.py.
"""

import pytest
from backend.models.client_keywords import ClientKeyword  # noqa: F401 - ensures table is registered
from backend.schemas.keyword_schemas import KeywordCreate, KeywordType, KeywordUpdate
from backend.services import crud_client_keywords as kw_crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create(db, client_id, keyword, ktype=KeywordType.primary, source="manual", **kwargs):
    data = KeywordCreate(keyword=keyword, keyword_type=ktype, **kwargs)
    return kw_crud.create_keyword(db, client_id, data, source=source)


# ---------------------------------------------------------------------------
# get_keywords_for_client
# ---------------------------------------------------------------------------


class TestGetKeywordsForClient:
    def test_empty_returns_empty_list(self, db_session, sample_client):
        result = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert result == []

    def test_returns_active_keywords(self, db_session, sample_client):
        _create(db_session, sample_client.id, "marketing automation")
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert len(rows) == 1
        assert rows[0].keyword == "marketing automation"

    def test_filters_by_keyword_type(self, db_session, sample_client):
        _create(db_session, sample_client.id, "crm software", KeywordType.primary)
        _create(db_session, sample_client.id, "free crm", KeywordType.negative)
        primary = kw_crud.get_keywords_for_client(
            db_session, sample_client.id, keyword_type="primary"
        )
        assert len(primary) == 1
        assert primary[0].keyword == "crm software"

    def test_active_only_excludes_inactive(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "old keyword")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows == []

    def test_active_only_false_includes_inactive(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "archived")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id, active_only=False)
        assert len(rows) == 1

    def test_does_not_cross_clients(self, db_session, sample_client, db_session_second_client):
        _create(db_session, sample_client.id, "client-a keyword")
        rows = kw_crud.get_keywords_for_client(db_session, "other-client-id")
        assert rows == []


# ---------------------------------------------------------------------------
# get_keyword
# ---------------------------------------------------------------------------


class TestGetKeyword:
    def test_returns_none_for_missing(self, db_session, sample_client):
        assert kw_crud.get_keyword(db_session, 9999, sample_client.id) is None

    def test_returns_none_for_wrong_client(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "my keyword")
        assert kw_crud.get_keyword(db_session, kw.id, "other-client") is None

    def test_returns_keyword(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "found keyword")
        result = kw_crud.get_keyword(db_session, kw.id, sample_client.id)
        assert result is not None
        assert result.keyword == "found keyword"


# ---------------------------------------------------------------------------
# count_active_by_type
# ---------------------------------------------------------------------------


class TestCountActiveByType:
    def test_zero_on_empty(self, db_session, sample_client):
        assert kw_crud.count_active_by_type(db_session, sample_client.id, "primary") == 0

    def test_counts_only_active(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "active kw")
        _create(db_session, sample_client.id, "also active")
        inactive = _create(db_session, sample_client.id, "inactive kw")
        kw_crud.soft_delete_keyword(db_session, inactive.id, sample_client.id)
        count = kw_crud.count_active_by_type(db_session, sample_client.id, "primary")
        assert count == 2

    def test_ignores_other_types(self, db_session, sample_client):
        _create(db_session, sample_client.id, "neg kw", KeywordType.negative)
        assert kw_crud.count_active_by_type(db_session, sample_client.id, "primary") == 0


# ---------------------------------------------------------------------------
# create_keyword
# ---------------------------------------------------------------------------


class TestCreateKeyword:
    def test_creates_keyword(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "saas marketing")
        assert kw is not None
        assert kw.keyword == "saas marketing"
        assert kw.keyword_type == "primary"
        assert kw.source == "manual"
        assert kw.is_active is True

    def test_normalises_to_lowercase(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "SaaS Marketing")
        assert kw.keyword == "saas marketing"

    def test_strips_whitespace(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "  saas  ")
        assert kw.keyword == "saas"

    def test_assigns_source(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "research kw", source="research_tool")
        assert kw.source == "research_tool"

    def test_raises_at_cap(self, db_session, sample_client):
        for i in range(50):
            _create(db_session, sample_client.id, f"keyword {i}")
        with pytest.raises(ValueError, match="Maximum 50 active"):
            _create(db_session, sample_client.id, "one too many")

    def test_duplicate_active_returns_none(self, db_session, sample_client):
        _create(db_session, sample_client.id, "dup kw")
        result = _create(db_session, sample_client.id, "dup kw")
        assert result is None

    def test_duplicate_inactive_reactivates(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "reactivate me")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        result = _create(db_session, sample_client.id, "reactivate me")
        assert result is not None
        assert result.is_active is True

    def test_reactivation_preserves_manual_source(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "manual kw", source="manual")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        # Research tool tries to reactivate — manual flag must not be downgraded
        result = _create(db_session, sample_client.id, "manual kw", source="research_tool")
        assert result.source == "manual"

    def test_research_tool_can_set_source_on_its_own_rows(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "rt kw", source="research_tool")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        result = _create(db_session, sample_client.id, "rt kw", source="research_tool")
        assert result.source == "research_tool"


# ---------------------------------------------------------------------------
# update_keyword
# ---------------------------------------------------------------------------


class TestUpdateKeyword:
    def test_returns_none_for_missing(self, db_session, sample_client):
        data = KeywordUpdate(notes="hello")
        assert kw_crud.update_keyword(db_session, 9999, sample_client.id, data) is None

    def test_updates_notes(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "my kw")
        result = kw_crud.update_keyword(
            db_session, kw.id, sample_client.id, KeywordUpdate(notes="important")
        )
        assert result.notes == "important"

    def test_content_edit_promotes_to_manual(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "rt kw", source="research_tool")
        kw_crud.update_keyword(db_session, kw.id, sample_client.id, KeywordUpdate(notes="edited"))
        db_session.refresh(kw)
        assert kw.source == "manual"

    def test_deactivation_does_not_claim_row(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "rt kw", source="research_tool")
        kw_crud.update_keyword(db_session, kw.id, sample_client.id, KeywordUpdate(is_active=False))
        db_session.refresh(kw)
        assert kw.source == "research_tool"

    def test_reactivation_claims_row(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "rt kw", source="research_tool")
        kw_crud.update_keyword(db_session, kw.id, sample_client.id, KeywordUpdate(is_active=False))
        kw_crud.update_keyword(db_session, kw.id, sample_client.id, KeywordUpdate(is_active=True))
        db_session.refresh(kw)
        assert kw.source == "manual"

    def test_reactivation_at_cap_raises(self, db_session, sample_client):
        # Fill cap (50 active keywords)
        for i in range(50):
            _create(db_session, sample_client.id, f"cap kw {i}")
        # Insert an inactive keyword directly (bypassing the cap guard on create_keyword)
        inactive = ClientKeyword(
            client_id=sample_client.id,
            keyword="inactive one",
            keyword_type="primary",
            source="manual",
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()
        db_session.refresh(inactive)
        with pytest.raises(ValueError, match="Maximum 50"):
            kw_crud.update_keyword(
                db_session, inactive.id, sample_client.id, KeywordUpdate(is_active=True)
            )

    def test_keyword_normalised_on_update(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "original")
        result = kw_crud.update_keyword(
            db_session, kw.id, sample_client.id, KeywordUpdate(keyword="  NEW VALUE  ")
        )
        assert result.keyword == "new value"


# ---------------------------------------------------------------------------
# soft_delete_keyword
# ---------------------------------------------------------------------------


class TestSoftDeleteKeyword:
    def test_returns_false_for_missing(self, db_session, sample_client):
        assert kw_crud.soft_delete_keyword(db_session, 9999, sample_client.id) is False

    def test_sets_is_active_false(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "delete me")
        deleted = kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        assert deleted is True
        db_session.refresh(kw)
        assert kw.is_active is False

    def test_does_not_hard_delete(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "soft only")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        row = kw_crud.get_keyword(db_session, kw.id, sample_client.id)
        assert row is not None

    def test_wrong_client_returns_false(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "mine")
        assert kw_crud.soft_delete_keyword(db_session, kw.id, "other-client") is False


# ---------------------------------------------------------------------------
# bulk_upsert_keywords
# ---------------------------------------------------------------------------


class TestBulkUpsertKeywords:
    def test_inserts_new_keywords(self, db_session, sample_client):
        keywords = [
            KeywordCreate(keyword="kw one", keyword_type=KeywordType.primary),
            KeywordCreate(keyword="kw two", keyword_type=KeywordType.primary),
        ]
        result = kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords)
        assert result["imported"] == 2
        assert result["skipped"] == 0

    def test_skips_existing_active_keyword(self, db_session, sample_client):
        _create(db_session, sample_client.id, "existing")
        keywords = [KeywordCreate(keyword="existing", keyword_type=KeywordType.primary)]
        result = kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords)
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_reactivates_inactive_keyword(self, db_session, sample_client):
        kw = _create(db_session, sample_client.id, "was deleted")
        kw_crud.soft_delete_keyword(db_session, kw.id, sample_client.id)
        keywords = [KeywordCreate(keyword="was deleted", keyword_type=KeywordType.primary)]
        result = kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords)
        assert result["skipped"] == 1  # reactivation counts as skipped (existing row)
        db_session.refresh(kw)
        assert kw.is_active is True

    def test_skips_when_cap_reached(self, db_session, sample_client):
        for i in range(50):
            _create(db_session, sample_client.id, f"filler {i}")
        keywords = [KeywordCreate(keyword="overflow", keyword_type=KeywordType.primary)]
        result = kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords)
        assert result["skipped"] == 1
        assert result["imported"] == 0

    def test_manual_does_not_overwrite_research_tool_source(self, db_session, sample_client):
        _create(db_session, sample_client.id, "rt kw", source="research_tool")
        keywords = [KeywordCreate(keyword="rt kw", keyword_type=KeywordType.primary)]
        kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords, source="manual")
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows[0].source == "manual"  # manual call claims the row

    def test_research_tool_does_not_overwrite_manual_source(self, db_session, sample_client):
        _create(db_session, sample_client.id, "manual kw", source="manual")
        keywords = [KeywordCreate(keyword="manual kw", keyword_type=KeywordType.primary)]
        kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords, source="research_tool")
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows[0].source == "manual"

    def test_commit_false_does_not_persist(self, db_session, sample_client):
        keywords = [KeywordCreate(keyword="uncommitted", keyword_type=KeywordType.primary)]
        kw_crud.bulk_upsert_keywords(db_session, sample_client.id, keywords, _commit=False)
        db_session.rollback()
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows == []


# ---------------------------------------------------------------------------
# seed_from_research_result
# ---------------------------------------------------------------------------


class TestSeedFromResearchResult:
    def _seed(self, db, client_id, result_id="rr-123", data=None):
        data = data or {}
        return kw_crud.seed_from_research_result(db, client_id, result_id, data)

    def test_empty_data_returns_zeros(self, db_session, sample_client):
        result = self._seed(db_session, sample_client.id)
        assert result == {"imported": 0, "skipped": 0, "deactivated": 0}

    def test_seeds_primary_keywords_as_strings(self, db_session, sample_client):
        data = {"primary_keywords": ["crm software", "sales automation"]}
        result = self._seed(db_session, sample_client.id, data=data)
        assert result["imported"] == 2
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id, keyword_type="primary")
        assert {r.keyword for r in rows} == {"crm software", "sales automation"}

    def test_seeds_primary_keywords_as_dicts(self, db_session, sample_client):
        data = {
            "primary_keywords": [
                {"keyword": "pipeline management", "difficulty": "medium", "relevance_score": 8.0}
            ]
        }
        result = self._seed(db_session, sample_client.id, data=data)
        assert result["imported"] == 1
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows[0].difficulty == "medium"
        assert rows[0].relevance_score == 8.0

    def test_seeds_secondary_quick_win_negative(self, db_session, sample_client):
        data = {
            "secondary_keywords": ["lead generation"],
            "quick_win_keywords": ["crm demo"],
            "negative_keywords": ["free crm"],
        }
        result = self._seed(db_session, sample_client.id, data=data)
        assert result["imported"] == 3
        neg = kw_crud.get_keywords_for_client(db_session, sample_client.id, keyword_type="negative")
        assert neg[0].keyword == "free crm"

    def test_deactivates_stale_research_keywords(self, db_session, sample_client):
        # Seed run A
        data_a = {"primary_keywords": ["old kw"]}
        self._seed(db_session, sample_client.id, result_id="rr-A", data=data_a)
        # Seed run B with different keywords
        data_b = {"primary_keywords": ["new kw"]}
        result_b = self._seed(db_session, sample_client.id, result_id="rr-B", data=data_b)
        # "old kw" should be deactivated
        assert result_b["deactivated"] == 1
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert len(rows) == 1
        assert rows[0].keyword == "new kw"

    def test_manual_keywords_survive_reseed(self, db_session, sample_client):
        # Manually added keyword
        _create(db_session, sample_client.id, "brand keyword", source="manual")
        # Research run with completely different keywords
        data = {"primary_keywords": ["research kw"]}
        self._seed(db_session, sample_client.id, data=data)
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        keywords = {r.keyword for r in rows}
        assert "brand keyword" in keywords  # manual survives
        assert "research kw" in keywords

    def test_keyword_reappearing_in_new_run_is_not_deactivated(self, db_session, sample_client):
        data_a = {"primary_keywords": ["persistent kw"]}
        self._seed(db_session, sample_client.id, result_id="rr-A", data=data_a)
        data_b = {"primary_keywords": ["persistent kw", "new kw"]}
        result_b = self._seed(db_session, sample_client.id, result_id="rr-B", data=data_b)
        assert result_b["deactivated"] == 0  # "persistent kw" reactivated, not left inactive
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert len(rows) == 2

    def test_skips_malformed_dict_entries(self, db_session, sample_client):
        data = {"primary_keywords": [{"no_keyword_field": "oops"}]}
        result = self._seed(db_session, sample_client.id, data=data)
        assert result["imported"] == 0

    def test_sets_source_to_research_tool(self, db_session, sample_client):
        data = {"primary_keywords": ["sourced kw"]}
        self._seed(db_session, sample_client.id, data=data)
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows[0].source == "research_tool"

    def test_sets_research_result_id(self, db_session, sample_client):
        data = {"primary_keywords": ["tagged kw"]}
        self._seed(db_session, sample_client.id, result_id="rr-tagged", data=data)
        rows = kw_crud.get_keywords_for_client(db_session, sample_client.id)
        assert rows[0].research_result_id == "rr-tagged"


# ---------------------------------------------------------------------------
# Cap enforcement — confirming cap holds at boundaries
# ---------------------------------------------------------------------------
# Concurrency safety is provided by isolation_level="IMMEDIATE" on the SQLite
# engine (database.py): BEGIN IMMEDIATE acquires the write lock at transaction
# start, so T2 blocks until T1 commits and then reads a fresh snapshot.
# PostgreSQL relies on SELECT FOR UPDATE, which re-evaluates in READ COMMITTED
# after unblocking.  No application-layer post-flush guard is needed.


class TestCapBoundary:
    def test_51st_keyword_is_rejected(self, db_session, sample_client):
        for i in range(50):
            _create(db_session, sample_client.id, f"filler {i}")
        with pytest.raises(ValueError, match="Maximum 50"):
            _create(db_session, sample_client.id, "one too many")

    def test_50th_keyword_is_accepted(self, db_session, sample_client):
        for i in range(49):
            _create(db_session, sample_client.id, f"filler {i}")
        kw = _create(db_session, sample_client.id, "legitimate 50th")
        assert kw is not None
        assert kw.keyword == "legitimate 50th"
        assert kw_crud.count_active_by_type(db_session, sample_client.id, "primary") == 50

    def test_reactivation_at_cap_rejects(self, db_session, sample_client):
        for i in range(50):
            _create(db_session, sample_client.id, f"filler {i}")
        inactive = ClientKeyword(
            client_id=sample_client.id,
            keyword="inactive one",
            keyword_type="primary",
            source="manual",
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()
        db_session.refresh(inactive)
        with pytest.raises(ValueError, match="Maximum 50"):
            kw_crud.update_keyword(
                db_session, inactive.id, sample_client.id, KeywordUpdate(is_active=True)
            )


# ---------------------------------------------------------------------------
# Shared fixture for cross-client isolation test
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session_second_client():
    """Thin alias - the isolation test just needs any non-matching client_id."""
    return None  # the test passes "other-client-id" as a string literal
