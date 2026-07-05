"""
Factory functions for creating test model instances.

Provides consistent test data across all test suites and reduces boilerplate
in test files.

Usage:
    from tests.fixtures.model_factories import create_test_user, create_test_client

    def test_something():
        user = create_test_user(email="custom@example.com")
        client = create_test_client(user_id=user["id"], name="Custom Client")
"""

from datetime import datetime, timedelta
from typing import List, Optional
import uuid


# ==================== User Factories ====================


def create_test_user(
    email: str = "test@example.com",
    password: str = "testpass123",
    full_name: str = "Test User",
    is_active: bool = True,
    is_superuser: bool = False,
    **kwargs,
) -> dict:
    """
    Create test user data.

    Args:
        email: User email address
        password: Plain text password (will be hashed by system)
        full_name: User's full name
        is_active: Whether user account is active
        is_superuser: Whether user has admin privileges
        **kwargs: Additional fields to override

    Returns:
        Dict with user data
    """
    return {
        "id": f"user-{uuid.uuid4().hex[:12]}",
        "email": email,
        "hashed_password": password,  # Will be hashed by system
        "full_name": full_name,
        "is_active": is_active,
        "is_superuser": is_superuser,
        "created_at": datetime.utcnow(),
        **kwargs,
    }


# ==================== Client Factories ====================


def create_test_client(
    name: str = "Test Client", user_id: Optional[str] = None, email: Optional[str] = None, **kwargs
) -> dict:
    """
    Create test client data.

    Args:
        name: Client company name
        user_id: ID of user who owns this client
        email: Client contact email
        **kwargs: Additional fields to override

    Returns:
        Dict with client data
    """
    return {
        "id": f"client-{uuid.uuid4().hex[:12]}",
        "user_id": user_id or f"user-{uuid.uuid4().hex[:12]}",
        "name": name,
        "email": email,
        "business_description": "We provide innovative solutions for modern businesses looking to scale efficiently.",
        "ideal_customer": "Small to medium-sized businesses with 10-50 employees in the technology sector.",
        "main_problem_solved": "Manual workflows and inefficient processes that slow down growth.",
        "tone_preference": "professional",
        "platforms": ["linkedin", "twitter"],
        "customer_pain_points": [
            "Wasting time on manual data entry",
            "Poor team collaboration",
            "Lack of actionable insights",
        ],
        "customer_questions": [
            "How can we automate our workflows?",
            "What metrics should we track?",
        ],
        "created_at": datetime.utcnow(),
        **kwargs,
    }


# ==================== Project Factories ====================


def create_test_project(
    name: str = "Test Project",
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: str = "draft",
    num_posts: int = 30,
    target_platform: str = "blog",
    **kwargs,
) -> dict:
    """
    Create test project data.

    Args:
        name: Project name
        client_id: ID of client this project belongs to
        user_id: ID of user who owns this project
        status: Project status (draft/processing/qa_review/ready/delivered)
        num_posts: Number of posts to generate
        target_platform: Target platform for generation (default: blog)
        **kwargs: Additional fields to override

    Returns:
        Dict with project data
    """
    return {
        "id": f"proj-{uuid.uuid4().hex[:12]}",
        "client_id": client_id or f"client-{uuid.uuid4().hex[:12]}",
        "user_id": user_id or f"user-{uuid.uuid4().hex[:12]}",
        "name": name,
        "status": status,
        "num_posts": num_posts,
        "platforms": ["linkedin", "twitter"],
        "target_platform": target_platform,  # NEW: Target platform for generation
        "templates": ["1", "2", "9"],  # Legacy field
        "template_quantities": {"1": 10, "2": 10, "9": 10},  # New pricing model
        "price_per_post": 40.0,
        "research_price_per_post": 0.0,
        "total_price": num_posts * 40.0,
        "tone": "professional",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        **kwargs,
    }


# ==================== Brief Factories ====================


def create_test_brief(project_id: Optional[str] = None, source: str = "paste", **kwargs) -> dict:
    """
    Create test client brief data.

    Args:
        project_id: ID of project this brief belongs to
        source: Source of brief (upload/paste)
        **kwargs: Additional fields to override

    Returns:
        Dict with brief data
    """
    content = """Company Name: Acme Corp

Business Description: We provide cloud-based project management software for small businesses.

Ideal Customer: Small business owners with 5-20 employees who need better team collaboration.

Main Problem Solved: Manual workflows and scattered communication across multiple tools.

Customer Pain Points:
- Wasting time on manual data entry
- Poor team collaboration
- Lack of visibility into project progress

Customer Questions:
- How can we improve productivity without adding complexity?
- What tools integrate with our existing stack?

Platform Preferences: LinkedIn, Twitter

Brand Voice: Professional yet approachable, data-driven
"""

    return {
        "id": f"brief-{uuid.uuid4().hex[:12]}",
        "project_id": project_id or f"proj-{uuid.uuid4().hex[:12]}",
        "content": content,
        "source": source,
        "file_path": None if source == "paste" else "/path/to/brief.txt",
        "parsed_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        **kwargs,
    }


# ==================== Post Factories ====================


def create_test_post(
    project_id: Optional[str] = None,
    run_id: Optional[str] = None,
    template_id: int = 1,
    template_name: str = "Problem Recognition",
    platform: str = "linkedin",
    status: str = "approved",
    **kwargs,
) -> dict:
    """
    Create test post data.

    Args:
        project_id: ID of project this post belongs to
        run_id: ID of generation run
        template_id: Template number (1-15)
        template_name: Template name
        platform: Target platform
        status: Post status (approved/flagged/regenerating)
        **kwargs: Additional fields to override

    Returns:
        Dict with post data
    """
    content = """Here's a test post about productivity:

Most teams waste 30% of their time switching between apps.

Our research shows that small businesses use 12+ different tools daily.
- 45 minutes lost to context switching
- 3 hours per week in status meetings
- $15K annual cost per employee

The solution? Consolidate your workflow.

What's your biggest productivity killer? 👇

[CTA: Try our free workflow assessment]"""

    return {
        "id": f"post-{uuid.uuid4().hex[:12]}",
        "project_id": project_id or f"proj-{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "template_id": template_id,
        "template_name": template_name,
        "content": content,
        "target_platform": platform,
        "word_count": len(content.split()),
        "has_cta": True,
        "readability_score": 65.5,
        "status": status,
        "flags": [] if status == "approved" else ["too_short"],
        "variant": 0,
        "created_at": datetime.utcnow(),
        **kwargs,
    }


def create_multiple_test_posts(
    count: int = 30, project_id: Optional[str] = None, run_id: Optional[str] = None, **kwargs
) -> List[dict]:
    """
    Create multiple test posts.

    Args:
        count: Number of posts to create
        project_id: ID of project (same for all posts)
        run_id: ID of generation run (same for all posts)
        **kwargs: Additional fields to override

    Returns:
        List of post dicts
    """
    posts = []
    for i in range(count):
        post = create_test_post(
            project_id=project_id, run_id=run_id, template_id=(i % 15) + 1, **kwargs
        )
        posts.append(post)
    return posts


# ==================== Run Factories ====================


def create_test_run(
    project_id: Optional[str] = None, status: str = "completed", is_batch: bool = True, **kwargs
) -> dict:
    """
    Create test generation run data.

    Args:
        project_id: ID of project this run belongs to
        status: Run status (pending/running/succeeded/failed)
        is_batch: Whether this is a batch generation
        **kwargs: Additional fields to override

    Returns:
        Dict with run data
    """
    run_data = {
        "id": f"run-{uuid.uuid4().hex[:12]}",
        "project_id": project_id or f"proj-{uuid.uuid4().hex[:12]}",
        "is_batch": is_batch,
        "status": status,
        "started_at": datetime.utcnow() - timedelta(minutes=5),
        "completed_at": None,
        "logs": [],
        "error_message": None,
        "created_at": datetime.utcnow() - timedelta(minutes=5),
        **kwargs,
    }

    if status == "completed":
        run_data["completed_at"] = datetime.utcnow()
        run_data["logs"] = [
            {"timestamp": "2024-01-01T10:00:00", "message": "Starting generation"},
            {"timestamp": "2024-01-01T10:05:00", "message": "Generation complete"},
        ]
    elif status == "failed":
        run_data["completed_at"] = datetime.utcnow()
        run_data["error_message"] = "Mock error: Generation failed"
        run_data["logs"] = [
            {"timestamp": "2024-01-01T10:00:00", "message": "Starting generation"},
            {"timestamp": "2024-01-01T10:02:00", "message": "Error encountered"},
        ]
    elif status == "running":
        run_data["logs"] = [
            {"timestamp": "2024-01-01T10:00:00", "message": "Starting generation"},
            {"timestamp": "2024-01-01T10:03:00", "message": "Processing posts 1-10"},
        ]

    return run_data


# ==================== Deliverable Factories ====================


def create_test_deliverable(
    project_id: Optional[str] = None,
    client_id: Optional[str] = None,
    run_id: Optional[str] = None,
    format: str = "txt",
    status: str = "ready",
    **kwargs,
) -> dict:
    """
    Create test deliverable data.

    Args:
        project_id: ID of project this deliverable belongs to
        client_id: ID of client
        run_id: ID of generation run
        format: File format (txt/docx/pdf)
        status: Deliverable status (draft/ready/delivered)
        **kwargs: Additional fields to override

    Returns:
        Dict with deliverable data
    """
    return {
        "id": f"deliv-{uuid.uuid4().hex[:12]}",
        "project_id": project_id or f"proj-{uuid.uuid4().hex[:12]}",
        "client_id": client_id or f"client-{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "format": format,
        "path": f"/data/outputs/TestClient/TestClient_deliverable.{format}",
        "status": status,
        "file_size_bytes": 15360 if format == "txt" else 45120,
        "checksum": "abc123def456",
        "created_at": datetime.utcnow(),
        "delivered_at": datetime.utcnow() if status == "delivered" else None,
        "proof_url": "https://example.com/proof" if status == "delivered" else None,
        "proof_notes": "Delivered via email" if status == "delivered" else None,
        **kwargs,
    }


# ==================== Convenience Functions ====================


def create_full_project_data(
    user_email: str = "test@example.com",
    client_name: str = "Test Client",
    project_name: str = "Test Project",
    num_posts: int = 30,
) -> dict:
    """
    Create a complete set of related test data.

    This creates a user, client, project, brief, run, posts, and deliverable
    all linked together with proper relationships.

    Args:
        user_email: Email for test user
        client_name: Name for test client
        project_name: Name for test project
        num_posts: Number of posts to generate

    Returns:
        Dict with all related models
    """
    user = create_test_user(email=user_email)
    client = create_test_client(name=client_name, user_id=user["id"])
    project = create_test_project(
        name=project_name, client_id=client["id"], user_id=user["id"], num_posts=num_posts
    )
    brief = create_test_brief(project_id=project["id"])
    run = create_test_run(project_id=project["id"], status="completed")
    posts = create_multiple_test_posts(count=num_posts, project_id=project["id"], run_id=run["id"])
    deliverable = create_test_deliverable(
        project_id=project["id"], client_id=client["id"], run_id=run["id"]
    )

    return {
        "user": user,
        "client": client,
        "project": project,
        "brief": brief,
        "run": run,
        "posts": posts,
        "deliverable": deliverable,
    }
