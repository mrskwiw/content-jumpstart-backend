"""Render deploy-failure alerts (BUGS #239).

A failed Render deploy leaves the previous version serving, so the site looks healthy
while new code never ships — prod deploys failed silently for ~2 weeks in 2026-08 that
way. Render posts workspace events here; failures are emailed to ``OPS_ALERT_EMAIL``.

    POST /api/ops/render-webhook   — no login, no CSRF; the signature is the auth

Signatures follow the Standard Webhooks spec, which Render's docs say it implements:
the HMAC-SHA256 key is the base64-decoded secret after ``whsec_``, the signed content
is ``"{webhook-id}.{webhook-timestamp}.{body}"``, and ``webhook-signature`` holds
space-separated ``v1,<base64>`` values (several during secret rotation).

Delivery: the response is 200 only once the alert email has actually gone out (or the
event needs no alert); otherwise 503, so Render retries. Render's retries are the
durable queue — up to 8 attempts over ~33h, and after the 3rd failure Render emails
the account that the webhook is failing, so even a broken mailer surfaces. A webhook-id
is remembered only after a successful send, so a retry of an unsent alert is sent and a
retry of a sent one is not. The send is capped at 12s to stay inside Render's 15s
deadline (the mailer alone can take ~33s); a send that outlives the cap and later
succeeds still marks its id, so the retry isn't re-sent. Production runs one worker
(Dockerfile), so the in-process id memory is shared by all requests; a restart can at
worst repeat one email.

Environment:
    RENDER_WEBHOOK_SECRET  the webhook's signing secret (unset → route answers 404, so
                           customer instances, which also ship this route, stay inert)
    OPS_ALERT_EMAIL        who receives alerts (unset → 503, so Render retries and,
                           after 3 failures, emails the account)
"""

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from backend.utils.logger import logger

router = APIRouter()

# Standard Webhooks tolerance; Render's docs suggest "within the last five minutes".
_TOLERANCE_SECONDS = 300

# Lifecycle events whose `status` can be "failed" (Render sets `status` only on
# build_ended, deploy_ended and job events; a failed pre-deploy surfaces as
# deploy_ended: failed). image_pull_failed is a failure by its type alone.
_STATUS_EVENTS = frozenset({"deploy_ended", "build_ended"})

# Must finish inside Render's 15s delivery deadline.
_SEND_DEADLINE_SECONDS = 12.0
_FAILURE_EVENTS = frozenset({"image_pull_failed"})

# Render retries a notification with the same webhook-id. Remember recent ids so one
# failure produces one email (best effort: per process, bounded).
_SEEN_LIMIT = 500
_seen_ids: Set[str] = set()
_seen_order: Deque[str] = deque()


def _signing_key(secret: str) -> bytes:
    """Decode a Standard Webhooks secret (``whsec_<base64>``) into the HMAC key."""
    raw = secret[len("whsec_") :] if secret.startswith("whsec_") else secret
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        # Not base64: use the bytes as given rather than reject a working secret.
        return raw.encode()


def _signature_valid(secret: str, msg_id: str, timestamp: str, body: bytes, header: str) -> bool:
    """Verify a Standard Webhooks signature, including the replay window."""
    if not (msg_id and timestamp and header):
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - sent_at) > _TOLERANCE_SECONDS:
        return False

    content = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(_signing_key(secret), content, hashlib.sha256).digest()
    ).decode()
    for candidate in header.split():
        version, _, signature = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(signature, expected):
            return True
    return False


def _is_failure(event: Dict[str, Any]) -> bool:
    event_type = event.get("type")
    if event_type in _FAILURE_EVENTS:
        return True
    data = event.get("data") or {}
    return event_type in _STATUS_EVENTS and data.get("status") == "failed"


def _remember(msg_id: str) -> None:
    """Record a webhook-id whose alert went out (retries reuse the id)."""
    if msg_id in _seen_ids:
        return
    _seen_ids.add(msg_id)
    _seen_order.append(msg_id)
    while len(_seen_order) > _SEEN_LIMIT:
        _seen_ids.discard(_seen_order.popleft())


def _format_time(iso: Optional[str]) -> str:
    """Render an event time as America/Chicago with the UTC source kept."""
    if not iso:
        return "unknown time"
    # Render sends nanoseconds ("…19.979294509Z"); fromisoformat takes at most 6 digits.
    normalized = re.sub(r"(\.\d{6})\d+", r"\1", iso).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return iso
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    utc = parsed.astimezone(timezone.utc)
    stamp = f"{utc:%Y-%m-%d %H:%M} UTC"
    try:
        from zoneinfo import ZoneInfo

        local = utc.astimezone(ZoneInfo("America/Chicago"))
        return f"{stamp} → {local:%Y-%m-%d %I:%M %p %Z}"
    except Exception:  # noqa: BLE001 - no tz database in the image: UTC alone is still useful
        return stamp


def _send_email(message: Any) -> bool:
    """Send via the app's transport (Resend / SMTP / log). Never raises."""
    from agent.email_system import EmailSystem

    ok, detail = EmailSystem().send_email(message)
    if not ok:
        logger.error(f"Render deploy-failure alert email not sent: {detail}")
    return ok


def _deliver(event: Dict[str, Any], recipient: str, msg_id: str) -> bool:
    """Send the alert; remember the id only if it went out. Returns whether it did."""
    if _alert(event, recipient, msg_id):
        _remember(msg_id)
        return True
    return False


def _alert(event: Dict[str, Any], recipient: str, msg_id: str) -> bool:
    from agent.email_system import EmailMessage, EmailPriority

    data = event.get("data") or {}
    service = data.get("serviceName") or "unknown service"
    service_id = data.get("serviceId") or "unknown"
    event_type = event.get("type", "unknown")
    status_text = data.get("status", "failed")
    body = (
        f"A Render {event_type} event reported '{status_text}' for {service}.\n\n"
        f"Service:  {service} ({service_id})\n"
        f"Event:    {event_type} (event id {data.get('id', 'n/a')})\n"
        f"When:     {_format_time(event.get('timestamp'))}\n"
        f"Dashboard: https://dashboard.render.com/web/{service_id}\n\n"
        "The previous version keeps serving after a failed deploy, so the site can look "
        "healthy while new code never ships. Check the deploy logs (BUGS #239)."
    )
    return _send_email(
        EmailMessage(
            # Also Resend's Idempotency-Key: stable per webhook-id, so the provider drops
            # a duplicate send of this alert (retry or concurrent delivery).
            message_id=f"render-alert-{msg_id}",
            to_email=recipient,
            subject=f"[Render] {event_type} failed: {service}",
            body_text=body,
            priority=EmailPriority.HIGH,
        )
    )


@router.post("/render-webhook", status_code=status.HTTP_200_OK)
async def render_webhook(request: Request) -> Dict[str, str]:
    """Receive a Render workspace webhook and email on deploy failures."""
    secret = os.getenv("RENDER_WEBHOOK_SECRET", "").strip()
    if not secret:
        # Inert on every instance that isn't the configured receiver.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    body = await request.body()
    msg_id = request.headers.get("webhook-id", "")
    if not _signature_valid(
        secret,
        msg_id,
        request.headers.get("webhook-timestamp", ""),
        body,
        request.headers.get("webhook-signature", ""),
    ):
        logger.warning("Render webhook rejected: invalid or stale signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        event = json.loads(body)
    except ValueError:
        logger.error("Render webhook: signed body is not JSON; acknowledged and ignored")
        return {"status": "ignored"}
    if not isinstance(event, dict) or not _is_failure(event):
        return {"status": "ignored"}
    if msg_id in _seen_ids:
        return {"status": "duplicate"}

    service = (event.get("data") or {}).get("serviceName")
    recipient = os.getenv("OPS_ALERT_EMAIL", "").strip()
    if not recipient:
        logger.error(f"Render deploy failure for {service} but OPS_ALERT_EMAIL is unset")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alert not routed")

    try:
        sent = await asyncio.wait_for(
            run_in_threadpool(_deliver, event, recipient, msg_id),
            timeout=_SEND_DEADLINE_SECONDS,
        )
    except asyncio.TimeoutError:
        sent = False
        logger.error(f"Render deploy-failure alert for {service} timed out; Render will retry")
    if not sent:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alert not sent")
    return {"status": "alerted"}
