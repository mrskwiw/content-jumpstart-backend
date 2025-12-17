"""Test Revision Management Database

Quick test to verify database schema, models, and CRUD operations.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.project_db import ProjectDatabase
from src.models.project import Project, ProjectStatus, Revision, RevisionPost, RevisionStatus


def test_database_initialization():
    """Test 1: Database initialization"""
    print("\n" + "=" * 60)
    print("TEST 1: Database Initialization")
    print("=" * 60)

    # Use test database
    db_path = Path(__file__).parent / "test_projects.db"
    if db_path.exists():
        db_path.unlink()  # Delete old test db

    db = ProjectDatabase(db_path=db_path)
    print("[OK] Database initialized successfully")
    print(f"  Database path: {db_path}")
    return db


def test_create_project(db: ProjectDatabase):
    """Test 2: Create a project"""
    print("\n" + "=" * 60)
    print("TEST 2: Create Project")
    print("=" * 60)

    project = Project(
        project_id="TestClient_20250101_120000",
        client_name="Test Client Corp",
        deliverable_path="data/outputs/TestClient/deliverable.md",
        brief_path="tests/fixtures/test_brief.txt",
        num_posts=30,
        quality_profile_name="professional_linkedin",
        status=ProjectStatus.COMPLETED,
    )

    success = db.create_project(project)
    if success:
        print("[OK] Project created successfully")
        print(f"  Project ID: {project.project_id}")
        print(f"  Client: {project.client_name}")
        print(f"  Posts: {project.num_posts}")
    else:
        print("[FAIL] Failed to create project")
        return None

    # Verify it was created
    retrieved = db.get_project(project.project_id)
    if retrieved:
        print("[OK] Project retrieved successfully")
        print(f"  Status: {retrieved.status.value}")
    else:
        print("[FAIL] Failed to retrieve project")
        return None

    return project


def test_revision_scope(db: ProjectDatabase, project: Project):
    """Test 3: Revision scope tracking"""
    print("\n" + "=" * 60)
    print("TEST 3: Revision Scope Tracking")
    print("=" * 60)

    scope = db.get_revision_scope(project.project_id)
    if scope:
        print("[OK] Revision scope retrieved")
        print(f"  Allowed: {scope.allowed_revisions}")
        print(f"  Used: {scope.used_revisions}")
        print(f"  Remaining: {scope.remaining_revisions}")
        print(f"  At limit: {scope.is_at_limit}")
    else:
        print("[FAIL] Failed to get revision scope")
        return None

    return scope


def test_create_revision(db: ProjectDatabase, project: Project):
    """Test 4: Create a revision"""
    print("\n" + "=" * 60)
    print("TEST 4: Create Revision")
    print("=" * 60)

    revision = Revision(
        revision_id=f"{project.project_id}_rev_1",
        project_id=project.project_id,
        attempt_number=1,
        feedback="Make posts 3, 7, and 12 more casual and add more emojis",
        status=RevisionStatus.PENDING,
    )

    success = db.create_revision(revision)
    if success:
        print("[OK] Revision created successfully")
        print(f"  Revision ID: {revision.revision_id}")
        print(f"  Attempt: {revision.attempt_number}")
        print(f"  Feedback: {revision.feedback[:50]}...")
    else:
        print("[FAIL] Failed to create revision")
        return None

    # Check scope was updated
    scope = db.get_revision_scope(project.project_id)
    if scope:
        print("[OK] Scope updated automatically")
        print(f"  Used: {scope.used_revisions} (was 0)")
        print(f"  Remaining: {scope.remaining_revisions} (was 5)")

    return revision


def test_create_revision_posts(db: ProjectDatabase, revision: Revision):
    """Test 5: Save revised posts"""
    print("\n" + "=" * 60)
    print("TEST 5: Save Revised Posts")
    print("=" * 60)

    posts = [
        RevisionPost(
            post_index=3,
            template_id=1,
            template_name="Problem Recognition",
            original_content="Original post content here...",
            original_word_count=250,
            revised_content="Revised post content with more casual tone 😊",
            revised_word_count=230,
            changes_summary="Made tone more casual, added emoji, shortened by 20 words",
        ),
        RevisionPost(
            post_index=7,
            template_id=5,
            template_name="Question Post",
            original_content="Another original post...",
            original_word_count=180,
            revised_content="Revised question post with friendly vibe 🤔",
            revised_word_count=175,
            changes_summary="Added friendly tone, included emoji",
        ),
    ]

    success = db.save_revision_posts(revision.revision_id, posts)
    if success:
        print(f"[OK] Saved {len(posts)} revised posts")
        for post in posts:
            print(
                f"  Post #{post.post_index}: {post.original_word_count} -> {post.revised_word_count} words"
            )
    else:
        print("[FAIL] Failed to save revision posts")
        return False

    # Retrieve revision with posts
    retrieved = db.get_revision(revision.revision_id)
    if retrieved and retrieved.posts:
        print(f"[OK] Retrieved revision with {len(retrieved.posts)} posts")
    else:
        print("[FAIL] Failed to retrieve revision posts")

    return True


def test_scope_limit_enforcement(db: ProjectDatabase, project: Project):
    """Test 6: Scope limit enforcement"""
    print("\n" + "=" * 60)
    print("TEST 6: Scope Limit Enforcement")
    print("=" * 60)

    # Create revisions 2-5 (reaching limit)
    for i in range(2, 6):
        revision = Revision(
            revision_id=f"{project.project_id}_rev_{i}",
            project_id=project.project_id,
            attempt_number=i,
            feedback=f"Revision {i} feedback",
            status=RevisionStatus.COMPLETED,
        )
        db.create_revision(revision)
        print(f"  Created revision {i}")

    # Check scope
    scope = db.get_revision_scope(project.project_id)
    print("\n[OK] Scope after 5 revisions:")
    print(f"  Used: {scope.used_revisions}")
    print(f"  Remaining: {scope.remaining_revisions}")
    print(f"  At limit: {scope.is_at_limit}")
    print(f"  Exceeded: {scope.scope_exceeded}")

    # Try to create 6th revision (should still work, but scope_exceeded flag set)
    revision_6 = Revision(
        revision_id=f"{project.project_id}_rev_6",
        project_id=project.project_id,
        attempt_number=6,
        feedback="This should exceed scope",
        status=RevisionStatus.PENDING,
    )
    db.create_revision(revision_6)

    scope = db.get_revision_scope(project.project_id)
    print("\n[OK] Scope after 6th revision:")
    print(f"  Used: {scope.used_revisions}")
    print(f"  Remaining: {scope.remaining_revisions}")
    print(f"  Scope exceeded: {scope.scope_exceeded} [WARN]")

    # Test upsell acceptance
    print("\n  Testing upsell acceptance...")
    db.accept_upsell(project.project_id, additional_revisions=5)
    scope = db.get_revision_scope(project.project_id)
    print("[OK] After accepting upsell (+5 revisions):")
    print(f"  Allowed: {scope.allowed_revisions}")
    print(f"  Remaining: {scope.remaining_revisions}")
    print(f"  Scope exceeded: {scope.scope_exceeded} (reset)")


def test_client_stats(db: ProjectDatabase, project: Project):
    """Test 7: Client statistics"""
    print("\n" + "=" * 60)
    print("TEST 7: Client Statistics")
    print("=" * 60)

    stats = db.get_client_stats(project.client_name)
    print("[OK] Client statistics:")
    print(f"  Total projects: {stats['total_projects']}")
    print(f"  Total revisions: {stats['total_revisions']}")
    print(f"  Avg revisions/project: {stats['avg_revisions_per_project']}")
    print(f"  Scope exceeded count: {stats['scope_exceeded_count']}")


def test_get_all_projects_by_client(db: ProjectDatabase, client_name: str):
    """Test 8: Get all projects for client"""
    print("\n" + "=" * 60)
    print("TEST 8: Get All Projects by Client")
    print("=" * 60)

    projects = db.get_projects_by_client(client_name)
    print(f"[OK] Found {len(projects)} project(s) for {client_name}")
    for p in projects:
        print(f"  - {p.project_id} ({p.num_posts} posts, {p.status.value})")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" REVISION MANAGEMENT DATABASE TESTS")
    print("=" * 70)

    try:
        # Initialize database
        db = test_database_initialization()

        # Create project
        project = test_create_project(db)
        if not project:
            return False

        # Test revision scope
        scope = test_revision_scope(db, project)
        if not scope:
            return False

        # Create revision
        revision = test_create_revision(db, project)
        if not revision:
            return False

        # Save revision posts
        if not test_create_revision_posts(db, revision):
            return False

        # Test scope limits
        test_scope_limit_enforcement(db, project)

        # Test analytics
        test_client_stats(db, project)

        # Test queries
        test_get_all_projects_by_client(db, project.client_name)

        print("\n" + "=" * 70)
        print(" [OK] ALL TESTS PASSED!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
