"""CSV export (EXPORT-02 / GAP-PROD-04): generated posts → CSV.

The product exported DOCX / PDF / TXT / MD but not CSV — a table-stakes gap for
operators who bulk-import posts into schedulers / spreadsheets. Pure and
deterministic; delegates escaping (commas, quotes, newlines) to the stdlib ``csv``
module so the output is always valid.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# Default columns, in a sensible operator order.
DEFAULT_COLUMNS: tuple[str, ...] = (
    "platform",
    "template",
    "content",
    "word_count",
    "character_count",
    "hashtags",
)


def _cell(value: Any) -> str:
    """Render a cell value: join list-like hashtags, stringify the rest."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return str(value)


def posts_to_csv(
    posts: Iterable[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> str:
    """Serialize posts to a CSV string (header + one row per post).

    Unknown/missing fields render as empty; extra keys on a post are ignored.
    ``columns`` overrides the default column set/order.
    """
    cols = list(columns) if columns is not None else list(DEFAULT_COLUMNS)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for post in posts:
        writer.writerow({col: _cell(post.get(col)) for col in cols})
    return buf.getvalue()
