#!/usr/bin/env python3
"""
Test script to verify backend integration without inference calls
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"[OK] Health check: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_api_health():
    """Test API health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"[OK] API health check: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_login():
    """Test authentication"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "mrskwiw@gmail.com", "password": "Random!1Pass"}
    )
    print(f"[OK] Login: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Token received: {data['access_token'][:50]}...")
        return data['access_token']
    else:
        print(f"  Error: {response.json()}")
        return None

def test_clients_endpoint(token):
    """Test clients endpoint with auth"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
    print(f"[OK] Clients endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        # API returns a list directly or a dict with 'clients' key
        if isinstance(data, list):
            print(f"  Clients found: {len(data)}")
        else:
            print(f"  Clients found: {len(data.get('clients', []))}")
    else:
        print(f"  Error: {response.json()}")
    return response.status_code == 200

def test_projects_endpoint(token):
    """Test projects endpoint with auth"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    print(f"[OK] Projects endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        # API returns a list directly or a dict with 'projects' key
        if isinstance(data, list):
            print(f"  Projects found: {len(data)}")
        else:
            print(f"  Projects found: {len(data.get('projects', []))}")
    else:
        print(f"  Error: {response.json()}")
    return response.status_code == 200

def main():
    """Run all integration tests"""
    print("=== Backend Integration Tests (No Inference) ===\n")

    # Test health endpoints
    test_health()
    print()
    test_api_health()
    print()

    # Test authentication
    token = test_login()
    print()

    if token:
        # Test authenticated endpoints
        test_clients_endpoint(token)
        print()
        test_projects_endpoint(token)
        print()

    print("=== Integration tests complete ===")

if __name__ == "__main__":
    main()
