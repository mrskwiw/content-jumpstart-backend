#!/usr/bin/env python3
"""
Content Jumpstart - Main CLI Entry Point

Simplified interface using the CoordinatorAgent for complete workflow orchestration
"""

import argparse
import asyncio
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.agents.coordinator import CoordinatorAgent
from src.models.client_brief import Platform
from src.utils.logger import logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Content Jumpstart - Generate professional social media content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with existing brief file
  python run_jumpstart.py path/to/brief.txt

  # Run with interactive brief builder
  python run_jumpstart.py --interactive

  # Include voice samples for analysis
  python run_jumpstart.py brief.txt --voice-samples sample1.txt sample2.txt

  # Generate with specific template quantities
  python run_jumpstart.py brief.txt --template-quantities '{"1": 3, "2": 5, "9": 2}'

  # Generate fewer posts (legacy)
  python run_jumpstart.py brief.txt --num-posts 10

  # Target specific platform
  python run_jumpstart.py brief.txt --platform twitter

  # Set posting schedule start date
  python run_jumpstart.py brief.txt --start-date 2025-12-01
        """,
    )

    parser.add_argument("brief", nargs="?", help="Path to client brief file (or use --interactive)")

    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Run interactive brief builder"
    )

    parser.add_argument(
        "--voice-samples",
        nargs="+",
        metavar="FILE",
        help="Paths to sample posts for voice analysis",
    )

    parser.add_argument(
        "-n", "--num-posts", type=int, default=30, help="Number of posts to generate (default: 30)"
    )

    parser.add_argument(
        "--template-quantities",
        type=str,
        metavar="JSON",
        help='Template quantities as JSON dict (e.g., \'{"1": 3, "2": 5, "9": 2}\')',
    )

    parser.add_argument(
        "--topics",
        type=str,
        help="Comma-separated list of content topics to focus on (overrides research suggestions)",
    )

    parser.add_argument(
        "-p",
        "--platform",
        choices=["linkedin", "twitter", "facebook", "blog", "email"],
        help="Target platform (default: from brief or linkedin)",
    )

    parser.add_argument(
        "--start-date", type=str, help="Posting schedule start date (YYYY-MM-DD, default: today)"
    )

    parser.add_argument(
        "--no-analytics", action="store_true", help="Skip analytics tracker generation"
    )

    parser.add_argument("--no-docx", action="store_true", help="Skip DOCX deliverable generation")

    parser.add_argument(
        "--fill-missing", action="store_true", help="Prompt for any missing required fields"
    )

    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()

    # Validate arguments
    if not args.interactive and not args.brief:
        print("Error: Must provide either a brief file or use --interactive")
        print("Run 'python run_jumpstart.py --help' for usage information")
        sys.exit(1)

    try:
        # Initialize coordinator
        coordinator = CoordinatorAgent()

        # Get client brief
        if args.interactive:
            # Run interactive builder
            client_brief = coordinator.run_interactive_builder()
            brief_input = client_brief
        else:
            # Use provided brief file
            brief_path = Path(args.brief)
            if not brief_path.exists():
                print(f"Error: Brief file not found: {brief_path}")
                sys.exit(1)
            brief_input = brief_path

        # Load voice samples if provided
        voice_samples = None
        if args.voice_samples:
            voice_samples = []
            for sample_path in args.voice_samples:
                sample_file = Path(sample_path)
                if not sample_file.exists():
                    print(f"Warning: Voice sample not found: {sample_file}")
                    continue

                sample_text = sample_file.read_text(encoding="utf-8")
                voice_samples.append(sample_text)

            if not voice_samples:
                print("Warning: No valid voice samples found")
                voice_samples = None

        # Parse platform
        platform = None
        if args.platform:
            platform_map = {
                "linkedin": Platform.LINKEDIN,
                "twitter": Platform.TWITTER,
                "facebook": Platform.FACEBOOK,
                "blog": Platform.BLOG,
                "email": Platform.EMAIL,
            }
            platform = platform_map[args.platform]

        # Parse start date
        start_date = None
        if args.start_date:
            try:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid date format: {args.start_date}")
                print("Use YYYY-MM-DD format (e.g., 2025-12-01)")
                sys.exit(1)

        # Parse template quantities
        template_quantities = None
        if args.template_quantities:
            try:
                template_quantities = json.loads(args.template_quantities)

                # Validate format
                if not isinstance(template_quantities, dict):
                    raise ValueError("Template quantities must be a JSON object/dict")

                # Validate each entry (template ID and quantity)
                for template_id, quantity in template_quantities.items():
                    # Ensure template_id is numeric string
                    try:
                        template_id_int = int(template_id)
                        if template_id_int < 1 or template_id_int > 100:
                            raise ValueError(f"Template ID must be between 1-100: {template_id}")
                    except ValueError:
                        raise ValueError(f"Template ID must be numeric: {template_id}")

                    # Ensure quantity is valid integer
                    if not isinstance(quantity, int) or quantity < 0 or quantity > 100:
                        raise ValueError(
                            f"Quantity for template {template_id} must be 0-100: {quantity}"
                        )

                # Calculate total posts from quantities
                total_from_quantities = sum(template_quantities.values())
                if total_from_quantities == 0:
                    print("Warning: Template quantities sum to 0 posts")

                # Override num_posts if quantities provided
                if total_from_quantities > 0:
                    print(f"Using template quantities: {total_from_quantities} total posts")
                    args.num_posts = total_from_quantities

            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON format for template quantities: {e}")
                print("Example: --template-quantities '{\"1\": 3, \"2\": 5, \"9\": 2}'")
                sys.exit(1)
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

        # Run complete workflow
        saved_files = await coordinator.run_complete_workflow(
            brief_input=brief_input,
            voice_samples=voice_samples,
            num_posts=args.num_posts,
            template_quantities=template_quantities,  # NEW: Pass quantities
            platform=platform,
            interactive=args.fill_missing,
            include_analytics=not args.no_analytics,
            include_docx=not args.no_docx,
            start_date=start_date,
        )

        # Success!
        print("\n" + "=" * 60)
        print("SUCCESS! Content generation complete.")
        print("=" * 60)

        if saved_files:
            first_file = next(iter(saved_files.values()))
            output_dir = first_file.parent
            print("\nDeliverables saved to:")
            print(f"  {output_dir}")
            print(f"\nGenerated {len(saved_files)} files:")
            for key, path in saved_files.items():
                print(f"  - {path.name}")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("\nCheck logs/content_jumpstart.log for details")
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
