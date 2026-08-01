"""Unit tests for the IMAGE-GEN backbone (GEN_IMAGE MediaKind).

Mirrors how P12.1 shipped the video/audio backbone: the StubProvider produces a
deterministic image asset, the cost model prices an image as a flat per-unit cost,
and a real image provider name fails closed until its integration lands.
"""

from backend.services.media.cost import estimate_cost
from backend.services.media.providers import (
    MediaKind,
    NotImplementedProvider,
    StubProvider,
    _is_image,
    _is_video,
    dry_run_enabled,
    get_provider,
)


def test_gen_image_is_image_not_video():
    assert _is_image(MediaKind.GEN_IMAGE) is True
    assert _is_video(MediaKind.GEN_IMAGE) is False
    # Existing kinds are unaffected.
    assert _is_image(MediaKind.GEN_CLIP) is False
    assert _is_image(MediaKind.TTS) is False


def test_stub_produces_an_image_asset_with_no_duration():
    stub = StubProvider(MediaKind.GEN_IMAGE)
    started = stub.start({"prompt": "a red bicycle"})
    assert started.ok and not started.done and started.external_id

    result = stub.poll(started.external_id)
    assert result.ok and result.done
    assert result.asset_url.endswith(".png")
    assert result.mime == "image/png"
    assert result.duration_s is None
    assert result.cost_cents == 0


def test_stub_start_is_deterministic_for_the_same_prompt():
    a = StubProvider(MediaKind.GEN_IMAGE).start({"prompt": "same"})
    b = StubProvider(MediaKind.GEN_IMAGE).start({"prompt": "same"})
    assert a.external_id == b.external_id


def test_estimate_cost_prices_an_image_as_a_flat_unit(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    # Stub is free; a real per-image provider is a flat cost (rate × the 1s default).
    assert estimate_cost(MediaKind.GEN_IMAGE, "stub") == 0
    assert estimate_cost(MediaKind.GEN_IMAGE, "flux") == 5
    # An unmapped provider still never reads $0 (conservative fallback).
    assert estimate_cost(MediaKind.GEN_IMAGE, "mystery") > 0


def test_real_image_provider_fails_closed_until_implemented(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    prov = get_provider(MediaKind.GEN_IMAGE, "flux")
    assert isinstance(prov, NotImplementedProvider)
    res = prov.start({"prompt": "x"})
    assert res.ok is False and "not implemented" in (res.error or "").lower()


def test_dry_run_routes_image_to_stub(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    assert dry_run_enabled() is True
    prov = get_provider(MediaKind.GEN_IMAGE, "flux")
    assert isinstance(prov, StubProvider)
