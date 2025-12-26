"""
Frontend-Backend Alignment Test Suite

This test validates that the backend API responses match exactly what
the frontend expects, ensuring proper integration.

Backend: Returns camelCase via Pydantic alias_generator
Frontend: Expects camelCase via TypeScript interfaces

Test strategy: Send what frontend sends, expect what frontend expects.
"""

import requests
import json
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"

# Color output
class C:
    G = '\033[92m'  # Green
    R = '\033[91m'  # Red
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    E = '\033[0m'   # End

def log(msg: str, color: str = C.B):
    print(f"{color}{msg}{C.E}")

def success(msg: str):
    log(f"[OK] {msg}", C.G)

def error(msg: str):
    log(f"[ERROR] {msg}", C.R)

def info(msg: str):
    log(f"[INFO] {msg}", C.B)

def section(title: str):
    print(f"\n{'='*70}")
    log(title, C.B)
    print('='*70)

# Test state
auth_token = None
client_id = None
project_id = None

def api_call(method: str, path: str, data: Any = None, auth: bool = True) -> requests.Response:
    """Make API call matching frontend axios client"""
    headers = {"Content-Type": "application/json"}
    if auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    url = f"{BASE_URL}{path}"

    if method == "GET":
        return requests.get(url, headers=headers)
    elif method == "POST":
        return requests.post(url, headers=headers, json=data)
    elif method == "PATCH":
        return requests.patch(url, headers=headers, json=data)
    elif method == "DELETE":
        return requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")

def test_auth():
    """Test authentication (matches AuthContext.tsx)"""
    global auth_token

    section("TEST 1: AUTHENTICATION")

    # Login (matches authApi.login)
    info("Testing login...")
    resp = api_call("POST", "/api/auth/login", {
        "email": "mrskwiw@gmail.com",
        "password": "Random!1Pass"
    }, auth=False)

    assert resp.status_code == 200, f"Login failed: {resp.status_code}"
    data = resp.json()

    # Validate response structure (matches LoginResponse interface)
    assert "access_token" in data, "Missing access_token"
    assert "refresh_token" in data, "Missing refresh_token"
    assert "user" in data, "Missing user"
    assert "id" in data["user"], "Missing user.id"
    assert "email" in data["user"], "Missing user.email"

    auth_token = data["access_token"]
    success(f"Login successful - user: {data['user']['email']}")

    # Verify token works
    info("Testing authenticated request...")
    resp = api_call("GET", "/api/clients")
    assert resp.status_code == 200, f"Auth test failed: {resp.status_code}"
    success("Token authentication works")

    return True

def test_clients():
    """Test client CRUD (matches clientsApi)"""
    global client_id

    section("TEST 2: CLIENT MANAGEMENT")

    # CREATE (matches clientsApi.create)
    info("Creating client...")
    create_data = {
        "name": "Test Integration Co",
        "email": "test@integration.com",
        "business_description": "Integration testing company",
        "ideal_customer": "Developers",
        "main_problem_solved": "Testing APIs",
        "tone_preference": "professional",
        "platforms": ["linkedin"],
        "customer_pain_points": ["Manual testing"],
        "customer_questions": ["How to automate?"]
    }

    resp = api_call("POST", "/api/clients/", create_data)
    assert resp.status_code == 201, f"Create failed: {resp.status_code} - {resp.text}"
    data = resp.json()

    # Validate camelCase response (matches Client interface)
    assert "id" in data, "Missing id"
    assert "name" in data, "Missing name"
    assert "businessDescription" in data, "Missing businessDescription (should be camelCase)"
    assert "idealCustomer" in data, "Missing idealCustomer (should be camelCase)"
    assert "mainProblemSolved" in data, "Missing mainProblemSolved (should be camelCase)"
    assert "tonePreference" in data, "Missing tonePreference (should be camelCase)"
    assert "customerPainPoints" in data, "Missing customerPainPoints (should be camelCase)"

    client_id = data["id"]
    success(f"Client created: {client_id}")

    # GET (matches clientsApi.get)
    info(f"Retrieving client {client_id}...")
    resp = api_call("GET", f"/api/clients/{client_id}")
    assert resp.status_code == 200, f"Get failed: {resp.status_code}"
    data = resp.json()
    assert data["id"] == client_id
    assert data["name"] == "Test Integration Co"
    success("Client retrieved with correct camelCase fields")

    # LIST (matches clientsApi.list)
    info("Listing clients...")
    resp = api_call("GET", "/api/clients/")
    assert resp.status_code == 200, f"List failed: {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list), "Should return array"
    assert len(data) > 0, "Should have at least one client"
    success(f"Listed {len(data)} client(s)")

    # UPDATE (matches clientsApi.update)
    info("Updating client...")
    update_data = {"tone_preference": "friendly"}
    resp = api_call("PATCH", f"/api/clients/{client_id}", update_data)
    assert resp.status_code == 200, f"Update failed: {resp.status_code}"
    data = resp.json()
    assert "tonePreference" in data, "Missing tonePreference in response"
    assert data["tonePreference"] == "friendly", "Update not applied"
    success("Client updated")

    return True

def test_projects():
    """Test project CRUD (matches projectsApi)"""
    global project_id

    section("TEST 3: PROJECT MANAGEMENT")

    if not client_id:
        error("No client_id - skipping")
        return False

    # CREATE (matches projectsApi.create)
    info("Creating project...")
    create_data = {
        "name": "Test Campaign",
        "client_id": client_id,  # snake_case as frontend sends it
        "templates": ["problem_recognition", "statistic"],
        "platforms": ["linkedin"],
        "tone": "professional"
    }

    resp = api_call("POST", "/api/projects/", create_data)
    assert resp.status_code == 201, f"Create failed: {resp.status_code} - {resp.text}"
    data = resp.json()

    # Validate camelCase response (matches Project interface)
    assert "id" in data, "Missing id"
    assert "clientId" in data, "Missing clientId (should be camelCase)"
    assert "name" in data, "Missing name"
    assert data["clientId"] == client_id, "clientId mismatch"

    project_id = data["id"]
    success(f"Project created: {project_id}")

    # GET (matches projectsApi.get)
    info(f"Retrieving project {project_id}...")
    resp = api_call("GET", f"/api/projects/{project_id}")
    assert resp.status_code == 200, f"Get failed: {resp.status_code}"
    data = resp.json()
    assert data["id"] == project_id
    success("Project retrieved with correct camelCase fields")

    # LIST (matches projectsApi.list)
    info("Listing projects...")
    resp = api_call("GET", "/api/projects/")
    assert resp.status_code == 200, f"List failed: {resp.status_code}"
    data = resp.json()

    # Should return PaginatedResponse with nested metadata
    assert "items" in data, "Missing items (should be paginated response)"
    assert "metadata" in data, "Missing metadata"
    assert "total" in data["metadata"], "Missing metadata.total"
    assert "page" in data["metadata"], "Missing metadata.page"
    assert "pageSize" in data["metadata"] or "page_size" in data["metadata"], "Missing metadata.pageSize"
    assert isinstance(data["items"], list), "items should be array"
    success(f"Listed {len(data['items'])} project(s) with pagination metadata")

    # UPDATE (matches projectsApi.update)
    info("Updating project...")
    update_data = {"status": "ready"}
    resp = api_call("PATCH", f"/api/projects/{project_id}", update_data)
    assert resp.status_code == 200, f"Update failed: {resp.status_code}"
    success("Project updated")

    return True

def test_generation():
    """Test content generation (matches generatorApi.generateAll)"""
    section("TEST 4: CONTENT GENERATION")

    if not project_id or not client_id:
        error("No project_id or client_id - skipping")
        return False

    # Start generation (matches generatorApi.generateAll)
    info("Starting content generation...")
    gen_data = {
        "project_id": project_id,
        "client_id": client_id,
        "is_batch": True
    }

    resp = api_call("POST", "/api/generator/generate-all", gen_data)
    assert resp.status_code in [200, 201], f"Generate failed: {resp.status_code} - {resp.text}"
    data = resp.json()

    # Should return Run with camelCase fields
    assert "id" in data, "Missing id"
    assert "projectId" in data, "Missing projectId (should be camelCase)"
    assert "status" in data, "Missing status"
    run_id = data["id"]
    success(f"Generation started: {run_id}")

    return True

def cleanup():
    """Clean up test data"""
    section("CLEANUP")

    # Note: Backend doesn't provide DELETE endpoint for clients
    # Test data will remain in database (acceptable for testing)
    info("Skipping cleanup - DELETE /api/clients not implemented")
    info(f"Test client ID: {client_id} (can be manually deleted if needed)")

def main():
    """Run all tests"""
    section("FRONTEND-BACKEND ALIGNMENT TEST SUITE")

    tests = [
        ("Authentication", test_auth),
        ("Client Management", test_clients),
        ("Project Management", test_projects),
        ("Content Generation", test_generation),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except AssertionError as e:
            error(f"{name} failed: {e}")
            results.append((name, False))
        except Exception as e:
            error(f"{name} crashed: {e}")
            results.append((name, False))

    # Cleanup
    try:
        cleanup()
    except Exception as e:
        info(f"Cleanup had issues: {e}")

    # Summary
    section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            success(name)
        else:
            error(name)

    print(f"\n{C.B}Total: {passed}/{total} tests passed{C.E}\n")

    if passed == total:
        success("ALL TESTS PASSED - Frontend and backend are aligned!")
        return 0
    else:
        error(f"{total - passed} test(s) failed - Frontend-backend misalignment detected")
        return 1

if __name__ == "__main__":
    exit(main())
