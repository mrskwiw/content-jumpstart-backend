"""
Manual test script for web search integration.

Run this to verify Brave Search or Tavily API is working correctly.

Usage:
    python tests/manual/test_web_search.py
"""

import sys
from pathlib import Path

# Fix Windows console encoding
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = Path(__file__).parent.parent.parent / "project"
sys.path.insert(0, str(project_root))

from src.utils.web_search import get_search_client, WebSearchClient


def test_auto_detection():
    """Test automatic provider detection"""
    print("=" * 60)
    print("TEST 1: Auto-Detection")
    print("=" * 60)

    client = get_search_client()
    print(f"✓ Provider: {client.provider}")
    print(f"✓ Has API key: {bool(client.api_key)}")

    if client.provider == "stub":
        print("\n⚠️  WARNING: Using stub mode (no real API calls)")
        print("   Set BRAVE_API_KEY or TAVILY_API_KEY to use real search")
    else:
        print(f"\n✓ Using real search provider: {client.provider}")

    print()


def test_basic_search():
    """Test basic search functionality"""
    print("=" * 60)
    print("TEST 2: Basic Search")
    print("=" * 60)

    client = get_search_client()
    response = client.search("Python programming", max_results=5)

    print(f"✓ Query: {response.query}")
    print(f"✓ Results: {response.total_results}")
    print(f"✓ Search time: {response.search_time_ms:.1f}ms")
    print(f"✓ Provider: {response.results[0].source if response.results else 'none'}")

    print("\nFirst 3 results:")
    for i, result in enumerate(response.results[:3], 1):
        print(f"\n{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   Snippet: {result.snippet[:80]}...")

    print()


def test_competitor_search():
    """Test competitor-specific search"""
    print("=" * 60)
    print("TEST 3: Competitor Search")
    print("=" * 60)

    client = get_search_client()
    response = client.search_competitors(
        business_description="We help B2B SaaS companies reduce customer churn through AI-powered analytics",
        industry="B2B SaaS",
        location="United States",
    )

    print(f"✓ Query: {response.query}")
    print(f"✓ Results: {response.total_results}")

    print("\nTop 5 competitor-related results:")
    for i, result in enumerate(response.results[:5], 1):
        print(f"\n{i}. {result.title}")
        print(f"   {result.url}")

    print()


def test_all_providers():
    """Test each provider explicitly"""
    print("=" * 60)
    print("TEST 4: Provider-Specific Tests")
    print("=" * 60)

    providers = ["stub", "brave", "tavily"]

    for provider in providers:
        print(f"\n--- Testing {provider.upper()} ---")
        try:
            client = WebSearchClient(provider=provider)
            response = client.search("test query", max_results=3)

            print(f"✓ Provider initialized: {client.provider}")
            print(f"✓ Results returned: {len(response.results)}")

            if response.results:
                print(f"✓ Sample result: {response.results[0].title[:50]}...")

            if client.provider == "stub":
                print("⚠️  Note: Stub mode active (expected if no API key)")

        except Exception as e:
            print(f"✗ Error: {str(e)}")

    print()


def test_error_handling():
    """Test error handling and fallback"""
    print("=" * 60)
    print("TEST 5: Error Handling")
    print("=" * 60)

    # Test with invalid API key
    client = WebSearchClient(provider="brave", api_key="invalid_key_12345")
    response = client.search("test", max_results=3)

    print(f"✓ Handled invalid API key gracefully")
    print(f"✓ Fell back to: {response.results[0].source if response.results else 'no results'}")
    print(f"✓ Results returned: {len(response.results)}")

    print()


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WEB SEARCH INTEGRATION TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_auto_detection()
        test_basic_search()
        test_competitor_search()
        test_all_providers()
        test_error_handling()

        print("=" * 60)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 60)

        # Summary
        client = get_search_client()
        print("\nSUMMARY:")
        print(f"  Active Provider: {client.provider}")

        if client.provider == "stub":
            print("\n  ⚠️  RECOMMENDATION:")
            print("  Configure BRAVE_API_KEY or TAVILY_API_KEY for production use")
            print("  See: project/docs/WEB_SEARCH_INTEGRATION.md")
        else:
            print(f"\n  ✓ Production-ready with {client.provider} API")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
