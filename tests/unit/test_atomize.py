"""Content atomization — to_thread + pull_quotes."""

from backend.services.atomize import pull_quotes, to_thread


def test_short_text_single_unnumbered():
    thread = to_thread("One short thought here.", max_chars=270)
    assert thread == ["One short thought here."]


def test_long_text_splits_and_numbers():
    text = " ".join(f"Sentence number {i} has some words in it." for i in range(1, 21))
    thread = to_thread(text, max_chars=120)
    assert len(thread) > 1
    # every post fits the limit and is numbered i/total
    for i, post in enumerate(thread, 1):
        assert len(post) <= 120
        assert post.endswith(f"({i}/{len(thread)})")


def test_oversized_single_sentence_is_word_split():
    sentence = "word " * 100  # ~500 chars, no sentence breaks
    thread = to_thread(sentence.strip(), max_chars=80)
    assert len(thread) > 1
    for post in thread:
        assert len(post) <= 80


def test_pull_quotes_selects_punchy_sentences():
    text = (
        "Clarity beats cleverness every single time in onboarding copy. "
        "Here is a very long meandering sentence that goes on and on well past the "
        "twenty word ceiling we set for a good punchy pull quote graphic candidate line. "
        "Boring words won."  # too short (3 words)
    )
    quotes = pull_quotes(text, min_words=6, max_words=20)
    assert "Clarity beats cleverness every single time in onboarding copy." in quotes
    assert all(6 <= len(q.split()) <= 20 for q in quotes)


def test_pull_quotes_respects_limit():
    text = " ".join("This is a solid punchy sentence worth quoting today." for _ in range(5))
    assert len(pull_quotes(text, limit=2)) == 2


def test_pull_quotes_skips_colon_endings():
    text = "Here are the three reasons it worked so well for us: Reason one is clarity always."
    quotes = pull_quotes(text)
    assert not any(q.endswith(":") for q in quotes)
