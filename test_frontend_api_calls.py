"""
Comprehensive API Integration Tests
Tests all endpoints exactly as the frontend calls them.
Based on operator-dashboard/src/api/* TypeScript files.
"""
import sys
import io

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Test credentials (from main.py auto-seeded users)
TEST_USER = {
    "email": "mrskwiw@gmail.com",
    "password": "Random!1Pass"
}

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class FrontendAPITester:
    """Tests all API endpoints as called by the React frontend"""

    def __init__(self):
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.client_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.run_id: Optional[str] = None
        self.post_ids: List[str] = []
        self.deliverable_id: Optional[str] = None

        self.tests_passed = 0
        self.tests_failed = 0
        self.errors: List[Dict] = []

    def log(self, message: str, color: str = Colors.RESET):
        """Print colored message"""
        print(f"{color}{message}{Colors.RESET}")

    def success(self, test_name: str, details: str = ""):
        """Mark test as passed"""
        self.tests_passed += 1
        self.log(f"✓ PASS: {test_name}", Colors.GREEN)
        if details:
            self.log(f"  └─ {details}", Colors.CYAN)

    def fail(self, test_name: str, error: str):
        """Mark test as failed"""
        self.tests_failed += 1
        self.errors.append({"test": test_name, "error": error})
        self.log(f"✗ FAIL: {test_name}", Colors.RED)
        self.log(f"  └─ {error}", Colors.YELLOW)

    def section(self, title: str):
        """Print section header"""
        self.log(f"\n{' '*80}", Colors.BOLD)
        self.log(f"{'='*80}", Colors.BOLD)
        self.log(f"{title.center(80)}", Colors.BOLD)
        self.log(f"{'='*80}", Colors.BOLD)
        self.log(f"", Colors.RESET)

    def get_headers(self, include_auth: bool = True) -> Dict:
        """Get request headers with optional auth token"""
        headers = {"Content-Type": "application/json"}
        if include_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def test_request(
        self,
        test_name: str,
        method: str,
        url: str,
        expected_status: int = 200,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        include_auth: bool = True,
        validate: Optional[callable] = None
    ) -> Optional[Dict]:
        """Make API request and validate response"""
        try:
            headers = self.get_headers(include_auth)

            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=json_data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=json_data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Check status code
            if response.status_code != expected_status:
                self.fail(
                    test_name,
                    f"Status {response.status_code} (expected {expected_status}). Response: {response.text[:300]}"
                )
                return None

            # Parse JSON
            try:
                data = response.json()
            except:
                # Non-JSON response (e.g., file download)
                self.success(test_name, f"Status {response.status_code}")
                return {"_raw_response": True}

            # Custom validation
            if validate:
                try:
                    validate(data)
                except AssertionError as e:
                    self.fail(test_name, f"Validation failed: {str(e)}")
                    return None

            self.success(test_name, f"Status {response.status_code}")
            return data

        except Exception as e:
            self.fail(test_name, f"Request failed: {str(e)}")
            return None

    def run_all_tests(self):
        """Execute all tests in order"""

        # ============================================================
        # 1. HEALTH CHECK
        # ============================================================
        self.section("1. HEALTH & MONITORING")

        self.test_request(
            "GET /api/health - Health check",
            "GET",
            f"{API_BASE}/health",
            include_auth=False,
            validate=lambda d: (
                assert_has_key(d, "status"),
                assert_has_key(d, "version"),
                assert_has_key(d, "service")
            )
        )

        # ============================================================
        # 2. AUTHENTICATION (from operator-dashboard/src/api/auth.ts)
        # ============================================================
        self.section("2. AUTHENTICATION")

        # Test 2.1: Login (auth.ts line 5-38)
        # Frontend sends: { email: string, password: string }
        login_data = self.test_request(
            "POST /api/auth/login - Valid credentials",
            "POST",
            f"{API_BASE}/auth/login",
            json_data={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            },
            include_auth=False,
            validate=lambda d: (
                assert_has_key(d, "access_token"),
                assert_has_key(d, "refresh_token"),
                assert_has_key(d, "token_type"),
                assert_has_key(d, "user"),
                assert_equals(d["token_type"], "bearer")
            )
        )

        if login_data:
            self.token = login_data["access_token"]
            self.refresh_token = login_data["refresh_token"]
            self.user_id = login_data["user"]["id"]
            self.log(f"  └─ Logged in as: {login_data['user']['email']}", Colors.BLUE)
            self.log(f"  └─ User ID: {self.user_id}", Colors.BLUE)

        # Test 2.2: Login with invalid credentials
        self.test_request(
            "POST /api/auth/login - Invalid credentials (should fail)",
            "POST",
            f"{API_BASE}/auth/login",
            expected_status=401,
            json_data={
                "email": "wrong@example.com",
                "password": "wrongpass"
            },
            include_auth=False
        )

        # Test 2.3: Refresh token (auth.ts line 41-45)
        # Frontend sends: { refresh_token: string }
        # Frontend expects: { access_token, token_type } (NO user field)
        if self.refresh_token:
            refresh_data = self.test_request(
                "POST /api/auth/refresh - Refresh access token",
                "POST",
                f"{API_BASE}/auth/refresh",
                json_data={
                    "refresh_token": self.refresh_token
                },
                include_auth=False,
                validate=lambda d: (
                    assert_has_key(d, "access_token"),
                    assert_has_key(d, "token_type"),
                    # Note: refresh should NOT include user field
                )
            )

            if refresh_data:
                self.log(f"  └─ Token refreshed successfully", Colors.BLUE)

        # ============================================================
        # 3. CLIENT MANAGEMENT (from operator-dashboard/src/api/clients.ts)
        # ============================================================
        self.section("3. CLIENT MANAGEMENT")

        # Test 3.1: Create client (clients.ts line 39-53)
        # Frontend sends camelCase, converts to snake_case before API call
        client_data = self.test_request(
            "POST /api/clients/ - Create new client",
            "POST",
            f"{API_BASE}/clients/",
            expected_status=201,  # Backend returns 201 for creates
            json_data={
                "name": f"Test Company {datetime.now().strftime('%Y%m%d%H%M%S')}",
                "email": "test@example.com",
                "business_description": "We provide SaaS solutions",
                "ideal_customer": "Small business owners",
                "main_problem_solved": "Time management",
                "tone_preference": "Professional but approachable",
                "platforms": ["linkedin", "twitter"],
                "customer_pain_points": ["Lack of time", "Complex workflows"],
                "customer_questions": ["How do I get started?"]
            },
            validate=lambda d: (
                assert_has_key(d, "id"),
                assert_has_key(d, "name")
            )
        )

        if client_data:
            self.client_id = client_data["id"]
            self.log(f"  └─ Client ID: {self.client_id}", Colors.BLUE)

        # Test 3.2: List clients (clients.ts line 29-31)
        clients_list = self.test_request(
            "GET /api/clients/ - List all clients",
            "GET",
            f"{API_BASE}/clients/",
            validate=lambda d: assert_is_list(d)
        )

        if clients_list:
            self.log(f"  └─ Found {len(clients_list)} clients", Colors.BLUE)

        # Test 3.3: Get specific client (clients.ts line 34-36)
        if self.client_id:
            self.test_request(
                f"GET /api/clients/{self.client_id} - Get client by ID",
                "GET",
                f"{API_BASE}/clients/{self.client_id}",
                validate=lambda d: (
                    assert_equals(d["id"], self.client_id),
                    assert_has_key(d, "name")
                )
            )

        # Test 3.4: Update client (clients.ts line 56-71)
        if self.client_id:
            self.test_request(
                f"PATCH /api/clients/{self.client_id} - Update client",
                "PATCH",
                f"{API_BASE}/clients/{self.client_id}",
                json_data={
                    "tone_preference": "Casual and friendly"
                }
            )

        # ============================================================
        # 4. PROJECT MANAGEMENT (from operator-dashboard/src/api/projects.ts)
        # ============================================================
        self.section("4. PROJECT MANAGEMENT")

        # Test 4.1: Create project (projects.ts line 59-69)
        # Frontend converts camelCase to snake_case
        if self.client_id:
            project_data = self.test_request(
                "POST /api/projects/ - Create new project",
                "POST",
                f"{API_BASE}/projects/",
                expected_status=201,  # Backend returns 201 for creates
                json_data={
                    "name": f"Test Project {datetime.now().strftime('%H%M%S')}",
                    "client_id": self.client_id,  # Frontend sends snake_case
                    "templates": ["problem_recognition", "statistic_insight"],
                    "platforms": ["linkedin", "twitter"],
                    "tone": "professional"
                },
                validate=lambda d: (
                    assert_has_key(d, "id"),
                    assert_equals(d["client_id"], self.client_id)
                )
            )

            if project_data:
                self.project_id = project_data["id"]
                self.log(f"  └─ Project ID: {self.project_id}", Colors.BLUE)

        # Test 4.2: List projects (projects.ts line 38-40)
        # Supports pagination params: page, page_size, cursor
        # Backend returns { items: [...], metadata: {...} }
        projects_list = self.test_request(
            "GET /api/projects/ - List projects (paginated)",
            "GET",
            f"{API_BASE}/projects/",
            params={"page": 1, "page_size": 10},
            validate=lambda d: (
                assert_has_key(d, "items"),
                assert_has_key(d, "metadata"),
                assert_is_list(d["items"])
            )
        )

        if projects_list:
            self.log(f"  └─ Found {len(projects_list['items'])} projects (page 1)", Colors.BLUE)

        # Test 4.3: List projects with client filter
        if self.client_id:
            self.test_request(
                f"GET /api/projects/?clientId={self.client_id} - Filter by client",
                "GET",
                f"{API_BASE}/projects/",
                params={"clientId": self.client_id}
            )

        # Test 4.4: Get specific project (projects.ts line 54-56)
        if self.project_id:
            self.test_request(
                f"GET /api/projects/{self.project_id} - Get project by ID",
                "GET",
                f"{API_BASE}/projects/{self.project_id}",
                validate=lambda d: assert_equals(d["id"], self.project_id)
            )

        # Test 4.5: Update project (projects.ts line 72-74)
        if self.project_id:
            self.test_request(
                f"PATCH /api/projects/{self.project_id} - Update project",
                "PATCH",
                f"{API_BASE}/projects/{self.project_id}",
                json_data={
                    "status": "in_progress"
                }
            )

        # ============================================================
        # 5. CONTENT GENERATION (from operator-dashboard/src/api/generator.ts)
        # ============================================================
        self.section("5. CONTENT GENERATION")

        # Test 5.1: Generate all posts (generator.ts line 6-14)
        # Frontend sends: { projectId, clientId, isBatch }
        # Converts to: { project_id, client_id, is_batch }
        if self.project_id and self.client_id:
            gen_data = self.test_request(
                "POST /api/generator/generate-all - Generate content",
                "POST",
                f"{API_BASE}/generator/generate-all",
                json_data={
                    "project_id": self.project_id,
                    "client_id": self.client_id,
                    "is_batch": True
                },
                validate=lambda d: (
                    assert_has_key(d, "id"),
                    assert_has_key(d, "status")
                )
            )

            if gen_data:
                self.run_id = gen_data["id"]
                self.log(f"  └─ Run ID: {self.run_id}", Colors.BLUE)
                self.log(f"  └─ Status: {gen_data['status']}", Colors.BLUE)

        # Test 5.2: Wait for generation to complete
        if self.run_id:
            self.log("  └─ Waiting for generation to complete (max 120s)...", Colors.CYAN)
            max_wait = 120
            start_time = time.time()
            completed = False

            while time.time() - start_time < max_wait:
                try:
                    response = requests.get(
                        f"{API_BASE}/runs/{self.run_id}",
                        headers=self.get_headers(),
                        timeout=10
                    )
                    if response.status_code == 200:
                        run_data = response.json()
                        status = run_data.get("status")
                        progress = run_data.get("progress", 0)

                        if status == "completed":
                            self.success("Generation completed", f"Progress: {progress}%")
                            completed = True
                            break
                        elif status == "failed":
                            self.fail("Generation", f"Generation failed: {run_data.get('error_message', 'Unknown error')}")
                            break
                        else:
                            self.log(f"  └─ Status: {status}, Progress: {progress}%", Colors.CYAN)

                except Exception as e:
                    self.log(f"  └─ Error checking status: {str(e)}", Colors.YELLOW)

                time.sleep(10)

            if not completed and time.time() - start_time >= max_wait:
                self.fail("Generation timeout", "Did not complete within 120s")

        # ============================================================
        # 6. POST MANAGEMENT (from operator-dashboard/src/api/posts.ts)
        # ============================================================
        self.section("6. POST MANAGEMENT")

        # Test 6.1: List posts (posts.ts line 26-28)
        # Supports pagination: page, page_size, cursor
        # Supports filters: projectId, runId, status
        if self.run_id:
            posts_data = self.test_request(
                f"GET /api/posts/?runId={self.run_id} - List posts by run",
                "GET",
                f"{API_BASE}/posts/",
                params={"runId": self.run_id, "page": 1, "page_size": 10},
                validate=lambda d: (
                    assert_has_key(d, "items"),
                    assert_has_key(d, "total"),
                    assert_is_list(d["items"])
                )
            )

            if posts_data and len(posts_data["items"]) > 0:
                self.post_ids = [post["id"] for post in posts_data["items"][:3]]
                self.log(f"  └─ Found {len(posts_data['items'])} posts", Colors.BLUE)
                self.log(f"  └─ First 3 IDs: {self.post_ids}", Colors.BLUE)

        # Test 6.2: Get specific post (posts.ts line 48-50)
        if self.post_ids:
            self.test_request(
                f"GET /api/posts/{self.post_ids[0]} - Get post by ID",
                "GET",
                f"{API_BASE}/posts/{self.post_ids[0]}",
                validate=lambda d: (
                    assert_has_key(d, "id"),
                    assert_has_key(d, "content"),
                    assert_has_key(d, "platform")
                )
            )

        # Test 6.3: Update post (posts.ts line 60-62)
        if self.post_ids:
            self.test_request(
                f"PATCH /api/posts/{self.post_ids[0]} - Update post content",
                "PATCH",
                f"{API_BASE}/posts/{self.post_ids[0]}",
                json_data={
                    "content": "Updated content via integration test"
                },
                validate=lambda d: assert_has_key(d, "id")
            )

        # ============================================================
        # 7. RUNS (from operator-dashboard/src/api/runs.ts)
        # ============================================================
        self.section("7. RUNS MANAGEMENT")

        # Test 7.1: List runs
        if self.project_id:
            runs_data = self.test_request(
                f"GET /api/runs/?projectId={self.project_id} - List runs by project",
                "GET",
                f"{API_BASE}/runs/",
                params={"projectId": self.project_id}
            )

        # Test 7.2: Get run details
        if self.run_id:
            self.test_request(
                f"GET /api/runs/{self.run_id} - Get run details",
                "GET",
                f"{API_BASE}/runs/{self.run_id}",
                validate=lambda d: (
                    assert_has_key(d, "id"),
                    assert_has_key(d, "status")
                )
            )

        # ============================================================
        # 8. DELIVERABLES (from operator-dashboard/src/api/deliverables.ts)
        # ============================================================
        self.section("8. DELIVERABLES")

        # Test 8.1: Export package (generator.ts line 28-36)
        # Frontend sends: { projectId, clientId, format }
        # Converts to: { project_id, client_id, format }
        if self.project_id and self.client_id:
            deliverable_data = self.test_request(
                "POST /api/generator/export - Export deliverable",
                "POST",
                f"{API_BASE}/generator/export",
                json_data={
                    "project_id": self.project_id,
                    "client_id": self.client_id,
                    "format": "docx"
                },
                validate=lambda d: (
                    assert_has_key(d, "id"),
                    assert_has_key(d, "file_path")
                )
            )

            if deliverable_data:
                self.deliverable_id = deliverable_data["id"]
                self.log(f"  └─ Deliverable ID: {self.deliverable_id}", Colors.BLUE)

        # Test 8.2: List deliverables
        if self.project_id:
            self.test_request(
                f"GET /api/deliverables/?projectId={self.project_id} - List deliverables",
                "GET",
                f"{API_BASE}/deliverables/",
                params={"projectId": self.project_id}
            )

        # Test 8.3: Download deliverable
        if self.deliverable_id:
            self.test_request(
                f"GET /api/deliverables/{self.deliverable_id}/download - Download file",
                "GET",
                f"{API_BASE}/deliverables/{self.deliverable_id}/download"
            )

        # ============================================================
        # 9. ERROR HANDLING & EDGE CASES
        # ============================================================
        self.section("9. ERROR HANDLING & EDGE CASES")

        # Test 9.1: Invalid auth token
        self.test_request(
            "GET /api/projects/ - Invalid token (should fail)",
            "GET",
            f"{API_BASE}/projects/",
            expected_status=403,  # Backend returns 403 for "Not authenticated"
            include_auth=False
        )

        # Test 9.2: Missing required fields
        self.test_request(
            "POST /api/clients/ - Missing required fields (should fail)",
            "POST",
            f"{API_BASE}/clients/",
            expected_status=422,
            json_data={"email": "test@test.com"}  # Missing 'name'
        )

        # Test 9.3: Invalid ID format
        self.test_request(
            "GET /api/projects/invalid-id - Invalid ID (should fail)",
            "GET",
            f"{API_BASE}/projects/invalid-id",
            expected_status=404
        )

        # Test 9.4: Non-existent resource
        self.test_request(
            "GET /api/clients/client-nonexistent - Non-existent resource (should fail)",
            "GET",
            f"{API_BASE}/clients/client-nonexistent",
            expected_status=404
        )

    def print_summary(self):
        """Print final test summary"""
        self.section("TEST SUMMARY")

        total = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total * 100) if total > 0 else 0

        self.log(f"Total Tests:  {total}", Colors.BOLD)
        self.log(f"Passed:       {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed:       {self.tests_failed}", Colors.RED)
        self.log(f"Pass Rate:    {pass_rate:.1f}%", Colors.BOLD)

        if self.errors:
            self.log(f"\n{'─'*80}", Colors.RED)
            self.log("FAILED TESTS:", Colors.RED)
            self.log(f"{'─'*80}", Colors.RED)
            for i, error in enumerate(self.errors, 1):
                self.log(f"\n{i}. {error['test']}", Colors.RED)
                self.log(f"   {error['error']}", Colors.YELLOW)


# ============================================================
# VALIDATION HELPERS
# ============================================================

def assert_has_key(data: Dict, key: str):
    """Assert key exists in dict"""
    if key not in data:
        raise AssertionError(f"Missing key: '{key}'")

def assert_equals(value: Any, expected: Any):
    """Assert value equals expected"""
    if value != expected:
        raise AssertionError(f"Expected '{expected}', got '{value}'")

def assert_is_list(value: Any):
    """Assert value is a list"""
    if not isinstance(value, list):
        raise AssertionError(f"Expected list, got {type(value).__name__}")


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"FRONTEND API INTEGRATION TESTS")
    print(f"Testing all endpoints as called by operator-dashboard")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*80}{Colors.RESET}\n")

    tester = FrontendAPITester()
    tester.run_all_tests()
    tester.print_summary()

    # Exit with error code if any tests failed
    exit(0 if tester.tests_failed == 0 else 1)
