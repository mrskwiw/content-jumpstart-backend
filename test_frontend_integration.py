"""
Comprehensive Frontend Integration Test Suite

Tests all API endpoints that the frontend calls, simulating user interactions
through the operator dashboard.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test credentials
TEST_CREDENTIALS = {
    "email": "mrskwiw@gmail.com",
    "password": "Random!1Pass"
}

# Global test state
auth_token: Optional[str] = None
test_client_id: Optional[str] = None
test_project_id: Optional[str] = None
test_run_id: Optional[str] = None

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}[ERROR] {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}[WARN] {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO] {message}{Colors.END}")

def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print('=' * 60)

def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    use_auth: bool = True,
    files: Optional[Dict] = None
) -> requests.Response:
    """Make an HTTP request to the API"""
    url = f"{BASE_URL}{endpoint}"
    headers = {}

    if use_auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if data and not files:
        headers["Content-Type"] = "application/json"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response
    except Exception as e:
        print_error(f"Request failed: {e}")
        raise

# =============================================================================
# TEST 1: AUTHENTICATION FLOW
# =============================================================================

def test_authentication():
    """Test authentication endpoints"""
    global auth_token

    print_section("TEST 1: AUTHENTICATION")

    # Test 1.1: Login with valid credentials
    print_info("Testing login with valid credentials...")
    response = make_request(
        "POST",
        "/api/auth/login",
        data=TEST_CREDENTIALS,
        use_auth=False
    )

    if response.status_code == 200:
        data = response.json()
        if "access_token" in data and "user" in data:
            auth_token = data["access_token"]
            print_success(f"Login successful - Token: {auth_token[:20]}...")
        else:
            print_error(f"Login response invalid: {data}")
            return False
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return False

    # Test 1.2: Verify token works by making authenticated request
    print_info("Testing token authentication...")
    response = make_request("GET", "/api/clients")

    if response.status_code == 200:
        print_success("Token authentication successful")
    else:
        print_error(f"Token authentication failed: {response.status_code} - {response.text}")
        return False

    # Test 1.3: Login with invalid credentials
    print_info("Testing login with invalid credentials...")
    response = make_request(
        "POST",
        "/api/auth/login",
        data={"email": "wrong@email.com", "password": "wrongpassword"},
        use_auth=False
    )

    if response.status_code == 401:
        print_success("Invalid credentials correctly rejected")
    else:
        print_warning(f"Expected 401, got {response.status_code}")

    # Test 1.4: Access protected endpoint without auth
    print_info("Testing protected endpoint without auth...")
    response = requests.get(f"{BASE_URL}/api/clients")

    if response.status_code == 401:
        print_success("Unauthorized access correctly blocked")
    else:
        print_warning(f"Expected 401, got {response.status_code}")

    return True

# =============================================================================
# TEST 2: CLIENT MANAGEMENT
# =============================================================================

def test_client_management():
    """Test client CRUD operations"""
    global test_client_id

    print_section("TEST 2: CLIENT MANAGEMENT")

    # Test 2.1: Create client
    print_info("Creating new client...")
    # Match exactly what frontend sends (snake_case after conversion from camelCase)
    client_data = {
        "name": "Test Company Inc",
        "email": "testcompany@example.com",
        "business_description": "We provide cutting-edge technology solutions",
        "ideal_customer": "Tech-savvy business owners",
        "main_problem_solved": "Complex workflow automation",
        "tone_preference": "professional",
        "platforms": ["linkedin", "twitter"],
        "customer_pain_points": ["Manual processes", "Time-consuming tasks"],
        "customer_questions": ["How can we automate?", "What's the ROI?"]
    }

    response = make_request("POST", "/api/clients", data=client_data)

    if response.status_code == 201:
        data = response.json()
        if data.get("success") and "data" in data:
            test_client_id = data["data"]["id"]
            print_success(f"Client created: {test_client_id}")
        else:
            print_error(f"Create client response invalid: {data}")
            return False
    else:
        print_error(f"Create client failed: {response.status_code} - {response.text}")
        return False

    # Test 2.2: Get client by ID
    print_info(f"Getting client {test_client_id}...")
    response = make_request("GET", f"/api/clients/{test_client_id}")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            client = data["data"]
            print_success(f"Client retrieved: {client.get('company_name')}")
        else:
            print_error(f"Get client response invalid: {data}")
            return False
    else:
        print_error(f"Get client failed: {response.status_code} - {response.text}")
        return False

    # Test 2.3: List all clients
    print_info("Listing all clients...")
    response = make_request("GET", "/api/clients")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            clients = data["data"]
            print_success(f"Found {len(clients)} client(s)")
        else:
            print_error(f"List clients response invalid: {data}")
            return False
    else:
        print_error(f"List clients failed: {response.status_code} - {response.text}")
        return False

    # Test 2.4: Update client
    print_info(f"Updating client {test_client_id}...")
    update_data = {
        "contact_phone": "+1-555-9999",
        "notes": "Updated via integration test"
    }

    response = make_request("PUT", f"/api/clients/{test_client_id}", data=update_data)

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print_success("Client updated successfully")
        else:
            print_error(f"Update client response invalid: {data}")
            return False
    else:
        print_error(f"Update client failed: {response.status_code} - {response.text}")
        return False

    # Test 2.5: Create duplicate client (should fail)
    print_info("Testing duplicate client creation...")
    response = make_request("POST", "/api/clients", data=client_data)

    if response.status_code == 409:
        print_success("Duplicate client correctly rejected")
    else:
        print_warning(f"Expected 409, got {response.status_code}")

    return True

# =============================================================================
# TEST 3: PROJECT MANAGEMENT
# =============================================================================

def test_project_management():
    """Test project CRUD operations"""
    global test_project_id

    print_section("TEST 3: PROJECT MANAGEMENT")

    if not test_client_id:
        print_error("No test client ID - skipping project tests")
        return False

    # Test 3.1: Create project
    print_info("Creating new project...")
    project_data = {
        "client_id": test_client_id,
        "project_name": "Test Content Campaign",
        "platform": "linkedin",
        "num_posts": 30,
        "status": "draft"
    }

    response = make_request("POST", "/api/projects", data=project_data)

    if response.status_code == 201:
        data = response.json()
        if data.get("success") and "data" in data:
            test_project_id = data["data"]["id"]
            print_success(f"Project created: {test_project_id}")
        else:
            print_error(f"Create project response invalid: {data}")
            return False
    else:
        print_error(f"Create project failed: {response.status_code} - {response.text}")
        return False

    # Test 3.2: Get project by ID
    print_info(f"Getting project {test_project_id}...")
    response = make_request("GET", f"/api/projects/{test_project_id}")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            project = data["data"]
            print_success(f"Project retrieved: {project.get('project_name')}")
        else:
            print_error(f"Get project response invalid: {data}")
            return False
    else:
        print_error(f"Get project failed: {response.status_code} - {response.text}")
        return False

    # Test 3.3: List all projects
    print_info("Listing all projects...")
    response = make_request("GET", "/api/projects")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            projects = data["data"]
            print_success(f"Found {len(projects)} project(s)")
        else:
            print_error(f"List projects response invalid: {data}")
            return False
    else:
        print_error(f"List projects failed: {response.status_code} - {response.text}")
        return False

    # Test 3.4: List projects by client
    print_info(f"Listing projects for client {test_client_id}...")
    response = make_request("GET", f"/api/projects?client_id={test_client_id}")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            projects = data["data"]
            print_success(f"Found {len(projects)} project(s) for client")
        else:
            print_error(f"List projects by client response invalid: {data}")
            return False
    else:
        print_error(f"List projects by client failed: {response.status_code} - {response.text}")
        return False

    # Test 3.5: Update project
    print_info(f"Updating project {test_project_id}...")
    update_data = {
        "status": "in_progress",
        "notes": "Started content generation"
    }

    response = make_request("PUT", f"/api/projects/{test_project_id}", data=update_data)

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print_success("Project updated successfully")
        else:
            print_error(f"Update project response invalid: {data}")
            return False
    else:
        print_error(f"Update project failed: {response.status_code} - {response.text}")
        return False

    return True

# =============================================================================
# TEST 4: BRIEF MANAGEMENT
# =============================================================================

def test_brief_management():
    """Test brief CRUD operations"""

    print_section("TEST 4: BRIEF MANAGEMENT")

    if not test_project_id:
        print_error("No test project ID - skipping brief tests")
        return False

    # Test 4.1: Create brief
    print_info("Creating brief...")
    brief_data = {
        "project_id": test_project_id,
        "company_name": "Test Company Inc",
        "business_description": "We provide cutting-edge AI solutions for content marketing",
        "ideal_customer": "Marketing managers at B2B SaaS companies",
        "main_problem_solved": "Time-consuming content creation process",
        "customer_pain_points": [
            "Spending 20+ hours per month on social media",
            "Inconsistent posting schedule",
            "Struggling to maintain brand voice"
        ],
        "unique_value_proposition": "AI-powered content generation in minutes, not hours",
        "brand_voice_keywords": ["professional", "innovative", "efficient"],
        "platform": "linkedin",
        "content_goals": "Build thought leadership and generate leads",
        "cta_preferences": "Visit website, download resources, book demo"
    }

    response = make_request("POST", "/api/briefs", data=brief_data)

    if response.status_code == 201:
        data = response.json()
        if data.get("success") and "data" in data:
            brief_id = data["data"]["id"]
            print_success(f"Brief created: {brief_id}")
        else:
            print_error(f"Create brief response invalid: {data}")
            return False
    else:
        print_error(f"Create brief failed: {response.status_code} - {response.text}")
        return False

    # Test 4.2: Get brief by project
    print_info(f"Getting brief for project {test_project_id}...")
    response = make_request("GET", f"/api/briefs/project/{test_project_id}")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            brief = data["data"]
            print_success(f"Brief retrieved for {brief.get('company_name')}")
        else:
            print_error(f"Get brief response invalid: {data}")
            return False
    else:
        print_error(f"Get brief failed: {response.status_code} - {response.text}")
        return False

    # Test 4.3: Update brief
    print_info(f"Updating brief...")
    update_data = {
        "content_goals": "Build thought leadership, generate leads, and increase brand awareness"
    }

    response = make_request("PUT", f"/api/briefs/project/{test_project_id}", data=update_data)

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print_success("Brief updated successfully")
        else:
            print_error(f"Update brief response invalid: {data}")
            return False
    else:
        print_error(f"Update brief failed: {response.status_code} - {response.text}")
        return False

    return True

# =============================================================================
# TEST 5: CONTENT GENERATION
# =============================================================================

def test_content_generation():
    """Test content generation workflow"""
    global test_run_id

    print_section("TEST 5: CONTENT GENERATION")

    if not test_project_id:
        print_error("No test project ID - skipping generation tests")
        return False

    # Test 5.1: Start content generation
    print_info("Starting content generation...")
    generation_data = {
        "project_id": test_project_id,
        "num_posts": 5,  # Generate only 5 posts for testing speed
        "platform": "linkedin",
        "templates": None  # Let system choose templates
    }

    response = make_request("POST", "/api/generator/generate", data=generation_data)

    if response.status_code == 201:
        data = response.json()
        if data.get("success") and "data" in data:
            test_run_id = data["data"]["run_id"]
            print_success(f"Generation started: Run ID {test_run_id}")
        else:
            print_error(f"Start generation response invalid: {data}")
            return False
    else:
        print_error(f"Start generation failed: {response.status_code} - {response.text}")
        return False

    # Test 5.2: Monitor generation progress
    print_info("Monitoring generation progress...")
    max_attempts = 60  # Wait up to 60 seconds
    attempt = 0

    while attempt < max_attempts:
        response = make_request("GET", f"/api/runs/{test_run_id}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "data" in data:
                run = data["data"]
                status = run.get("status")
                progress = run.get("progress", 0)

                print_info(f"Status: {status}, Progress: {progress}%")

                if status == "completed":
                    print_success(f"Generation completed successfully")
                    break
                elif status == "failed":
                    print_error(f"Generation failed: {run.get('error_message')}")
                    return False

                time.sleep(1)
                attempt += 1
            else:
                print_error(f"Get run status response invalid: {data}")
                return False
        else:
            print_error(f"Get run status failed: {response.status_code} - {response.text}")
            return False

    if attempt >= max_attempts:
        print_warning("Generation took too long - may still be in progress")

    # Test 5.3: Get generated posts
    print_info(f"Retrieving generated posts for run {test_run_id}...")
    response = make_request("GET", f"/api/posts?run_id={test_run_id}")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            posts = data["data"]
            print_success(f"Retrieved {len(posts)} post(s)")

            # Display first post as sample
            if posts:
                first_post = posts[0]
                print_info(f"Sample post (ID {first_post['id']}):")
                print(f"  Template: {first_post.get('template_type')}")
                print(f"  Word count: {first_post.get('word_count')}")
                print(f"  Quality score: {first_post.get('quality_score', 0):.2f}")
        else:
            print_error(f"Get posts response invalid: {data}")
            return False
    else:
        print_error(f"Get posts failed: {response.status_code} - {response.text}")
        return False

    return True

# =============================================================================
# TEST 6: QA AND VALIDATION
# =============================================================================

def test_qa_validation():
    """Test QA and validation features"""

    print_section("TEST 6: QA AND VALIDATION")

    if not test_run_id:
        print_error("No test run ID - skipping QA tests")
        return False

    # Test 6.1: Get QA report for run
    print_info(f"Getting QA report for run {test_run_id}...")
    response = make_request("GET", f"/api/runs/{test_run_id}/qa-report")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            qa_report = data["data"]
            print_success(f"QA report retrieved")
            print_info(f"  Overall score: {qa_report.get('overall_quality_score', 0):.2f}")
            print_info(f"  Passed: {qa_report.get('overall_passed')}")

            # Display validator results
            for validator_name, validator_data in qa_report.items():
                if isinstance(validator_data, dict) and "passed" in validator_data:
                    status = "✓" if validator_data["passed"] else "✗"
                    print_info(f"  {status} {validator_name}: {validator_data.get('message', 'N/A')}")
        else:
            print_error(f"Get QA report response invalid: {data}")
            return False
    else:
        print_error(f"Get QA report failed: {response.status_code} - {response.text}")
        return False

    # Test 6.2: Get posts filtered by QA status
    print_info("Getting posts that need review...")
    response = make_request("GET", f"/api/posts?run_id={test_run_id}&needs_review=true")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            posts = data["data"]
            print_success(f"Found {len(posts)} post(s) needing review")
        else:
            print_error(f"Get posts by QA status response invalid: {data}")
            return False
    else:
        print_error(f"Get posts by QA status failed: {response.status_code} - {response.text}")
        return False

    return True

# =============================================================================
# TEST 7: DELIVERABLE EXPORT
# =============================================================================

def test_deliverable_export():
    """Test deliverable export features"""

    print_section("TEST 7: DELIVERABLE EXPORT")

    if not test_project_id:
        print_error("No test project ID - skipping export tests")
        return False

    # Test 7.1: Export deliverable as markdown
    print_info("Exporting deliverable as markdown...")
    response = make_request("GET", f"/api/deliverables/{test_project_id}/export?format=markdown")

    if response.status_code == 200:
        print_success(f"Markdown export successful ({len(response.content)} bytes)")
    else:
        print_error(f"Markdown export failed: {response.status_code} - {response.text}")
        return False

    # Test 7.2: Export deliverable as DOCX
    print_info("Exporting deliverable as DOCX...")
    response = make_request("GET", f"/api/deliverables/{test_project_id}/export?format=docx")

    if response.status_code == 200:
        print_success(f"DOCX export successful ({len(response.content)} bytes)")
    else:
        print_error(f"DOCX export failed: {response.status_code} - {response.text}")
        return False

    # Test 7.3: Get analytics for project
    print_info("Getting project analytics...")
    response = make_request("GET", f"/api/deliverables/{test_project_id}/analytics")

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and "data" in data:
            analytics = data["data"]
            print_success("Analytics retrieved")
            print_info(f"  Total posts: {analytics.get('total_posts')}")
            print_info(f"  Avg quality score: {analytics.get('avg_quality_score', 0):.2f}")
            print_info(f"  Avg word count: {analytics.get('avg_word_count', 0):.0f}")
        else:
            print_error(f"Get analytics response invalid: {data}")
            return False
    else:
        print_error(f"Get analytics failed: {response.status_code} - {response.text}")
        return False

    return True

# =============================================================================
# TEST 8: EDGE CASES
# =============================================================================

def test_edge_cases():
    """Test edge cases and error handling"""

    print_section("TEST 8: EDGE CASES")

    # Test 8.1: Get non-existent client
    print_info("Testing non-existent client retrieval...")
    response = make_request("GET", "/api/clients/client-nonexistent")

    if response.status_code == 404:
        print_success("Non-existent client correctly returns 404")
    else:
        print_warning(f"Expected 404, got {response.status_code}")

    # Test 8.2: Create project with invalid client ID
    print_info("Testing project creation with invalid client ID...")
    invalid_project_data = {
        "client_id": "client-nonexistent",
        "project_name": "Invalid Project",
        "platform": "linkedin",
        "num_posts": 30
    }

    response = make_request("POST", "/api/projects", data=invalid_project_data)

    if response.status_code == 404:
        print_success("Invalid client ID correctly rejected")
    else:
        print_warning(f"Expected 404, got {response.status_code}")

    # Test 8.3: Create brief with missing required fields
    print_info("Testing brief creation with missing fields...")
    invalid_brief_data = {
        "project_id": test_project_id,
        "company_name": "Test"
        # Missing required fields
    }

    response = make_request("POST", "/api/briefs", data=invalid_brief_data)

    if response.status_code == 422:
        print_success("Missing required fields correctly rejected")
    else:
        print_warning(f"Expected 422, got {response.status_code}")

    # Test 8.4: Start generation with invalid platform
    print_info("Testing generation with invalid platform...")
    invalid_gen_data = {
        "project_id": test_project_id,
        "num_posts": 5,
        "platform": "invalid_platform"
    }

    response = make_request("POST", "/api/generator/generate", data=invalid_gen_data)

    if response.status_code in [400, 422]:
        print_success("Invalid platform correctly rejected")
    else:
        print_warning(f"Expected 400/422, got {response.status_code}")

    return True

# =============================================================================
# TEST 9: CLEANUP
# =============================================================================

def test_cleanup():
    """Clean up test data"""

    print_section("TEST 9: CLEANUP")

    # Delete test client (cascade deletes projects, briefs, runs, posts)
    if test_client_id:
        print_info(f"Deleting test client {test_client_id}...")
        response = make_request("DELETE", f"/api/clients/{test_client_id}")

        if response.status_code == 200:
            print_success("Test client deleted successfully")
        else:
            print_warning(f"Delete client returned {response.status_code}")

    return True

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print(" CONTENT JUMPSTART FRONTEND INTEGRATION TEST SUITE")
    print("="*60)

    tests = [
        ("Authentication", test_authentication),
        ("Client Management", test_client_management),
        ("Project Management", test_project_management),
        ("Brief Management", test_brief_management),
        ("Content Generation", test_content_generation),
        ("QA Validation", test_qa_validation),
        ("Deliverable Export", test_deliverable_export),
        ("Edge Cases", test_edge_cases),
        ("Cleanup", test_cleanup),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print_success("ALL TESTS PASSED!")
        return 0
    else:
        print_error(f"{total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    exit(run_all_tests())
