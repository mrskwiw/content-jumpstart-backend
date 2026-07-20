"""
Engagement metric collectors (Phase 11).

Two paths, chosen per-call by ANALYTICS_DRY_RUN (default ON until real platform
apps are approved):
  * dry-run  -> `_stub_metrics`, deterministic fake engagement from the post id,
    so the collect → aggregate → serve loop works and is testable now.
  * real     -> a per-platform `BaseCollector` that queries the platform's
    insights API using the connected account's (refreshed) OAuth token, mirroring
    the publisher abstraction. A platform with no collector or no credential is
    skipped (logged), never faked.

Set ANALYTICS_DRY_RUN=false once a platform app + token exist to collect real
numbers. Endpoints reflect each platform's current public insights API.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from sqlalchemy.orm import Session

from backend.models import Post
from backend.models.analytics import PostMetric
from backend.models.distribution import PostedContent, ScheduledPost
from backend.services.distribution import oauth, orchestrator

logger = logging.getLogger(__name__)

_METRIC_KEYS = ("likes", "comments", "shares", "impressions", "reach")
_HTTP_TIMEOUT = 30


def dry_run_enabled() -> bool:
    # Default ON: without real platform collectors + creds, stub is the only source.
    return os.getenv("ANALYTICS_DRY_RUN", "true").strip().lower() in ("1", "true", "yes")


def _stub_metrics(seed: str) -> Dict[str, int]:
    """Deterministic, plausible engagement numbers derived from a seed."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    impressions = 500 + (h % 4500)
    like_rate = ((h >> 8) % 8 + 1) / 100.0  # 1%–8%
    likes = int(impressions * like_rate)
    comments = int(likes * 0.10) + (h % 5)
    shares = int(likes * 0.05) + (h % 3)
    reach = int(impressions * 0.8)
    return {
        "impressions": impressions,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "reach": reach,
    }


def _zero() -> Dict[str, int]:
    return {k: 0 for k in _METRIC_KEYS}


# ── Real per-platform collectors ────────────────────────────────────────────────


class BaseCollector:
    """Fetch engagement metrics for one published post on one platform.

    `account_ref` is part of the contract for symmetry with publishers, but the
    read endpoints are self-scoping: the stored `platform_post_id` (a Facebook
    compound id, IG media id, LinkedIn URN, tweet id, or video id) plus the
    credential's token already identify the exact object, so most collectors
    don't need account_ref. It's threaded through for platforms that may require
    it later.
    """

    platform = "base"

    def collect(
        self, platform_post_id: str, token: str, account_ref: Optional[str]
    ) -> Dict[str, int]:  # pragma: no cover - overridden
        raise NotImplementedError


class TwitterCollector(BaseCollector):
    platform = "twitter"

    def collect(self, platform_post_id, token, account_ref):
        # impression_count lives in non_public_metrics/organic_metrics (author
        # context), NOT public_metrics — request both so impressions aren't 0.
        resp = requests.get(
            f"https://api.twitter.com/2/tweets/{platform_post_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"tweet.fields": "public_metrics,non_public_metrics,organic_metrics"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        pub = data.get("public_metrics") or {}
        nonpub = data.get("non_public_metrics") or {}
        organic = data.get("organic_metrics") or {}
        impressions = (
            nonpub.get("impression_count")
            or organic.get("impression_count")
            or pub.get("impression_count")
            or 0
        )
        return {
            "likes": pub.get("like_count", 0),
            "comments": pub.get("reply_count", 0),
            "shares": pub.get("retweet_count", 0) + pub.get("quote_count", 0),
            "impressions": impressions,
            "reach": impressions,
        }


class LinkedInCollector(BaseCollector):
    platform = "linkedin"

    def collect(self, platform_post_id, token, account_ref):
        # socialActions gives like/comment summaries for a share/ugcPost URN.
        resp = requests.get(
            f"https://api.linkedin.com/v2/socialActions/{platform_post_id}",
            headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        out = _zero()
        out["likes"] = (body.get("likesSummary") or {}).get("totalLikes", 0)
        out["comments"] = (body.get("commentsSummary") or {}).get("totalComments", 0)
        return out


class FacebookCollector(BaseCollector):
    platform = "facebook"

    def collect(self, platform_post_id, token, account_ref):
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{platform_post_id}",
            params={
                "fields": "likes.summary(true),comments.summary(true),shares,"
                "insights.metric(post_impressions,post_impressions_unique)",
                "access_token": token,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        out = _zero()
        out["likes"] = ((body.get("likes") or {}).get("summary") or {}).get("total_count", 0)
        out["comments"] = ((body.get("comments") or {}).get("summary") or {}).get("total_count", 0)
        out["shares"] = (body.get("shares") or {}).get("count", 0)
        for row in (body.get("insights") or {}).get("data") or []:
            val = (row.get("values") or [{}])[0].get("value", 0)
            if row.get("name") == "post_impressions":
                out["impressions"] = val
            elif row.get("name") == "post_impressions_unique":
                out["reach"] = val
        return out


class InstagramCollector(BaseCollector):
    platform = "instagram"

    def collect(self, platform_post_id, token, account_ref):
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{platform_post_id}/insights",
            params={"metric": "impressions,reach,likes,comments,shares", "access_token": token},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        out = _zero()
        mapping = {
            "impressions": "impressions",
            "reach": "reach",
            "likes": "likes",
            "comments": "comments",
            "shares": "shares",
        }
        for row in resp.json().get("data") or []:
            key = mapping.get(row.get("name"))
            if key:
                out[key] = (row.get("values") or [{}])[0].get("value", 0)
        return out


class TikTokCollector(BaseCollector):
    platform = "tiktok"

    def collect(self, platform_post_id, token, account_ref):
        resp = requests.post(
            "https://open.tiktokapis.com/v2/video/query/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"fields": "like_count,comment_count,share_count,view_count"},
            json={"filters": {"video_ids": [platform_post_id]}},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        videos = (resp.json().get("data") or {}).get("videos") or []
        v = videos[0] if videos else {}
        views = v.get("view_count", 0)
        return {
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "shares": v.get("share_count", 0),
            "impressions": views,
            "reach": views,
        }


class YouTubeCollector(BaseCollector):
    platform = "youtube"

    def collect(self, platform_post_id, token, account_ref):
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "statistics", "id": platform_post_id},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items") or []
        stats = items[0].get("statistics", {}) if items else {}
        views = int(stats.get("viewCount", 0))
        return {
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "shares": 0,  # not exposed by the API
            "impressions": views,
            "reach": views,
        }


_REAL_COLLECTORS = {
    "twitter": TwitterCollector,
    "linkedin": LinkedInCollector,
    "facebook": FacebookCollector,
    "instagram": InstagramCollector,
    "tiktok": TikTokCollector,
    "youtube": YouTubeCollector,
}


def get_collector(platform: str) -> Optional[BaseCollector]:
    impl = _REAL_COLLECTORS.get(platform)
    return impl() if impl else None


# ── Orchestration ───────────────────────────────────────────────────────────────


def _scheduled_post(db: Session, pc: PostedContent) -> Optional[ScheduledPost]:
    return db.query(ScheduledPost).filter(ScheduledPost.id == pc.scheduled_post_id).first()


def _template_for(db: Session, sp: Optional[ScheduledPost]) -> Optional[str]:
    if sp and sp.post_id:
        post = db.query(Post).filter(Post.id == sp.post_id).first()
        if post:
            return post.template_name
    return None


def _real_metrics(db: Session, user_id: str, pc: PostedContent, sp: Optional[ScheduledPost]):
    """Collect real metrics for one posted item, or None if it can't be collected."""
    collector = get_collector(pc.platform)
    if collector is None or not pc.platform_post_id:
        return None
    client_id = sp.client_id if sp else None
    cred = orchestrator._load_credential(db, user_id, pc.platform, client_id)
    if cred is None:
        logger.info("Analytics: no credential for %s pc %s — skipped", pc.platform, pc.id)
        return None
    try:
        token = oauth.ensure_fresh_token(db, cred)
        metrics = collector.collect(pc.platform_post_id, token, cred.account_ref)
    except Exception as e:  # noqa: BLE001 - one bad post must not abort the batch
        logger.warning("Analytics collect failed for %s pc %s: %s", pc.platform, pc.id, e)
        return None
    # Fill any missing keys with 0.
    return {k: int(metrics.get(k, 0)) for k in _METRIC_KEYS}


def collect_for_user(db: Session, user_id: str) -> Dict[str, int]:
    """Collect engagement metrics for every published post the user owns.

    Idempotent per (posted_content, day): re-running the same day updates the
    existing snapshot rather than duplicating it.
    """
    dry_run = dry_run_enabled()
    today = datetime.now(timezone.utc).date()
    posted = db.query(PostedContent).filter(PostedContent.user_id == user_id).all()
    collected = 0
    skipped = 0
    for pc in posted:
        sp = _scheduled_post(db, pc)
        if dry_run:
            metrics = _stub_metrics(pc.platform_post_id or pc.id)
        else:
            metrics = _real_metrics(db, user_id, pc, sp)
            if metrics is None:
                skipped += 1
                continue
        existing = (
            db.query(PostMetric)
            .filter(PostMetric.posted_content_id == pc.id, PostMetric.metric_date == today)
            .first()
        )
        if existing:
            for k, v in metrics.items():
                setattr(existing, k, v)
        else:
            db.add(
                PostMetric(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    posted_content_id=pc.id,
                    scheduled_post_id=pc.scheduled_post_id,
                    platform=pc.platform,
                    template_name=_template_for(db, sp),
                    metric_date=today,
                    **metrics,
                )
            )
        collected += 1
    db.commit()
    return {"collected": collected, "skipped": skipped, "dry_run": dry_run}
