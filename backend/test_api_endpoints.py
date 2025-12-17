"""
Test script for Direct API endpoints.

This script tests all Phase 2 endpoints to verify:
- Backend starts correctly
- All routers are accessible
- JWT authentication works
- CRUD operations function properly
- Database operations succeed

Run with: python test_api_endpoints.py
"""
import asyncio
import io
import sys

import httpx

# Fix UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# API configuration
API_BASE = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "SecurePassword123!"


class APITester:
    def __init__(self):
        self.base_url = API_BASE
        self.access_token = None
        self.client_id = None
        self.project_id = None
        self.brief_id = None
        self.deliverable_id = None
        self.post_id = None

    async def test_health_check(self):
        """Test /health endpoint"""
        print("\n🔍 Testing health check endpoint...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            data = response.json()
            assert data["status"] == "healthy", "API not healthy"
            print("[OK] Health check passed")
            print(f"   Rate limits: {data['rate_limits']}")

    async def test_register_user(self):
        """Test POST /api/auth/register"""
        print("\n🔍 Testing user registration...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/register",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "full_name": "Test User"},
            )
            if response.status_code == 400 and "already registered" in response.text:
                print("[WARNING]  User already exists (expected if running multiple times)")
                return
            assert (
                response.status_code == 201
            ), f"Registration failed: {response.status_code} - {response.text}"
            data = response.json()
            assert "access_token" in data, "No access token in response"
            self.access_token = data["access_token"]
            print("[OK] User registration successful")

    async def test_login(self):
        """Test POST /api/auth/login"""
        print("\n🔍 Testing login...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            assert (
                response.status_code == 200
            ), f"Login failed: {response.status_code} - {response.text}"
            data = response.json()
            assert "access_token" in data, "No access token in response"
            self.access_token = data["access_token"]
            print("[OK] Login successful")
            print(f"   Access token: {self.access_token[:20]}...")

    def get_headers(self):
        """Get authentication headers"""
        return {"Authorization": f"Bearer {self.access_token}"}

    async def test_create_client(self):
        """Test POST /api/clients/"""
        print("\n🔍 Testing client creation...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/clients/",
                headers=self.get_headers(),
                json={"name": "Test Client Corp", "email": "client@testclient.com"},
            )
            assert (
                response.status_code == 201
            ), f"Client creation failed: {response.status_code} - {response.text}"
            data = response.json()
            assert "id" in data, "No id in response"
            self.client_id = data["id"]
            print("[OK] Client created successfully")
            print(f"   Client ID: {self.client_id}")

    async def test_list_clients(self):
        """Test GET /api/clients/"""
        print("\n🔍 Testing list clients...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/clients/", headers=self.get_headers())
            assert (
                response.status_code == 200
            ), f"List clients failed: {response.status_code} - {response.text}"
            data = response.json()
            assert isinstance(data, list), "Response should be a list"
            assert len(data) > 0, "No clients found"
            print(f"[OK] Listed {len(data)} client(s)")

    async def test_get_client(self):
        """Test GET /api/clients/{client_id}"""
        print("\n🔍 Testing get client by ID...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/clients/{self.client_id}", headers=self.get_headers()
            )
            assert (
                response.status_code == 200
            ), f"Get client failed: {response.status_code} - {response.text}"
            data = response.json()
            assert data["id"] == self.client_id, "Client ID mismatch"
            assert data["name"] == "Test Client Corp", "Client name mismatch"
            print("[OK] Client retrieved successfully")

    async def test_create_project(self):
        """Test POST /api/projects/"""
        print("\n🔍 Testing project creation...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/projects/",
                headers=self.get_headers(),
                json={
                    "name": "Test Project",
                    "client_id": self.client_id,
                    "templates": ["1", "2", "3"],
                    "platforms": ["linkedin", "twitter"],
                    "tone": "professional",
                },
            )
            assert (
                response.status_code == 201
            ), f"Project creation failed: {response.status_code} - {response.text}"
            data = response.json()
            assert "id" in data, "No project id in response"
            self.project_id = data["id"]
            print("[OK] Project created successfully")
            print(f"   Project ID: {self.project_id}")

    async def test_list_projects(self):
        """Test GET /api/projects/"""
        print("\n🔍 Testing list projects...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/projects/", headers=self.get_headers()
            )
            assert (
                response.status_code == 200
            ), f"List projects failed: {response.status_code} - {response.text}"
            data = response.json()
            assert isinstance(data, list), "Response should be a list"
            assert len(data) > 0, "No projects found"
            print(f"[OK] Listed {len(data)} project(s)")

    async def test_get_project(self):
        """Test GET /api/projects/{project_id}"""
        print("\n🔍 Testing get project by ID...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/projects/{self.project_id}", headers=self.get_headers()
            )
            assert (
                response.status_code == 200
            ), f"Get project failed: {response.status_code} - {response.text}"
            data = response.json()
            assert data["id"] == self.project_id, "Project ID mismatch"
            assert data["name"] == "Test Project", "Project name mismatch"
            print("[OK] Project retrieved successfully")

    async def test_update_project(self):
        """Test PUT /api/projects/{project_id}"""
        print("\n🔍 Testing project update...")
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/projects/{self.project_id}",
                headers=self.get_headers(),
                json={"name": "Updated Test Project", "status": "processing"},
            )
            assert (
                response.status_code == 200
            ), f"Project update failed: {response.status_code} - {response.text}"
            data = response.json()
            assert data["name"] == "Updated Test Project", "Project name not updated"
            assert data["status"] == "processing", "Project status not updated"
            print("[OK] Project updated successfully")

    async def test_create_brief_paste(self):
        """Test POST /api/briefs/create (paste text)"""
        print("\n🔍 Testing brief creation (paste)...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/briefs/create",
                headers=self.get_headers(),
                json={
                    "project_id": self.project_id,
                    "content": "This is a test client brief with all the necessary information.",
                },
            )
            assert (
                response.status_code == 201
            ), f"Brief creation failed: {response.status_code} - {response.text}"
            data = response.json()
            assert "id" in data, "No brief id in response"
            self.brief_id = data["id"]
            print("[OK] Brief created successfully")
            print(f"   Brief ID: {self.brief_id}")

    async def test_get_brief(self):
        """Test GET /api/briefs/{brief_id}"""
        print("\n🔍 Testing get brief by ID...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/briefs/{self.brief_id}", headers=self.get_headers()
            )
            assert (
                response.status_code == 200
            ), f"Get brief failed: {response.status_code} - {response.text}"
            data = response.json()
            assert data["id"] == self.brief_id, "Brief ID mismatch"
            assert data["project_id"] == self.project_id, "Project ID mismatch"
            print("[OK] Brief retrieved successfully")

    async def test_list_posts(self):
        """Test GET /api/posts/"""
        print("\n🔍 Testing list posts...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/posts/", headers=self.get_headers())
            assert (
                response.status_code == 200
            ), f"List posts failed: {response.status_code} - {response.text}"
            data = response.json()
            assert isinstance(data, list), "Response should be a list"
            print(f"[OK] Listed {len(data)} post(s)")

    async def test_list_deliverables(self):
        """Test GET /api/deliverables/"""
        print("\n🔍 Testing list deliverables...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/deliverables/", headers=self.get_headers()
            )
            assert (
                response.status_code == 200
            ), f"List deliverables failed: {response.status_code} - {response.text}"
            data = response.json()
            assert isinstance(data, list), "Response should be a list"
            print(f"[OK] Listed {len(data)} deliverable(s)")

    async def test_delete_project(self):
        """Test DELETE /api/projects/{project_id}"""
        print("\n🔍 Testing project deletion...")
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/projects/{self.project_id}", headers=self.get_headers()
            )
            assert (
                response.status_code == 204
            ), f"Project deletion failed: {response.status_code} - {response.text}"
            print("[OK] Project deleted successfully")

    async def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("[RUN] Starting API Endpoint Tests")
        print("=" * 60)

        try:
            # Phase 1: Health and Auth
            await self.test_health_check()
            await self.test_register_user()
            await self.test_login()

            # Phase 2: Clients
            await self.test_create_client()
            await self.test_list_clients()
            await self.test_get_client()

            # Phase 3: Projects
            await self.test_create_project()
            await self.test_list_projects()
            await self.test_get_project()
            await self.test_update_project()

            # Phase 4: Briefs
            await self.test_create_brief_paste()
            await self.test_get_brief()

            # Phase 5: Posts and Deliverables
            await self.test_list_posts()
            await self.test_list_deliverables()

            # Phase 6: Cleanup
            await self.test_delete_project()

            print("\n" + "=" * 60)
            print("[OK] All API tests passed successfully!")
            print("=" * 60)

        except AssertionError as e:
            print("\n" + "=" * 60)
            print(f"[FAILED] Test failed: {e}")
            print("=" * 60)
            sys.exit(1)
        except Exception as e:
            print("\n" + "=" * 60)
            print(f"[FAILED] Unexpected error: {e}")
            print("=" * 60)
            sys.exit(1)


async def main():
    """Main test runner"""
    print("\n[WARNING]  Make sure the backend is running on http://localhost:8000")
    print("   Start it with: cd project/backend && python main.py\n")

    tester = APITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
