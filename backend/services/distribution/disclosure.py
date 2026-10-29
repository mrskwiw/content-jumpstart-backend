"""AI-content disclosure at publish time (COMPLIANCE-01 items 2–3).

The product produces FIRST DRAFTS; users are expected to edit text before publishing.
So disclosure targets what is published *as AI output* (user decisions 2026-10-28,
docs/explore-compliance-01.md v1.1):

- D1  a text post published identical to its AI draft is disclosed; edited text is not.
- D2  "identical" = equal after normalising whitespace/line breaks and letter case.
- D3  platform-generated media (``media-asset://`` refs) is always disclosed.
- D4  native API flag where the platform has one (TikTok ``is_aigc``, YouTube
      ``containsSyntheticMedia``); otherwise a short visible label is appended.
- D5  free-text scheduled posts carry a schedule-time checkbox; ``None`` means AI.

Everything here is pure (no DB) so the rule lives in one place and every caller —
the schedule-time gate, the publisher call, the API response — agrees.

Not legal advice: whether this satisfies EU AI Act Art. 50 is a counsel question
(docs/COMPLIANCE_01_EXPOSURE_ASSESSMENT.md §6). The label text is configurable.
"""

import os
import re
from typing import Any, Optional

# Platforms whose publish API has a native AI-content flag (verified 2026-10-28).
NATIVE_FLAG_PLATFORMS: frozenset[str] = frozenset({"tiktok", "youtube"})

DEFAULT_LABEL = "Drafted with AI"

# Media produced by the platform's own generation pipeline (a MediaAsset always has a
# job_id), as opposed to a plain URL to the user's own media.
_GENERATED_MEDIA_PREFIX = "media-asset://"

_WHITESPACE = re.compile(r"\s+")


def normalise(text: Optional[str]) -> str:
    """Collapse whitespace runs to one space, trim, and casefold (D2)."""
    return _WHITESPACE.sub(" ", text or "").strip().casefold()


def is_unedited_draft(text: Optional[str], draft: Optional[str]) -> bool:
    """True if ``text`` is still the AI draft. No snapshot (pre-v10 post) ⇒ True."""
    if draft is None:
        return True
    return normalise(text) == normalise(draft)


def needs_disclosure(sp: Any, post: Optional[Any]) -> bool:
    """Decide whether a scheduled post must be disclosed as AI-generated.

    Args:
        sp: the ScheduledPost (uses ``content``, ``media_url``, ``ai_generated``).
        post: the linked Post (``ai_draft_content``), or None — for free text, or when
            a linked post is missing/inaccessible (then always disclosed).
    """
    if (sp.media_url or "").startswith(_GENERATED_MEDIA_PREFIX):
        return True  # D3
    if post is not None:
        return is_unedited_draft(sp.content, post.ai_draft_content)  # D1/D2
    if sp.post_id:
        # Linked, but the post is gone or no longer accessible: there's no draft to
        # compare against, and the checkbox is for free text only — disclose.
        return True
    return sp.ai_generated is not False  # D5 — None (unanswered) counts as AI


def disclosure_label() -> str:
    """The visible label (env ``AI_DISCLOSURE_LABEL``). Blank falls back to the default:
    it can be reworded, not switched off by an empty value."""
    return os.getenv("AI_DISCLOSURE_LABEL", "").strip() or DEFAULT_LABEL


def with_text_label(content: str, platform: str) -> str:
    """Append the visible label on platforms without a native flag (D4). Idempotent."""
    if platform in NATIVE_FLAG_PLATFORMS:
        return content
    label = disclosure_label()
    if normalise(content).endswith(normalise(label)):
        return content
    return f"{content}\n\n{label}"
