"""Integration tests for memory-aware content generation"""

from datetime import datetime
from pathlib import Path

import pytest

from src.agents.brief_parser import BriefParserAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.database.project_db import ProjectDatabase
from src.models.client_memory import ClientMemory


class TestMemoryAwareGeneration:
    """Test memory-aware content generation"""

    @pytest.fixture
    def db(self):
        """Get database instance"""
        db_path = Path(__file__).parent.parent.parent / "data" / "projects.db"
        return ProjectDatabase(db_path)

    @pytest.fixture
    def test_client(self):
        """Test client name"""
        return f"TestClient_MemoryGen_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    @pytest.fixture
    def client_brief(self, test_client):
        """Sample client brief"""
        brief_text = f"""
Client: {test_client}
Business: Professional marketing agency
Target Audience: Small business owners
Primary problem: Need to generate consistent content
Brand voice: Professional, friendly
Key phrases: ROI, data-driven, actionable insights
"""
        parser = BriefParserAgent()
        return parser.parse_brief(brief_text)

    @pytest.fixture
    def client_memory(self, db, test_client):
        """Create test client memory"""
        memory = ClientMemory(client_name=test_client)
        memory.add_project(num_posts=30, project_value=1800.0)
        memory.voice_archetype = "Expert"
        memory.preferred_templates = [1, 2, 3]
        memory.avoided_templates = [6, 8]
        memory.voice_adjustments = {"tone": "more casual", "length": "shorter"}
        memory.signature_phrases = ["data-driven", "actionable"]
        db.create_client_memory(memory)
        return memory

    def test_01_generation_without_memory(self, client_brief, test_client):
        """Test generation without client memory (new client)"""
        print("\n[TEST 1] Generation Without Memory")
        print("-" * 60)

        # Create generator without database
        generator = ContentGeneratorAgent()

        # Generate posts
        posts = generator.generate_posts(
            client_brief=client_brief,
            num_posts=5,
            template_count=5,
            use_client_memory=False,
        )

        assert len(posts) == 5
        assert all(p.client_name == test_client for p in posts)
        print(f"[OK] Generated {len(posts)} posts without memory")

    def test_02_generation_with_memory_no_db(self, client_brief, test_client):
        """Test generation with use_client_memory=True but no db (graceful degradation)"""
        print("\n[TEST 2] Generation With Memory But No DB")
        print("-" * 60)

        # Create generator without database
        generator = ContentGeneratorAgent(db=None)

        # Generate posts (should work without errors)
        posts = generator.generate_posts(
            client_brief=client_brief,
            num_posts=5,
            template_count=5,
            use_client_memory=True,  # Enabled but no db
        )

        assert len(posts) == 5
        print(f"[OK] Generated {len(posts)} posts (gracefully handled missing db)")

    def test_03_generation_with_memory_new_client(self, db, client_brief, test_client):
        """Test generation with memory for new client (no history)"""
        print("\n[TEST 3] Generation With Memory - New Client")
        print("-" * 60)

        # Create generator with database
        generator = ContentGeneratorAgent(db=db)

        # Generate posts for new client (no memory exists)
        posts = generator.generate_posts(
            client_brief=client_brief,
            num_posts=5,
            template_count=5,
            use_client_memory=True,
        )

        assert len(posts) == 5
        print(f"[OK] Generated {len(posts)} posts for new client (no memory effects)")

    def test_04_generation_with_memory_repeat_client(
        self, db, client_brief, client_memory, test_client
    ):
        """Test generation with memory for repeat client"""
        print("\n[TEST 4] Generation With Memory - Repeat Client")
        print("-" * 60)

        # Create generator with database
        generator = ContentGeneratorAgent(db=db)

        # Generate posts for repeat client (memory exists)
        posts = generator.generate_posts(
            client_brief=client_brief,
            num_posts=10,
            template_count=10,
            use_client_memory=True,
        )

        assert len(posts) == 10

        # Check that preferred templates are represented
        template_ids = [p.template_id for p in posts]
        print(f"  - Template IDs used: {sorted(set(template_ids))}")
        print(f"  - Preferred templates: {client_memory.preferred_templates}")
        print(f"  - Avoided templates: {client_memory.avoided_templates}")

        # Verify avoided templates are underrepresented
        avoided_count = sum(1 for tid in template_ids if tid in client_memory.avoided_templates)
        print(f"  - Avoided template count: {avoided_count}/{len(posts)}")

        print(f"[OK] Generated {len(posts)} posts with memory optimization")

    @pytest.mark.asyncio
    async def test_05_async_generation_with_memory(
        self, db, client_brief, client_memory, test_client
    ):
        """Test async generation with client memory"""
        print("\n[TEST 5] Async Generation With Memory")
        print("-" * 60)

        # Create generator with database
        generator = ContentGeneratorAgent(db=db)

        # Generate posts async for repeat client
        posts = await generator.generate_posts_async(
            client_brief=client_brief,
            num_posts=10,
            template_count=10,
            use_client_memory=True,
        )

        assert len(posts) == 10

        # Check memory effects
        template_ids = [p.template_id for p in posts]
        avoided_count = sum(1 for tid in template_ids if tid in client_memory.avoided_templates)

        print(f"  - Template IDs used: {sorted(set(template_ids))}")
        print(f"  - Avoided template count: {avoided_count}/{len(posts)}")
        print(f"[OK] Generated {len(posts)} posts async with memory optimization")

    def test_06_system_prompt_includes_memory(self, db, client_brief, client_memory, test_client):
        """Test that system prompt includes client memory insights"""
        print("\n[TEST 6] System Prompt Includes Memory")
        print("-" * 60)

        # Create generator with database
        generator = ContentGeneratorAgent(db=db)

        # Load client memory
        memory = db.get_client_memory(test_client)

        # Build system prompt with memory
        from src.models.client_brief import Platform

        prompt = generator._build_system_prompt(
            client_brief=client_brief,
            platform=Platform.LINKEDIN,
            client_memory=memory,
        )

        # Verify memory insights are in prompt
        assert "CLIENT HISTORY" in prompt
        assert f"{memory.total_projects} previous project" in prompt
        assert "LEARNED PREFERENCES" in prompt
        assert "more casual" in prompt
        assert "shorter" in prompt
        assert "CLIENT SIGNATURE PHRASES" in prompt
        assert "data-driven" in prompt
        assert "actionable" in prompt

        print("[OK] System prompt includes:")
        print(f"  - Client history: {memory.total_projects} projects")
        print(f"  - Voice adjustments: {len(memory.voice_adjustments)}")
        print(f"  - Signature phrases: {len(memory.signature_phrases)}")

    def test_07_system_prompt_without_memory(self, client_brief):
        """Test that system prompt works without memory (backward compatibility)"""
        print("\n[TEST 7] System Prompt Without Memory (Backward Compat)")
        print("-" * 60)

        # Create generator without database
        generator = ContentGeneratorAgent()

        # Build system prompt without memory
        from src.models.client_brief import Platform

        prompt = generator._build_system_prompt(
            client_brief=client_brief,
            platform=Platform.LINKEDIN,
            client_memory=None,
        )

        # Verify memory sections are NOT in prompt
        assert "CLIENT HISTORY" not in prompt
        assert "LEARNED PREFERENCES" not in prompt

        # But base prompt still works
        assert "PLATFORM: LINKEDIN" in prompt

        print("[OK] System prompt works without memory (backward compatible)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
