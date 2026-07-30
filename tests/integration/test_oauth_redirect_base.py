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
