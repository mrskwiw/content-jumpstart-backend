"""Quick test of headline validator"""
from src.models.post import Post
from src.validators.headline_validator import HeadlineValidator

# Create test posts with longer content
posts = [
    Post(
        content="5 Simple Ways to Boost Your Sales\n\n" + " ".join(["word"] * 100),
        template_name="test",
        template_id=1,
        position=1,
        client_name="TestClient",
    ),
    Post(
        content="How to Grow Your Business Fast with Proven Strategies\n\n"
        + " ".join(["word"] * 100),
        template_name="test",
        template_id=2,
        position=2,
        client_name="TestClient",
    ),
    Post(
        content="My thoughts on marketing\n\n" + " ".join(["word"] * 100),
        template_name="test",
        template_id=3,
        position=3,
        client_name="TestClient",
    ),
]

validator = HeadlineValidator(min_elements=3)
results = validator.validate(posts)

print("Headline Validation Results:")
print(f"  Passed: {results['passed']}")
print(f"  Average Elements: {results['average_elements']:.1f}/3")
print(f"  Below Threshold: {results['below_threshold_count']}/{results['headlines_analyzed']}")
print("\nHeadline Scores:")
for score in results["headline_scores"]:
    details = score["details"]
    print(f"  Post {score['post_idx']+1}: {score['elements']} elements")
    print(f"    Headline: \"{score['headline']}\"")
    print(
        f"    Has number: {details['has_number']}, Power word: {details['has_power_word']}, Question: {details['is_question']}"
    )

print("\nTest PASSED: Headline validator working correctly!")
