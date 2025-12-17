"""Data models for posting schedule generation"""
import csv
from datetime import date, time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DayOfWeek(str, Enum):
    """Day of week enumeration for scheduling"""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class ScheduledPost(BaseModel):
    """Individual post with scheduling metadata

    Attributes:
        post_id: Unique identifier for the post (1-30)
        post_title: Post title or first line
        post_excerpt: Brief content summary
        scheduled_date: Target publication date
        scheduled_time: Optional specific time of day
        day_of_week: Day of week enum value
        week_number: Week number in campaign (1-based)
        platform: Target platform (LinkedIn, Twitter, etc.)
        notes: Optional scheduling notes or reminders
    """

    post_id: int = Field(..., ge=1)
    post_title: str
    post_excerpt: str
    scheduled_date: date
    scheduled_time: Optional[time] = None
    day_of_week: DayOfWeek
    week_number: int = Field(..., ge=1)
    platform: str
    notes: Optional[str] = None


class PostingSchedule(BaseModel):
    """Complete posting schedule for a client campaign

    Manages the full 30-day content calendar with weekly breakdown,
    platform-specific posting guidelines, and export capabilities.

    Attributes:
        client_name: Client identifier for the campaign
        start_date: Campaign start date
        end_date: Campaign end date
        total_weeks: Number of weeks in campaign
        posts_per_week: Target post frequency
        scheduled_posts: List of scheduled posts with metadata
        best_posting_times: Platform-specific optimal posting times
        frequency_notes: Additional scheduling guidance
    """

    client_name: str
    start_date: date
    end_date: date
    total_weeks: int = Field(..., ge=1)
    posts_per_week: int = Field(..., ge=1)
    scheduled_posts: List[ScheduledPost]
    best_posting_times: Dict[str, List[str]] = Field(default_factory=dict)
    frequency_notes: str = ""

    def to_markdown_calendar(self) -> str:
        """Export as markdown calendar with weekly breakdown"""
        lines = []
        lines.append(f"# Posting Schedule: {self.client_name}\n")
        lines.append(
            f"**Schedule Duration:** {self.start_date.strftime('%b %d, %Y')} to {self.end_date.strftime('%b %d, %Y')} ({self.total_weeks} weeks)\n"
        )
        lines.append(f"**Frequency:** {self.posts_per_week} posts per week\n")
        lines.append(f"**Total Posts:** {len(self.scheduled_posts)}\n\n---\n")

        posts_by_week = {}
        for post in self.scheduled_posts:
            if post.week_number not in posts_by_week:
                posts_by_week[post.week_number] = []
            posts_by_week[post.week_number].append(post)

        for week_num in sorted(posts_by_week.keys()):
            week_posts = posts_by_week[week_num]
            first_post, last_post = week_posts[0], week_posts[-1]
            lines.append(
                f"\n## Week {week_num} ({first_post.scheduled_date.strftime('%b %d')} - {last_post.scheduled_date.strftime('%b %d, %Y')})\n\n"
            )
            lines.append(
                "| Date | Day | Time | Post | Platform | Notes |\n|------|-----|------|------|----------|-------|\n"
            )

            for post in week_posts:
                date_str = post.scheduled_date.strftime("%b %d")
                time_str = post.scheduled_time.strftime("%I:%M %p") if post.scheduled_time else ""
                lines.append(
                    f"| {date_str} | {post.day_of_week.value} | {time_str} | #{post.post_id}: {post.post_title} | {post.platform} | {post.notes or '-'} |\n"
                )

        lines.append("\n---\n\n## Posting Guidelines\n")
        if self.best_posting_times and self.scheduled_posts:
            platform = self.scheduled_posts[0].platform
            times = self.best_posting_times.get(platform.lower(), [])
            if times:
                lines.append(f"\n### Best Times ({platform}):\n")
                lines.extend(f"- {t}\n" for t in times)

        lines.append(
            "\n### Tips:\n1. Post during recommended times\n2. Respond to comments within 2 hours\n3. Vary times week-to-week\n"
        )
        if self.frequency_notes:
            lines.append(f"\n---\n*{self.frequency_notes}*\n")
        return "".join(lines)

    def to_csv(self, output_path: Path) -> Path:
        """Export as CSV"""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Post ID", "Title", "Excerpt", "Date", "Day", "Time", "Week", "Platform", "Notes"]
            )
            for post in self.scheduled_posts:
                writer.writerow(
                    [
                        post.post_id,
                        post.post_title,
                        post.post_excerpt,
                        post.scheduled_date.strftime("%Y-%m-%d"),
                        post.day_of_week.value,
                        post.scheduled_time.strftime("%H:%M") if post.scheduled_time else "",
                        post.week_number,
                        post.platform,
                        post.notes or "",
                    ]
                )
        return output_path

    def to_ical(self, output_path: Path) -> Path:
        """Export as iCal"""
        try:
            from datetime import datetime, timedelta

            from icalendar import Calendar, Event
        except ImportError:
            raise ImportError("icalendar required: pip install icalendar")

        cal = Calendar()
        cal.add("prodid", "-//30-Day Content Jumpstart//EN")
        cal.add("version", "2.0")
        cal.add("x-wr-calname", f"{self.client_name} Posting Schedule")

        for post in self.scheduled_posts:
            event = Event()
            event.add("summary", f"POST: {post.post_title}")
            event.add("description", post.post_excerpt)
            dt = datetime.combine(post.scheduled_date, post.scheduled_time or time(12, 0))
            event.add("dtstart", dt)
            event.add("dtend", dt + timedelta(hours=1))
            event.add("location", post.platform)
            if post.notes:
                event["description"] = f"{post.post_excerpt}\n\nNotes: {post.notes}"
            cal.add_component(event)

        output_path.write_bytes(cal.to_ical())
        return output_path
