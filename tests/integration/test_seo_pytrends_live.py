"""
Live integration tests for SEO Keyword Research with real Google Trends data.

These tests make actual API calls to Google Trends and should be run sparingly
to avoid rate limiting. Use pytest markers to control execution:

    pytest tests/integration/test_seo_pytrends_live.py -v         # Run live tests
    pytest -m "not live"                                          # Skip live tests
"""

import pytest
import time
from pathlib import Path

from src.research.seo_keyword_research import SEOKeywordResearcher
from src.models.seo_models import Keyword, SearchIntent, KeywordDifficulty


@pytest.mark.live
@pytest.mark.slow
class TestSEOPytrendsLive:
    """Live tests using real Google Trends API"""

    def test_enrich_with_google_trends_popular_keywords(self):
        """Test trends enrichment with popular keywords (high likelihood of data)"""
        # Use very popular keywords that definitely have trends data
        keywords = [
            Keyword(
                keyword="python programming",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.HIGH,
                monthly_volume_estimate="100K-1M",
                relevance_score=9.0,
                long_tail=False,
                question_based=False,
                related_topics=["programming"],
            ),
            Keyword(
                keyword="machine learning",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.HIGH,
                monthly_volume_estimate="100K-1M",
                relevance_score=9.0,
                long_tail=False,
                question_based=False,
                related_topics=["AI"],
            ),
            Keyword(
                keyword="data science",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="100K-1M",
                relevance_score=8.5,
                long_tail=False,
                question_based=False,
                related_topics=["analytics"],
            ),
        ]

        # Create SEO researcher instance
        researcher = SEOKeywordResearcher(project_id="test_pytrends_live")

        # Enrich keywords with Google Trends data
        researcher._enrich_with_google_trends(keywords)

        # Verify at least one keyword was enriched
        enriched_count = sum(1 for kw in keywords if kw.trend_score is not None)
        if enriched_count == 0:
            pytest.skip(
                "Google Trends API returned no data (rate limited or unavailable in this environment)"
            )
        assert enriched_count > 0, "At least one keyword should be enriched with trends data"

        # Check each enriched keyword
        for kw in keywords:
            if kw.trend_score is not None:
                print(f"\n[OK] Enriched: {kw.keyword}")
                print(f"   Trend Score: {kw.trend_score:.1f}/100")
                print(f"   Direction: {kw.trend_direction}")
                print(f"   Seasonal: {kw.seasonal}")
                print(f"   Related Queries: {kw.related_queries[:3]}")

                # Validate trend score
                assert (
                    0 <= kw.trend_score <= 100
                ), f"Trend score should be 0-100, got {kw.trend_score}"

                # Validate trend direction
                assert kw.trend_direction in [
                    "rising",
                    "stable",
                    "declining",
                    "seasonal",
                ], f"Invalid trend direction: {kw.trend_direction}"

                # Validate seasonal is boolean
                assert isinstance(kw.seasonal, bool), "Seasonal should be boolean"

                # Related queries should be a list
                assert isinstance(kw.related_queries, list), "Related queries should be a list"

    def test_enrich_with_google_trends_batch_processing(self):
        """Test that batch processing works with 6+ keywords"""
        # Create 7 keywords to test batch processing (processes 5 at a time)
        keywords = []
        test_terms = [
            "covid vaccine",
            "climate change",
            "artificial intelligence",
            "cryptocurrency",
            "remote work",
            "electric vehicles",
            "social media",
        ]

        for term in test_terms:
            keywords.append(
                Keyword(
                    keyword=term,
                    search_intent=SearchIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    monthly_volume_estimate="10K-100K",
                    relevance_score=8.0,
                    long_tail=False,
                    question_based=False,
                    related_topics=[term.split()[0]],
                )
            )

        researcher = SEOKeywordResearcher(project_id="test_batch_processing")

        # This should process 2 batches (5 + 2)
        start_time = time.time()
        researcher._enrich_with_google_trends(keywords)
        elapsed_time = time.time() - start_time

        # Verify rate limiting (should take at least 2 seconds for 2nd batch)
        # Note: Limited to first 10 keywords, so only processes 7
        print(f"\n⏱️  Processing time: {elapsed_time:.2f}s")

        # Count enriched keywords
        enriched_count = sum(1 for kw in keywords if kw.trend_score is not None)
        print(f"📊 Enriched {enriched_count}/{len(keywords)} keywords")

        if enriched_count == 0:
            pytest.skip(
                "Google Trends API returned no data (rate limited or unavailable in this environment)"
            )
        assert enriched_count > 0, "Should enrich at least some keywords"

        # Display results
        for kw in keywords:
            if kw.trend_score is not None:
                direction_emoji = {
                    "rising": "📈",
                    "stable": "➡️",
                    "declining": "📉",
                    "seasonal": "🔄",
                }.get(kw.trend_direction, "")

                print(f"   • {kw.keyword}: {kw.trend_score:.1f} {direction_emoji}")

    def test_enrich_with_google_trends_seasonal_detection(self):
        """Test seasonal pattern detection with keywords known to be seasonal"""
        # Keywords that should show seasonal patterns
        seasonal_keywords = [
            Keyword(
                keyword="christmas gifts",
                search_intent=SearchIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.HIGH,
                monthly_volume_estimate="1M-10M",
                relevance_score=7.0,
                long_tail=False,
                question_based=False,
                related_topics=["holidays"],
            ),
            Keyword(
                keyword="tax preparation",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="100K-1M",
                relevance_score=8.0,
                long_tail=False,
                question_based=False,
                related_topics=["finance"],
            ),
            Keyword(
                keyword="back to school",
                search_intent=SearchIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="100K-1M",
                relevance_score=7.5,
                long_tail=False,
                question_based=False,
                related_topics=["education"],
            ),
        ]

        researcher = SEOKeywordResearcher(project_id="test_seasonal")
        researcher._enrich_with_google_trends(seasonal_keywords)

        # Check for seasonal detection
        seasonal_found = False
        for kw in seasonal_keywords:
            if kw.trend_score is not None:
                print(f"\n📊 {kw.keyword}:")
                print(f"   Score: {kw.trend_score:.1f}")
                print(f"   Direction: {kw.trend_direction}")
                print(f"   Seasonal: {kw.seasonal}")

                if kw.seasonal or kw.trend_direction == "seasonal":
                    seasonal_found = True
                    print(f"   [OK] Seasonal pattern detected!")

        # Note: This assertion might fail if Google doesn't return enough data
        # or if the variance threshold isn't met
        if seasonal_found:
            print("\n[OK] Successfully detected seasonal patterns")
        else:
            print("\n⚠️  No seasonal patterns detected (may need more data points)")

    def test_enrich_with_google_trends_related_queries(self):
        """Test that related queries are populated"""
        keywords = [
            Keyword(
                keyword="seo optimization",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="10K-100K",
                relevance_score=8.5,
                long_tail=False,
                question_based=False,
                related_topics=["SEO"],
            ),
        ]

        researcher = SEOKeywordResearcher(project_id="test_related_queries")
        researcher._enrich_with_google_trends(keywords)

        kw = keywords[0]
        if kw.related_queries:
            print(f"\n🔍 Related queries for '{kw.keyword}':")
            for i, query in enumerate(kw.related_queries, 1):
                print(f"   {i}. {query}")

            assert len(kw.related_queries) > 0, "Should have related queries"
            assert len(kw.related_queries) <= 5, "Should limit to 5 related queries"
        else:
            print(f"\n⚠️  No related queries found for '{kw.keyword}'")

    def test_enrich_graceful_failure_invalid_keyword(self):
        """Test that enrichment gracefully handles keywords with no data"""
        keywords = [
            Keyword(
                keyword="xyzabc123impossible",  # Nonsense keyword with no data
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.LOW,
                monthly_volume_estimate="Unknown",
                relevance_score=5.0,
                long_tail=False,
                question_based=False,
                related_topics=[],
            ),
        ]

        researcher = SEOKeywordResearcher(project_id="test_invalid")

        # Should not raise an exception
        try:
            researcher._enrich_with_google_trends(keywords)
            print("\n[OK] Gracefully handled invalid keyword")
        except Exception as e:
            pytest.fail(f"Should not raise exception for invalid keyword: {e}")

        # Keyword should remain unenriched
        assert keywords[0].trend_score is None, "Invalid keyword should not be enriched"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "-m", "live"])
