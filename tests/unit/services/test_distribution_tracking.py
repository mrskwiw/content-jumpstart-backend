"""UTM tagging of published content (opt-in) — _publishable_content wiring."""

from types import SimpleNamespace

from backend.services.distribution.orchestrator import (
    _publishable_content,
    _utm_tagging_enabled,
)


def _sp(content, platform="linkedin", project_id="proj-1", sp_id="sp-1"):
    return SimpleNamespace(content=content, platform=platform, project_id=project_id, id=sp_id)


def test_tagging_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DISTRIBUTION_UTM_TAGGING", raising=False)
    assert _utm_tagging_enabled() is False
    sp = _sp("See https://acme.com/p")
    assert _publishable_content(sp) == "See https://acme.com/p"  # unchanged


def test_tagging_enabled_tags_urls_with_platform_and_campaign(monkeypatch):
    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "true")
    sp = _sp("See https://acme.com/p", platform="linkedin", project_id="proj-1")
    out = _publishable_content(sp)
    assert "utm_source=linkedin" in out
    assert "utm_campaign=proj-1" in out
    assert "utm_medium=social" in out


def test_campaign_falls_back_to_scheduled_post_id(monkeypatch):
    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "1")
    sp = _sp("x https://acme.com", project_id=None, sp_id="sp-xyz")
    assert "utm_campaign=sp-xyz" in _publishable_content(sp)


def test_no_urls_content_unchanged_when_enabled(monkeypatch):
    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "true")
    sp = _sp("no links here, just prose")
    assert _publishable_content(sp) == "no links here, just prose"


def test_enabled_flag_accepts_common_truthy_values(monkeypatch):
    for val in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", val)
        assert _utm_tagging_enabled() is True
    for val in ("", "0", "false", "no"):
        monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", val)
        assert _utm_tagging_enabled() is False
