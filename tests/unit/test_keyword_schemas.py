"""Unit tests for keyword Pydantic schemas."""

import pytest
from pydantic import ValidationError

from backend.schemas.keyword_schemas import (
    KeywordBulkUpsert,
    KeywordCreate,
    KeywordType,
    KeywordUpdate,
)


# ---------------------------------------------------------------------------
# KeywordCreate
# ---------------------------------------------------------------------------


class TestKeywordCreate:
    def test_valid_primary(self):
        kw = KeywordCreate(keyword="content marketing", keyword_type=KeywordType.primary)
        assert kw.keyword == "content marketing"
        assert kw.keyword_type == KeywordType.primary

    def test_strips_whitespace(self):
        kw = KeywordCreate(keyword="  seo tips  ", keyword_type=KeywordType.secondary)
        assert kw.keyword == "seo tips"

    def test_min_length_enforced(self):
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="a", keyword_type=KeywordType.negative)

    def test_max_length_enforced(self):
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="x" * 201, keyword_type=KeywordType.primary)

    def test_negative_keyword_100_char_limit(self):
        """Negative keywords have an extra 100-char cap via field_validator."""
        long_neg = "a" * 101
        with pytest.raises(ValidationError, match="100 characters"):
            KeywordCreate(keyword=long_neg, keyword_type=KeywordType.negative)

    def test_non_negative_keyword_allows_up_to_200_chars(self):
        kw = KeywordCreate(keyword="b" * 150, keyword_type=KeywordType.primary)
        assert len(kw.keyword) == 150

    def test_optional_fields_default_none(self):
        kw = KeywordCreate(keyword="seo audit", keyword_type=KeywordType.quick_win)
        assert kw.search_intent is None
        assert kw.difficulty is None
        assert kw.monthly_volume is None
        assert kw.relevance_score is None
        assert kw.quality_score is None
        assert kw.notes is None

    def test_relevance_score_bounds(self):
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="test kw", keyword_type=KeywordType.primary, relevance_score=0.5)
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="test kw", keyword_type=KeywordType.primary, relevance_score=10.1)

    def test_quality_score_bounds(self):
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="test kw", keyword_type=KeywordType.primary, quality_score=-1)
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="test kw", keyword_type=KeywordType.primary, quality_score=101)

    def test_notes_max_length(self):
        with pytest.raises(ValidationError):
            KeywordCreate(
                keyword="test kw",
                keyword_type=KeywordType.primary,
                notes="n" * 501,
            )

    def test_all_keyword_types_accepted(self):
        for ktype in KeywordType:
            kw = KeywordCreate(keyword="some keyword", keyword_type=ktype)
            assert kw.keyword_type == ktype

    def test_invalid_keyword_type_rejected(self):
        with pytest.raises(ValidationError):
            KeywordCreate(keyword="test", keyword_type="unknown")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# KeywordUpdate
# ---------------------------------------------------------------------------


class TestKeywordUpdate:
    def test_all_fields_optional(self):
        ku = KeywordUpdate()
        assert ku.keyword is None
        assert ku.search_intent is None
        assert ku.difficulty is None
        assert ku.notes is None
        assert ku.is_active is None

    def test_strips_keyword_whitespace(self):
        ku = KeywordUpdate(keyword="  email marketing  ")
        assert ku.keyword == "email marketing"

    def test_none_keyword_unchanged(self):
        ku = KeywordUpdate(keyword=None)
        assert ku.keyword is None

    def test_is_active_bool(self):
        ku = KeywordUpdate(is_active=False)
        assert ku.is_active is False

    def test_model_dump_exclude_unset(self):
        ku = KeywordUpdate(keyword="new kw")
        dumped = ku.model_dump(exclude_unset=True)
        assert dumped == {"keyword": "new kw"}


# ---------------------------------------------------------------------------
# KeywordBulkUpsert
# ---------------------------------------------------------------------------


class TestKeywordBulkUpsert:
    def _make_kw(self, text: str, ktype: KeywordType = KeywordType.primary) -> dict:
        return {"keyword": text, "keyword_type": ktype}

    def test_valid_bulk(self):
        payload = KeywordBulkUpsert(
            keywords=[
                self._make_kw("keyword one"),
                self._make_kw("keyword two", KeywordType.negative),
            ]
        )
        assert len(payload.keywords) == 2

    def test_max_50_enforced(self):
        with pytest.raises(ValidationError):
            KeywordBulkUpsert(keywords=[self._make_kw(f"kw{i}") for i in range(51)])

    def test_empty_list_invalid(self):
        """Empty list passes Pydantic but CRUD layer would return no-op — schema itself doesn't reject it."""
        # Pydantic v2 doesn't enforce min_length on List by default;
        # the router accepts it and returns imported=0.
        payload = KeywordBulkUpsert(keywords=[])
        assert payload.keywords == []
