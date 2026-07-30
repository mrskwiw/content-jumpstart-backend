"""S-01.4e — redirect_uri_for resolves the OAuth base from instance_config (+ env fallback).

Wiring the runtime resolver into the OAuth legs lets the control plane's custom-domain
promotion take effect without a redeploy. Backward-compatible: no db (or empty
instance_config) == the env behavior. The critical invariant is that both OAuth legs
resolve the SAME redirect_uri (they call redirect_uri_for with the same db), else the
provider rejects the token exchange.
"""

from backend.services.distribution import oauth
from backend.services.distribution.oauth import redirect_uri_for
from backend.services.settings_service import set_instance_config

_ENV = "OAUTH_REDIRECT_BASE_URL"


def _suffix(platform="linkedin"):
    return f"/api/distribution/oauth/{platform}/callback"


def test_no_db_uses_env_unchanged(monkeypatch):
    monkeypatch.setenv(_ENV, "https://env.example.com")
    monkeypatch.delenv("LINKEDIN_REDIRECT_URI", raising=False)
    assert redirect_uri_for("linkedin") == "https://env.example.com" + _suffix()


def test_db_without_config_falls_back_to_env(db_session, monkeypatch):
    monkeypatch.setenv(_ENV, "https://env.example.com")
    monkeypatch.delenv("LINKEDIN_REDIRECT_URI", raising=False)
    # instance_config has no oauth_redirect_base -> env base.
    assert redirect_uri_for("linkedin", db_session) == "https://env.example.com" + _suffix()


def test_db_with_config_uses_instance_config(db_session, monkeypatch):
    monkeypatch.setenv(_ENV, "https://env.example.com")
    monkeypatch.delenv("LINKEDIN_REDIRECT_URI", raising=False)
    set_instance_config(db_session, "oauth_redirect_base", "https://custom.customer.com/")
    # instance_config wins over env; trailing slash stripped.
    assert redirect_uri_for("linkedin", db_session) == "https://custom.customer.com" + _suffix()


def test_per_platform_override_wins_even_with_db(db_session, monkeypatch):
    monkeypatch.setenv(_ENV, "https://env.example.com")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "https://override.example.com/cb")
    set_instance_config(db_session, "oauth_redirect_base", "https://custom.customer.com")
    assert redirect_uri_for("linkedin", db_session) == "https://override.example.com/cb"


def test_both_legs_resolve_identically(db_session, monkeypatch):
    # build_authorize_url and exchange_code both call redirect_uri_for(platform, db),
    # so with the same db they produce the identical redirect_uri. Assert the shared
    # resolver is deterministic under a custom domain (the OAuth-match invariant).
    monkeypatch.delenv("LINKEDIN_REDIRECT_URI", raising=False)
    monkeypatch.setenv(_ENV, "https://env.example.com")
    set_instance_config(db_session, "oauth_redirect_base", "https://custom.customer.com")
    a = redirect_uri_for("linkedin", db_session)
    b = redirect_uri_for("linkedin", db_session)
    assert a == b == "https://custom.customer.com" + _suffix()


def test_missing_base_raises(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    monkeypatch.delenv("LINKEDIN_REDIRECT_URI", raising=False)
    try:
        redirect_uri_for("linkedin")
        assert False, "expected OAuthError"
    except oauth.OAuthError:
        pass


def test_build_authorize_url_uses_pinned_redirect_uri(monkeypatch):
    # An explicit redirect_uri bypasses resolution entirely — even with NO base set
    # (which would otherwise raise), proving the pinned value is used verbatim.
    from urllib.parse import quote

    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "sec")
    monkeypatch.delenv(_ENV, raising=False)
    url = oauth.build_authorize_url(
        "linkedin", "state123", redirect_uri="https://pinned.example.com/cb"
    )
    assert quote("https://pinned.example.com/cb", safe="") in url


def test_exchange_code_prefers_pinned_over_changed_config(db_session, monkeypatch):
    # The [high] fix: even if instance_config changes between the two OAuth legs, the
    # exchange uses the PINNED redirect_uri (from the signed state), not a re-resolve.
    monkeypatch.setenv(_ENV, "https://env.example.com")
    set_instance_config(db_session, "oauth_redirect_base", "https://changed.example.com")
    captured: dict = {}

    def _fake_post(provider, data):  # noqa: ANN001
        captured.update(data)
        return {"access_token": "tok"}

    monkeypatch.setattr(oauth, "_post_token", _fake_post)
    oauth.exchange_code(
        "linkedin",
        "code123",
        code_verifier="v",
        redirect_uri="https://pinned.example.com/cb",
        db=db_session,
    )
    assert captured["redirect_uri"] == "https://pinned.example.com/cb"


def test_callback_error_path_uses_env_base_not_instance_config(client, db_session, monkeypatch):
    # The [high] fix: the ERROR redirect must stay DB-free/robust — it uses the env
    # base, NOT the instance_config custom domain (which would add a DB read to the
    # error path).
    monkeypatch.setenv(_ENV, "https://env.example.com")
    set_instance_config(db_session, "oauth_redirect_base", "https://custom.example.com")
    r = client.get(
        "/api/distribution/oauth/linkedin/callback?error=access_denied",
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("https://env.example.com/dashboard")
