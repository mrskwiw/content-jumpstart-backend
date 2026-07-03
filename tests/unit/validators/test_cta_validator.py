"""Tests for CTAValidator — CTA variety, placement, and end-with-question checks."""

from unittest.mock import MagicMock

import pytest

from src.validators.cta_validator import CTAValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post(content: str, template_name: str = "test_template"):
    """Return a minimal mock Post with the given content."""
    p = MagicMock()
    p.content = content
    p.template_name = template_name
    p.has_cta = True
    p.target_platform = None
    return p


def _posts(*contents):
    return [_post(c) for c in contents]


# ---------------------------------------------------------------------------
# _check_post_ends_with_question
# ---------------------------------------------------------------------------


class TestCheckPostEndsWithQuestion:
    """Unit tests for the _check_post_ends_with_question helper."""

    def setup_method(self):
        self.validator = CTAValidator()

    def test_statement_ending_no_issue(self):
        post = _post("Great insight.\n\nShare your thoughts below.")
        assert self.validator._check_post_ends_with_question(post) == []

    def test_question_ending_raises_issue(self):
        post = _post("Great insight.\n\nWhat do you think?")
        issues = self.validator._check_post_ends_with_question(post)
        assert len(issues) == 1
        assert "ends with a question" in issues[0]
        assert "test_template" in issues[0]

    def test_question_with_trailing_whitespace(self):
        """Trailing spaces after '?' should still be caught."""
        post = _post("Some content.\n\nHave you tried this?   ")
        issues = self.validator._check_post_ends_with_question(post)
        assert len(issues) == 1

    def test_question_mark_mid_post_not_flagged(self):
        """A '?' in the body (not the final line) should NOT be flagged."""
        post = _post("Have you tried this?\n\nHere is why it works.\n\nDownload the guide.")
        assert self.validator._check_post_ends_with_question(post) == []

    def test_empty_content_no_issue(self):
        post = _post("")
        assert self.validator._check_post_ends_with_question(post) == []

    def test_whitespace_only_content_no_issue(self):
        post = _post("   \n\n  ")
        assert self.validator._check_post_ends_with_question(post) == []

    def test_single_question_line(self):
        """A post consisting of only a question should be flagged."""
        post = _post("What is your biggest challenge?")
        issues = self.validator._check_post_ends_with_question(post)
        assert len(issues) == 1

    def test_template_name_none(self):
        """When template_name is None the issue string uses 'post' as fallback."""
        post = _post("What do you think?", template_name=None)
        post.template_name = None
        issues = self.validator._check_post_ends_with_question(post)
        assert "post" in issues[0]


# ---------------------------------------------------------------------------
# validate() — integration of end-with-question into full validation
# ---------------------------------------------------------------------------


class TestValidateEndsWithQuestion:
    """validate() flags question-ending posts on non-exempt templates.

    Generic question closers ("What do you think?") are now surfaced as issues
    by the batch validator so they can't ship silently.  Posts from templates
    that intentionally end with questions (Question Post, Contrarian Take,
    Reader Q&A) are exempt — their template_name contains a keyword that
    suppresses the check.
    """

    def setup_method(self):
        self.validator = CTAValidator()

    def test_all_statement_endings_pass(self):
        posts = _posts(
            "Good content.\n\nShare your take below.",
            "Another post.\n\nBook a call at [link].",
        )
        result = self.validator.validate(posts)
        question_issues = [i for i in result["issues"] if "ends with a question" in i]
        assert question_issues == []

    def test_question_on_generic_template_is_flagged(self):
        """A question-ending post on a non-exempt template surfaces an issue."""
        posts = _posts(
            "Good content.\n\nShare your take below.",
            "Another post.\n\nWhat do you think?",
        )
        result = self.validator.validate(posts)
        question_issues = [i for i in result["issues"] if "ends with a question" in i]
        assert len(question_issues) == 1

    def test_multiple_question_endings_all_surfaced(self):
        """Multiple question-ending posts all produce issues."""
        posts = _posts(
            "Post one.\n\nWhat do you think?",
            "Post two.\n\nHave you tried this?",
            "Post three.\n\nDownload the guide.",
        )
        result = self.validator.validate(posts)
        question_issues = [i for i in result["issues"] if "ends with a question" in i]
        assert len(question_issues) == 2

    def test_engagement_question_on_exempt_template_passes(self):
        """Posts from Question Post / Contrarian / Q&A templates are exempt."""
        exempt_names = [
            "The Question Post",
            "Question",  # exact stored name (template_loader.py)
            "Against the Grain",  # exact stored name — keyword "contrarian" absent
            "Against the Grain Contrarian Take",
            "Reader Question Response",
            "Reader Question",  # exact stored name (template_loader.py)
        ]
        for template_name in exempt_names:
            p = _post("Thoughtful body.\n\nWhat do you think?", template_name)
            result = self.validator.validate([p])
            question_issues = [i for i in result["issues"] if "ends with a question" in i]
            assert question_issues == [], f"Should be exempt: {template_name!r}"

    def test_engagement_question_classified_not_missing_cta(self):
        """An engagement-question post is classified correctly, not as missing CTA."""
        posts = _posts("Content.\n\nWhat is your experience?")
        result = self.validator.validate(posts)
        missing_issues = [i for i in result["issues"] if "missing" in i.lower()]
        assert missing_issues == []
        assert result["cta_distribution"].get("engagement_question", 0) == 1


# ---------------------------------------------------------------------------
# Statement-only contract — question-ending booking CTAs must be caught
# ---------------------------------------------------------------------------


class TestQuestionEndingBookingCTA:
    """Regression: booking CTAs that end with ? must be flagged even though
    _check_post_ends_with_question is not wired into validate().
    The placement checker covers this via the full CTA_PATTERNS last-line scan.
    """

    def setup_method(self):
        self.validator = CTAValidator()

    def test_appointment_question_is_flagged(self):
        post = _post("Good content about dental care.\n\nAppointment?")
        issues = self.validator._check_post_cta_placement(post)
        assert any("rewrite as a statement" in i for i in issues)

    def test_consultation_question_is_flagged(self):
        post = _post("Content about our services.\n\nConsultation?")
        issues = self.validator._check_post_cta_placement(post)
        assert any("rewrite as a statement" in i for i in issues)

    def test_booking_phrase_question_is_flagged(self):
        post = _post("Content.\n\nReady to book your appointment?")
        issues = self.validator._check_post_cta_placement(post)
        assert any("rewrite as a statement" in i for i in issues)

    def test_appointment_statement_passes(self):
        post = _post("Content.\n\nBook your appointment today.")
        assert self.validator._check_post_cta_placement(post) == []

    def test_appointment_in_body_not_flagged_as_misplaced(self):
        """'appointment' in body text must not trigger the body-scan CTA check."""
        post = _post(
            "Many patients who missed an appointment for years find us.\n\nBook your visit today."
        )
        issues = self.validator._check_post_cta_placement(post)
        assert not any("mid-post" in i for i in issues)


# ---------------------------------------------------------------------------
# _check_post_cta_placement — ensure existing checks still work
# ---------------------------------------------------------------------------


class TestCheckPostCtaPlacement:
    """Tests for CTA placement checker — body-scan and last-line question check.

    Parameterised cases ensure every _PLACEMENT_PATTERNS entry has coverage so
    a broken pattern is caught immediately rather than slipping through silently.
    """

    def setup_method(self):
        self.validator = CTAValidator()

    # ------------------------------------------------------------------ #
    # Original checks                                                       #
    # ------------------------------------------------------------------ #

    def test_cta_on_last_line_no_issue(self):
        post = _post("Good content.\n\nShare your thoughts below.")
        assert self.validator._check_post_cta_placement(post) == []

    def test_cta_mid_post_flagged(self):
        post = _post("Drop a comment below.\n\nHere is more content.\n\nSome closing line.")
        issues = self.validator._check_post_cta_placement(post)
        assert any("move to final line" in i for i in issues)

    def test_cta_question_on_last_line_flagged(self):
        post = _post("Good content.\n\nDrop a comment below?")
        issues = self.validator._check_post_cta_placement(post)
        assert any("rewrite as a statement" in i for i in issues)

    # ------------------------------------------------------------------ #
    # Parameterised: each _PLACEMENT_PATTERNS entry caught mid-post        #
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize(
        "body_cta,closing",
        [
            # Pattern group: comment / contact / reply / link
            ("Drop your comment here.", "Here is the closing."),
            ("DM me for the details.", "Here is the closing."),
            ("Reply below with your answer.", "Here is the closing."),
            ("Click the link to find out more.", "Here is the closing."),
            # Booking
            ("Book a call with our team.", "Here is the closing."),
            ("Schedule your consultation today.", "Here is the closing."),
            # Signup / download / learn / share
            ("Sign up for our newsletter.", "Here is the closing."),
            ("Download the free guide now.", "Here is the closing."),
            ("Learn more at the link.", "Here is the closing."),
            ("Tell me about your experience in the comments.", "Here is the closing."),
            ("Give us a call today.", "Here is the closing."),
            # Engagement verbs
            ("Follow us on LinkedIn for daily tips.", "Here is the closing."),
            ("Connect with us today.", "Here is the closing."),
            ("Visit us to learn more.", "Here is the closing."),
            ("Register now for the webinar.", "Here is the closing."),
            ("Apply today to get started.", "Here is the closing."),
            # Action verbs with object
            ("Read the full guide below.", "Here is the closing."),
            ("Watch our video to see the difference.", "Here is the closing."),
            ("Explore our services today.", "Here is the closing."),
            # Soft CTAs
            ("Let's book a call and walk through it.", "Here is the closing."),
            ("Let's schedule a quick demo.", "Here is the closing."),
            ("Let's get started with your free trial today.", "Here is the closing."),
            ("Ask us for a free consultation.", "Here is the closing."),
            ("Ask your dentist about our service today.", "Here is the closing."),
            ("Ask your doctor if this is right for you.", "Here is the closing."),
            ("Ask us anything below.", "Here is the closing."),
            ("Ask me in the comments.", "Here is the closing."),
            ("Try it free for 30 days.", "Here is the closing."),
            ("Try us for your next appointment.", "Here is the closing."),
            ("Visit our page for the full details.", "Here is the closing."),
            ("Start your free trial today.", "Here is the closing."),
            ("Begin your journey with us.", "Here is the closing."),
            ("Let's make it work today.", "Here is the closing."),
            ("Let's do it now.", "Here is the closing."),
        ],
    )
    def test_mid_post_cta_flagged(self, body_cta, closing):
        """Each _PLACEMENT_PATTERNS entry must trigger 'move to final line'
        when the CTA appears in the body, not the last line."""
        post = _post(f"{body_cta}\n\nMore content here.\n\n{closing}")
        issues = self.validator._check_post_cta_placement(post)
        assert any(
            "move to final line" in i for i in issues
        ), f"Expected body-scan flag for: {body_cta!r}"

    # ------------------------------------------------------------------ #
    # False-positive guard: body text that must NOT trigger               #
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize(
        "safe_body",
        [
            "We see patients who missed an appointment for years.",
            "Visit our office for a comfortable clean smile.",
            "If you follow the same pattern as most people.",
            "Let's start with the most common fear about dentistry.",
            "Let's talk about why anxiety is so common.",
            "Many patients ask us about their dental anxiety.",
            "Connect the dots between avoidance and worsening health.",
            "If you have read this far you already know.",
            "Try to imagine what that would feel like.",
            "Start with this simple idea first.",
            "Let's make this clear for everyone.",
            "Let's talk about why this matters today.",
            "Visit our office for a comfortable clean smile.",
            "Many patients try to find the right dentist.",
            "We apply fluoride treatment after every cleaning.",
            "Apply the same logic to your content strategy.",
        ],
    )
    def test_body_text_not_flagged(self, safe_body):
        """Normal body sentences must not trigger the body-scan CTA check."""
        post = _post(f"{safe_body}\n\nBook your appointment today.")
        issues = self.validator._check_post_cta_placement(post)
        assert not any(
            "mid-post" in i for i in issues
        ), f"False positive on body text: {safe_body!r}"
