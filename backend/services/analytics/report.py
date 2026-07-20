"""
PDF engagement report (Phase 11).

Renders a one-page analytics summary — headline totals, auto-insights, and
per-platform / per-template breakdowns — to PDF bytes using reportlab (already a
project dependency for research briefs). Data comes entirely from the analytics
engine, so the report reflects the same numbers as the dashboard endpoints.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from html import escape
from typing import List

from sqlalchemy.orm import Session

from backend.services.analytics import engine


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _table(headers: List[str], rows: List[List[str]]):
    # reportlab imported lazily so this module (and the analytics router) load even
    # where reportlab isn't installed; only building a PDF requires it.
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    data = [headers] + rows
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build_pdf(db: Session, user_id: str) -> bytes:
    """Build the engagement report PDF and return its bytes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Engagement Report")
    flow = []

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flow.append(Paragraph("Engagement Report", styles["Title"]))
    flow.append(Paragraph(f"Generated {generated}", styles["Normal"]))
    flow.append(Spacer(1, 0.2 * inch))

    ov = engine.overview(db, user_id)
    flow.append(
        _table(
            ["Posts", "Impressions", "Reach", "Engagements", "Eng. rate"],
            [
                [
                    str(ov["posts"]),
                    f"{ov['impressions']:,}",
                    f"{ov['reach']:,}",
                    f"{ov['engagement']:,}",
                    _pct(ov["engagement_rate"]),
                ]
            ],
        )
    )
    flow.append(Spacer(1, 0.25 * inch))

    flow.append(Paragraph("Insights", styles["Heading2"]))
    for line in engine.insights(db, user_id):
        # Insight lines embed user-controlled template names; ReportLab parses
        # Paragraph text as XML-like markup, so escape &, <, > to avoid a 500.
        flow.append(Paragraph(f"• {escape(line, quote=False)}", styles["Normal"]))
    flow.append(Spacer(1, 0.25 * inch))

    platforms = engine.by_platform_with_benchmark(db, user_id)
    if platforms:
        flow.append(Paragraph("By platform", styles["Heading2"]))
        flow.append(
            _table(
                ["Platform", "Posts", "Impressions", "Eng. rate", "Benchmark"],
                [
                    [
                        p["platform"].title(),
                        str(p["posts"]),
                        f"{p['impressions']:,}",
                        _pct(p["engagement_rate"]),
                        p["benchmark_tier"],
                    ]
                    for p in platforms
                ],
            )
        )
        flow.append(Spacer(1, 0.25 * inch))

    templates = [t for t in engine.by_template(db, user_id) if t["template"] != "untagged"]
    if templates:
        flow.append(Paragraph("By template", styles["Heading2"]))
        flow.append(
            _table(
                ["Template", "Posts", "Eng. rate"],
                [[t["template"], str(t["posts"]), _pct(t["engagement_rate"])] for t in templates],
            )
        )

    doc.build(flow)
    return buf.getvalue()
