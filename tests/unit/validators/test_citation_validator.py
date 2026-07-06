"""Tests for CitationValidator — unverified source-attribution detection."""

from unittest.mock import MagicMock

import pytest

from src.validators.citation_validator import CitationValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post(content: str, template_name: str = "test_template", has_web_search_context: bool = False):
    p = MagicMock()
    p.content = content
    p.template_name = template_name
    p.has_web_search_context = has_web_search_context
    return p


def _posts(*contents):
    return [_post(c) for c in contents]


# ---------------------------------------------------------------------------
# CitationValidator.validate — return shape
# ---------------------------------------------------------------------------


class TestReturnShape:
    def setup_method(self):
        self.v = CitationValidator()

    def test_returns_dict_with_expected_keys(self):
        result = self.v.validate(_posts("No citation here."))
        assert "warnings" in result
        assert "posts_flagged" in result

    def test_warnings_is_list(self):
        result = self.v.validate(_posts("Clean content."))
        assert isinstance(result["warnings"], list)

    def test_posts_flagged_is_int(self):
        result = self.v.validate(_posts("Clean content."))
        assert isinstance(result["posts_flagged"], int)

    def test_empty_post_list(self):
        result = self.v.validate([])
        assert result["warnings"] == []
        assert result["posts_flagged"] == 0


# ---------------------------------------------------------------------------
# Clean content — no warnings expected
# ---------------------------------------------------------------------------


class TestCleanContent:
    def setup_method(self):
        self.v = CitationValidator()

    def test_plain_statement_no_flag(self):
        result = self.v.validate(_posts("Home prices in Seattle rose 8% last year."))
        assert result["posts_flagged"] == 0

    def test_question_post_no_flag(self):
        result = self.v.validate(_posts("What would you do with $40K in equity?"))
        assert result["posts_flagged"] == 0

    def test_empty_content_no_flag(self):
        result = self.v.validate(_posts(""))
        assert result["posts_flagged"] == 0

    def test_none_content_no_crash(self):
        post = _post(None)
        result = self.v.validate([post])
        assert result["posts_flagged"] == 0

    def test_lowercase_according_to_common_word_no_false_positive(self):
        # "according to" followed by a lowercase word — not an org name
        result = self.v.validate(_posts("Buy now, according to your gut feeling."))
        assert result["posts_flagged"] == 0


# ---------------------------------------------------------------------------
# Flagged patterns
# ---------------------------------------------------------------------------


class TestAttributionPatterns:
    def setup_method(self):
        self.v = CitationValidator()

    def test_according_to_org(self):
        result = self.v.validate(_posts("According to Deloitte, 40% of AI projects fail."))
        assert result["posts_flagged"] == 1

    def test_org_reports(self):
        result = self.v.validate(_posts("The NAR reports that buyers lose 63% of offers."))
        assert result["posts_flagged"] == 1

    def test_org_found(self):
        result = self.v.validate(_posts("McKinsey found that productivity drops 30%."))
        assert result["posts_flagged"] == 1

    def test_org_data_shows(self):
        result = self.v.validate(_posts("Zillow data shows prices up 12% year-over-year."))
        assert result["posts_flagged"] == 1

    def test_org_study(self):
        result = self.v.validate(_posts("A Harvard study confirms buyers overpay by 8%."))
        assert result["posts_flagged"] == 1

    def test_org_survey(self):
        result = self.v.validate(
            _posts("Redfin survey reveals 70% of buyers regret waiving inspection.")
        )
        assert result["posts_flagged"] == 1

    def test_per_org(self):
        result = self.v.validate(_posts("Per Freddie Mac, rates dropped to 6.2% last week."))
        assert result["posts_flagged"] == 1

    def test_source_colon_inline(self):
        result = self.v.validate(_posts("63% of buyers lose their first offer. (Source: NAR 2024)"))
        assert result["posts_flagged"] == 1

    def test_source_colon_label(self):
        result = self.v.validate(
            _posts("Buyers wait 6 months on average.\nSource: Zillow Research")
        )
        assert result["posts_flagged"] == 1

    def test_case_insensitive_according_to(self):
        result = self.v.validate(_posts("ACCORDING TO The Fed, rates will stay higher longer."))
        assert result["posts_flagged"] == 1


# ---------------------------------------------------------------------------
# Warning message content
# ---------------------------------------------------------------------------


class TestWarningMessage:
    def setup_method(self):
        self.v = CitationValidator()

    def test_warning_includes_post_index(self):
        # Post index is 1-based position in the list passed to validate
        posts = [_post("Clean post."), _post("According to Deloitte, 40% fail.")]
        result = self.v.validate(posts)
        assert "Post 2" in result["warnings"][0]

    def test_warning_includes_template_name(self):
        post = _post("McKinsey found that X.", template_name="Statistic Post")
        result = self.v.validate([post])
        assert "Statistic Post" in result["warnings"][0]

    def test_warning_includes_snippet(self):
        result = self.v.validate(_posts("According to Deloitte, AI projects are failing."))
        assert "According to Deloitte" in result["warnings"][0]

    def test_warning_includes_regeneration_guidance(self):
        # Advisory guidance tells the operator what to do with the flagged citation.
        result = self.v.validate(_posts("Per NAR, 63% of first-time buyers lose their dream home."))
        assert "verify before publishing" in result["warnings"][0]


# ---------------------------------------------------------------------------
# Multiple posts
# ---------------------------------------------------------------------------


class TestMultiplePosts:
    def setup_method(self):
        self.v = CitationValidator()

    def test_only_flagged_posts_counted(self):
        posts = _posts(
            "No citation here.",
            "According to Forbes, markets are up.",
            "Another clean post.",
            "McKinsey found that 60% of mergers fail.",
        )
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 2
        assert len(result["warnings"]) == 2

    def test_all_clean_posts(self):
        posts = _posts("Clean one.", "Clean two.", "Clean three.")
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 0
        assert result["warnings"] == []

    def test_all_flagged_posts(self):
        posts = _posts(
            "According to NAR, prices rose.",
            "Zillow reports a 10% increase.",
        )
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 2

    def test_one_post_multiple_citations_counts_once(self):
        # A post with two citation patterns should produce one warning, not two
        content = "According to NAR, prices rose. Per Zillow, inventory is down."
        result = self.v.validate(_posts(content))
        assert result["posts_flagged"] == 1
        assert len(result["warnings"]) == 1


# ---------------------------------------------------------------------------
# Advisory-only behavior
# ---------------------------------------------------------------------------


class TestAdvisoryOnlyBehavior:
    """The validator is advisory-only by design: every citation becomes a
    non-blocking warning. It never emits blocking 'issues' or a 'passed'
    verdict, and it does not track web-search context (no such field exists on
    Post). See the citation_validator module docstring and qa_agent, which
    keeps citation results out of pass/fail semantics.

    (These tests previously encoded a GEN-02 web-search advisory/blocking
    distinction that was never implemented — updated to assert the actual,
    committed advisory-only contract.)
    """

    def setup_method(self):
        self.v = CitationValidator()

    def test_citation_is_flagged_as_advisory_warning(self):
        """A citation is flagged as a non-blocking warning, not a blocking issue."""
        posts = [_post("According to Forrester, 80% of projects fail.")]
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 1
        assert len(result["warnings"]) == 1
        assert "verify before publishing" in result["warnings"][0]
        # Advisory-only: no blocking keys are produced.
        assert "issues" not in result
        assert "passed" not in result

    def test_second_citation_also_flagged_as_advisory(self):
        """Any citation is flagged advisory; there is no web-search exemption."""
        posts = [_post("According to TechCrunch, AI adoption is accelerating.")]
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 1
        assert len(result["warnings"]) == 1
        assert "verify before publishing" in result["warnings"][0]
        assert "issues" not in result

    def test_multiple_citations_all_flagged_advisory(self):
        """Both citations are flagged; none are treated as blocking."""
        posts = [
            _post("According to McKinsey, costs rose 20%."),
            _post("According to Wired, startups are struggling."),
        ]
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 2
        assert len(result["warnings"]) == 2
        assert "McKinsey" in result["warnings"][0]
        assert "issues" not in result

    def test_clean_post_not_flagged(self):
        """No citation: not flagged, no warnings."""
        posts = [_post("Most companies are investing more in AI this year.")]
        result = self.v.validate(posts)
        assert result["posts_flagged"] == 0
        assert result["warnings"] == []
