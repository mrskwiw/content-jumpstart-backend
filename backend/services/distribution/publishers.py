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

from backend.services.distribution.net_guard import safe_stream_get

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

    def verify(self) -> PublishResult:
        """Prove a manually-entered credential works BEFORE it's persisted.

        Default: assume valid. OAuth platforms are validated by their consent handshake,
        so there's nothing to round-trip at manual-connect time. Publishers with
        app-password / manual auth (e.g. Bluesky) override this to actually authenticate,
        so a bad credential is rejected at connect time instead of failing at publish.
        """
        return PublishResult(success=True)


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

    def verify(self) -> PublishResult:
        # Fail closed: don't let a credential be stored for a platform we can't publish to.
        return self.publish("")


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
        # common personal-account publish path. Per LinkedIn's OIDC contract the
        # `sub` claim IS the member id, and urn:li:person:{sub} is the correct UGC
        # author URN (equivalent to persisting the id at connect time).
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
            # 2) Stream the source video into the session. media_url is
            # operator-supplied and fetched server-side here, so it goes through
            # the SSRF guard (rejects internal/loopback/link-local targets and
            # re-validates every redirect hop). session_url is LinkedIn/Google-
            # issued, not user input, so it is not guarded.
            with safe_stream_get(media_url, timeout=_HTTP_TIMEOUT) as src:
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


class BlueskyPublisher(BasePublisher):
    """Bluesky text post via the AT Protocol (DIST-EXPAND).

    Bluesky uses app-password auth (not OAuth): the credential's ``account_ref`` is the
    handle/DID and ``access_token`` is an app password. Publish is two calls — exchange the
    app password for a session, then create a feed post. Credentials are connected via the
    manual ``POST /api/distribution/credentials`` endpoint (there is no OAuth flow)."""

    platform = "bluesky"

    _DEFAULT_HOST = "https://bsky.social"

    def _base(self) -> Optional[str]:
        # The AT Protocol service host, env-configurable so an instance whose accounts live
        # on another/self-hosted PDS can point at it (per-tenant deployment = one PDS per
        # instance). Exhaustive semantics:
        #   • TRULY UNSET (var absent)               → default bsky.social (the common case)
        #   • PRESENT-BUT-BLANK / not an http(s) URL → None, so publish() fails closed.
        # A blank value is a misconfiguration (templated-but-empty), NOT an opt-out — silently
        # defaulting it could publish to the wrong PDS with the wrong credentials. os.getenv
        # returns None only when the var is absent, so blank ("" / whitespace) is distinguished
        # from unset here. Scheme match is case-insensitive (URL schemes are, per RFC 3986) and
        # normalized to lowercase. Full per-handle DID discovery is a future enhancement.
        raw = os.getenv("BLUESKY_PDS_URL")
        if raw is None:
            return f"{self._DEFAULT_HOST}/xrpc"
        scheme, sep, rest = raw.strip().rstrip("/").partition("://")
        if sep != "://" or scheme.lower() not in ("http", "https") or not rest:
            return None
        return f"{scheme.lower()}://{rest}/xrpc"

    def _authenticate(self):
        """Open an AT Protocol session (createSession) without posting anything.

        Returns ``(session, None)`` on success — session is a dict with ``base``, ``handle``,
        ``jwt``, ``did`` — or ``(None, PublishResult)`` carrying the failure for the caller to
        return. Shared by :meth:`publish` and :meth:`verify` so both reject a bad host / missing
        handle / bad app password identically.
        """
        import requests

        base = self._base()
        if base is None:
            return None, PublishResult(
                success=False,
                error="BLUESKY_PDS_URL is set but is not a valid http(s) URL — fix the instance config",
            )
        handle = self.account_ref
        if not handle:
            return None, PublishResult(
                success=False,
                error="Bluesky requires the account handle (set account_ref on the credential)",
            )
        sess = requests.post(
            f"{base}/com.atproto.server.createSession",
            json={"identifier": handle, "password": self.access_token},
            timeout=_HTTP_TIMEOUT,
        )
        if sess.status_code >= 400:
            return None, PublishResult(
                success=False, error=f"Bluesky auth {sess.status_code}: {sess.text[:200]}"
            )
        sd = sess.json() or {}
        jwt, did = sd.get("accessJwt"), sd.get("did")
        if not jwt or not did:
            return None, PublishResult(success=False, error="Bluesky session missing accessJwt/did")
        return {"base": base, "handle": handle, "jwt": jwt, "did": did}, None

    def verify(self) -> PublishResult:
        """Authenticate the handle + app password (createSession) WITHOUT posting, so a bad
        credential is rejected at connect time rather than creating a false "connected" state
        that only fails at publish. No record is created."""
        try:
            _session, err = self._authenticate()
            return err or PublishResult(success=True)
        except Exception as e:  # network / parse
            logger.warning("Bluesky verify failed: %s", e)
            return PublishResult(success=False, error=str(e))

    def publish(self, content: str, media_url: Optional[str] = None) -> PublishResult:
        import requests
        from datetime import datetime, timezone

        try:
            # Image/video embeds require an uploadBlob + record-embed flow not built yet.
            # Fail closed rather than silently publishing text-only and reporting success.
            if media_url:
                return PublishResult(
                    success=False,
                    error="Bluesky media embeds are not supported yet — schedule a text-only post (omit media_url)",
                )
            session, err = self._authenticate()
            if err:
                return err
            base, handle, jwt, did = (
                session["base"],
                session["handle"],
                session["jwt"],
                session["did"],
            )
            created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            rec = requests.post(
                f"{base}/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": {"text": content, "createdAt": created_at},
                },
                timeout=_HTTP_TIMEOUT,
            )
            if rec.status_code >= 400:
                return PublishResult(
                    success=False, error=f"Bluesky post {rec.status_code}: {rec.text[:300]}"
                )
            uri = (rec.json() or {}).get("uri", "")  # at://did/app.bsky.feed.post/<rkey>
            rkey = uri.rsplit("/", 1)[-1] if uri else ""
            url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else None
            return PublishResult(success=True, platform_post_id=uri, platform_url=url)
        except Exception as e:  # network / auth / parse
            logger.warning("Bluesky publish failed: %s", e)
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
    "bluesky": BlueskyPublisher,
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
