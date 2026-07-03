"""Integration tests for research context integration"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.services.research_context_builder import build_research_context
from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief


class TestResearchContextIntegration:
    def test_full_flow_with_research(self):
        mock_db = Mock()
        client_id = "test-123"

        # Create mock research results
        mock_result = Mock()
        mock_result.tool_name = "voice_analysis"
        mock_result.data = {
            "summary": "Professional and friendly voice focused on patient care",
            "primary_tone": "professional",
            "readability_score": 8.5,
        }
        mock_result.created_at = datetime.now()
        mock_result.status = "completed"

        with (
            patch("backend.services.research_context_builder.cache") as mc,
            patch("backend.services.research_context_builder.crud") as cr,
        ):
            mc.get_by_key.return_value = None
            cr.get_research_results_by_client.return_value = [mock_result]

            context = build_research_context(mock_db, client_id)

            assert context["formatted_text"] != ""
            assert len(context["tools_included"]) > 0
