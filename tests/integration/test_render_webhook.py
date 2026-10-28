"""BUGS #239: alert when a Render deploy fails.

A failed deploy leaves the previous version serving, so the site looks healthy while
new code never ships. Prod deploys failed silently for ~2 weeks in 2026-08 that way.
Render posts workspace events to POST /api/ops/render-webhook; failures are emailed.

Signatures follow the Standard Webhooks spec (Render docs: "Render's webhook
implementation follows the specification defined by the Standard Webhooks project"):
key = base64-decoded secret after "whsec_", signed content = "{id}.{timestamp}.{body}",
header "webhook-signature" = space-separated "v1,<base64 HMAC-SHA256>".
"""

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import ops_webhooks

_KEY = b"render-webhook-test-key-0123456789abcd"
SECRET = "whsec_" + base64.b64encode(_KEY).decode()  # pragma: allowlist secret (test-only fake key)
PATH = "/api/ops/render-webhook"


def _sign(body: bytes, msg_id: str, ts: int, key: bytes = _KEY) -> str:
    content = f"{msg_id}.{ts}.".encode() + body
    return "v1," + base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()


def _post(client, event, *, msg_id="msg_1", ts=None, signature=None, raw=None):
    body = raw if raw is not None else json.dumps(event).encode()
    ts = int(time.time()) if ts is None else ts
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": str(ts),
        "webhook-signature": signature or _sign(body, msg_id, ts),
        "content-type": "application/json",
    }
    return client.post(PATH, content=body, headers=headers)


def _event(type_="deploy_ended", status="failed", service="content-jumpstart-backend"):
    data = {"id": "evt-1", "serviceId": "srv-abc123", "serviceName": service}
    if status is not None:
        data["status"] = status
    return {"type": type_, "timestamp": "2026-10-27T17:31:11.000Z", "data": data}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RENDER_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("OPS_ALERT_EMAIL", "ops@example.com")
    ops_webhooks._seen_ids.clear()
    return TestClient(app)


@pytest.fixture
def sent(monkeypatch):
    """Capture alert emails instead of sending them."""
    messages = []
    monkeypatch.setattr(ops_webhooks, "_send_email", lambda msg: messages.append(msg) or True)
    return messages


# ---------- authenticity ----------


def test_route_is_hidden_when_no_secret_is_configured(monkeypatch, sent):
    # Every customer instance ships this route; only the one Render targets sets it.
    monkeypatch.delenv("RENDER_WEBHOOK_SECRET", raising=False)
    resp = _post(TestClient(app), _event())
    assert resp.status_code == 404
    assert sent == []


def test_valid_signature_is_accepted(client, sent):
    assert _post(client, _event()).status_code == 200


@pytest.mark.parametrize(
    "bad",
    [
        "v1," + base64.b64encode(b"x" * 32).decode(),  # wrong HMAC
        "v1a,whatever",  # unknown version
        "",  # missing
    ],
)
def test_bad_signature_is_rejected_and_never_alerts(client, sent, bad):
    body = json.dumps(_event()).encode()
    resp = client.post(
        PATH,
        content=body,
        headers={
            "webhook-id": "msg_1",
            "webhook-timestamp": str(int(time.time())),
            "webhook-signature": bad,
        },
    )
    assert resp.status_code == 401
    assert sent == []


def test_signature_from_another_key_is_rejected(client, sent):
    body = json.dumps(_event()).encode()
    ts = int(time.time())
    resp = _post(client, None, raw=body, ts=ts, signature=_sign(body, "msg_1", ts, b"other-key"))
    assert resp.status_code == 401


def test_one_valid_signature_among_several_is_enough(client, sent):
    # Standard Webhooks sends space-separated signatures during secret rotation.
    body = json.dumps(_event()).encode()
    ts = int(time.time())
    sig = "v1,bm90LWl0 " + _sign(body, "msg_1", ts)
    assert _post(client, None, raw=body, ts=ts, signature=sig).status_code == 200


@pytest.mark.parametrize("skew", [-301, 301])
def test_stale_or_future_timestamp_is_rejected(client, sent, skew):
    assert _post(client, _event(), ts=int(time.time()) + skew).status_code == 401
    assert sent == []


def test_body_tampering_is_rejected(client, sent):
    body = json.dumps(_event(status="succeeded")).encode()
    ts = int(time.time())
    sig = _sign(body, "msg_1", ts)
    tampered = json.dumps(_event(status="failed")).encode()
    assert _post(client, None, raw=tampered, ts=ts, signature=sig).status_code == 401
    assert sent == []


# ---------- what alerts ----------


@pytest.mark.parametrize("etype", ["deploy_ended", "build_ended"])
def test_failed_lifecycle_event_sends_one_alert(client, sent, etype):
    assert _post(client, _event(type_=etype, status="failed")).status_code == 200
    assert len(sent) == 1
    msg = sent[0]
    assert msg.to_email == "ops@example.com"
    assert "content-jumpstart-backend" in msg.subject
    assert etype in msg.body_text
    assert "srv-abc123" in msg.body_text
    assert "https://dashboard.render.com/web/srv-abc123" in msg.body_text
    # Times in America/Chicago, with the UTC source kept (user preference).
    assert "17:31 UTC" in msg.body_text and "CDT" in msg.body_text


def test_image_pull_failed_alerts_without_a_status(client, sent):
    assert _post(client, _event(type_="image_pull_failed", status=None)).status_code == 200
    assert len(sent) == 1


@pytest.mark.parametrize(
    "event",
    [
        _event(status="succeeded"),
        _event(status="canceled"),
        _event(type_="deploy_started", status=None),
        _event(type_="build_ended", status="succeeded"),
        # Codex review of 0a2d6b2: Render only puts `status` on build_ended,
        # deploy_ended and job events, so pre_deploy_ended can never be matched as a
        # failure; a failed pre-deploy surfaces as deploy_ended: failed.
        _event(type_="pre_deploy_ended", status=None),
    ],
)
def test_non_failures_do_not_alert(client, sent, event):
    assert _post(client, event).status_code == 200
    assert sent == []


def test_retried_delivery_alerts_only_once(client, sent):
    # Render retries with the same webhook-id (and a new timestamp).
    assert _post(client, _event(), msg_id="msg_dup").status_code == 200
    assert _post(client, _event(), msg_id="msg_dup", ts=int(time.time()) + 1).status_code == 200
    assert len(sent) == 1


# ---------- delivery: 200 only once the alert is out; otherwise let Render retry ----------
# Codex review of 0a2d6b2: acknowledging before the email was sent (and marking the
# webhook-id seen) meant a failed send lost the alert for good, since Render does not
# retry a 2xx. Render's own retries (8 attempts over ~33h, plus an email to the account
# after the 3rd failure) are the durable queue: answer 503 until the alert is out.


def test_email_failure_returns_503_and_the_retry_sends_it(client, monkeypatch):
    outcomes = iter([False, True])
    delivered = []

    def flaky(msg):
        ok = next(outcomes)
        if ok:
            delivered.append(msg)
        return ok

    monkeypatch.setattr(ops_webhooks, "_send_email", flaky)
    assert _post(client, _event(), msg_id="msg_retry").status_code == 503
    # Render retries with the same id: not treated as a duplicate, because it never went out.
    assert _post(client, _event(), msg_id="msg_retry").status_code == 200
    assert len(delivered) == 1


def test_slow_email_returns_503_within_rendering_deadline(client, monkeypatch):
    monkeypatch.setattr(ops_webhooks, "_SEND_DEADLINE_SECONDS", 0.05)
    monkeypatch.setattr(ops_webhooks, "_send_email", lambda msg: time.sleep(0.5) or True)
    start = time.monotonic()
    assert _post(client, _event(), msg_id="msg_slow").status_code == 503
    assert time.monotonic() - start < 0.4  # answered before the send finished


def test_missing_alert_address_returns_503(client, monkeypatch, sent):
    # Misconfiguration: retries + Render's "webhook failing" email beat a silent log.
    monkeypatch.delenv("OPS_ALERT_EMAIL", raising=False)
    assert _post(client, _event()).status_code == 503
    assert sent == []


def test_signed_but_unparseable_body_is_acknowledged(client, sent):
    body = b"not json"
    ts = int(time.time())
    resp = _post(client, None, raw=body, msg_id="m", ts=ts, signature=_sign(body, "m", ts))
    assert resp.status_code == 200
    assert sent == []


def test_route_is_exempt_from_csrf_and_needs_no_login(client, sent):
    # Render sends neither a CSRF token nor a session; the signature is the auth.
    with patch("backend.middleware.auth_dependency.require_access") as gate:
        assert _post(client, _event()).status_code == 200
    gate.assert_not_called()


def test_provider_idempotency_key_is_stable_per_webhook_id(client, monkeypatch):
    # Codex review of 8aad92d: the email's message_id is Resend's Idempotency-Key
    # (agent/email_system.py). Deriving it from webhook-id, not a random UUID, lets the
    # provider drop a duplicate send of the same alert — from a retry after a timed-out
    # send, or from a concurrent delivery — without a lock here.
    seen = []
    outcomes = iter([False, True])
    monkeypatch.setattr(
        ops_webhooks, "_send_email", lambda msg: seen.append(msg.message_id) or next(outcomes)
    )
    _post(client, _event(), msg_id="msg_idem")
    _post(client, _event(), msg_id="msg_idem")
    assert seen == ["render-alert-msg_idem", "render-alert-msg_idem"]
