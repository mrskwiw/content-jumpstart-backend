"""
Token Sync Service - Syncs token usage from cost_tracker.db to main database

Pulls token usage data from the cost tracking database and populates
the Run, Post, and ResearchResult models with actual API costs.

This service acts as a bridge between the existing cost_tracker.py
infrastructure and the new token usage fields in the database.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from backend.models import Post, ResearchResult, Run
from backend.utils.logger import logger


class TokenSyncService:
    """Service to sync token usage from cost_tracker.db to main database"""

    def __init__(self, cost_tracker_db_path: Optional[Path] = None):
        """
        Initialize token sync service

        Args:
            cost_tracker_db_path: Path to cost_tracker.db (default: data/cost_tracking.db)
        """
        if cost_tracker_db_path is None:
            # Default path where cost_tracker.py stores data
            cost_tracker_db_path = Path("data/cost_tracking.db")

        self.cost_tracker_db_path = cost_tracker_db_path

        # Verify cost tracker database exists
        if not self.cost_tracker_db_path.exists():
            logger.warning(
                f"Cost tracker database not found at {self.cost_tracker_db_path}. "
                "Token usage tracking will not be available."
            )

    def sync_run_token_usage(self, db: Session, run_id: str, project_id: str) -> Dict[str, int]:
        """
        Sync token usage for a completed run

        Queries cost_tracker.db for all API calls made for this project_id
        during the run's time window and aggregates the token usage.

        Args:
            db: Database session
            run_id: Run ID to sync
            project_id: Project ID to query cost tracker

        Returns:
            Dict with token counts and cost
        """
        # Get the run from database
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            logger.error(f"Run {run_id} not found")
            return {}

        # Define time window for this run
        start_time = run.started_at
        end_time = run.completed_at or datetime.utcnow()

        # Query cost tracker for API calls in this time window
        usage_data = self._get_project_usage(
            project_id=project_id, start_time=start_time, end_time=end_time
        )

        if not usage_data:
            logger.warning(
                f"No cost tracking data found for project {project_id} "
                f"between {start_time} and {end_time}"
            )
            return {}

        # Update run with aggregated token usage
        run.total_input_tokens = usage_data["total_input_tokens"]
        run.total_output_tokens = usage_data["total_output_tokens"]
        run.total_cache_creation_tokens = usage_data["total_cache_creation_tokens"]
        run.total_cache_read_tokens = usage_data["total_cache_read_tokens"]
        run.total_cost_usd = usage_data["total_cost"]

        db.commit()
        db.refresh(run)

        logger.info(
            f"Synced token usage for run {run_id}: "
            f"{usage_data['total_input_tokens']} input, "
            f"{usage_data['total_output_tokens']} output, "
            f"${usage_data['total_cost']:.4f}"
        )

        return usage_data

    def sync_research_token_usage(
        self, db: Session, research_result_id: str, client_id: str
    ) -> Dict[str, int]:
        """
        Sync token usage for a research result

        Queries cost_tracker.db for API calls made during research execution.

        Args:
            db: Database session
            research_result_id: Research result ID to sync
            client_id: Client ID to query cost tracker

        Returns:
            Dict with token counts and cost
        """
        # Get the research result from database
        research = db.query(ResearchResult).filter(ResearchResult.id == research_result_id).first()
        if not research:
            logger.error(f"Research result {research_result_id} not found")
            return {}

        # Define time window (created_at +/- 5 minutes for safety)
        start_time = research.created_at - timedelta(minutes=5)
        end_time = (
            research.created_at
            + timedelta(seconds=research.duration_seconds or 300)
            + timedelta(minutes=5)
        )

        # API calls are tracked under project_id in cost_tracker.db;
        # fall back to client_id only when no project is associated.
        lookup_id = research.project_id or client_id
        usage_data = self._get_project_usage(
            project_id=lookup_id, start_time=start_time, end_time=end_time
        )

        if not usage_data:
            logger.warning(
                f"No cost tracking data found for research {research_result_id} "
                f"(lookup_id={lookup_id}) between {start_time} and {end_time}"
            )
            return {}

        # Update research result with token usage
        research.input_tokens = usage_data["total_input_tokens"]
        research.output_tokens = usage_data["total_output_tokens"]
        research.cache_creation_tokens = usage_data["total_cache_creation_tokens"]
        research.cache_read_tokens = usage_data["total_cache_read_tokens"]
        research.actual_cost_usd = usage_data["total_cost"]

        db.commit()
        db.refresh(research)

        logger.info(
            f"Synced token usage for research {research_result_id}: "
            f"{usage_data['total_input_tokens']} input, "
            f"{usage_data['total_output_tokens']} output, "
            f"${usage_data['total_cost']:.4f}"
        )

        return usage_data

    def estimate_post_token_usage(self, db: Session, run_id: str) -> int:
        """
        Estimate token usage for individual posts in a run

        Distributes the run's total token usage proportionally across posts
        based on word count.

        Args:
            db: Database session
            run_id: Run ID to estimate post usage for

        Returns:
            Number of posts updated
        """
        # Get the run
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run or not run.total_input_tokens:
            logger.warning(
                f"Run {run_id} not found or has no token usage data. "
                "Call sync_run_token_usage first."
            )
            return 0

        # Get all posts for this run
        posts = db.query(Post).filter(Post.run_id == run_id).all()
        if not posts:
            logger.warning(f"No posts found for run {run_id}")
            return 0

        # Calculate total word count
        total_word_count = sum(p.word_count or 0 for p in posts)
        if total_word_count == 0:
            # If no word counts, distribute equally
            posts_updated = 0
            tokens_per_post_input = run.total_input_tokens // len(posts)
            tokens_per_post_output = run.total_output_tokens // len(posts)
            cost_per_post = run.total_cost_usd / len(posts)

            for post in posts:
                post.input_tokens = tokens_per_post_input
                post.output_tokens = tokens_per_post_output
                post.cache_read_tokens = 0  # Can't estimate cache reads per post
                post.cost_usd = cost_per_post
                posts_updated += 1

            db.commit()
            logger.info(f"Estimated token usage for {posts_updated} posts (equal distribution)")
            return posts_updated

        # Distribute proportionally by word count
        posts_updated = 0
        for post in posts:
            if post.word_count:
                proportion = post.word_count / total_word_count

                post.input_tokens = int(run.total_input_tokens * proportion)
                post.output_tokens = int(run.total_output_tokens * proportion)
                post.cache_read_tokens = int((run.total_cache_read_tokens or 0) * proportion)
                post.cost_usd = run.total_cost_usd * proportion
                posts_updated += 1

        db.commit()
        logger.info(f"Estimated token usage for {posts_updated} posts (proportional by word count)")
        return posts_updated

    def _get_project_usage(
        self, project_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, int]:
        """
        Query cost_tracker.db for API calls in time window

        Args:
            project_id: Project ID to query
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Dict with aggregated token counts and cost
        """
        if not self.cost_tracker_db_path.exists():
            return {}

        try:
            conn = sqlite3.connect(self.cost_tracker_db_path)
            cursor = conn.cursor()

            # Query all API calls for this project in time window
            cursor.execute(
                """
                SELECT
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(cache_creation_tokens) as total_cache_creation,
                    SUM(cache_read_tokens) as total_cache_read,
                    SUM(cost) as total_cost
                FROM api_calls
                WHERE project_id = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                """,
                (project_id, start_time.isoformat(), end_time.isoformat()),
            )

            result = cursor.fetchone()
            conn.close()

            if result and result[0] is not None:
                return {
                    "total_input_tokens": int(result[0] or 0),
                    "total_output_tokens": int(result[1] or 0),
                    "total_cache_creation_tokens": int(result[2] or 0),
                    "total_cache_read_tokens": int(result[3] or 0),
                    "total_cost": float(result[4] or 0.0),
                }

            return {}

        except sqlite3.Error as e:
            logger.error(f"Failed to query cost_tracker.db: {e}")
            return {}


# Singleton instance
token_sync_service = TokenSyncService()
