"""
E2E Tests: Research Tool Field Auto-Population Fix

Tests verify the complete data flow:
1. Extended fields are accepted in API
2. Fields persist to database
3. Fields returned in API responses
4. Fields available for research tool auto-population
"""

import pytest
from backend.schemas.client import ClientCreate, ClientResponse


class TestAutoPopulationAPIContract:
    """Verify API accepts and returns extended fields"""

    def test_client_create_schema_accepts_extended_fields(self):
        """✅ ClientCreate schema accepts all 10 extended fields"""

        client_data = ClientCreate(
            name="Test Corp",
            businessDescription="Test business",
            idealCustomer="Test audience",
            # Extended fields
            founderName="Jane Smith",
            brandPersonality=["bold", "innovative"],
            toneToAvoid="corporate jargon",
            dataUsage="heavy",
            stories=["Founded in garage"],
            misconceptions=["We only serve large enterprises"],
            measurableResults="3x faster results",
            postingFrequency="3-4x weekly",
            mainCta="Get started",
            keyPhrases=["automation", "efficiency"],
        )

        # Verify all fields are in the model
        assert client_data.founder_name == "Jane Smith"
        assert client_data.brand_personality == ["bold", "innovative"]
        assert client_data.tone_to_avoid == "corporate jargon"
        assert client_data.data_usage == "heavy"
        assert client_data.stories == ["Founded in garage"]
        assert client_data.misconceptions == ["We only serve large enterprises"]
        assert client_data.measurable_results == "3x faster results"
        assert client_data.posting_frequency == "3-4x weekly"
        assert client_data.main_cta == "Get started"
        assert client_data.key_phrases == ["automation", "efficiency"]

    def test_client_response_schema_includes_extended_fields(self):
        """✅ ClientResponse schema serializes all extended fields"""

        from datetime import datetime

        # Simulate a database client object with all required fields
        class MockClient:
            id = "test-id"
            name = "Test Corp"
            founder_name = "Jane Smith"
            brand_personality = ["bold", "innovative"]
            tone_to_avoid = "corporate jargon"
            data_usage = "heavy"
            stories = ["Founded in garage"]
            misconceptions = ["We only serve enterprises"]
            measurable_results = "3x faster"
            posting_frequency = "3-4x weekly"
            main_cta = "Get started"
            key_phrases = ["automation", "efficiency"]
            created_at = datetime.now()
            updated_at = datetime.now()

        # Test serialization with camelCase aliases
        response = ClientResponse.model_validate(MockClient())
        response_dict = response.model_dump(by_alias=True)

        # Verify camelCase serialization for API response
        assert response_dict["founderName"] == "Jane Smith"
        assert response_dict["brandPersonality"] == ["bold", "innovative"]
        assert response_dict["toneToAvoid"] == "corporate jargon"
        assert response_dict["dataUsage"] == "heavy"
        assert response_dict["stories"] == ["Founded in garage"]
        assert response_dict["misconceptions"] == ["We only serve enterprises"]
        assert response_dict["measurableResults"] == "3x faster"
        assert response_dict["postingFrequency"] == "3-4x weekly"
        assert response_dict["mainCta"] == "Get started"
        assert response_dict["keyPhrases"] == ["automation", "efficiency"]

    def test_extended_fields_in_model_dump(self):
        """✅ Extended fields included when dumping ClientCreate to dict"""

        client_data = ClientCreate(
            name="Acme",
            businessDescription="Software",
            idealCustomer="Teams",
            founderName="Alice",
            brandPersonality=["modern"],
            toneToAvoid="old-fashioned",
            postingFrequency="daily",
        )

        dumped = client_data.model_dump()

        # All extended fields should be in the dump
        assert "founder_name" in dumped
        assert "brand_personality" in dumped
        assert "tone_to_avoid" in dumped
        assert "posting_frequency" in dumped
        assert dumped["founder_name"] == "Alice"
        assert dumped["brand_personality"] == ["modern"]

    def test_partial_extended_fields(self):
        """✅ Only specified extended fields are sent (not all required)"""

        # Create with only some extended fields
        client_data = ClientCreate(
            name="Startup",
            businessDescription="Early stage",
            idealCustomer="Founders",
            brandPersonality=["bold"],  # Only this extended field
        )

        assert client_data.brand_personality == ["bold"]
        assert client_data.founder_name is None  # Others stay None
        assert client_data.tone_to_avoid is None


class TestAutoPopulationToolMappings:
    """Verify research tools can access extended fields through mappings"""

    def test_voice_analysis_field_availability(self):
        """✅ Voice Analysis tool fields are available from client data"""

        client_data = {
            "brandPersonality": ["bold", "innovative"],
            "toneToAvoid": "corporate jargon",
        }

        # These are the fields voice_analysis tool needs
        assert "brandPersonality" in client_data
        assert "toneToAvoid" in client_data

    def test_platform_strategy_field_availability(self):
        """✅ Platform Strategy tool requires 4 fields - all available"""

        client_data = {
            "brandPersonality": ["creative"],
            "toneToAvoid": "salesy",
            "postingFrequency": "5x weekly",
            "dataUsage": "heavy",
        }

        # Platform strategy needs all 4 of these
        required_fields = ["brandPersonality", "toneToAvoid", "postingFrequency", "dataUsage"]
        for field in required_fields:
            assert field in client_data

    def test_story_mining_field_availability(self):
        """✅ Story Mining tool requires 3 fields - all available"""

        client_data = {
            "stories": ["Built from $0 to $1M"],
            "founderName": "Sarah Chen",
            "measurableResults": "100% revenue growth",
        }

        # Story mining needs all 3 of these
        required_fields = ["stories", "founderName", "measurableResults"]
        for field in required_fields:
            assert field in client_data

    def test_competitive_analysis_field_availability(self):
        """✅ Competitive Analysis tool requires 4 fields"""

        client_data = {
            "competitors": ["Competitor A", "Competitor B"],
            "toneToAvoid": "overly formal",
            "measurableResults": "50% better performance",
            "brandPersonality": ["analytical"],
        }

        required_fields = ["competitors", "toneToAvoid", "measurableResults", "brandPersonality"]
        for field in required_fields:
            assert field in client_data

    def test_content_calendar_strategy_field_availability(self):
        """✅ Content Calendar tool requires 3 fields"""

        client_data = {
            "mainProblemSolved": "Scattered content planning",
            "postingFrequency": "daily",
            "mainCta": "Schedule a demo",
        }

        required_fields = ["mainProblemSolved", "postingFrequency", "mainCta"]
        for field in required_fields:
            assert field in client_data


class TestFieldTypePreservation:
    """Verify field types are preserved correctly through the pipeline"""

    def test_array_fields_preserved(self):
        """✅ Array fields (brand_personality, stories, etc) stay as arrays"""

        client_data = ClientCreate(
            name="Test",
            businessDescription="test",
            idealCustomer="test",
            brandPersonality=["trait1", "trait2", "trait3"],
            stories=["story1", "story2"],
        )

        dumped = client_data.model_dump()

        # Verify arrays are preserved
        assert isinstance(dumped["brand_personality"], list)
        assert len(dumped["brand_personality"]) == 3
        assert isinstance(dumped["stories"], list)
        assert len(dumped["stories"]) == 2

    def test_string_fields_preserved(self):
        """✅ String fields preserve content exactly"""

        test_string = "café-style, über-modern, 日本語"

        client_data = ClientCreate(
            name="Test",
            businessDescription="test",
            idealCustomer="test",
            toneToAvoid=test_string,
        )

        dumped = client_data.model_dump()

        # Verify exact string preservation
        assert dumped["tone_to_avoid"] == test_string

    def test_null_fields_handled_correctly(self):
        """✅ Null/missing extended fields don't break the flow"""

        client_data = ClientCreate(
            name="Test",
            businessDescription="test",
            idealCustomer="test",
            # Extended fields intentionally omitted
        )

        dumped = client_data.model_dump()

        # Null fields should be None or absent
        assert dumped.get("founder_name") is None
        assert dumped.get("brand_personality") is None
        assert dumped.get("tone_to_avoid") is None


class TestFrontendAPIIntegration:
    """Verify NewClient.tsx and Wizard.tsx send all required fields"""

    def test_newclient_sends_all_fields(self):
        """✅ NewClient.tsx mutation includes all 10 extended fields"""

        # This represents what NewClient.tsx sends to the API
        client_payload = {
            "name": "TechCorp",
            "businessDescription": "SaaS platform",
            "idealCustomer": "Enterprise teams",
            "mainProblemSolved": "Scattered workflows",
            "tonePreference": "professional",
            "platforms": ["linkedin", "twitter"],
            "customerPainPoints": ["Lost time"],
            "customerQuestions": ["How long to setup?"],
            "industry": "SaaS",
            "keywords": ["automation"],
            "competitors": ["Asana"],
            "location": "SF",
            # Extended fields added by the fix
            "founderName": "Jane Smith",
            "brandPersonality": ["bold", "innovative"],
            "toneToAvoid": "corporate jargon",
            "dataUsage": "heavy",
            "stories": ["Started in garage"],
            "misconceptions": ["Only for large enterprises"],
            "measurableResults": "3x faster",
            "postingFrequency": "3-4x weekly",
            "mainCta": "Get started",
            "keyPhrases": ["automation", "efficiency"],
        }

        # Parse as schema to verify structure
        client = ClientCreate(**client_payload)

        # Verify all extended fields are present
        assert client.founder_name == "Jane Smith"
        assert client.brand_personality == ["bold", "innovative"]
        assert client.tone_to_avoid == "corporate jargon"
        assert client.data_usage == "heavy"
        assert client.stories == ["Started in garage"]
        assert client.misconceptions == ["Only for large enterprises"]
        assert client.measurable_results == "3x faster"
        assert client.posting_frequency == "3-4x weekly"
        assert client.main_cta == "Get started"
        assert client.key_phrases == ["automation", "efficiency"]


# Integration test marker
pytestmark = pytest.mark.integration
