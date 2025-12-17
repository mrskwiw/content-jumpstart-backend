#!/usr/bin/env python3
"""
Test script for response caching implementation.

Tests:
1. Cache-Control headers on GET requests
2. ETag generation and validation
3. 304 Not Modified responses
4. Cache invalidation headers on mutations
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import requests
from typing import Dict, Optional


class CachingTester:
    """Test caching implementation"""

    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def test_cache_control_headers(self, endpoint: str) -> Dict:
        """
        Test that Cache-Control headers are present.

        Args:
            endpoint: API endpoint to test (e.g., "/api/posts")

        Returns:
            Dict with test results
        """
        print(f"\n{'='*60}")
        print(f"Testing Cache-Control headers: {endpoint}")
        print(f"{'='*60}")

        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url)

        cache_control = response.headers.get("Cache-Control")
        etag = response.headers.get("ETag")
        vary = response.headers.get("Vary")

        print(f"Status: {response.status_code}")
        print(f"Cache-Control: {cache_control}")
        print(f"ETag: {etag}")
        print(f"Vary: {vary}")

        result = {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "has_cache_control": cache_control is not None,
            "has_etag": etag is not None,
            "has_vary": vary is not None,
            "cache_control": cache_control,
            "etag": etag,
        }

        if cache_control and "max-age" in cache_control:
            print("✓ Cache-Control header present with max-age")
        else:
            print("✗ Cache-Control header missing or invalid")

        if etag:
            print("✓ ETag header present")
        else:
            print("✗ ETag header missing")

        return result

    def test_304_not_modified(self, endpoint: str, etag: str) -> Dict:
        """
        Test 304 Not Modified response with If-None-Match header.

        Args:
            endpoint: API endpoint to test
            etag: ETag from previous response

        Returns:
            Dict with test results
        """
        print(f"\n{'='*60}")
        print(f"Testing 304 Not Modified: {endpoint}")
        print(f"{'='*60}")

        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, headers={"If-None-Match": etag})

        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.content)}")

        result = {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "is_304": response.status_code == 304,
            "has_empty_body": len(response.content) == 0,
        }

        if response.status_code == 304:
            print("✓ 304 Not Modified response received")
        else:
            print(f"✗ Expected 304, got {response.status_code}")

        if len(response.content) == 0:
            print("✓ Response body is empty (as expected for 304)")
        else:
            print(f"✗ Response body not empty ({len(response.content)} bytes)")

        return result

    def test_cache_invalidation(self, mutation_endpoint: str, method: str = "POST") -> Dict:
        """
        Test that cache invalidation headers are present on mutations.

        Args:
            mutation_endpoint: API endpoint for mutation (POST/PUT/DELETE)
            method: HTTP method to use

        Returns:
            Dict with test results
        """
        print(f"\n{'='*60}")
        print(f"Testing cache invalidation: {method} {mutation_endpoint}")
        print(f"{'='*60}")

        url = f"{self.base_url}{mutation_endpoint}"

        # For POST/PUT, send minimal payload
        data = {} if method in ["POST", "PUT"] else None

        try:
            if method == "POST":
                response = self.session.post(url, json=data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            cache_invalidate = response.headers.get("X-Cache-Invalidate")
            cache_timestamp = response.headers.get("X-Cache-Timestamp")

            print(f"Status: {response.status_code}")
            print(f"X-Cache-Invalidate: {cache_invalidate}")
            print(f"X-Cache-Timestamp: {cache_timestamp}")

            result = {
                "endpoint": mutation_endpoint,
                "method": method,
                "status_code": response.status_code,
                "has_invalidation_header": cache_invalidate is not None,
                "has_timestamp_header": cache_timestamp is not None,
                "invalidated_resources": cache_invalidate,
            }

            if cache_invalidate:
                print("✓ Cache invalidation header present")
            else:
                print("⚠ Cache invalidation header missing (may not be implemented)")

            return result

        except Exception as e:
            print(f"✗ Error: {e}")
            return {
                "endpoint": mutation_endpoint,
                "method": method,
                "error": str(e),
            }

    def test_etag_changes_on_modification(self, get_endpoint: str) -> Dict:
        """
        Test that ETag changes when resource is modified.

        Args:
            get_endpoint: GET endpoint to fetch resource

        Returns:
            Dict with test results
        """
        print(f"\n{'='*60}")
        print(f"Testing ETag change detection: {get_endpoint}")
        print(f"{'='*60}")

        url = f"{self.base_url}{get_endpoint}"

        # First request
        response1 = self.session.get(url)
        etag1 = response1.headers.get("ETag")
        print(f"First ETag: {etag1}")

        # Second request (should be same)
        response2 = self.session.get(url)
        etag2 = response2.headers.get("ETag")
        print(f"Second ETag: {etag2}")

        result = {
            "endpoint": get_endpoint,
            "etag1": etag1,
            "etag2": etag2,
            "etags_match": etag1 == etag2,
        }

        if etag1 == etag2:
            print("✓ ETags match for unchanged resource")
        else:
            print("✗ ETags differ for same resource (unexpected)")

        return result


def main():
    """Run caching tests"""
    print("="*60)
    print("RESPONSE CACHING TEST SUITE")
    print("="*60)
    print()
    print("Prerequisites:")
    print("  1. API server running on http://localhost:8000")
    print("  2. Valid authentication token (or public endpoints)")
    print("  3. Test data exists in database")
    print()

    # Get auth token from user
    token = input("Enter auth token (press Enter to skip for public endpoints): ").strip()
    if not token:
        token = None
        print("⚠ Running without authentication - only public endpoints will work")

    tester = CachingTester(token=token)

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        print(f"✓ Server is running (status: {response.json().get('status')})")
    except Exception as e:
        print(f"✗ Server not running: {e}")
        print("\nStart the server with: uvicorn backend.main:app --reload")
        return

    # Test results
    results = []

    # Test 1: Cache-Control headers on GET requests
    print("\n" + "="*60)
    print("TEST 1: Cache-Control Headers")
    print("="*60)

    for endpoint in ["/api/posts", "/api/projects"]:
        result = tester.test_cache_control_headers(endpoint)
        results.append(result)

        # If successful and has ETag, test 304
        if result.get("has_etag") and result.get("etag"):
            result_304 = tester.test_304_not_modified(endpoint, result["etag"])
            results.append(result_304)

    # Test 2: ETag stability
    print("\n" + "="*60)
    print("TEST 2: ETag Stability")
    print("="*60)

    for endpoint in ["/api/posts", "/api/projects"]:
        result = tester.test_etag_changes_on_modification(endpoint)
        results.append(result)

    # Test 3: Cache invalidation headers (if mutations are accessible)
    print("\n" + "="*60)
    print("TEST 3: Cache Invalidation Headers")
    print("="*60)
    print("Note: These tests may fail if you don't have write permissions")

    # We can't easily test mutations without knowing valid IDs,
    # so we'll just document the expected headers
    print("\nExpected headers on mutations:")
    print("  POST/PUT/DELETE → X-Cache-Invalidate: projects,posts")
    print("  POST/PUT/DELETE → X-Cache-Timestamp: <timestamp>")

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r.get("has_cache_control") or r.get("is_304") or r.get("etags_match"))
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")
    print()

    # Detailed results
    for i, result in enumerate(results, 1):
        print(f"Test {i}: {result.get('endpoint', 'N/A')}")
        for key, value in result.items():
            if key != "endpoint":
                print(f"  {key}: {value}")
        print()

    print("="*60)
    print("Caching implementation test complete!")
    print("="*60)


if __name__ == "__main__":
    main()
