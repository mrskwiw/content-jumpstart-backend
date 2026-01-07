"""
Deliverable service for extended operations.

Provides functions for fetching deliverable details including
file previews, related posts, and QA summaries.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models.post import Post
from backend.schemas.deliverable import DeliverableDetailResponse, PostSummary, QASummary
from backend.services import crud
from backend.utils.logger import logger


def get_file_preview(file_path: Path, max_chars: int = 5000) -> Tuple[Optional[str], bool]:
    """
    Read file preview (first max_chars characters).

    Args:
        file_path: Path to the file
        max_chars: Maximum number of characters to read

    Returns:
        Tuple of (content, was_truncated)
        - content: File content or None if file doesn't exist
        - was_truncated: True if content was truncated
    """
    if not file_path.exists():
        logger.warning(f"File not found for preview: {file_path}")
        return None, False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(max_chars + 1)
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars]
            return content, truncated
    except UnicodeDecodeError:
        # File is binary or has encoding issues
        logger.warning(f"Unable to decode file as UTF-8: {file_path}")
        return "Unable to preview this file (binary or encoding issue)", False
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        return f"Error reading file: {str(e)}", False


def calculate_qa_summary(posts: List[Post]) -> Optional[QASummary]:
    """
    Calculate QA summary statistics from a list of posts.

    Args:
        posts: List of Post objects

    Returns:
        QASummary object with calculated statistics, or None if no posts
    """
    if not posts:
        return None

    total = len(posts)
    flagged = sum(1 for p in posts if p.status == 'flagged')
    approved = sum(1 for p in posts if p.status == 'approved')

    # Calculate averages for readability
    readability_scores = [p.readability_score for p in posts if p.readability_score is not None]
    avg_readability = sum(readability_scores) / len(readability_scores) if readability_scores else None

    # Calculate averages for word count
    word_counts = [p.word_count for p in posts if p.word_count is not None]
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else None

    # Calculate CTA percentage
    posts_with_cta = sum(1 for p in posts if p.has_cta)
    cta_percentage = (posts_with_cta / total * 100) if total > 0 else None

    # Find most common flags
    all_flags = []
    for p in posts:
        if p.flags:
            all_flags.extend(p.flags)

    flag_counts = Counter(all_flags)
    common_flags = [flag for flag, count in flag_counts.most_common(5)]

    return QASummary(
        avg_readability=avg_readability,
        avg_word_count=avg_word_count,
        total_posts=total,
        flagged_count=flagged,
        approved_count=approved,
        cta_percentage=cta_percentage,
        common_flags=common_flags,
    )


def get_deliverable_details(db: Session, deliverable_id: str) -> Optional[DeliverableDetailResponse]:
    """
    Get deliverable with extended details including:
    - File preview (first 5000 characters)
    - Related posts (from same run)
    - QA summary statistics
    - File modification timestamp

    Args:
        db: Database session
        deliverable_id: Deliverable ID

    Returns:
        DeliverableDetailResponse object or None if not found
    """
    # Get base deliverable
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        logger.warning(f"Deliverable not found: {deliverable_id}")
        return None

    # Get file preview
    file_path = Path("data/outputs") / deliverable.path
    file_preview, was_truncated = get_file_preview(file_path)

    # Get file modified time
    file_modified_at = None
    if file_path.exists():
        try:
            file_modified_at = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        except Exception as e:
            logger.error(f"Error getting file modified time for {file_path}: {e}")

    # Get posts if run_id exists
    posts_summaries = []
    qa_summary = None
    if deliverable.run_id:
        run_posts = db.query(Post).filter(Post.run_id == deliverable.run_id).all()

        # Create post summaries
        posts_summaries = [
            PostSummary(
                id=p.id,
                template_name=p.template_name,
                word_count=p.word_count,
                readability_score=p.readability_score,
                status=p.status,
                flags=p.flags,
                content_preview=p.content[:150] + "..." if len(p.content) > 150 else p.content
            )
            for p in run_posts
        ]

        # Calculate QA summary
        qa_summary = calculate_qa_summary(run_posts)

        logger.info(f"Found {len(run_posts)} posts for deliverable {deliverable_id}")

    # Build response
    return DeliverableDetailResponse(
        id=deliverable.id,
        project_id=deliverable.project_id,
        client_id=deliverable.client_id,
        run_id=deliverable.run_id,
        format=deliverable.format,
        path=deliverable.path,
        status=deliverable.status,
        created_at=deliverable.created_at,
        delivered_at=deliverable.delivered_at,
        proof_url=deliverable.proof_url,
        proof_notes=deliverable.proof_notes,
        checksum=deliverable.checksum,
        file_size_bytes=deliverable.file_size_bytes,
        file_preview=file_preview,
        file_preview_truncated=was_truncated,
        posts=posts_summaries,
        qa_summary=qa_summary,
        file_modified_at=file_modified_at,
    )
