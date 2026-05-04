"""
Simple test script to verify backend is working.
"""

import sys

import requests


def test_health_check():
    """Test health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)  # nosec B113
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Rate Limit Queue: {data['rate_limits']['queue_length']}")
            print(
                f"   Requests: {data['rate_limits']['requests_per_minute']['current']}/{data['rate_limits']['requests_per_minute']['limit']}"
            )
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        print("   Start with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_root_endpoint():
    """Test root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = requests.get("http://localhost:8000/", timeout=10)  # nosec B113
        if response.status_code == 200:
            data = response.json()
            print("✅ Root endpoint passed")
            print(f"   Message: {data['message']}")
            print(f"   Docs: http://localhost:8000{data['docs']}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Backend Verification Tests")
    print("=" * 60)

    tests = [
        test_health_check,
        test_root_endpoint,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✅ All tests passed! Backend is working correctly.")
        print("\n📚 Next steps:")
        print("   1. View API docs: http://localhost:8000/docs")
        print("   2. Continue with Phase 2 (schemas + routers)")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
