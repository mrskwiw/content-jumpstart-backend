"""Posting schedule generator with optimal timing recommendations"""

from datetime import date, time, timedelta
from typing import List, Optional, Tuple

from ..models.client_brief import Platform
from ..models.post import Post
from ..models.posting_schedule import DayOfWeek, PostingSchedule, ScheduledPost
from ..utils.logger import logger


class ScheduleGenerator:
    """Generates calendar-based posting schedules with optimal times"""

    # Optimal posting times by platform (day_of_week, time)
    # Based on 2024-2025 social media engagement data
    PLATFORM_OPTIMAL_TIMES = {
        Platform.LINKEDIN: [
            (1, time(9, 0)),  # Tuesday 9 AM
            (2, time(12, 0)),  # Wednesday 12 PM
            (3, time(14, 0)),  # Thursday 2 PM
            (4, time(10, 0)),  # Friday 10 AM
        ],
        Platform.TWITTER: [
            (0, time(12, 0)),  # Monday 12 PM
            (2, time(15, 0)),  # Wednesday 3 PM
            (4, time(11, 0)),  # Friday 11 AM
            (6, time(14, 0)),  # Sunday 2 PM
        ],
        Platform.FACEBOOK: [
            (2, time(13, 0)),  # Wednesday 1 PM
            (3, time(11, 0)),  # Thursday 11 AM
            (5, time(9, 0)),  # Saturday 9 AM
            (6, time(12, 0)),  # Sunday 12 PM
        ],
        Platform.BLOG: [
            (1, time(10, 0)),  # Tuesday 10 AM
            (3, time(10, 0)),  # Thursday 10 AM
        ],
        Platform.EMAIL: [
            (1, time(10, 0)),  # Tuesday 10 AM
            (3, time(14, 0)),  # Thursday 2 PM
        ],
    }

    # Platform-specific posting notes
    PLATFORM_NOTES = {
        Platform.LINKEDIN: "Use 3-5 hashtags. First 140 chars are critical (mobile preview).",
        Platform.TWITTER: "Consider threading longer posts. Use 1-2 hashtags max.",
        Platform.FACEBOOK: "Add engaging image or video. Ask questions to boost comments.",
        Platform.BLOG: "Optimize for SEO. Include internal links to related posts.",
        Platform.EMAIL: "Personalize subject line. Preview text matters.",
    }

    def __init__(self):
        """Initialize schedule generator"""

    def generate_schedule(
        self,
        posts: List[Post],
        start_date: date,
        posts_per_week: int = 4,
        platforms: Optional[List[Platform]] = None,
        timezone: str = "UTC",
    ) -> PostingSchedule:
        """
        Generate calendar-based posting schedule

        Algorithm:
        1. Determine posting slots based on posts_per_week and platforms
        2. Assign optimal times based on platform best practices
        3. Distribute posts evenly across weeks
        4. Avoid posting multiple times on same day (unless >7 posts/week)
        5. Include platform-specific notes

        Args:
            posts: List of Post objects to schedule
            start_date: First posting date
            posts_per_week: Number of posts per week
            platforms: Target platforms (auto-detects from posts if not provided)
            timezone: Timezone for schedule

        Returns:
            PostingSchedule with date/time for each post
        """
        logger.info(f"Generating posting schedule for {len(posts)} posts starting {start_date}")

        # Auto-detect platforms if not provided
        if platforms is None:
            platforms = self._detect_platforms(posts)

        # Generate posting slots
        posting_slots = self._generate_posting_slots(
            num_posts=len(posts),
            start_date=start_date,
            posts_per_week=posts_per_week,
            platforms=platforms,
        )

        # Create scheduled posts
        scheduled_posts = []

        for i, post in enumerate(posts):
            if i >= len(posting_slots):
                # Shouldn't happen, but safety check
                break

            slot_date, slot_time, slot_platform = posting_slots[i]

            # Use post's target platform if specified, otherwise use slot platform
            platform_str = post.target_platform or slot_platform.value

            # Get platform notes
            platform_notes = None
            try:
                platform_enum = Platform(platform_str.lower())
                platform_notes = self.PLATFORM_NOTES.get(platform_enum)
            except ValueError:
                pass

            # Extract title (first 60 chars or first line)
            lines = post.content.strip().split("\n")
            post_title = lines[0][:60] if lines else f"Post #{i+1}"
            if len(lines[0]) > 60:
                post_title += "..."

            # Extract excerpt (first 150 chars)
            post_excerpt = post.content.strip()[:150]
            if len(post.content.strip()) > 150:
                post_excerpt += "..."

            # Calculate week number (1-indexed)
            week_number = ((slot_date - start_date).days // 7) + 1

            # Get day of week enum
            weekday_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            day_of_week = DayOfWeek(weekday_names[slot_date.weekday()])

            scheduled_post = ScheduledPost(
                post_id=i + 1,
                post_title=post_title,
                post_excerpt=post_excerpt,
                scheduled_date=slot_date,
                scheduled_time=slot_time,
                day_of_week=day_of_week,
                week_number=week_number,
                platform=platform_str,
                notes=platform_notes,
            )

            scheduled_posts.append(scheduled_post)

        # Calculate end date and total weeks
        if scheduled_posts:
            end_date = max(sp.scheduled_date for sp in scheduled_posts)
            total_weeks = ((end_date - start_date).days // 7) + 1
        else:
            end_date = start_date
            total_weeks = 1

        # Build best posting times recommendations by platform
        best_posting_times = {}
        for platform in platforms:
            times = self.PLATFORM_OPTIMAL_TIMES.get(platform, [])
            weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            time_strings = []
            for dow, t in times:
                time_strings.append(f"{weekday_names[dow]} at {t.strftime('%I:%M %p')}")
            best_posting_times[platform.value] = time_strings

        # Create frequency notes
        frequency_notes = (
            f"Posting {posts_per_week} times per week on {', '.join(p.value for p in platforms)}"
        )

        # Create schedule
        schedule = PostingSchedule(
            client_name=posts[0].client_name if posts else "Client",
            start_date=start_date,
            end_date=end_date,
            total_weeks=total_weeks,
            posts_per_week=posts_per_week,
            scheduled_posts=scheduled_posts,
            best_posting_times=best_posting_times,
            frequency_notes=frequency_notes,
        )

        logger.info(f"Schedule generated: {len(scheduled_posts)} posts over {total_weeks} weeks")

        return schedule

    def _detect_platforms(self, posts: List[Post]) -> List[Platform]:
        """Auto-detect platforms from posts"""
        detected = set()

        for post in posts:
            if post.target_platform:
                try:
                    platform = Platform(post.target_platform.lower())
                    detected.add(platform)
                except ValueError:
                    pass

        # Default to LinkedIn if no platforms detected
        if not detected:
            detected.add(Platform.LINKEDIN)

        return list(detected)

    def _generate_posting_slots(
        self,
        num_posts: int,
        start_date: date,
        posts_per_week: int,
        platforms: List[Platform],
    ) -> List[Tuple[date, time, Platform]]:
        """
        Generate posting slots (date, time, platform)

        Strategy:
        - Distribute posts across optimal days for each platform
        - Rotate through platforms if multiple
        - Use platform-specific optimal times
        - Avoid same-day posting unless necessary
        """
        slots = []
        current_date = start_date
        platform_index = 0

        # Get optimal times for each platform
        platform_times = {}
        for platform in platforms:
            platform_times[platform] = self.PLATFORM_OPTIMAL_TIMES.get(
                platform,
                [(1, time(10, 0)), (3, time(14, 0))],  # Default times
            )

        # Track slots per week
        week_start = start_date
        slots_this_week = 0

        for post_num in range(num_posts):
            # Select platform (rotate)
            platform = platforms[platform_index % len(platforms)]
            platform_index += 1

            # Get optimal posting times for this platform
            optimal_times = platform_times[platform]

            # Find next available slot
            slot_found = False
            days_checked = 0
            max_days = 60  # Safety limit

            while not slot_found and days_checked < max_days:
                # Get day of week (0=Monday, 6=Sunday)
                weekday = current_date.weekday()

                # Check if this day has optimal time for this platform
                matching_times = [t for dow, t in optimal_times if dow == weekday]

                if matching_times:
                    # Use first matching time
                    posting_time = matching_times[0]
                    slots.append((current_date, posting_time, platform))
                    slot_found = True
                    slots_this_week += 1

                    # Move to next day
                    current_date += timedelta(days=1)

                    # Check if we've hit week limit
                    if slots_this_week >= posts_per_week:
                        # Move to next week
                        current_date = week_start + timedelta(weeks=1)
                        week_start = current_date
                        slots_this_week = 0
                else:
                    # No optimal time for this day, move to next day
                    current_date += timedelta(days=1)

                days_checked += 1

                # Check if we've moved to next week
                if (current_date - week_start).days >= 7:
                    week_start = current_date
                    slots_this_week = 0

            if not slot_found:
                # Fallback: use current date with default time
                logger.warning(f"Could not find optimal slot for post {post_num+1}, using fallback")
                slots.append((current_date, time(10, 0), platform))
                current_date += timedelta(days=1)

        return slots


# Default generator instance (lazy loaded)
default_schedule_generator = None


def get_default_schedule_generator() -> ScheduleGenerator:
    """Get or create default schedule generator instance"""
    global default_schedule_generator
    if default_schedule_generator is None:
        default_schedule_generator = ScheduleGenerator()
    return default_schedule_generator
