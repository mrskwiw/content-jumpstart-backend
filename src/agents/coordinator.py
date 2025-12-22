"""
Coordinator Agent - Orchestrates the complete content generation workflow

This agent coordinates all other agents to provide a seamless end-to-end experience:
1. Accepts brief in multiple formats (file, dict, interactive)
2. Validates brief completeness
3. Prompts for missing information
4. Optionally analyzes voice samples
5. Orchestrates content generation
6. Produces all deliverables
"""

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..agents.brief_parser import BriefParserAgent
from ..agents.client_classifier import ClientClassifier
from ..agents.content_generator import ContentGeneratorAgent
from ..agents.post_regenerator import PostRegenerator
from ..agents.qa_agent import QAAgent
from ..agents.voice_analyzer import VoiceAnalyzer
from ..config.settings import settings
from ..models.client_brief import ClientBrief, DataUsagePreference, Platform, TonePreference
from ..models.post import Post
from ..utils.logger import logger
from ..utils.output_formatter import OutputFormatter


class CoordinatorAgent:
    """
    Main orchestrator for the content generation system

    Handles:
    - Brief input in multiple formats
    - Interactive brief building
    - Voice sample analysis
    - Workflow orchestration
    - Deliverable generation
    """

    def __init__(self):
        """Initialize coordinator with all sub-agents"""
        self.brief_parser = BriefParserAgent()
        self.client_classifier = ClientClassifier()
        self.content_generator = ContentGeneratorAgent()
        self.qa_agent = QAAgent()
        self.voice_analyzer = VoiceAnalyzer()
        self.post_regenerator = PostRegenerator()
        self.output_formatter = OutputFormatter()

    async def run_complete_workflow(
        self,
        brief_input: Union[str, Path, Dict, ClientBrief],
        voice_samples: Optional[List[str]] = None,
        num_posts: int = 30,
        platform: Optional[Platform] = None,
        interactive: bool = False,
        include_analytics: bool = True,
        include_docx: bool = True,
        start_date: Optional[date] = None,
        auto_fix: bool = False,
    ) -> Dict[str, Path]:
        """
        Run complete workflow from brief to deliverables

        Args:
            brief_input: Brief as file path, dict, or ClientBrief object
            voice_samples: Optional list of sample post texts for voice analysis
            num_posts: Number of posts to generate (default: 30)
            platform: Target platform (default: LinkedIn)
            interactive: If True, prompt for missing information
            include_analytics: Generate analytics tracker
            include_docx: Generate DOCX deliverable
            start_date: Posting schedule start date (default: today)
            auto_fix: If True, automatically regenerate posts that fail quality checks

        Returns:
            Dictionary mapping file types to generated file paths
        """
        logger.info("=" * 60)
        logger.info("CONTENT JUMPSTART - COORDINATOR AGENT")
        logger.info("=" * 60)

        # Step 1: Process brief input
        logger.info("\n[1/7] Processing client brief...")
        client_brief = await self._process_brief_input(brief_input, interactive)
        logger.info(f"   Client: {client_brief.company_name}")
        logger.info(f"   Platforms: {', '.join(p.value for p in client_brief.target_platforms)}")

        # Step 2: Analyze voice samples (if provided)
        voice_guide = None
        if voice_samples:
            logger.info(f"\n[2/7] Analyzing {len(voice_samples)} voice samples...")
            voice_guide = await self._analyze_voice_samples(voice_samples, client_brief)
            logger.info(f"   Dominant tones: {', '.join(voice_guide.dominant_tones)}")
            logger.info(f"   Tone consistency: {int(voice_guide.tone_consistency_score * 100)}%")
        else:
            logger.info("\n[2/7] Skipping voice analysis (no samples provided)")

        # Step 3: Classify client type
        logger.info("\n[3/7] Classifying client type...")
        client_type, confidence = self.client_classifier.classify_client(client_brief)
        logger.info(f"   Client type: {client_type.value}")
        logger.info(f"   Confidence: {int(confidence * 100)}%")

        # Step 4: Generate content
        logger.info(f"\n[4/7] Generating {num_posts} posts...")
        logger.info(f"   Mode: {'Async' if settings.PARALLEL_GENERATION else 'Sync'}")

        target_platform = platform or (
            client_brief.target_platforms[0] if client_brief.target_platforms else Platform.LINKEDIN
        )

        if settings.PARALLEL_GENERATION:
            posts = await self.content_generator.generate_posts_async(
                client_brief=client_brief,
                num_posts=num_posts,
                platform=target_platform,
            )
        else:
            posts = self.content_generator.generate_posts(
                client_brief=client_brief,
                num_posts=num_posts,
                platform=target_platform,
            )

        logger.info(f"   Generated: {len(posts)} posts")
        logger.info(f"   Avg length: {sum(p.word_count for p in posts) // len(posts)} words")

        # Step 5: Run QA validation
        logger.info("\n[5/7] Running quality validation...")
        qa_report = self.qa_agent.validate_posts(posts, client_brief.company_name)
        logger.info(f"   Quality score: {int(qa_report.quality_score * 100)}%")
        logger.info(f"   Status: {'PASSED' if qa_report.overall_passed else 'NEEDS REVIEW'}")

        if qa_report.all_issues:
            logger.info(f"   Issues found: {len(qa_report.all_issues)}")
            for issue in qa_report.all_issues[:3]:  # Show first 3 issues
                logger.info(f"     - {issue}")

        # Step 5.5: Auto-regenerate failed posts (if enabled)
        if auto_fix:
            logger.info("\n[5.5/7] Auto-fixing quality issues...")
            regenerated_posts, regen_stats = self.post_regenerator.regenerate_failed_posts(
                posts=posts,
                templates=selected_templates,
                client_brief=client_brief,
                system_prompt=cached_system_prompt,
            )
            posts = regenerated_posts  # Update with regenerated versions
            logger.info(
                f"   Regenerated: {regen_stats['posts_regenerated']}/{regen_stats['total_posts']} posts"
            )
            logger.info(f"   Improved: {regen_stats['posts_improved']} posts")

            if regen_stats["reasons"]:
                logger.info("   Reasons breakdown:")
                for reason_type, count in regen_stats["reasons"].items():
                    logger.info(f"     - {reason_type}: {count}")

        # Step 6: Generate all deliverables
        logger.info("\n[6/7] Generating deliverables package...")

        schedule_start = start_date or date.today()

        saved_files = self.output_formatter.save_complete_package(
            posts=posts,
            client_brief=client_brief,
            client_name=client_brief.company_name,
            include_analytics_tracker=include_analytics,
            include_docx=include_docx,
            start_date=schedule_start,
            qa_report=qa_report,
        )

        logger.info(f"   Generated {len(saved_files)} files")

        # Step 7: Summary
        logger.info("\n[7/7] Workflow complete!")
        logger.info("=" * 60)
        logger.info("DELIVERABLES SUMMARY")
        logger.info("=" * 60)

        # Group files by type
        file_groups = {
            "Posts": ["deliverable", "posts_txt", "posts_json"],
            "Voice Guides": ["brand_voice", "brand_voice_enhanced"],
            "Schedules": ["schedule_markdown", "schedule_csv", "schedule_ical"],
            "Analytics": ["analytics_csv", "analytics_xlsx"],
            "Documents": ["docx", "qa_report"],
        }

        for group_name, file_keys in file_groups.items():
            group_files = [k for k in file_keys if k in saved_files]
            if group_files:
                logger.info(f"\n{group_name}:")
                for key in group_files:
                    file_path = saved_files[key]
                    logger.info(f"  - {file_path.name}")

        # Show output directory
        if saved_files:
            first_file = next(iter(saved_files.values()))
            output_dir = first_file.parent
            logger.info(f"\nAll files saved to: {output_dir}")

        logger.info("\n" + "=" * 60)

        return saved_files

    async def _process_brief_input(
        self,
        brief_input: Union[str, Path, Dict, ClientBrief],
        interactive: bool = False,
    ) -> ClientBrief:
        """
        Process brief input from various formats

        Args:
            brief_input: Brief as file path, dict, or ClientBrief
            interactive: If True, prompt for missing information

        Returns:
            Validated ClientBrief object
        """
        # If already a ClientBrief, validate and return
        if isinstance(brief_input, ClientBrief):
            logger.info("   Using provided ClientBrief object")
            if interactive:
                return await self._fill_missing_fields(brief_input)
            return brief_input

        # If dict, convert to ClientBrief
        if isinstance(brief_input, dict):
            logger.info("   Converting dictionary to ClientBrief")
            client_brief = ClientBrief(**brief_input)
            if interactive:
                return await self._fill_missing_fields(client_brief)
            return client_brief

        # If file path, parse with BriefParserAgent
        if isinstance(brief_input, (str, Path)):
            file_path = Path(brief_input)
            if not file_path.exists():
                raise FileNotFoundError(f"Brief file not found: {file_path}")

            logger.info(f"   Parsing brief from: {file_path.name}")
            brief_text = file_path.read_text(encoding="utf-8")
            client_brief = self.brief_parser.parse_brief(brief_text)

            if interactive:
                return await self._fill_missing_fields(client_brief)
            return client_brief

        raise TypeError(f"Unsupported brief_input type: {type(brief_input)}")

    async def _fill_missing_fields(self, client_brief: ClientBrief) -> ClientBrief:
        """
        Interactively fill missing required fields

        Args:
            client_brief: Partially filled ClientBrief

        Returns:
            Complete ClientBrief with all required fields
        """
        logger.info("   Checking for missing required fields...")

        # Check required fields
        required_fields = {
            "company_name": "Company/Client Name",
            "business_description": "Business Description",
            "ideal_customer": "Ideal Customer Profile",
            "main_problem_solved": "Main Problem Solved",
        }

        missing_fields = []
        for field_name, field_label in required_fields.items():
            value = getattr(client_brief, field_name, None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing_fields.append((field_name, field_label))

        if missing_fields:
            logger.info(f"   Found {len(missing_fields)} missing required fields")
            logger.info("   Please provide the following information:")

            # In a real implementation, this would use interactive prompts
            # For now, we'll raise an error with instructions
            missing_field_names = ", ".join([label for _, label in missing_fields])
            raise ValueError(
                f"Missing required fields: {missing_field_names}\n"
                "Please provide these fields in your brief or use the interactive builder."
            )

        logger.info("   All required fields present")
        return client_brief

    async def _analyze_voice_samples(
        self,
        voice_samples: List[str],
        client_brief: ClientBrief,
    ) -> "EnhancedVoiceGuide":
        """
        Analyze voice samples to extract tone patterns

        Args:
            voice_samples: List of sample post texts
            client_brief: Client brief for context

        Returns:
            EnhancedVoiceGuide with analyzed patterns
        """
        # Convert text samples to Post objects for analysis
        sample_posts = []
        for i, sample_text in enumerate(voice_samples, 1):
            post = Post(
                content=sample_text,
                template_id=0,  # Unknown template
                template_name="Voice Sample",
                variant=i,
                client_name=client_brief.company_name,
                target_platform=(
                    client_brief.target_platforms[0]
                    if client_brief.target_platforms
                    else Platform.LINKEDIN
                ),
            )
            sample_posts.append(post)

        # Analyze voice patterns
        voice_guide = self.voice_analyzer.analyze_voice_patterns(
            posts=sample_posts,
            client_brief=client_brief,
        )

        return voice_guide

    def run_interactive_builder(self) -> ClientBrief:
        """
        Run interactive brief builder (CLI-based)

        Returns:
            Complete ClientBrief built interactively
        """
        logger.info("\n" + "=" * 60)
        logger.info("INTERACTIVE BRIEF BUILDER")
        logger.info("=" * 60)

        print("\nLet's build your client brief step by step.\n")

        # Required fields
        company_name = input("Company/Client Name: ").strip()
        business_description = input("\nBusiness Description (what they do): ").strip()
        ideal_customer = input("\nIdeal Customer Profile (who they serve): ").strip()
        main_problem_solved = input("\nMain Problem Solved (what pain point): ").strip()

        # Pain points
        print("\nCustomer Pain Points (enter one per line, empty line to finish):")
        pain_points = []
        while True:
            pain = input(f"  Pain point #{len(pain_points) + 1}: ").strip()
            if not pain:
                break
            pain_points.append(pain)

        if not pain_points:
            pain_points = ["(No pain points provided)"]

        # Brand personality
        print(
            "\nBrand Personality Tones (select from: direct, approachable, witty, data_driven, empathetic, bold, thoughtful)"
        )
        print("Enter tone preferences (comma-separated): ")
        tones_input = input("  Tones: ").strip()

        tone_map = {
            "direct": TonePreference.DIRECT,
            "approachable": TonePreference.APPROACHABLE,
            "witty": TonePreference.WITTY,
            "data_driven": TonePreference.DATA_DRIVEN,
            "data-driven": TonePreference.DATA_DRIVEN,
            "empathetic": TonePreference.EMPATHETIC,
            "bold": TonePreference.BOLD,
            "thoughtful": TonePreference.THOUGHTFUL,
        }

        tones = []
        if tones_input:
            for tone in tones_input.split(","):
                tone_clean = tone.strip().lower()
                if tone_clean in tone_map:
                    tones.append(tone_map[tone_clean])

        if not tones:
            tones = [TonePreference.APPROACHABLE, TonePreference.DIRECT]

        # Key phrases
        print("\nKey Phrases/Taglines (enter one per line, empty line to finish):")
        key_phrases = []
        while True:
            phrase = input(f"  Phrase #{len(key_phrases) + 1}: ").strip()
            if not phrase:
                break
            key_phrases.append(phrase)

        if not key_phrases:
            key_phrases = []

        # Customer questions
        print("\nCommon Customer Questions (enter one per line, empty line to finish):")
        questions = []
        while True:
            question = input(f"  Question #{len(questions) + 1}: ").strip()
            if not question:
                break
            questions.append(question)

        if not questions:
            questions = []

        # Platform selection
        print("\nTarget Platforms (select from: linkedin, twitter, facebook, blog, email)")
        print("Enter platforms (comma-separated): ")
        platforms_input = input("  Platforms: ").strip()

        platform_map = {
            "linkedin": Platform.LINKEDIN,
            "twitter": Platform.TWITTER,
            "facebook": Platform.FACEBOOK,
            "blog": Platform.BLOG,
            "email": Platform.EMAIL,
        }

        platforms = []
        if platforms_input:
            for plat in platforms_input.split(","):
                plat_clean = plat.strip().lower()
                if plat_clean in platform_map:
                    platforms.append(platform_map[plat_clean])

        if not platforms:
            platforms = [Platform.LINKEDIN]

        # Posting frequency
        posting_frequency = input("\nPosting Frequency (e.g., '3-4x weekly', 'Daily'): ").strip()
        if not posting_frequency:
            posting_frequency = "3-4x weekly"

        # Data usage
        print("\nData Usage Preference (none, light, moderate, heavy): ")
        data_usage_input = input("  Data usage: ").strip().lower()

        data_usage_map = {
            "none": DataUsagePreference.NONE,
            "light": DataUsagePreference.LIGHT,
            "moderate": DataUsagePreference.MODERATE,
            "heavy": DataUsagePreference.HEAVY,
        }

        data_usage = data_usage_map.get(data_usage_input, DataUsagePreference.MODERATE)

        # Main CTA
        main_cta = input("\nMain Call-to-Action (e.g., 'Book a demo', 'Sign up'): ").strip()
        if not main_cta:
            main_cta = "Get in touch"

        # Build ClientBrief
        client_brief = ClientBrief(
            company_name=company_name,
            business_description=business_description,
            ideal_customer=ideal_customer,
            main_problem_solved=main_problem_solved,
            customer_pain_points=pain_points,
            brand_personality=tones,
            key_phrases=key_phrases,
            customer_questions=questions,
            target_platforms=platforms,
            posting_frequency=posting_frequency,
            data_usage=data_usage,
            main_cta=main_cta,
        )

        print("\n" + "=" * 60)
        print("BRIEF COMPLETE!")
        print("=" * 60)
        print(f"\nClient: {client_brief.company_name}")
        print(f"Platforms: {', '.join(p.value for p in client_brief.target_platforms)}")
        print(f"Tones: {', '.join(t.value for t in client_brief.brand_personality)}")
        print("\n")

        return client_brief


# Convenience function for running workflow
async def run_workflow(
    brief_input: Union[str, Path, Dict, ClientBrief],
    voice_samples: Optional[List[str]] = None,
    num_posts: int = 30,
    platform: Optional[Platform] = None,
    interactive: bool = False,
    include_analytics: bool = True,
    include_docx: bool = True,
    start_date: Optional[date] = None,
) -> Dict[str, Path]:
    """
    Convenience function to run complete workflow

    Args:
        brief_input: Brief as file path, dict, or ClientBrief object
        voice_samples: Optional list of sample post texts
        num_posts: Number of posts to generate
        platform: Target platform
        interactive: Prompt for missing information
        include_analytics: Generate analytics tracker
        include_docx: Generate DOCX deliverable
        start_date: Posting schedule start date

    Returns:
        Dictionary of generated file paths
    """
    coordinator = CoordinatorAgent()
    return await coordinator.run_complete_workflow(
        brief_input=brief_input,
        voice_samples=voice_samples,
        num_posts=num_posts,
        platform=platform,
        interactive=interactive,
        include_analytics=include_analytics,
        include_docx=include_docx,
        start_date=start_date,
    )
