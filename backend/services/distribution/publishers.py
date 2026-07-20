"""
Platform publisher abstraction for Phase 10 distribution.

Each platform is a `BasePublisher` that turns decrypted credentials + content
into a `PublishResult`. The whole schedule→publish→track loop works today via
`StubPublisher` (no network); real platforms are pluggable. LinkedIn is
implemented against the real API (adapted from the phase plan); the other
platforms are scaffolded and fail closed with a clear message until their
integration + platform app approval land.

Dry-run: set env `DISTRIBUTION_DRY_RUN=true` (or use a `platform="stub"`
credential) to route every publish to the stub — safe for demos and tests.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    success: bool
    platform_post_id: Optional[str] = None
    platform_url: Optional[str] = None
    error: Optional[str] = None


def dry_run_enabled() -> bool:
    return os.getenv("DISTRIBUTION_DRY_RUN", "false").strip().lower() in ("1", "true", "yes")


class BasePublisher:
    platform: str = "base"

    def __init__(self, access_token: str, account_ref: Optional[str] = None, **kw):
        self.access_token = access_token
        self.account_ref = account_ref

    def publish(
        self, content: str, media_url: Optional[str] = None
    ) -> PublishResult:  # pragma: no cover
        raise NotImplementedError


class StubPublisher(BasePublisher):
    """Deterministic no-network publisher for dry-run/demo/tests."""

    platform = "stub"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import hashlib

        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return PublishResult(
            success=True,
            platform_post_id=f"stub_{digest}",
            platform_url=f"https://stub.local/post/{digest}",
        )


class NotImplementedPublisher(BasePublisher):
    """Fail-closed publisher for platforms whose integration isn't built yet."""

    def __init__(self, platform: str, *a, **kw):
        super().__init__(*a, **kw)
        self.platform = platform

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        return PublishResult(
            success=False,
            error=(
                f"Publishing to '{self.platform}' is not implemented yet — it requires a "
                f"registered platform app + OAuth. Use DISTRIBUTION_DRY_RUN or a 'stub' "
                f"credential to exercise the flow."
            ),
        )


class LinkedInPublisher(BasePublisher):
    """LinkedIn UGC text post via api.linkedin.com/v2 (real network call)."""

    platform = "linkedin"
    BASE_URL = "https://api.linkedin.com/v2"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            author = (
                f"urn:li:organization:{self.account_ref}"
                if self.account_ref
                else self._person_urn(headers)
            )
            payload = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
            resp = requests.post(
                f"{self.BASE_URL}/ugcPosts", headers=headers, json=payload, timeout=30
            )
            if resp.status_code == 201:
                post_id = resp.headers.get("X-RestLi-Id", "")
                return PublishResult(
                    success=True,
                    platform_post_id=post_id,
                    platform_url=f"https://www.linkedin.com/feed/update/{post_id}",
                )
            return PublishResult(
                success=False, error=f"LinkedIn API {resp.status_code}: {resp.text[:300]}"
            )
        except Exception as e:  # network / auth / parse
            logger.warning("LinkedIn publish failed: %s", e)
            return PublishResult(success=False, error=str(e))

    def _person_urn(self, headers: dict) -> str:
        import requests

        resp = requests.get(f"{self.BASE_URL}/me", headers=headers, timeout=30)
        resp.raise_for_status()
        return f"urn:li:person:{resp.json()['id']}"


# Real publishers wired here as they're implemented.
_REAL_PUBLISHERS = {"linkedin": LinkedInPublisher}


def get_publisher(
    platform: str, access_token: str, account_ref: Optional[str] = None
) -> BasePublisher:
    """Resolve the publisher for a platform.

    Order: explicit dry-run / 'stub' platform → StubPublisher; a platform with a
    real implementation → that publisher; otherwise a fail-closed
    NotImplementedPublisher.
    """
    if platform == "stub" or dry_run_enabled():
        return StubPublisher(access_token=access_token, account_ref=account_ref)
    impl = _REAL_PUBLISHERS.get(platform)
    if impl:
        return impl(access_token=access_token, account_ref=account_ref)
    return NotImplementedPublisher(platform, access_token=access_token, account_ref=account_ref)
