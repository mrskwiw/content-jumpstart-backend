"""Test script for client memory database operations"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.project_db import ProjectDatabase
from models.client_memory import FeedbackTheme, VoiceSample


def test_client_memory_operations():
    """Test all client memory database operations"""

    print("=" * 60)
    print("Testing Client Memory Database Operations")
    print("=" * 60)

    db_path = Path(__file__).parent / "data" / "projects.db"
    db = ProjectDatabase(db_path)

    test_client = "TestClient_MemoryTest"

    print("\n[TEST 1] Get or Create Client Memory")
    print("-" * 60)
    memory = db.get_or_create_client_memory(test_client)
    print(f"✓ Created new memory for: {memory.client_name}")
    print(f"  - Total projects: {memory.total_projects}")
    print(f"  - Is repeat client: {memory.is_repeat_client}")

    print("\n[TEST 2] Add Project and Update Memory")
    print("-" * 60)
    memory.add_project(num_posts=30, project_value=1800.0)
    success = db.update_client_memory(memory)
    print(f"✓ Updated memory: {success}")
    print(f"  - Total projects: {memory.total_projects}")
    print(f"  - Total posts: {memory.total_posts_generated}")
    print(f"  - Lifetime value: ${memory.lifetime_value}")
    print(f"  - Is repeat client: {memory.is_repeat_client}")

    print("\n[TEST 3] Update Template Preferences")
    print("-" * 60)
    memory.update_template_preference(template_id=1, revision_rate=0.15)
    memory.update_template_preference(template_id=6, revision_rate=0.60)
    success = db.update_client_memory(memory)
    print(f"✓ Updated template preferences: {success}")
    print(f"  - Preferred templates: {memory.preferred_templates}")
    print(f"  - Avoided templates: {memory.avoided_templates}")
    print(f"  - Template performance: {memory.template_performance}")

    print("\n[TEST 4] Update Voice Adjustments")
    print("-" * 60)
    memory.update_voice_adjustment("tone", "more_casual")
    memory.update_voice_adjustment("length", "shorter")
    success = db.update_client_memory(memory)
    print(f"✓ Updated voice adjustments: {success}")
    print(f"  - Voice adjustments: {memory.voice_adjustments}")

    print("\n[TEST 5] Store Voice Sample")
    print("-" * 60)
    voice_sample = VoiceSample(
        client_name=test_client,
        project_id=f"{test_client}_20251201_120000",
        average_readability=65.5,
        voice_archetype="Expert",
        dominant_tone="professional_friendly",
        average_word_count=220,
        question_usage_rate=0.4,
        common_hooks=["Ever wonder why...", "Here's the thing about..."],
        common_transitions=["The key is...", "But here's what matters..."],
        common_ctas=["What's your take?", "Drop a comment if..."],
        key_phrases=["data-driven", "actionable insights", "bottom line"],
    )
    success = db.store_voice_sample(voice_sample)
    print(f"✓ Stored voice sample: {success}")
    print(f"  - Project: {voice_sample.project_id}")
    print(f"  - Archetype: {voice_sample.voice_archetype}")
    print(f"  - Readability: {voice_sample.average_readability}")

    print("\n[TEST 6] Retrieve Voice Samples")
    print("-" * 60)
    samples = db.get_voice_samples(test_client, limit=5)
    print(f"✓ Retrieved {len(samples)} voice samples")
    for sample in samples:
        print(
            f"  - {sample.project_id}: {sample.voice_archetype}, readability={sample.average_readability}"
        )

    print("\n[TEST 7] Record Feedback Themes")
    print("-" * 60)
    theme1 = FeedbackTheme(theme_type="tone", feedback_phrase="more casual")
    success = db.record_feedback_theme(test_client, theme1)
    print(f"✓ Recorded theme 'tone: more casual': {success}")

    theme2 = FeedbackTheme(theme_type="length", feedback_phrase="too long")
    success = db.record_feedback_theme(test_client, theme2)
    print(f"✓ Recorded theme 'length: too long': {success}")

    # Record same theme again to test increment
    success = db.record_feedback_theme(test_client, theme1)
    print(f"✓ Recorded theme 'tone: more casual' again (should increment): {success}")

    print("\n[TEST 8] Retrieve Feedback Themes")
    print("-" * 60)
    themes = db.get_feedback_themes(test_client)
    print(f"✓ Retrieved {len(themes)} feedback themes")
    for theme in themes:
        print(
            f"  - {theme.theme_type}: '{theme.feedback_phrase}' (occurred {theme.occurrence_count}x)"
        )

    print("\n[TEST 9] Update Template Performance")
    print("-" * 60)
    # Template 1: used, not revised (good)
    success = db.update_template_performance(
        test_client, template_id=1, was_revised=False, quality_score=8.5
    )
    print(f"✓ Template 1 (kept): {success}")

    # Template 1 used again, revised this time
    success = db.update_template_performance(
        test_client, template_id=1, was_revised=True, quality_score=7.0
    )
    print(f"✓ Template 1 (revised): {success}")

    # Template 6: used and revised (problematic)
    success = db.update_template_performance(
        test_client, template_id=6, was_revised=True, quality_score=5.5
    )
    print(f"✓ Template 6 (revised): {success}")

    print("\n[TEST 10] Retrieve Template Performance")
    print("-" * 60)
    perf = db.get_template_performance(test_client)
    print(f"✓ Retrieved performance for {len(perf)} templates")
    for template_id, data in perf.items():
        print(f"  - Template {template_id}:")
        print(
            f"    Usage: {data['usage_count']}, Revisions: {data['revision_count']}, Rate: {data['revision_rate']:.2f}"
        )
        print(
            f"    Avg Quality: {data['average_quality_score']:.1f}, Kept: {data['client_kept_count']}"
        )

    print("\n[TEST 11] Get All Client Names")
    print("-" * 60)
    client_names = db.get_all_client_names()
    print(f"✓ Retrieved {len(client_names)} client names")
    for name in client_names[:5]:  # Show first 5
        print(f"  - {name}")

    print("\n[TEST 12] Retrieve Updated Memory")
    print("-" * 60)
    updated_memory = db.get_client_memory(test_client)
    print("✓ Retrieved updated memory")
    print(f"  - Total projects: {updated_memory.total_projects}")
    print(f"  - Total posts: {updated_memory.total_posts_generated}")
    print(f"  - Lifetime value: ${updated_memory.lifetime_value}")
    print(f"  - Preferred templates: {updated_memory.preferred_templates}")
    print(f"  - Avoided templates: {updated_memory.avoided_templates}")
    print(f"  - Voice adjustments: {updated_memory.voice_adjustments}")
    print(f"  - Avg revisions/project: {updated_memory.avg_revisions_per_project}")
    print(f"  - High value client: {updated_memory.is_high_value_client}")

    print("\n" + "=" * 60)
    print("All Tests Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_client_memory_operations()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
