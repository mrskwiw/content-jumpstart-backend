"""Unit tests for deliverable_service's pure helpers (AUDIT-01 T1).

deliverable_service was covered only indirectly via integration tests. These exercise its two
self-contained helpers directly:
- calculate_qa_summary: the QA aggregation shown on a deliverable (counts, averages, CTA %, top
  flags), including the all-None-metrics and empty cases.
- get_file_preview: bounded file read with truncation + binary/missing handling.
"""

from types import SimpleNamespace

from backend.services.deliverable_service import calculate_qa_summary, get_file_preview


def _p(status="pending", readability=None, word_count=None, has_cta=False, flags=None):
    """A minimal Post stand-in — calculate_qa_summary only reads these attributes."""
    return SimpleNamespace(
        status=status,
        readability_score=readability,
        word_count=word_count,
        has_cta=has_cta,
        flags=flags or [],
    )


# ── calculate_qa_summary ──────────────────────────────────────────────────────


def test_qa_summary_is_none_for_no_posts():
    assert calculate_qa_summary([]) is None


def test_qa_summary_counts_averages_cta_and_top_flags():
    posts = [
        _p(status="approved", readability=80.0, word_count=100, has_cta=True, flags=["too_short"]),
        _p(
            status="flagged",
            readability=60.0,
            word_count=200,
            has_cta=False,
            flags=["too_short", "no_cta"],
        ),
        _p(status="approved", readability=None, word_count=None, has_cta=True, flags=[]),
    ]
    s = calculate_qa_summary(posts)

    assert s.total_posts == 3
    assert s.approved_count == 2
    assert s.flagged_count == 1
    assert s.avg_readability == 70.0  # (80+60)/2, None skipped
    assert s.avg_word_count == 150.0  # (100+200)/2, None skipped
    assert round(s.cta_percentage, 2) == 66.67  # 2 of 3
    assert s.common_flags[0] == "too_short"  # most common first
    assert set(s.common_flags) == {"too_short", "no_cta"}


def test_qa_summary_when_all_metrics_missing():
    # No readability/word_count/CTA/flags anywhere → averages None, CTA 0%, no flags.
    s = calculate_qa_summary([_p(status="pending")])
    assert s.total_posts == 1
    assert s.avg_readability is None
    assert s.avg_word_count is None
    assert s.cta_percentage == 0.0
    assert s.common_flags == []


def test_qa_summary_caps_common_flags_at_five():
    # Six distinct flags across posts → only the top 5 are surfaced.
    posts = [_p(flags=[f"flag_{i}"]) for i in range(6)]
    s = calculate_qa_summary(posts)
    assert len(s.common_flags) == 5


# ── get_file_preview ──────────────────────────────────────────────────────────


def test_preview_missing_file_returns_none(tmp_path):
    content, truncated = get_file_preview(tmp_path / "does_not_exist.txt")
    assert content is None
    assert truncated is False


def test_preview_short_file_is_not_truncated(tmp_path):
    f = tmp_path / "short.txt"
    f.write_text("hello world", encoding="utf-8")
    content, truncated = get_file_preview(f, max_chars=100)
    assert content == "hello world"
    assert truncated is False


def test_preview_long_file_is_truncated_to_max_chars(tmp_path):
    f = tmp_path / "long.txt"
    f.write_text("x" * 50, encoding="utf-8")
    content, truncated = get_file_preview(f, max_chars=10)
    assert content == "x" * 10
    assert truncated is True


def test_preview_binary_file_returns_a_message_not_a_crash(tmp_path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\xff\xfe\x00\x01 not valid utf-8 \xff")
    content, truncated = get_file_preview(f)
    assert content is not None and "Unable to preview" in content
    assert truncated is False
