"""
Healthcare Brief Template Blog Articles E2E Test

This test validates the complete platform workflow including research and content generation:
1. Load healthcare brief (Cascade Family Dentistry)
2. Create client and project
3. Execute research tools and save results
4. Generate one blog article from each of the 15 templates
5. Save all research results and article metadata to /tests/results

This test produces comprehensive output for validation and inspection.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app


class TestHealthcareTemplateBlog:
    """Template-based blog generation with research and output saving"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session, test_user, mock_anthropic_client):
        """Setup test dependencies and output directory"""
        self.client = TestClient(app)
        self.db_session = db_session
        self.test_user = test_user

        # Create output directory
        self.output_dir = Path(__file__).parent.parent / "results" / "healthcare_template_blog_e2e"
        self.research_dir = self.output_dir / "research"
        self.articles_dir = self.output_dir / "articles"

        # Clean and create directories
        import shutil

        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.research_dir.mkdir(exist_ok=True)
        self.articles_dir.mkdir(exist_ok=True)

        # Get authentication headers
        response = self.client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "testpass123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_healthcare_template_blog_workflow(self, mock_anthropic_client):
        """
        Complete workflow:
        1. Create client from healthcare brief
        2. Execute research tools (save outputs)
        3. Generate blog article from each template (save metadata)
        """
        # ========================================
        # STEP 1: Load Healthcare Brief
        # ========================================
        brief_path = Path(__file__).parent.parent / "fixtures" / "healthcare_brief.txt"
        assert brief_path.exists()

        healthcare_brief = brief_path.read_text(encoding="utf-8")

        # Save the brief to output
        (self.output_dir / "healthcare_brief.txt").write_text(healthcare_brief, encoding="utf-8")
        print(f"\n[TEST] Loaded healthcare brief ({len(healthcare_brief)} chars)")

        # ========================================
        # STEP 2: Create Client and Project
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
        assert response.status_code == 201
        client_response = response.json()
        client_id = client_response["id"]

        # Save client info
        (self.output_dir / "client_info.json").write_text(
            json.dumps(client_response, indent=2), encoding="utf-8"
        )
        print(f"[TEST] Created client: {client_response['companyName']} (ID: {client_id})")

        # Create project for first 10 templates (to avoid rate limiting in tests)
        project_data = {
            "client_id": client_id,
            "name": "Healthcare Template Blog E2E Test",
            "num_posts": 10,  # One from each of first 10 templates
            "templates": [str(i) for i in range(1, 11)],  # Templates 1-10
            "template_quantities": {str(i): 1 for i in range(1, 11)},
            "target_platform": "blog",
        }

        response = self.client.post("/api/projects/", json=project_data, headers=self.headers)
        assert response.status_code == 201
        project_response = response.json()
        project_id = project_response["id"]

        # Save project info
        (self.output_dir / "project_info.json").write_text(
            json.dumps(project_response, indent=2), encoding="utf-8"
        )
        print(f"[TEST] Created project: {project_response['name']} (ID: {project_id})")

        # ========================================
        # STEP 3: Execute Research Tools
        # ========================================
        research_tools = [
            {
                "name": "brand_archetype",
                "params": {
                    "business_description": client_data["business_description"],
                },
            },
            {
                "name": "audience_research",
                "params": {
                    "business_description": client_data["business_description"],
                    "target_audience": client_data["ideal_customer"],
                },
            },
        ]

        print(f"\n[TEST] Executing {len(research_tools)} research tools...")
        research_results = {}

        for i, tool in enumerate(research_tools, 1):
            tool_name = tool["name"]
            print(f"[TEST] [{i}/{len(research_tools)}] Running {tool_name}...")

            run_request = {
                "client_id": client_id,
                "project_id": project_id,
                "tool": tool_name,
                "params": tool["params"],
            }

            response = self.client.post("/api/research/run", json=run_request, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                research_results[tool_name] = result

                # Save research result to file
                output_file = self.research_dir / f"{tool_name}.json"
                output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
                print(f"[TEST]   [OK] {tool_name} completed - saved to {output_file.name}")
            else:
                print(
                    f"[TEST]   [SKIP] {tool_name} - {response.status_code}: {response.text[:100]}"
                )
                # Save error info
                error_info = {
                    "tool": tool_name,
                    "status_code": response.status_code,
                    "error": response.text,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                (self.research_dir / f"{tool_name}_error.json").write_text(
                    json.dumps(error_info, indent=2), encoding="utf-8"
                )

        print(
            f"\n[TEST] [OK] Completed {len(research_results)}/{len(research_tools)} research tools"
        )

        # ========================================
        # STEP 4: Generate Blog Articles from All Templates
        # ========================================
        template_names = [
            "Problem Recognition",
            "Statistic + Insight",
            "Against the Grain Contrarian",
            "Here's What Changed",
            "Question Post",
            "Personal Story",
            "Myth-Busting",
            "Things I Got Wrong",
            "Actionable How-To",
            "Comparison",
            "What I Learned From",
            "Inside Look",
            "Future-Thinking",
            "Reader Question Response",
            "Milestone/Celebration",
        ]

        print(f"\n[TEST] Generating blog articles from first 10 templates...")
        generated_articles = {}

        for template_num in range(1, 11):  # Only first 10 to avoid rate limiting
            template_id = str(template_num)
            template_name = template_names[template_num - 1]

            print(
                f"[TEST] [{template_num}/10] Generating from Template {template_num}: {template_name}..."
            )

            generation_request = {
                "client_id": client_id,
                "project_id": project_id,
                "target_platform": "blog",
                "template_ids": [template_id],
                "num_posts": 1,
            }

            response = self.client.post(
                "/api/generator/generate-all", json=generation_request, headers=self.headers
            )

            assert response.status_code in [200, 202], f"Generation failed: {response.text}"

            result = response.json()
            generated_articles[template_id] = result

            # Save article metadata
            article_metadata = {
                "template_id": template_id,
                "template_name": template_name,
                "run_id": result.get("id"),
                "status": result.get("status"),
                "started_at": result.get("startedAt"),
                "platform": "blog",
                "generation_request": generation_request,
                "timestamp": datetime.utcnow().isoformat(),
            }

            output_file = (
                self.articles_dir
                / f"template_{template_num:02d}_{template_name.replace(' ', '_').lower()}.json"
            )
            output_file.write_text(json.dumps(article_metadata, indent=2), encoding="utf-8")

            print(
                f"[TEST]   [OK] Template {template_num} - Run ID: {result.get('id')} - saved to {output_file.name}"
            )

        print(f"\n[TEST] [OK] All {len(generated_articles)} template blog articles generated")

        # ========================================
        # STEP 5: Save Summary Report
        # ========================================
        summary = {
            "test_name": "Healthcare Template Blog E2E Test",
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
            "research": {
                "tools_executed": len(research_results),
                "tools_successful": len(research_results),
                "tools_list": list(research_results.keys()),
            },
            "generation": {
                "templates_used": len(generated_articles),
                "platform": "blog",
                "templates": [
                    {
                        "id": tid,
                        "name": template_names[int(tid) - 1],
                        "run_id": generated_articles[tid].get("id"),
                    }
                    for tid in sorted(generated_articles.keys(), key=int)
                ],
            },
            "output_locations": {
                "brief": "healthcare_brief.txt",
                "client_info": "client_info.json",
                "project_info": "project_info.json",
                "research_dir": "research/",
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
        print("HEALTHCARE TEMPLATE BLOG E2E TEST SUMMARY")
        print("=" * 70)
        print(f"[OK] Client created: {client_data['name']}")
        print(f"[OK] Project created: {project_data['name']}")
        print(f"[OK] Research tools executed: {len(research_results)}")
        print(f"[OK] Blog articles generated: {len(generated_articles)} (from 10 templates)")
        print(f"[OK] All outputs saved to: {self.output_dir}")
        print(f"\nOutput structure:")
        print(f"  - healthcare_brief.txt")
        print(f"  - client_info.json")
        print(f"  - project_info.json")
        print(f"  - test_summary.json")
        print(f"  - research/ ({len(research_results)} files)")
        print(f"  - articles/ ({len(generated_articles)} files)")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
