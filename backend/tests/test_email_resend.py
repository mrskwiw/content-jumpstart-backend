"""Outbound email — Resend transport + provider selection (EmailSystem rework).

Verifies the flag-gated Resend rework: transport is chosen resend > smtp > log,
the Resend HTTP payload is well-formed (incl. attachments/html/reply-to), API
errors surface as (False, detail), and the historical SMTP_USER/SMTP_USERNAME
mismatch is now tolerated. `requests.post` is always mocked — no network.
"""

import base64
from unittest.mock import MagicMock, patch

import pytest

from agent.email_system import EmailSystem, EmailMessage

EMAIL_ENV = [
    "RESEND_API_KEY",
    "EMAIL_PROVIDER",
    "SMTP_USER",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_FROM_NAME",
]


@pytest.fixture
def clean_env(monkeypatch):
    """Start each test from a known-empty email environment."""
    for k in EMAIL_ENV:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def _msg(**kw) -> EmailMessage:
    base = dict(message_id="m1", to_email="user@example.com", subject="Hi", body_text="Hello")
    base.update(kw)
    return EmailMessage(**base)


def _ok_response(email_id="e_123"):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": email_id}
    return resp


# --------------------------------------------------------------------------- #
# provider selection
# --------------------------------------------------------------------------- #
def test_provider_prefers_resend(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    assert EmailSystem()._resolve_provider() == "resend"


def test_provider_smtp_without_resend(clean_env):
    clean_env.setenv("SMTP_USER", "u")
    clean_env.setenv("SMTP_PASSWORD", "p")
    assert EmailSystem()._resolve_provider() == "smtp"


def test_provider_log_without_config(clean_env):
    assert EmailSystem()._resolve_provider() == "log"


def test_explicit_provider_override_wins(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    clean_env.setenv("EMAIL_PROVIDER", "log")
    assert EmailSystem()._resolve_provider() == "log"


def test_unknown_provider_falls_back_to_auto(clean_env):
    # A typo must not silently disable sending — auto-selection still picks resend.
    clean_env.setenv("EMAIL_PROVIDER", "resnd")
    clean_env.setenv("RESEND_API_KEY", "re_x")
    assert EmailSystem()._resolve_provider() == "resend"


def test_smtp_username_alias_is_honoured(clean_env):
    # Historical bug: template documented SMTP_USERNAME while code read SMTP_USER.
    clean_env.setenv("SMTP_USERNAME", "alias@example.com")
    clean_env.setenv("SMTP_PASSWORD", "p")
    es = EmailSystem()
    assert es.smtp_user == "alias@example.com"
    assert es._resolve_provider() == "smtp"


# --------------------------------------------------------------------------- #
# Resend transport
# --------------------------------------------------------------------------- #
def test_resend_success_payload(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    with patch("requests.post", return_value=_ok_response()) as post:
        ok, detail = es.send_email(_msg())

    assert ok and "e_123" in detail
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer re_x"
    payload = kwargs["json"]
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Hi"
    assert payload["text"] == "Hello"
    assert payload["from"].endswith("<noreply@content-jumpstart.com>")


def test_resend_includes_html_and_reply_to(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    with patch("requests.post", return_value=_ok_response()) as post:
        es.send_email(_msg(body_html="<b>hi</b>", reply_to="r@example.com"))

    payload = post.call_args.kwargs["json"]
    assert payload["html"] == "<b>hi</b>"
    assert payload["reply_to"] == "r@example.com"


def test_resend_attachments_are_base64(clean_env, tmp_path):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    f = tmp_path / "report.txt"
    f.write_bytes(b"hello-bytes")
    es = EmailSystem()
    with patch("requests.post", return_value=_ok_response()) as post:
        es.send_email(_msg(attachments=[str(f)]))

    att = post.call_args.kwargs["json"]["attachments"]
    assert att[0]["filename"] == "report.txt"
    assert base64.b64decode(att[0]["content"]) == b"hello-bytes"


def test_resend_api_error_returns_false(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    resp = MagicMock(status_code=422, text="validation failed")
    with patch("requests.post", return_value=resp):
        ok, detail = es.send_email(_msg())
    assert not ok and "422" in detail


def test_resend_no_key_returns_error(clean_env):
    ok, detail = EmailSystem()._send_via_resend(_msg())
    assert not ok and "RESEND_API_KEY" in detail


def test_resend_sets_idempotency_key(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    msg = _msg()
    with patch("requests.post", return_value=_ok_response()) as post:
        es.send_email(msg)
    assert post.call_args.kwargs["headers"]["Idempotency-Key"] == msg.message_id


def test_resend_retries_on_5xx_then_succeeds(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err500 = MagicMock(status_code=500, text="server error")
    with patch("requests.post", side_effect=[err500, _ok_response("e_ok")]) as post:
        ok, detail = es.send_email(_msg())
    assert ok and "e_ok" in detail
    assert post.call_count == 2  # retried once, then succeeded


def test_resend_gives_up_after_max_attempts_on_5xx(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err500 = MagicMock(status_code=500, text="server error")
    with patch("requests.post", side_effect=[err500, err500]) as post:
        ok, detail = es.send_email(_msg())
    assert not ok and "500" in detail
    assert post.call_count == 2  # bounded retry, not infinite


def test_resend_retries_on_connection_error(clean_env):
    import requests

    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    with patch(
        "requests.post",
        side_effect=[requests.exceptions.ConnectionError("boom"), _ok_response("e_ok")],
    ) as post:
        ok, detail = es.send_email(_msg())
    assert ok and "e_ok" in detail
    assert post.call_count == 2


def test_resend_does_not_retry_on_4xx(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err422 = MagicMock(status_code=422, text="validation failed")
    with patch("requests.post", side_effect=[err422, err422]) as post:
        ok, detail = es.send_email(_msg())
    assert not ok and "422" in detail
    assert post.call_count == 1  # client error — no retry


def test_resend_retries_on_429(clean_env):
    # 429 is a transient rate-limit, not a hard client error — it must retry.
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err429 = MagicMock(status_code=429, text="rate limited")
    err429.headers = {}  # no Retry-After → no sleep
    with patch("requests.post", side_effect=[err429, _ok_response("e_ok")]) as post:
        ok, detail = es.send_email(_msg())
    assert ok and "e_ok" in detail
    assert post.call_count == 2


def test_resend_429_within_cap_sleeps_then_retries(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err429 = MagicMock(status_code=429, text="rate limited")
    err429.headers = {"Retry-After": "2"}  # within the 3s cap
    with (
        patch("requests.post", side_effect=[err429, _ok_response()]) as post,
        patch("time.sleep") as sleep,
    ):
        ok, _ = es.send_email(_msg())
    assert ok
    assert post.call_count == 2
    sleep.assert_called_once_with(2.0)


def test_resend_429_bails_when_retry_after_exceeds_cap(clean_env):
    # Provider asks to wait longer than we'll block — fail fast, don't retry too soon.
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err429 = MagicMock(status_code=429, text="rate limited")
    err429.headers = {"Retry-After": "60"}
    with (
        patch("requests.post", side_effect=[err429, _ok_response()]) as post,
        patch("time.sleep") as sleep,
    ):
        ok, detail = es.send_email(_msg())
    assert not ok and "429" in detail
    assert post.call_count == 1  # bailed instead of a doomed early retry
    sleep.assert_not_called()


def test_resend_429_bails_on_http_date_retry_after(clean_env):
    # HTTP-date form isn't parsed as seconds — bail rather than guess.
    clean_env.setenv("RESEND_API_KEY", "re_x")
    es = EmailSystem()
    err429 = MagicMock(status_code=429, text="rate limited")
    err429.headers = {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    with patch("requests.post", side_effect=[err429, _ok_response()]) as post:
        ok, detail = es.send_email(_msg())
    assert not ok and "429" in detail
    assert post.call_count == 1


def test_from_override_and_name(clean_env):
    clean_env.setenv("RESEND_API_KEY", "re_x")
    clean_env.setenv("EMAIL_FROM", "hello@example.com")
    clean_env.setenv("EMAIL_FROM_NAME", "CJ")
    es = EmailSystem()
    with patch("requests.post", return_value=_ok_response()) as post:
        es.send_email(_msg())
    assert post.call_args.kwargs["json"]["from"] == "CJ <hello@example.com>"


def test_log_fallback_does_not_call_network(clean_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # _log_email writes under ./data/email_logs
    es = EmailSystem()
    with patch("requests.post") as post:
        ok, _ = es.send_email(_msg())
    assert ok
    post.assert_not_called()
