"""Unit tests for posting_schedule module.

Tests cover:
- PostingSchedule model
- ScheduledPost model
- to_ical method with ImportError handling
"""

from datetime import date, time
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile

import pytest

from src.models.posting_schedule import (
    PostingSchedule,
    ScheduledPost,
    DayOfWeek,
)


@pytest.fixture
def sample_scheduled_posts():
    """Create sample scheduled posts."""
    return [
        ScheduledPost(
            post_id=1,
            post_title="Great Content Post",
            post_excerpt="This is a preview of the post content...",
            scheduled_date=date(2025, 1, 20),
            scheduled_time=time(10, 0),
            platform="linkedin",
            day_of_week=DayOfWeek.MONDAY,
            week_number=1,
        ),
        ScheduledPost(
            post_id=2,
            post_title="Another Great Post",
            post_excerpt="More preview content here...",
            scheduled_date=date(2025, 1, 21),
            scheduled_time=time(14, 0),
            platform="twitter",
            day_of_week=DayOfWeek.TUESDAY,
            week_number=1,
            notes="Important post - monitor engagement",
        ),
    ]


@pytest.fixture
def sample_schedule(sample_scheduled_posts):
    """Create sample posting schedule."""
    return PostingSchedule(
        client_name="TestClient",
        start_date=date(2025, 1, 20),
        end_date=date(2025, 2, 20),
        total_weeks=4,
        posts_per_week=5,
        scheduled_posts=sample_scheduled_posts,
    )


class TestPostingSchedule:
    """Tests for PostingSchedule model."""

    def test_schedule_creation(self, sample_schedule):
        """Test basic schedule creation."""
        assert sample_schedule.client_name == "TestClient"
        assert sample_schedule.start_date == date(2025, 1, 20)
        assert len(sample_schedule.scheduled_posts) == 2

    def test_scheduled_post_with_notes(self, sample_scheduled_posts):
        """Test scheduled post with notes field."""
        post_with_notes = sample_scheduled_posts[1]
        assert post_with_notes.notes == "Important post - monitor engagement"


class TestToIcal:
    """Tests for to_ical method (lines 146-173)."""

    def test_to_ical_import_error(self, sample_schedule):
        """Test that ImportError is raised when icalendar not installed (lines 152-153)."""
        with patch.dict(sys.modules, {"icalendar": None}):
            # Force import to fail by removing from sys.modules
            if "icalendar" in sys.modules:
                del sys.modules["icalendar"]

            # Mock the import to raise ImportError
            original_import = (
                __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
            )

            def mock_import(name, *args, **kwargs):
                if name == "icalendar":
                    raise ImportError("No module named 'icalendar'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ImportError) as exc_info:
                    sample_schedule.to_ical(Path("test.ics"))

                assert "icalendar required" in str(exc_info.value)

    def test_to_ical_success(self, sample_schedule):
        """Test successful iCal export when icalendar is available."""
        try:
            import icalendar  # noqa: F401

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "schedule.ics"
                result = sample_schedule.to_ical(output_path)

                assert result == output_path
                assert output_path.exists()

                content = output_path.read_bytes()
                assert b"VCALENDAR" in content
                assert b"TestClient" in content
                assert b"Great Content Post" in content
        except ImportError:
            pytest.skip("icalendar not installed")

    def test_to_ical_includes_notes(self, sample_schedule):
        """Test that notes are included in iCal description."""
        try:
            import icalendar  # noqa: F401

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "schedule.ics"
                sample_schedule.to_ical(output_path)

                content = output_path.read_text()
                # Post 2 has notes
                assert "monitor engagement" in content or "Important post" in content
        except ImportError:
            pytest.skip("icalendar not installed")


class TestDayOfWeek:
    """Tests for DayOfWeek enum."""

    def test_day_values(self):
        """Test all day of week values."""
        assert DayOfWeek.MONDAY.value == "Monday"
        assert DayOfWeek.TUESDAY.value == "Tuesday"
        assert DayOfWeek.WEDNESDAY.value == "Wednesday"
        assert DayOfWeek.THURSDAY.value == "Thursday"
        assert DayOfWeek.FRIDAY.value == "Friday"
        assert DayOfWeek.SATURDAY.value == "Saturday"
        assert DayOfWeek.SUNDAY.value == "Sunday"
