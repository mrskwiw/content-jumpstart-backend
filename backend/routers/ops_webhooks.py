"""Render deploy-failure alerts (BUGS #239).

A failed Render deploy leaves the previous version serving, so the site looks healthy
while new code never ships — prod deploys failed silently for ~2 weeks in 2026-08 that
way. Render posts workspace events here; failures are emailed to ``OPS_ALERT_EMAIL``.

    POST /api/ops/render-webhook   — no login, no CSRF; the signature is the auth

Signatures follow the Standard Webhooks spec, which Render's docs say it implements:
the HMAC-SHA256 key is the base64-decoded secret after ``whsec_``, the signed content
is ``"{webhook-id}.{webhook-timestamp}.{body}"``, and ``webhook-signature`` holds
space-separated ``v1,<base64>`` values (several during secret rotation).

Render disables a webhook after 8 failed deliveries, and expects a 2xx within 15s. So
once a request is authentic it is always acknowledged with 200, and the email is sent
in a background task — a broken mailer can never turn into a disabled webhook.

Environment:
    RENDER_WEBHOOK_SECRET  the webhook's signing secret (unset → route answers 404, so
                           customer instances, which also ship this route, stay inert)
    OPS_ALERT_EMAIL        who receives alerts (unset → logged as an error, not sent)
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Set

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from backend.utils.logger import logger

router = APIRouter()

# Standard Webhooks tolerance; Render's docs suggest "within the last five minutes".
_TOLERANCE_SECONDS = 300

# Lifecycle events whose `status` can be "failed"; image_pull_failed is a failure by type.
_STATUS_EVENTS = frozenset({"deploy_ended", "build_ended", "pre_deploy_ended"})
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


def _first_time(msg_id: str) -> bool:
    """True the first time a webhook-id is seen (retries reuse it)."""
    if msg_id in _seen_ids:
        return False
    _seen_ids.add(msg_id)
    _seen_order.append(msg_id)
    while len(_seen_order) > _SEEN_LIMIT:
        _seen_ids.discard(_seen_order.popleft())
    return True


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


def _alert(event: Dict[str, Any], recipient: str) -> None:
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
    _send_email(
        EmailMessage(
            message_id=f"render-alert-{uuid.uuid4().hex[:12]}",
            to_email=recipient,
            subject=f"[Render] {event_type} failed: {service}",
            body_text=body,
            priority=EmailPriority.HIGH,
        )
    )


@router.post("/render-webhook", status_code=status.HTTP_200_OK)
async def render_webhook(request: Request, background_tasks: BackgroundTasks) -> Dict[str, str]:
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

    # Authentic from here on: always acknowledge, so Render never retries or disables us.
    try:
        event = json.loads(body)
    except ValueError:
        logger.error("Render webhook: signed body is not JSON; acknowledged and ignored")
        return {"status": "ignored"}
    if not isinstance(event, dict) or not _is_failure(event):
        return {"status": "ignored"}
    if not _first_time(msg_id):
        return {"status": "duplicate"}

    recipient = os.getenv("OPS_ALERT_EMAIL", "").strip()
    if not recipient:
        logger.error(
            f"Render deploy failure for {(event.get('data') or {}).get('serviceName')} "
            "but OPS_ALERT_EMAIL is unset; no alert sent"
        )
        return {"status": "unrouted"}

    background_tasks.add_task(_alert, event, recipient)
    return {"status": "alerted"}
