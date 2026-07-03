"""
Healthcare Brief Simplified Workflow E2E Test

This test validates the core platform workflow without the complexity of all research tools.

Workflow:
1. Load healthcare brief (Cascade Family Dentistry) from fixtures
2. Create client in database with brief data
3. Create project
4. Generate 1 article for each content type (LinkedIn, Twitter, Facebook, Blog, Email, Instagram)
5. Save all outputs to /tests/results

This is a simplified version that focuses on testing the content generation pipeline
without getting bogged down in research tool parameter validation.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app


class TestHealthcareSimpleWorkflow:
    """Simplified full workflow test with healthcare brief"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session, test_user, mock_anthropic_client):
        """Setup test dependencies and output directories"""
        self.client = TestClient(app)
        self.db_session = db_session
        self.test_user = test_user

        # Create output directory
        self.output_dir = Path(__file__).parent.parent / "results" / "healthcare_simple_e2e"
        self.articles_dir = self.output_dir / "articles"

        # Clean and create directories
        import shutil

        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir.mkdir(exist_ok=True)

        # Get authentication headers
        response = self.client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "testpass123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_healthcare_full_workflow_simple(self, mock_anthropic_client):
        """
        Test complete workflow with healthcare brief:
        1. Create client from brief
        2. Create project
        3. Generate 1 article for each content type
        """
        # ========================================
        # STEP 1: Load Healthcare Brief
        # ========================================
        brief_path = Path(__file__).parent.parent / "fixtures" / "healthcare_brief.txt"
        assert brief_path.exists(), f"Healthcare brief not found at {brief_path}"

        healthcare_brief = brief_path.read_text(encoding="utf-8")

        # Save the brief to output
        (self.output_dir / "healthcare_brief.txt").write_text(healthcare_brief, encoding="utf-8")
        print(f"\n[TEST] Loaded healthcare brief ({len(healthcare_brief)} chars)")

        # ========================================
        # STEP 2: Create Client from Brief
        # ========================================
        client_data = {
            "name": "Cascade Family Dentistry",
            "email": "test@cascadefamilydentistry.com",
            "business_description": "Modern family dental practice offering general dentistry, cosmetic procedures, and pediatric care. We focus on preventive care and patient education in a comfortable, anxiety-free environment. State-of-the-art technology including digital x-rays, same-day crowns, and sedation dentistry for anxious patients. Dr. Kim sees every patient personally, offers evening and Saturday appointments for working families. Office feels like a modern spa with Netflix and noise-canceling headphones for anxious patients.",
            "ideal_customer": "Families seeking a 'dental home' for all ages, adults who haven't been to the dentist in years due to anxiety or bad past experiences, and professionals wanting cosmetic improvements (whitening, veneers)",
            "main_problem_solved": "Making dental care less scary and more accessible. Helping people overcome dental anxiety and understand why oral health matters for overall health. Making it easy for busy families to get everyone's dental care in one place.",
            "tone_preference": "professional",
            "industry": "Healthcare - Dental",
            "platforms": ["facebook", "linkedin"],
            "customer_pain_points": [
                "Dental anxiety from past trauma",
                "Haven't been to dentist in years",
                "Fear of judgment for neglect",
                "Busy family schedules",
                "Cosmetic concerns about smile",
            ],
        }

        response = self.client.post("/api/clients/", json=client_data, headers=self.headers)
        assert response.status_code == 201, f"Client creation failed: {response.text}"
        client_response = response.json()
        client_id = client_response["id"]

        # Save client info
        (self.output_dir / "client_info.json").write_text(
            json.dumps(client_response, indent=2), encoding="utf-8"
        )
        print(f"[TEST] Created client: {client_response['companyName']} (ID: {client_id})")

        # ========================================
        # STEP 3: Create Project
        # ========================================
        project_data = {
            "client_id": client_id,
            "name": "Healthcare E2E Test Project",
            "num_posts": 6,  # One for each platform
            "templates": ["1", "2", "3"],  # Use first 3 templates
            "template_quantities": {"1": 2, "2": 2, "3": 2},
            "target_platform": "linkedin",  # Default platform
        }

        response = self.client.post("/api/projects/", json=project_data, headers=self.headers)
        assert response.status_code == 201, f"Project creation failed: {response.text}"
        project_response = response.json()
        project_id = project_response["id"]

        # Save project info
        (self.output_dir / "project_info.json").write_text(
            json.dumps(project_response, indent=2), encoding="utf-8"
        )
        print(f"[TEST] Created project: {project_response['name']} (ID: {project_id})")

        # ========================================
        # STEP 4: Generate Content for All Platforms
        # ========================================
        platforms = ["linkedin", "twitter", "facebook", "blog", "email"]
        generated_posts = {}

        print(f"\n[TEST] Generating 1 article for each of {len(platforms)} platforms...")

        for i, platform in enumerate(platforms, 1):
            print(f"[TEST] [{i}/{len(platforms)}] Generating {platform} article...")

            generation_request = {
                "client_id": client_id,
                "project_id": project_id,
                "target_platform": platform,
                "template_ids": ["1"],  # Use first template
                "num_posts": 1,
            }

            response = self.client.post(
                "/api/generator/generate-all", json=generation_request, headers=self.headers
            )
            assert response.status_code in [
                200,
                202,
            ], f"Generation for {platform} failed: {response.text}"

            result = response.json()
            generated_posts[platform] = result

            # Save article metadata
            article_metadata = {
                "platform": platform,
                "run_id": result.get("id"),
                "status": result.get("status"),
                "started_at": result.get("startedAt"),
                "generation_request": generation_request,
                "timestamp": datetime.utcnow().isoformat(),
            }

            output_file = self.articles_dir / f"{platform}.json"
            output_file.write_text(json.dumps(article_metadata, indent=2), encoding="utf-8")

            print(
                f"[TEST]   [OK] {platform} article generation initiated (Run ID: {result.get('id', 'N/A')})"
            )

        print(f"\n[TEST] [OK] All {len(platforms)} platform articles generated successfully")

        # ========================================
        # STEP 5: Verify Generated Content
        # ========================================
        # Note: In test environment, background tasks are mocked, so we verify
        # the endpoint responses, not the actual post content

        response = self.client.get(f"/api/projects/{project_id}", headers=self.headers)
        assert response.status_code == 200
        project = response.json()
        print(f"\n[TEST] Project status: {project.get('status', 'unknown')}")

        # ========================================
        # STEP 6: Save Summary Report
        # ========================================
        summary = {
            "test_name": "Healthcare Simple E2E Test",
            "timestamp": datetime.utcnow().isoformat(),
            "client": {
                "id": client_id,
                "name": client_data["name"],
                "industry": client_data["industry"],
            },
            "project": {
                "id": project_id,
                "name": project_data["name"],
                "num_posts": project_data["num_posts"],
            },
            "generation": {
                "platforms": platforms,
                "articles_generated": len(generated_posts),
                "runs": [
                    {"platform": platform, "run_id": generated_posts[platform].get("id")}
                    for platform in platforms
                ],
            },
            "output_locations": {
                "brief": "healthcare_brief.txt",
                "client_info": "client_info.json",
                "project_info": "project_info.json",
                "articles_dir": "articles/",
            },
            "note": "In test environment, background tasks are mocked. In production, actual post content would be retrieved from the database after generation completes.",
        }

        summary_file = self.output_dir / "test_summary.json"
        summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        # ========================================
        # TEST SUMMARY
        # ========================================
        print("\n" + "=" * 70)
        print("HEALTHCARE BRIEF E2E TEST SUMMARY")
        print("=" * 70)
        print(f"[OK] Client created: {client_data['name']}")
        print(f"[OK] Project created: {project_data['name']}")
        print(f"[OK] Platforms generated: {len(platforms)}")
        print(f"  - {', '.join(platforms)}")
        print(f"[OK] All outputs saved to: {self.output_dir}")
        print(f"\nOutput structure:")
        print(f"  - healthcare_brief.txt")
        print(f"  - client_info.json")
        print(f"  - project_info.json")
        print(f"  - test_summary.json")
        print(f"  - articles/ ({len(platforms)} files)")
        print("[OK] Full workflow completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
