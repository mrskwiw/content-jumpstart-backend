"""CSV deliverable generation (EXPORT-02 wiring into export_service).

Verifies format="csv" produces a valid, parseable CSV file with the expected
columns, and that stdlib-csv escaping survives content with commas/quotes/newlines.
"""

import asyncio
import csv
import io
from pathlib import Path
from unittest.mock import MagicMock

from backend.services.export_service import generate_export_file


def _run(coro):
    return asyncio.run(coro)


def _make_client(name="Acme Co"):
    c = MagicMock()
    c.name = name
    c.id = "client-1"
    return c


def _make_project(name="Spring Campaign"):
    p = MagicMock()
    p.name = name
    p.id = "proj-1"
    return p


def _make_post(content="A clean post.", platform="linkedin", template="Story", words=3):
    p = MagicMock()
    p.content = content
    p.target_platform = platform
    p.template_name = template
    p.word_count = words
    return p


def _export_csv(posts, tmp_path, name="Acme Co/out.csv"):
    # generate_export_file writes under data/outputs/, so run from tmp cwd is not
    # needed; it returns the absolute path it wrote.
    return _run(
        generate_export_file(
            posts=posts,
            client=_make_client(),
            project=_make_project(),
            format="csv",
            relative_path=name,
        )
    )


def _parse(path: Path):
    text = path.read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def test_csv_has_header_and_one_row_per_post():
    posts = [_make_post(content=f"Post {i}", words=2) for i in range(3)]
    out_path, size = _export_csv(posts, None)
    try:
        rows = _parse(out_path)
        assert size > 0
        assert len(rows) == 3
        assert set(rows[0].keys()) == {
            "platform",
            "template",
            "content",
            "word_count",
            "character_count",
        }
        assert rows[0]["platform"] == "linkedin"  # raw slug, not display name
    finally:
        out_path.unlink(missing_ok=True)


def test_csv_escapes_commas_quotes_and_newlines():
    nasty = 'Line one, with comma\nLine "two" with quotes'
    out_path, _ = _export_csv([_make_post(content=nasty)], None)
    try:
        rows = _parse(out_path)
        # The csv module must round-trip the content intact despite the delimiters.
        assert rows[0]["content"] == nasty
        assert len(rows) == 1
    finally:
        out_path.unlink(missing_ok=True)


def test_csv_character_count_is_derived_from_content():
    out_path, _ = _export_csv([_make_post(content="hello world")], None)
    try:
        rows = _parse(out_path)
        assert rows[0]["character_count"] == str(len("hello world"))
    finally:
        out_path.unlink(missing_ok=True)


def test_csv_empty_posts_yields_header_only():
    out_path, size = _export_csv([], None)
    try:
        rows = _parse(out_path)
        assert rows == []  # no data rows
        assert size > 0  # header line still written
    finally:
        out_path.unlink(missing_ok=True)


def test_csv_none_content_renders_empty_cell():
    out_path, _ = _export_csv([_make_post(content=None)], None)
    try:
        rows = _parse(out_path)
        assert rows[0]["content"] == ""
        assert rows[0]["character_count"] == "0"
    finally:
        out_path.unlink(missing_ok=True)
