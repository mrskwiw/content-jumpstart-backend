"""Output formatting utilities for generated posts"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

# Phase 5 imports
from ..agents.voice_analyzer import VoiceAnalyzer
from ..models.client_brief import ClientBrief
from ..models.post import Post
from ..models.qa_report import QAReport
from ..models.seo_keyword import KeywordStrategy
from ..utils.analytics_tracker import AnalyticsTracker
from ..utils.docx_generator import DOCXGenerator
from ..utils.schedule_generator import ScheduleGenerator
from .logger import logger


class OutputFormatter:
    """Formats and exports generated posts in various formats"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize output formatter

        Args:
            output_dir: Directory for output files (defaults to settings)
        """
        if output_dir is None:
            from ..config.settings import settings

            output_dir = Path(settings.DEFAULT_OUTPUT_DIR)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_posts_as_text(
        self,
        posts: List[Post],
        include_metadata: bool = False,
        separator: str = "\n---\n\n",
    ) -> str:
        """
        Format posts as plain text

        Args:
            posts: List of Post objects
            include_metadata: Include post metadata
            separator: String to separate posts

        Returns:
            Formatted text string
        """
        formatted_posts = [
            post.to_formatted_string(include_metadata=include_metadata) for post in posts
        ]
        return separator.join(formatted_posts)

    def format_posts_as_json(self, posts: List[Post]) -> str:
        """
        Format posts as JSON

        Args:
            posts: List of Post objects

        Returns:
            JSON string
        """
        posts_data = [post.model_dump() for post in posts]
        return json.dumps(posts_data, indent=2, default=str)

    def format_posts_as_markdown(
        self, posts: List[Post], client_brief: Optional[ClientBrief] = None
    ) -> str:
        """
        Format posts as Markdown with optional client context

        Args:
            posts: List of Post objects
            client_brief: Optional client brief for header

        Returns:
            Markdown string
        """
        lines = []

        # Header
        if client_brief:
            lines.append(f"# 30-Day Content Jumpstart: {client_brief.company_name}\n")
            lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            lines.append(f"**Business:** {client_brief.business_description}\n")
            lines.append(f"**Target Audience:** {client_brief.ideal_customer}\n")
            lines.append(
                f"**Platform(s):** {', '.join([p.value for p in client_brief.target_platforms])}\n"
            )
            lines.append("---\n")
        else:
            lines.append("# 30-Day Content Jumpstart\n")
            lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            lines.append("---\n")

        # Posts
        for i, post in enumerate(posts, 1):
            lines.append(f"## Post {i}: {post.template_name}\n")
            lines.append(f"{post.content}\n")
            lines.append(f"\n*Template: {post.template_name} | ")
            lines.append(f"Words: {post.word_count} | ")
            lines.append(f"Has CTA: {'Yes' if post.has_cta else 'No'}*\n")
            lines.append("\n---\n")

        return "\n".join(lines)

    def format_brand_voice_guide(self, client_brief: ClientBrief) -> str:
        """
        Format brand voice guide from client brief

        Args:
            client_brief: Client brief information

        Returns:
            Formatted brand voice guide
        """
        lines = []

        lines.append(f"# Brand Voice Guide: {client_brief.company_name}\n")
        lines.append("## Audience\n")
        lines.append(f"**Ideal Customer:** {client_brief.ideal_customer}\n")
        lines.append(f"**Main Problem We Solve:** {client_brief.main_problem_solved}\n")

        if client_brief.customer_pain_points:
            lines.append("\n**Customer Pain Points:**\n")
            for pain in client_brief.customer_pain_points:
                lines.append(f"- {pain}\n")

        lines.append("\n## Voice & Tone\n")
        if client_brief.brand_personality:
            lines.append(
                f"**Personality:** {', '.join([p.value for p in client_brief.brand_personality])}\n"
            )

        if client_brief.key_phrases:
            lines.append("\n**Key Phrases to Use:**\n")
            for phrase in client_brief.key_phrases:
                lines.append(f'- "{phrase}"\n')

        lines.append("\n## Platform Preferences\n")
        lines.append(
            f"**Target Platforms:** {', '.join([p.value for p in client_brief.target_platforms])}\n"
        )
        lines.append(f"**Posting Frequency:** {client_brief.posting_frequency}\n")

        # Include stories as examples if available
        if hasattr(client_brief, "stories") and client_brief.stories:
            lines.append("\n## Example Stories/Wins\n")
            for i, story in enumerate(client_brief.stories, 1):
                lines.append(f"\n### Story {i}\n")
                lines.append(f"{story}\n")

        return "".join(lines)

    def format_keyword_strategy(
        self, keyword_strategy: KeywordStrategy, client_brief: ClientBrief
    ) -> str:
        """
        Format SEO keyword strategy as markdown

        Args:
            keyword_strategy: Keyword strategy to format
            client_brief: Client brief for context

        Returns:
            Formatted keyword strategy markdown
        """
        lines = []

        lines.append(f"# SEO Keyword Strategy: {client_brief.company_name}\n")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        lines.append(f"**Target Keyword Density:** {keyword_strategy.keyword_density_target:.1%}\n")
        lines.append("\n---\n")

        # Primary Keywords
        lines.append("\n## Primary Keywords\n")
        lines.append("*High-value keywords directly aligned with your core offering*\n\n")
        for kw in keyword_strategy.primary_keywords:
            lines.append(f"### {kw.keyword}\n")
            lines.append(f"- **Intent:** {kw.intent.value}\n")
            lines.append(f"- **Difficulty:** {kw.difficulty.value}\n")
            lines.append(f"- **Priority:** {kw.priority}\n")
            if kw.related_keywords:
                lines.append(f"- **Related:** {', '.join(kw.related_keywords)}\n")
            if kw.notes:
                lines.append(f"- **Notes:** {kw.notes}\n")
            lines.append("\n")

        # Secondary Keywords
        lines.append("## Secondary Keywords\n")
        lines.append("*Support keywords addressing specific pain points and solutions*\n\n")
        for kw in keyword_strategy.secondary_keywords:
            lines.append(f"### {kw.keyword}\n")
            lines.append(
                f"- **Intent:** {kw.intent.value} | **Difficulty:** {kw.difficulty.value}\n"
            )
            if kw.related_keywords:
                lines.append(f"- **Related:** {', '.join(kw.related_keywords)}\n")
            if kw.notes:
                lines.append(f"- **Notes:** {kw.notes}\n")
            lines.append("\n")

        # Long-tail Keywords
        lines.append("## Long-Tail Keywords\n")
        lines.append("*Specific, lower-competition keywords for niche topics*\n\n")
        for kw in keyword_strategy.longtail_keywords:
            lines.append(f"### {kw.keyword}\n")
            lines.append(
                f"- **Intent:** {kw.intent.value} | **Difficulty:** {kw.difficulty.value}\n"
            )
            if kw.notes:
                lines.append(f"- **Notes:** {kw.notes}\n")
            lines.append("\n")

        # Usage Guidelines
        lines.append("---\n")
        lines.append("\n## How to Use These Keywords\n\n")
        lines.append(
            "1. **Natural Integration:** Weave keywords into your content naturally - never force or stuff them\n"
        )
        lines.append(
            "2. **Primary First:** Aim to include at least one primary keyword per post when relevant\n"
        )
        lines.append(
            "3. **Variety:** Mix primary, secondary, and long-tail keywords across your 30 posts\n"
        )
        lines.append(
            "4. **Context Matters:** Use keywords where they genuinely fit the topic and message\n"
        )
        lines.append(
            "5. **Track Performance:** Monitor which keywords drive engagement and adjust future content\n\n"
        )

        return "".join(lines)

    def save_as_text(
        self, posts: List[Post], filename: str, include_metadata: bool = False
    ) -> Path:
        """
        Save posts as plain text file

        Args:
            posts: List of Post objects
            filename: Output filename (without extension)
            include_metadata: Include post metadata

        Returns:
            Path to saved file
        """
        content = self.format_posts_as_text(posts, include_metadata)
        output_path = self.output_dir / f"{filename}.txt"
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved posts to {output_path}")
        return output_path

    def save_as_json(self, posts: List[Post], filename: str) -> Path:
        """
        Save posts as JSON file

        Args:
            posts: List of Post objects
            filename: Output filename (without extension)

        Returns:
            Path to saved file
        """
        content = self.format_posts_as_json(posts)
        output_path = self.output_dir / f"{filename}.json"
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved posts to {output_path}")
        return output_path

    def save_as_markdown(
        self,
        posts: List[Post],
        filename: str,
        client_brief: Optional[ClientBrief] = None,
    ) -> Path:
        """
        Save posts as Markdown file

        Args:
            posts: List of Post objects
            filename: Output filename (without extension)
            client_brief: Optional client brief for context

        Returns:
            Path to saved file
        """
        content = self.format_posts_as_markdown(posts, client_brief)
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved posts to {output_path}")
        return output_path

    def save_complete_package(
        self,
        posts: List[Post],
        client_brief: ClientBrief,
        client_name: str,
        qa_report: Optional[QAReport] = None,
        keyword_strategy: Optional[KeywordStrategy] = None,
        start_date: Optional[date] = None,
        include_docx: bool = True,
        include_analytics_tracker: bool = True,
    ) -> Dict[str, Path]:
        """
        Save complete deliverable package for client

        Args:
            posts: List of generated posts
            client_brief: Client brief information
            client_name: Client identifier for filenames
            qa_report: Optional QA report to include
            keyword_strategy: Optional SEO keyword strategy to include
            start_date: Optional start date for posting schedule (defaults to today)
            include_docx: Generate DOCX deliverable (requires python-docx)
            include_analytics_tracker: Generate analytics tracking sheet

        Returns:
            Dictionary of file type to path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{client_name}_{timestamp}"

        # Create client-specific directory
        client_dir = self.output_dir / client_name
        client_dir.mkdir(parents=True, exist_ok=True)

        # Save in multiple formats
        saved_files = {}

        # Main deliverable (Markdown with full context)
        markdown_path = client_dir / f"{base_filename}_deliverable.md"
        markdown_path.write_text(
            self.format_posts_as_markdown(posts, client_brief), encoding="utf-8"
        )
        saved_files["markdown"] = markdown_path

        # Brand voice guide
        voice_guide_path = client_dir / f"{base_filename}_brand_voice.md"
        voice_guide_path.write_text(self.format_brand_voice_guide(client_brief), encoding="utf-8")
        saved_files["brand_voice"] = voice_guide_path

        # Plain text (easy copy/paste)
        text_path = client_dir / f"{base_filename}_posts.txt"
        text_path.write_text(
            self.format_posts_as_text(posts, include_metadata=False), encoding="utf-8"
        )
        saved_files["text"] = text_path

        # JSON (data format)
        json_path = client_dir / f"{base_filename}_posts.json"
        json_path.write_text(self.format_posts_as_json(posts), encoding="utf-8")
        saved_files["json"] = json_path

        # QA Report (if provided)
        if qa_report:
            qa_report_path = client_dir / f"{base_filename}_qa_report.md"
            qa_report_path.write_text(qa_report.to_markdown(), encoding="utf-8")
            saved_files["qa_report"] = qa_report_path
            logger.info(f"Saved QA report to {qa_report_path}")

        # Keyword Strategy (if provided)
        if keyword_strategy:
            keyword_strategy_path = client_dir / f"{base_filename}_keyword_strategy.md"
            keyword_strategy_path.write_text(
                self.format_keyword_strategy(keyword_strategy, client_brief), encoding="utf-8"
            )
            saved_files["keyword_strategy"] = keyword_strategy_path
            logger.info(f"Saved keyword strategy to {keyword_strategy_path}")

        # ===== PHASE 5: ENHANCED DELIVERABLES =====

        # Generate enhanced brand voice guide (analyzes generated posts)
        try:
            voice_analyzer = VoiceAnalyzer()
            enhanced_voice_guide = voice_analyzer.analyze_voice_patterns(posts, client_brief)

            voice_guide_enhanced_path = client_dir / f"{base_filename}_brand_voice_enhanced.md"
            voice_guide_enhanced_path.write_text(
                enhanced_voice_guide.to_markdown(), encoding="utf-8"
            )
            saved_files["brand_voice_enhanced"] = voice_guide_enhanced_path
            logger.info(f"Saved enhanced brand voice guide to {voice_guide_enhanced_path}")
        except Exception as e:
            logger.warning(f"Enhanced voice guide generation failed: {str(e)}")

        # Generate posting schedule with calendar dates
        try:
            schedule_generator = ScheduleGenerator()
            schedule_start = start_date or date.today()
            posting_schedule = schedule_generator.generate_schedule(
                posts=posts,
                start_date=schedule_start,
                posts_per_week=4,  # Default: 4 posts per week
                platforms=client_brief.target_platforms,
            )

            # Save schedule in multiple formats
            schedule_md_path = client_dir / f"{base_filename}_schedule.md"
            schedule_md_path.write_text(posting_schedule.to_markdown_calendar(), encoding="utf-8")
            saved_files["schedule_markdown"] = schedule_md_path

            schedule_csv_path = posting_schedule.to_csv(
                client_dir / f"{base_filename}_schedule.csv"
            )
            saved_files["schedule_csv"] = schedule_csv_path

            # iCal export (if icalendar available)
            try:
                schedule_ical_path = posting_schedule.to_ical(
                    client_dir / f"{base_filename}_schedule.ics"
                )
                saved_files["schedule_ical"] = schedule_ical_path
            except ImportError:
                logger.info("icalendar not installed - skipping .ics export")

            logger.info(f"Saved posting schedule to {schedule_md_path}")
        except Exception as e:
            logger.warning(f"Posting schedule generation failed: {str(e)}")

        # Generate analytics tracking sheet
        if include_analytics_tracker:
            try:
                analytics_tracker = AnalyticsTracker()

                # CSV version (always)
                tracker_csv_path = analytics_tracker.create_tracking_sheet(
                    posts=posts,
                    schedule=posting_schedule if "posting_schedule" in locals() else None,
                    output_path=client_dir / f"{base_filename}_analytics_tracker.csv",
                    format="csv",
                )
                saved_files["analytics_csv"] = tracker_csv_path

                # Excel version (if openpyxl available)
                try:
                    tracker_xlsx_path = analytics_tracker.create_tracking_sheet(
                        posts=posts,
                        schedule=posting_schedule if "posting_schedule" in locals() else None,
                        output_path=client_dir / f"{base_filename}_analytics_tracker.xlsx",
                        format="xlsx",
                    )
                    saved_files["analytics_xlsx"] = tracker_xlsx_path
                except ImportError:
                    logger.info("openpyxl not installed - skipping XLSX tracker")

            except Exception as e:
                logger.warning(f"Analytics tracker generation failed: {str(e)}")

        # Generate DOCX deliverable
        if include_docx:
            try:
                docx_generator = DOCXGenerator()

                # Prepare content for DOCX
                voice_guide_content = (
                    enhanced_voice_guide.to_markdown()
                    if "enhanced_voice_guide" in locals()
                    else self.format_brand_voice_guide(client_brief)
                )

                schedule_content = (
                    posting_schedule.to_markdown_calendar()
                    if "posting_schedule" in locals()
                    else "Schedule not available"
                )

                docx_path = docx_generator.create_deliverable_docx(
                    posts=posts,
                    client_brief=client_brief,
                    output_path=client_dir / f"{base_filename}_deliverable.docx",
                    include_voice_guide=True,
                    include_schedule=True,
                    qa_report=qa_report,
                    voice_guide_content=voice_guide_content,
                    schedule_content=schedule_content,
                )
                saved_files["docx"] = docx_path
                logger.info(f"Saved DOCX deliverable to {docx_path}")

            except ImportError:
                logger.warning("python-docx not installed - skipping DOCX generation")
            except Exception as e:
                logger.warning(f"DOCX generation failed: {str(e)}")

        logger.info(f"Saved complete package for {client_name} to {client_dir}")

        return saved_files

    def create_posting_schedule(self, posts: List[Post], posts_per_week: int = 3) -> str:
        """
        Create a suggested posting schedule

        Args:
            posts: List of Post objects
            posts_per_week: Number of posts per week

        Returns:
            Formatted schedule string
        """
        lines = []
        lines.append("# Suggested Posting Schedule\n")
        lines.append(f"**Posts per week:** {posts_per_week}\n")
        lines.append(f"**Total posts:** {len(posts)}\n")
        lines.append(f"**Duration:** ~{len(posts) // posts_per_week} weeks\n")
        lines.append("\n---\n")

        week = 1
        post_index = 0

        while post_index < len(posts):
            lines.append(f"\n## Week {week}\n")

            for _ in range(posts_per_week):
                if post_index >= len(posts):
                    break

                post = posts[post_index]
                lines.append(
                    f"- **Post {post_index + 1}:** {post.template_name} "
                    f"({post.word_count} words)\n"
                )
                post_index += 1

            week += 1

        return "".join(lines)


# Default formatter instance (lazy loaded)
default_formatter = None


def get_default_formatter() -> OutputFormatter:
    """Get or create default formatter instance"""
    global default_formatter
    if default_formatter is None:
        default_formatter = OutputFormatter()
    return default_formatter
