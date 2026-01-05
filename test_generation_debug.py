"""
Debug script to test content generation with template quantities
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform

async def test_generation():
    """Test basic generation with template quantities"""
    print("=" * 60)
    print("Testing Content Generation with Template Quantities")
    print("=" * 60)

    # Create a simple client brief
    brief = ClientBrief(
        company_name="Test Company Inc",
        business_description="A software company providing business solutions",
        ideal_customer="Small to medium businesses",
        main_problem_solved="Streamlining business processes",
        platforms=[Platform.LINKEDIN],
        tone_preference="Professional",
        customer_pain_points=["Complex workflows", "Time management"],
        customer_questions=["How to improve efficiency?"],
    )

    # Template quantities - just 2 posts for testing
    template_quantities = {1: 1, 2: 1}  # 1 post from template 1, 1 from template 2

    print(f"\nClient Brief: {brief.company_name}")
    print(f"Template Quantities: {template_quantities}")
    print(f"Expected Posts: {sum(template_quantities.values())}")

    # Initialize generator
    print("\nInitializing ContentGeneratorAgent...")
    try:
        generator = ContentGeneratorAgent()
        print("✓ Generator initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize generator: {e}")
        return

    # Check template loader
    print(f"\nTemplate Loader has {len(generator.template_loader.templates)} templates loaded")
    if len(generator.template_loader.templates) == 0:
        print("✗ WARNING: No templates loaded!")
        return

    # Test getting templates by ID
    print("\nTesting template retrieval:")
    for template_id in template_quantities.keys():
        template = generator.template_loader.get_template_by_id(template_id)
        if template:
            print(f"✓ Template {template_id}: {template.name}")
        else:
            print(f"✗ Template {template_id}: NOT FOUND")

    # Generate posts
    print("\nGenerating posts...")
    try:
        posts = await generator.generate_posts_async(
            client_brief=brief,
            template_quantities=template_quantities,
            platform=Platform.LINKEDIN,
            randomize=False,
            max_concurrent=2,
            use_client_memory=False,
        )

        print(f"\n✓ Generation completed!")
        print(f"  Posts generated: {len(posts)}")
        print(f"  Expected: {sum(template_quantities.values())}")

        if len(posts) == 0:
            print("\n✗ ERROR: No posts generated!")
            print("  This indicates a problem with the Anthropic API or generation logic")
        else:
            print("\n✓ SUCCESS: Posts generated correctly!")
            for idx, post in enumerate(posts, 1):
                print(f"\n  Post {idx}:")
                print(f"    Template: {post.template_name}")
                print(f"    Word Count: {post.word_count}")
                print(f"    Content Preview: {post.content[:100]}...")

    except Exception as e:
        print(f"\n✗ Generation failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation())
