"""Unit tests for Bug #110: unsupported platform detection in _generate_warnings."""

import pytest

from backend.routers.briefs import _generate_warnings


def _make_field(value, confidence="high"):
    """Return a minimal FieldExtraction-compatible object."""
    from unittest.mock import MagicMock

    f = MagicMock()
    f.value = value
    f.confidence = confidence
    return f


def _base_fields():
    """Return a fields dict with the three required fields satisfied."""
    return {
        "companyName": _make_field("Acme Corp"),
        "businessDescription": _make_field("B2B SaaS for ops teams"),
        "idealCustomer": _make_field("Operations managers"),
    }


class TestUnsupportedPlatformWarning:
    """_generate_warnings must flag platform values not in the Platform enum."""

    def test_supported_platforms_no_warning(self):
        fields = _base_fields()
        fields["platforms"] = _make_field(["linkedin", "twitter"])
        warnings = _generate_warnings(fields)
        platform_warnings = [
            w for w in warnings if "not supported" in w.lower() or "unsupported" in w.lower()
        ]
        assert not platform_warnings, f"Unexpected platform warning: {platform_warnings}"

    def test_tiktok_triggers_warning(self):
        fields = _base_fields()
        fields["platforms"] = _make_field(["linkedin", "tiktok"])
        warnings = _generate_warnings(fields)
        assert any("tiktok" in w.lower() for w in warnings), "Expected warning mentioning 'tiktok'"

    def test_youtube_triggers_warning(self):
        fields = _base_fields()
        fields["platforms"] = _make_field(["youtube"])
        warnings = _generate_warnings(fields)
        assert any("youtube" in w.lower() for w in warnings)

    def test_instagram_triggers_warning(self):
        fields = _base_fields()
        fields["platforms"] = _make_field(["instagram", "facebook"])
        warnings = _generate_warnings(fields)
        assert any("instagram" in w.lower() for w in warnings)

    def test_only_unsupported_platforms_listed_as_problem(self):
        """The warning must name tiktok as unsupported, but facebook is supported so only
        tiktok should appear in the 'Unsupported platforms detected:' portion of the message."""
        fields = _base_fields()
        fields["platforms"] = _make_field(["facebook", "tiktok"])
        warnings = _generate_warnings(fields)
        platform_warn = next((w for w in warnings if "tiktok" in w.lower()), None)
        assert platform_warn is not None
        # The "detected:" section should list only tiktok, not facebook.
        # Grab the text before "Supported platforms are:" to isolate the detected list.
        detected_section = platform_warn.lower().split("supported platforms are:")[0]
        assert "tiktok" in detected_section
        assert (
            "facebook" not in detected_section
        ), "Supported platform 'facebook' should not appear in the detected-unsupported section"

    def test_warning_lists_supported_platforms(self):
        """The warning message must name the supported set so the operator knows alternatives."""
        fields = _base_fields()
        fields["platforms"] = _make_field(["snapchat"])
        warnings = _generate_warnings(fields)
        warn_text = " ".join(warnings)
        assert (
            "linkedin" in warn_text.lower()
        ), "Warning should list supported platforms including 'linkedin'"

    def test_no_platforms_field_no_unsupported_warning(self):
        """If there is no 'platforms' key in fields, no unsupported-platform warning fires."""
        fields = _base_fields()
        warnings = _generate_warnings(fields)
        assert not any("not supported" in w.lower() for w in warnings)

    def test_empty_platforms_list_no_warning(self):
        fields = _base_fields()
        fields["platforms"] = _make_field([])
        warnings = _generate_warnings(fields)
        assert not any("not supported" in w.lower() for w in warnings)

    def test_multiple_unsupported_all_named(self):
        fields = _base_fields()
        fields["platforms"] = _make_field(["tiktok", "youtube", "instagram"])
        warnings = _generate_warnings(fields)
        warn_text = " ".join(w.lower() for w in warnings)
        for bad in ["tiktok", "youtube", "instagram"]:
            assert bad in warn_text, f"Expected '{bad}' in warning text"
