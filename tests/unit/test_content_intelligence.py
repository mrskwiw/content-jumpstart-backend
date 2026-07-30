"""Content-intelligence facade — assess_post composes genericity + predict."""

from backend.services.content_intelligence import assess_post

_STRONG = (
    "3 words killed our onboarding conversion.\n\n"
    "We A/B tested the signup button copy for six weeks across 12,000 visitors, "
    "splitting traffic evenly until the confidence interval closed. The clever, "
    "playful version everyone expected to win lost badly. The boring, literal one "
    "that told people exactly what happens next won by 34% on completed signups, and "
    "the gap held through the second month after we shipped it to everyone. When "
    "someone is deciding whether to trust you with their email, they are not looking "
    "to be entertained — they are looking to understand what happens next, plainly.\n\n"
    "What's the most boring change that ever moved your numbers? Tell me in the comments."
)

_WEAK = (
    "In today's fast-paced digital world, businesses must leverage cutting-edge "
    "solutions to unlock synergy and supercharge growth. In conclusion, it is "
    "important to note that we should elevate our robust strategies."
)


def test_strong_post_not_regenerated():
    a = assess_post(_STRONG, platform="linkedin")
    assert a.should_regenerate is False
    assert a.is_generic is False
    assert a.predicted_score >= 60
    assert a.reasons == []


def test_weak_generic_post_flagged_for_regeneration():
    a = assess_post(_WEAK, platform="linkedin")
    assert a.should_regenerate is True
    assert a.is_generic is True
    assert "generic_opener" in a.flags
    assert any("generic" in r for r in a.reasons)


def test_low_predicted_score_triggers_regeneration_even_if_not_generic():
    # short, specific, but far below platform length + no hook/cta/question
    a = assess_post("We shipped a fix.", platform="linkedin")
    assert a.is_generic is False
    assert a.should_regenerate is True
    assert any("predicted engagement" in r for r in a.reasons)


def test_trailing_hashtags_do_not_change_assessment():
    # Appended hashtags must not shift the length/engagement/genericity scoring.
    plain = assess_post(_STRONG, platform="linkedin")
    tagged = assess_post(_STRONG + "\n\n#growth #saas #onboarding", platform="linkedin")
    assert tagged.predicted_score == plain.predicted_score
    assert tagged.genericity_score == plain.genericity_score
    assert tagged.should_regenerate == plain.should_regenerate


def test_thresholds_are_tunable():
    # with a lenient floor, a mediocre post passes
    weakish = "We improved the dashboard and users seem happier with the new layout now."
    strict = assess_post(weakish, regenerate_below=90)
    lenient = assess_post(weakish, regenerate_below=0)
    assert strict.should_regenerate is True
    assert lenient.should_regenerate is False
