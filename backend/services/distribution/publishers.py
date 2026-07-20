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

        # Use the OpenID Connect userinfo endpoint, which matches the scopes the
        # connect flow requests (`openid profile`). The legacy /v2/me endpoint
        # needs r_liteprofile, which we do NOT request, so it would 403 on the
        # common personal-account publish path.
        resp = requests.get(f"{self.BASE_URL}/userinfo", headers=headers, timeout=30)
        resp.raise_for_status()
        return f"urn:li:person:{resp.json()['sub']}"


_HTTP_TIMEOUT = 30


class TwitterPublisher(BasePublisher):
    """Post a tweet via the X API v2 (POST /2/tweets)."""

    platform = "twitter"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests

        try:
            resp = requests.post(
                "https://api.twitter.com/2/tweets",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"text": content},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code in (200, 201):
                tweet_id = (resp.json().get("data") or {}).get("id", "")
                return PublishResult(
                    success=True,
                    platform_post_id=tweet_id,
                    platform_url=f"https://twitter.com/i/web/status/{tweet_id}",
                )
            return PublishResult(
                success=False, error=f"X API {resp.status_code}: {resp.text[:300]}"
            )
        except Exception as e:  # noqa: BLE001 - surface any failure as a result
            logger.warning("Twitter publish failed: %s", e)
            return PublishResult(success=False, error=str(e))


class FacebookPublisher(BasePublisher):
    """Post to a Facebook Page feed (POST /{page-id}/feed).

    `account_ref` must be the Page id and `access_token` a Page access token.
    """

    platform = "facebook"
    GRAPH = "https://graph.facebook.com/v19.0"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests

        if not self.account_ref:
            return PublishResult(
                success=False,
                error="Facebook requires account_ref (the Page id) on the connected account.",
            )
        try:
            # A media_url posts a photo; otherwise a plain text status.
            if media_url:
                url = f"{self.GRAPH}/{self.account_ref}/photos"
                data = {"url": media_url, "caption": content, "access_token": self.access_token}
            else:
                url = f"{self.GRAPH}/{self.account_ref}/feed"
                data = {"message": content, "access_token": self.access_token}
            resp = requests.post(url, data=data, timeout=_HTTP_TIMEOUT)
            if resp.status_code < 400:
                pid = resp.json().get("post_id") or resp.json().get("id") or ""
                return PublishResult(
                    success=True,
                    platform_post_id=pid,
                    platform_url=f"https://www.facebook.com/{pid}",
                )
            return PublishResult(
                success=False, error=f"Facebook Graph {resp.status_code}: {resp.text[:300]}"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Facebook publish failed: %s", e)
            return PublishResult(success=False, error=str(e))


class InstagramPublisher(BasePublisher):
    """Publish an Instagram post via the two-step Graph content-publishing flow.

    `account_ref` must be the IG Business/Creator user id. Instagram requires
    media — a `media_url` (public image URL) is mandatory.
    """

    platform = "instagram"
    GRAPH = "https://graph.facebook.com/v19.0"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests

        if not self.account_ref:
            return PublishResult(
                success=False, error="Instagram requires account_ref (the IG user id)."
            )
        if not media_url:
            return PublishResult(
                success=False,
                error="Instagram requires an image — attach a public media_url to the post.",
            )
        try:
            # 1) Create a media container.
            create = requests.post(
                f"{self.GRAPH}/{self.account_ref}/media",
                data={
                    "image_url": media_url,
                    "caption": content,
                    "access_token": self.access_token,
                },
                timeout=_HTTP_TIMEOUT,
            )
            if create.status_code >= 400:
                return PublishResult(
                    success=False,
                    error=f"Instagram container {create.status_code}: {create.text[:300]}",
                )
            creation_id = create.json().get("id")
            # 2) Publish the container.
            publish = requests.post(
                f"{self.GRAPH}/{self.account_ref}/media_publish",
                data={"creation_id": creation_id, "access_token": self.access_token},
                timeout=_HTTP_TIMEOUT,
            )
            if publish.status_code < 400:
                mid = publish.json().get("id", "")
                return PublishResult(
                    success=True,
                    platform_post_id=mid,
                    platform_url=f"https://www.instagram.com/p/{mid}",
                )
            return PublishResult(
                success=False,
                error=f"Instagram publish {publish.status_code}: {publish.text[:300]}",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Instagram publish failed: %s", e)
            return PublishResult(success=False, error=str(e))


class TikTokPublisher(BasePublisher):
    """Publish a video to TikTok via the Content Posting API (PULL_FROM_URL).

    TikTok is video-only, so a `media_url` (public video URL) is mandatory.
    """

    platform = "tiktok"
    INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests

        if not media_url:
            return PublishResult(
                success=False, error="TikTok requires a video — attach a public media_url."
            )
        try:
            resp = requests.post(
                self.INIT,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={
                    "post_info": {"title": content[:150], "privacy_level": "SELF_ONLY"},
                    "source_info": {"source": "PULL_FROM_URL", "video_url": media_url},
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code < 400:
                publish_id = (resp.json().get("data") or {}).get("publish_id", "")
                # Publishing is async on TikTok's side; we record the publish_id.
                return PublishResult(success=True, platform_post_id=publish_id, platform_url=None)
            return PublishResult(
                success=False, error=f"TikTok {resp.status_code}: {resp.text[:300]}"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("TikTok publish failed: %s", e)
            return PublishResult(success=False, error=str(e))


class YouTubePublisher(BasePublisher):
    """Upload a video to YouTube (Data API v3, resumable upload from a URL).

    YouTube is video-only, so a `media_url` (public video URL) is mandatory. The
    video bytes are streamed from media_url into a resumable upload session.
    """

    platform = "youtube"
    UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import json as _json

        import requests

        if not media_url:
            return PublishResult(
                success=False, error="YouTube requires a video — attach a public media_url."
            )
        try:
            title = (content.splitlines()[0] if content else "Untitled")[:95]
            metadata = {
                "snippet": {"title": title, "description": content},
                "status": {"privacyStatus": "private"},
            }
            # 1) Open a resumable session.
            init = requests.post(
                f"{self.UPLOAD}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                data=_json.dumps(metadata),
                timeout=_HTTP_TIMEOUT,
            )
            if init.status_code >= 400 or "location" not in init.headers:
                return PublishResult(
                    success=False, error=f"YouTube init {init.status_code}: {init.text[:300]}"
                )
            session_url = init.headers["location"]
            # 2) Stream the source video into the session.
            with requests.get(media_url, stream=True, timeout=_HTTP_TIMEOUT) as src:
                src.raise_for_status()
                up = requests.put(
                    session_url,
                    headers={"Content-Type": src.headers.get("Content-Type", "video/*")},
                    data=src.iter_content(chunk_size=1024 * 1024),
                    timeout=300,
                )
            if up.status_code < 400:
                vid = up.json().get("id", "")
                return PublishResult(
                    success=True,
                    platform_post_id=vid,
                    platform_url=f"https://www.youtube.com/watch?v={vid}",
                )
            return PublishResult(
                success=False, error=f"YouTube upload {up.status_code}: {up.text[:300]}"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("YouTube publish failed: %s", e)
            return PublishResult(success=False, error=str(e))


# Real publishers wired here as they're implemented. A platform absent from this
# map falls through to NotImplementedPublisher (fail-closed).
_REAL_PUBLISHERS = {
    "linkedin": LinkedInPublisher,
    "twitter": TwitterPublisher,
    "facebook": FacebookPublisher,
    "instagram": InstagramPublisher,
    "tiktok": TikTokPublisher,
    "youtube": YouTubePublisher,
}


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
