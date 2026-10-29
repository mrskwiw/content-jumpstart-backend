"""COMPLIANCE-01 Task 6: exports disclose AI generation.

Decision D6 (user, 2026-10-28): a per-post column in CSV, and one statement at the top
of document exports. PDF is produced only for research reports (no posts), so the
statement applies to the post deliverables: DOCX, MD, TXT.
"""

import asyncio
import csv
import io
from unittest.mock import MagicMock

import pytest

from backend.services.distribution.disclosure import EXPORT_STATEMENT
from backend.services.export_service import generate_export_file


def _client():
    c = MagicMock()
    c.name = "Acme Co"
    c.id = "client-1"
    return c


def _project():
    p = MagicMock()
    p.name = "Spring Campaign"
    p.id = "proj-1"
    return p


def _post(content, draft):
    p = MagicMock()
    p.content = content
    p.ai_draft_content = draft  # set explicitly: an unset MagicMock attr is a Mock, not None
    p.target_platform = "linkedin"
    p.template_name = "Story"
    p.word_count = len(content.split())
    p.twitter_share_copy = None
    p.readability_score = None
    p.has_cta = False
    p.flags = []
    return p


POSTS = [
    _post("Untouched AI draft.", "Untouched  AI draft."),  # unedited (whitespace only)
    _post("I rewrote this one myself.", "Original AI wording."),  # edited
    _post("Legacy post.", None),  # pre-v10, no snapshot ⇒ counts as unedited
]


def _export(fmt, name):
    path, _size = asyncio.run(
        generate_export_file(
            posts=POSTS,
            client=_client(),
            project=_project(),
            format=fmt,
            relative_path=f"Acme Co/{name}.{fmt}",
        )
    )
    return path


def test_csv_has_a_per_post_unedited_ai_draft_column():
    rows = list(csv.DictReader(io.StringIO(_export("csv", "c01").read_text(encoding="utf-8"))))
    assert [r["ai_generated_unedited"] for r in rows] == ["yes", "no", "yes"]


@pytest.mark.parametrize("fmt", ["md", "txt"])
def test_text_documents_open_with_the_statement(fmt):
    text = _export(fmt, f"c01-{fmt}").read_text(encoding="utf-8")
    assert EXPORT_STATEMENT in text
    assert text.index(EXPORT_STATEMENT) < text.index("Untouched AI draft.")


def test_docx_opens_with_the_statement():
    from docx import Document

    doc = Document(str(_export("docx", "c01-docx")))
    paragraphs = [p.text for p in doc.paragraphs]
    statement_at = next(i for i, t in enumerate(paragraphs) if EXPORT_STATEMENT in t)
    first_post_at = next(i for i, t in enumerate(paragraphs) if "Untouched AI draft." in t)
    assert statement_at < first_post_at
