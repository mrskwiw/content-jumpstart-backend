"""EXPORT-02 — posts_to_csv."""

import csv
import io

from backend.services.csv_export import DEFAULT_COLUMNS, posts_to_csv


def _parse(csv_text):
    return list(csv.DictReader(io.StringIO(csv_text)))


def test_header_and_rows():
    posts = [
        {"platform": "linkedin", "template": "story", "content": "Hello", "word_count": 1},
        {"platform": "twitter", "template": "hot-take", "content": "Hi", "word_count": 1},
    ]
    rows = _parse(posts_to_csv(posts))
    assert list(rows[0].keys()) == list(DEFAULT_COLUMNS)
    assert rows[0]["platform"] == "linkedin" and rows[0]["content"] == "Hello"
    assert len(rows) == 2


def test_missing_fields_are_empty():
    rows = _parse(posts_to_csv([{"platform": "linkedin"}]))
    assert rows[0]["content"] == "" and rows[0]["word_count"] == ""


def test_special_characters_escaped():
    # commas, quotes, and newlines must round-trip intact
    tricky = 'He said, "hi"\nand left, then, again'
    rows = _parse(posts_to_csv([{"platform": "x", "content": tricky}]))
    assert rows[0]["content"] == tricky


def test_hashtag_list_joined():
    rows = _parse(posts_to_csv([{"platform": "ig", "hashtags": ["#a", "#b", "#c"]}]))
    assert rows[0]["hashtags"] == "#a #b #c"


def test_extra_keys_ignored():
    rows = _parse(posts_to_csv([{"platform": "x", "secret_internal": "nope"}]))
    assert "secret_internal" not in rows[0]


def test_custom_columns():
    text = posts_to_csv([{"platform": "x", "content": "c"}], columns=["content", "platform"])
    rows = _parse(text)
    assert list(rows[0].keys()) == ["content", "platform"]


def test_empty_posts_header_only():
    text = posts_to_csv([])
    rows = _parse(text)
    assert rows == []
    assert text.splitlines()[0].split(",")[0] == "platform"
