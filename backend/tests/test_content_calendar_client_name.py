from types import SimpleNamespace

from backend.services.research_service import ResearchService


def test_content_calendar_uses_database_client_name_over_request_param():
    service = ResearchService()

    project = SimpleNamespace(platforms=["LinkedIn"], tone="professional")
    client = SimpleNamespace(
        name="Acme Analytics",
        business_description="A client business description that is comfortably long enough.",
        ideal_customer="Marketing leaders",
        industry="SaaS",
        location="Austin, TX",
        recommended_platforms=["LinkedIn", "Twitter"],
    )

    inputs = service._prepare_inputs(
        project,
        client,
        "content_calendar",
        {
            "business_name": "Competitor Co",
            "company_name": "Competitor Co",
            "primary_platforms": ["Twitter"],
        },
    )

    assert inputs["business_name"] == "Acme Analytics"
    assert inputs["company_name"] == "Acme Analytics"
    assert inputs["primary_platforms"] == ["Twitter"]
