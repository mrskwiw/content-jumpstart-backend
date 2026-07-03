"""Unit tests for Schedule Generator"""

from datetime import date, time

import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.models.posting_schedule import DayOfWeek
from src.utils.schedule_generator import ScheduleGenerator


@pytest.fixture
def sample_posts():
    """Create sample posts for testing"""
    posts = []
    for i in range(10):
        post = Post(
            content=f"This is sample post {i+1}. It contains enough content to test title and excerpt extraction. "
            * 3,
            template_id=1,
            template_name="Test Template",
            variant=i + 1,
            client_name="TestClient",
        )
        if i % 2 == 0:
            post.target_platform = Platform.LINKEDIN.value
        posts.append(post)
    return posts


class TestScheduleGenerator:
    """Test suite for Schedule Generator"""

    def test_initialization(self):
        """Test generator initializes"""
        generator = ScheduleGenerator()
        assert generator is not None

    def test_platform_detection(self, sample_posts):
        """Test platform auto-detection from posts"""
        generator = ScheduleGenerator()
        platforms = generator._detect_platforms(sample_posts)
        assert len(platforms) == 1
        assert Platform.LINKEDIN in platforms

    def test_platform_detection_defaults_to_linkedin(self):
        """Test platform defaults to LinkedIn when none specified"""
        generator = ScheduleGenerator()
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
        ]
        platforms = generator._detect_platforms(posts)
        assert Platform.LINKEDIN in platforms

    def test_generate_posting_slots(self):
        """Test posting slot generation"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)  # Monday
        slots = generator._generate_posting_slots(
            num_posts=8,
            start_date=start_date,
            posts_per_week=4,
            platforms=[Platform.LINKEDIN],
        )

        assert len(slots) == 8
        # Each slot should be a tuple of (date, time, Platform)
        assert all(isinstance(slot[0], date) for slot in slots)
        assert all(isinstance(slot[1], time) for slot in slots)
        assert all(isinstance(slot[2], Platform) for slot in slots)

    def test_generate_schedule_basic(self, sample_posts):
        """Test basic schedule generation"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)  # Monday

        schedule = generator.generate_schedule(
            posts=sample_posts[:10],
            start_date=start_date,
            posts_per_week=4,
        )

        # Verify schedule properties
        assert schedule.client_name == "TestClient"
        assert schedule.start_date == start_date
        assert len(schedule.scheduled_posts) == 10
        assert schedule.posts_per_week == 4
        assert schedule.total_weeks >= 2  # 10 posts at 4/week = 3 weeks

    def test_scheduled_post_fields(self, sample_posts):
        """Test that scheduled posts have correct fields"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:3],
            start_date=start_date,
            posts_per_week=2,
        )

        for sp in schedule.scheduled_posts:
            # Verify all required fields are present
            assert sp.post_id > 0
            assert isinstance(sp.post_title, str)
            assert isinstance(sp.post_excerpt, str)
            assert isinstance(sp.scheduled_date, date)
            assert isinstance(sp.scheduled_time, time) or sp.scheduled_time is None
            assert isinstance(sp.day_of_week, DayOfWeek)
            assert sp.week_number > 0
            assert isinstance(sp.platform, str)

            # Title should be extracted from content
            assert len(sp.post_title) > 0
            assert len(sp.post_title) <= 63  # 60 + "..."

            # Excerpt should be extracted
            assert len(sp.post_excerpt) > 0
            assert len(sp.post_excerpt) <= 153  # 150 + "..."

    def test_day_of_week_calculation(self, sample_posts):
        """Test that day of week is calculated correctly"""
        generator = ScheduleGenerator()
        # Start on a Tuesday (2025-01-07)
        start_date = date(2025, 1, 7)

        schedule = generator.generate_schedule(
            posts=sample_posts[:2],
            start_date=start_date,
            posts_per_week=2,
        )

        # Verify days match the date
        for sp in schedule.scheduled_posts:
            weekday = sp.scheduled_date.weekday()
            weekday_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            expected_day = DayOfWeek(weekday_names[weekday])
            assert sp.day_of_week == expected_day

    def test_week_number_calculation(self, sample_posts):
        """Test that week numbers are calculated correctly"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:8],
            start_date=start_date,
            posts_per_week=4,
        )

        # First 4 posts should be week 1
        week_1_posts = [sp for sp in schedule.scheduled_posts if sp.week_number == 1]
        assert len(week_1_posts) <= 4

        # Verify week numbers are sequential
        week_numbers = [sp.week_number for sp in schedule.scheduled_posts]
        assert all(wn > 0 for wn in week_numbers)

    def test_best_posting_times(self, sample_posts):
        """Test that best posting times are included"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:5],
            start_date=start_date,
            posts_per_week=3,
        )

        # Should have best posting times for detected platforms
        assert len(schedule.best_posting_times) > 0
        assert "linkedin" in schedule.best_posting_times

        # Times should be formatted strings
        times = schedule.best_posting_times["linkedin"]
        assert len(times) > 0
        assert all(isinstance(t, str) for t in times)
        assert all("at" in t for t in times)

    def test_frequency_notes(self, sample_posts):
        """Test that frequency notes are generated"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:5],
            start_date=start_date,
            posts_per_week=3,
        )

        assert isinstance(schedule.frequency_notes, str)
        assert len(schedule.frequency_notes) > 0
        assert "3 times per week" in schedule.frequency_notes.lower()

    def test_markdown_export(self, sample_posts):
        """Test that schedule can be exported to markdown"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:5],
            start_date=start_date,
            posts_per_week=3,
        )

        markdown = schedule.to_markdown_calendar()

        # Verify markdown structure
        assert "# Posting Schedule:" in markdown
        assert "## Week" in markdown
        assert "| Date | Day | Time |" in markdown
        assert "TestClient" in markdown
        assert "## Posting Guidelines" in markdown

    def test_csv_export(self, sample_posts, tmp_path):
        """Test that schedule can be exported to CSV"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:3],
            start_date=start_date,
            posts_per_week=2,
        )

        csv_path = tmp_path / "test_schedule.csv"
        result_path = schedule.to_csv(csv_path)

        assert result_path.exists()

        # Verify CSV content
        content = result_path.read_text()
        assert "Post ID" in content
        assert "Title" in content
        assert "Date" in content
        # Verify we have 3 data rows plus header
        lines = content.strip().split("\n")
        assert len(lines) == 4  # 1 header + 3 data rows

    def test_ical_export(self, sample_posts, tmp_path):
        """Test that schedule can be exported to iCal"""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=sample_posts[:3],
            start_date=start_date,
            posts_per_week=2,
        )

        ical_path = tmp_path / "test_schedule.ics"

        try:
            result_path = schedule.to_ical(ical_path)
            assert result_path.exists()

            # Verify iCal content
            content = result_path.read_text()
            assert "BEGIN:VCALENDAR" in content
            assert "POST:" in content
        except ImportError:
            pytest.skip("icalendar library not installed")

    def test_empty_posts(self):
        """Test schedule generation with empty posts list."""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        schedule = generator.generate_schedule(
            posts=[],
            start_date=start_date,
            posts_per_week=4,
        )

        assert len(schedule.scheduled_posts) == 0
        assert schedule.end_date == start_date
        assert schedule.total_weeks == 1

    def test_invalid_platform_string_in_post(self):
        """Test handling of invalid platform string in post (via mock)."""
        from unittest.mock import MagicMock

        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        # Create mock post with invalid platform string that bypasses validation
        post = MagicMock()
        post.content = "Test post content that is long enough for title and excerpt extraction."
        post.target_platform = "invalid_platform"  # Invalid platform string
        post.client_name = "TestClient"

        schedule = generator.generate_schedule(
            posts=[post],
            start_date=start_date,
            posts_per_week=4,
        )

        assert len(schedule.scheduled_posts) == 1
        # Platform should be preserved as-is
        assert schedule.scheduled_posts[0].platform == "invalid_platform"
        # Notes should be None for invalid platform
        assert schedule.scheduled_posts[0].notes is None

    def test_detect_platforms_with_invalid_target(self):
        """Test platform detection with invalid target_platform values (via mock)."""
        from unittest.mock import MagicMock

        generator = ScheduleGenerator()

        # Create mock posts with invalid platform strings
        post1 = MagicMock()
        post1.target_platform = "not_a_real_platform"

        post2 = MagicMock()
        post2.target_platform = "another_invalid"

        platforms = generator._detect_platforms([post1, post2])
        # Should default to LinkedIn when all platforms are invalid
        assert Platform.LINKEDIN in platforms

    def test_generate_slots_multiple_platforms(self):
        """Test slot generation with multiple platforms."""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        slots = generator._generate_posting_slots(
            num_posts=10,
            start_date=start_date,
            posts_per_week=4,
            platforms=[Platform.LINKEDIN, Platform.TWITTER],
        )

        assert len(slots) == 10
        # Should have mix of platforms
        platforms_used = set(slot[2] for slot in slots)
        assert len(platforms_used) >= 1

    def test_generate_slots_week_boundary(self):
        """Test slot generation respects week boundaries."""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)  # Monday

        slots = generator._generate_posting_slots(
            num_posts=12,  # More than one week at 4/week
            start_date=start_date,
            posts_per_week=4,
            platforms=[Platform.LINKEDIN],
        )

        assert len(slots) == 12
        # Verify slots span multiple weeks
        first_week_slots = [s for s in slots if (s[0] - start_date).days < 7]
        assert len(first_week_slots) <= 4

    def test_generate_slots_platform_without_optimal_times(self):
        """Test slot generation for platform without defined optimal times."""
        generator = ScheduleGenerator()
        start_date = date(2025, 1, 6)

        # Use GENERIC platform which isn't in PLATFORM_OPTIMAL_TIMES
        slots = generator._generate_posting_slots(
            num_posts=5,
            start_date=start_date,
            posts_per_week=2,
            platforms=[Platform.GENERIC],
        )

        # Should use default times
        assert len(slots) == 5


class TestGetDefaultScheduleGenerator:
    """Tests for get_default_schedule_generator function."""

    def test_get_default_generator(self):
        """Test getting default generator instance."""
        from src.utils.schedule_generator import get_default_schedule_generator
        import src.utils.schedule_generator as sg

        # Reset global
        sg.default_schedule_generator = None

        generator = get_default_schedule_generator()
        assert generator is not None
        assert isinstance(generator, ScheduleGenerator)

        # Cleanup
        sg.default_schedule_generator = None

    def test_get_default_generator_singleton(self):
        """Test that get_default_schedule_generator returns singleton."""
        from src.utils.schedule_generator import get_default_schedule_generator
        import src.utils.schedule_generator as sg

        # Reset global
        sg.default_schedule_generator = None

        gen1 = get_default_schedule_generator()
        gen2 = get_default_schedule_generator()

        assert gen1 is gen2

        # Cleanup
        sg.default_schedule_generator = None
