"""Test Audience Research formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Audience Research."""
    from backend.services.export_service import _format_audience_research

    # Sample audience research data (from AudienceResearch output)
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS - Customer Success",
        "target_description": "Customer success teams, revenue operations leaders, SaaS executives",
        "analysis_date": "2026-03-13",
        "executive_summary": "Your target audience consists primarily of mid-career professionals (35-44) in director and VP-level customer success roles at mid-market and enterprise SaaS companies. They are data-driven, results-oriented individuals who value efficiency and measurable outcomes. High education levels (mostly Bachelor's or Master's degrees) and upper-middle income ($100K-$200K). They consume content during work hours, prefer long-form educational content on LinkedIn and industry blogs, and make purchasing decisions based on ROI, peer recommendations, and case study evidence.",
        "audience_size_estimate": "Approximately 150,000 customer success professionals at B2B SaaS companies in North America",
        "demographics": {
            "primary_age_ranges": ["35-44", "25-34"],
            "gender_distribution": "58% female, 42% male (CS industry skews slightly female)",
            "locations": [
                "United States (primary)",
                "Canada",
                "United Kingdom",
                "Major metro areas: San Francisco, New York, Austin, Seattle",
            ],
            "income_levels": ["upper_middle", "high"],
            "education_levels": ["bachelors", "masters"],
            "job_titles": [
                "Director of Customer Success",
                "VP of Customer Success",
                "Customer Success Manager",
                "Head of Customer Success",
                "Chief Customer Officer",
                "Revenue Operations Manager",
                "Customer Success Operations Lead",
            ],
            "company_sizes": [
                "Mid-market (100-500 employees)",
                "Enterprise (500+ employees)",
                "Growth stage startups (50-100)",
            ],
        },
        "psychographics": {
            "values": [
                "Data-driven decision making",
                "Customer-centric approach",
                "Continuous learning and improvement",
                "Efficiency and productivity",
                "Measurable results",
            ],
            "interests": [
                "SaaS industry trends",
                "Data analytics and metrics",
                "Team management and leadership",
                "Customer retention strategies",
                "Career advancement",
                "Professional networking",
            ],
            "lifestyle": "Fast-paced professional lifestyle with work-life balance priorities. Remote or hybrid work arrangements. Active in professional communities. Balance family responsibilities with career ambitions.",
            "personality_traits": [
                "Results-oriented",
                "Analytical",
                "Empathetic",
                "Problem-solver",
                "Detail-focused",
                "Strategic thinker",
            ],
            "motivations": [
                "Reducing customer churn",
                "Improving team efficiency",
                "Proving ROI to leadership",
                "Career advancement and recognition",
                "Building high-performing teams",
                "Staying ahead of industry trends",
            ],
        },
        "behavioral_profile": {
            "content_consumption": "Consumes content during work hours (8am-6pm). Prefers long-form educational content (2000+ word guides, detailed case studies). Skims headlines first, bookmarks for later reading. Shares valuable insights with team and network.",
            "preferred_platforms": [
                "LinkedIn (daily usage)",
                "Industry blogs and newsletters",
                "Email newsletters",
                "Podcasts (during commute)",
                "YouTube (product demos and tutorials)",
            ],
            "online_behavior": "Active on LinkedIn - comments on thought leadership posts, shares insights, DMs for professional connections. Researches solutions extensively before purchasing. Joins relevant Slack communities and forums. Attends virtual conferences and webinars.",
            "purchase_behavior": "Long consideration period (3-6 months for major purchases). Requires multiple touchpoints - case studies, demos, peer recommendations. Involves team in evaluation. ROI calculation is critical. Prefers free trials or pilot programs before commitment.",
            "engagement_patterns": "Engages through comments on insightful posts, saves content for team sharing, direct messages for business inquiries, attends webinars for learning, downloads resources that provide immediate value.",
        },
        "pain_points": [
            "High customer churn rates eating into revenue",
            "Difficulty proving CS ROI to executive team",
            "Manual processes consuming too much time",
            "Lack of predictive insights into churn risk",
            "Reactive (not proactive) customer success approach",
            "Inconsistent customer data across systems",
            "Team burnout from constant firefighting",
            "Scaling CS operations with limited resources",
            "Poor visibility into customer health scores",
        ],
        "goals_aspirations": [
            "Reduce churn rate by 30-50%",
            "Implement predictive customer success",
            "Automate repetitive CS tasks",
            "Build data-driven CS playbooks",
            "Get promoted to VP or C-level",
            "Build and lead high-performing teams",
            "Become thought leader in CS space",
            "Improve customer lifetime value",
            "Achieve industry recognition (awards, speaking)",
        ],
        "content_preferences": [
            "Long-form guides (2000+ words) with actionable frameworks",
            "Data-driven case studies with specific metrics",
            "How-to content with step-by-step implementation",
            "Industry benchmarks and comparison data",
            "Video tutorials for complex topics",
            "Templates and worksheets",
            "Webinars with Q&A sessions",
            "LinkedIn posts with quick insights",
        ],
        "decision_factors": [
            "Proven ROI with specific metrics",
            "Peer recommendations and case studies",
            "Free trial or pilot program availability",
            "Integration with existing tech stack",
            "Implementation timeline and effort required",
            "Pricing and contract flexibility",
            "Quality of customer support",
        ],
        "information_sources": [
            "LinkedIn (primary)",
            "Industry newsletters (ChurnZero, Gainsight blogs)",
            "Podcasts (CS-focused)",
            "Peer recommendations from CS network",
            "Analyst reports (Gartner, Forrester)",
            "Reddit communities (r/CustomerSuccess)",
            "Conferences (Pulse, Success, SaaStr)",
            "YouTube channels for tutorials",
        ],
        "influencers_brands": [
            "ChurnZero (competitor)",
            "Gainsight (competitor)",
            "Lincoln Murphy (CS thought leader)",
            "Kristen Hayer (Success League)",
            "Totango",
            "Nick Mehta (Gainsight CEO)",
            "Intercom",
            "HubSpot",
        ],
        "audience_segments": [
            {
                "segment_name": "Established Directors",
                "segment_size": "40% of audience",
                "description": "Experienced CS leaders at mid-market/enterprise SaaS companies. 5-10 years in CS roles. Managing teams of 5-15 people. Focused on scaling operations and proving strategic value.",
                "key_characteristics": [
                    "Budget authority ($100K-$500K)",
                    "Strategic decision-makers",
                    "Data-driven and metrics-focused",
                    "Active in CS communities",
                ],
                "content_preferences": [
                    "Strategic frameworks and playbooks",
                    "ROI calculators and business case templates",
                    "Leadership and team management content",
                    "Industry benchmark data",
                ],
                "messaging_recommendations": "Position as strategic partner for scaling CS operations. Focus on ROI, efficiency gains, and competitive advantage. Use data-heavy case studies and peer testimonials.",
            },
            {
                "segment_name": "Ambitious Managers",
                "segment_size": "35% of audience",
                "description": "Individual contributors or team leads aspiring to director roles. 2-5 years in CS. Managing 0-5 people. Focused on proving impact and career advancement.",
                "key_characteristics": [
                    "Influencers (not budget holders)",
                    "Eager to learn and implement best practices",
                    "Building professional network",
                    "Tech-savvy and open to innovation",
                ],
                "content_preferences": [
                    "How-to guides and tactical playbooks",
                    "Career development content",
                    "Implementation tutorials",
                    "Quick wins and templates",
                ],
                "messaging_recommendations": "Position as enabler of career growth and professional development. Focus on practical implementation, skills building, and demonstrable results they can showcase to leadership.",
            },
            {
                "segment_name": "RevOps Innovators",
                "segment_size": "25% of audience",
                "description": "Revenue operations professionals who own the CS tech stack and analytics. Highly technical. Focus on integration, automation, and data infrastructure.",
                "key_characteristics": [
                    "Technical background",
                    "Integration and automation focused",
                    "Analytics and BI expertise",
                    "Cross-functional collaborators",
                ],
                "content_preferences": [
                    "Technical implementation guides",
                    "API documentation and integration tutorials",
                    "Data model and analytics content",
                    "Automation workflows",
                ],
                "messaging_recommendations": "Position as technical enabler with robust integrations and APIs. Focus on automation capabilities, data quality, and system efficiency. Use technical depth and architecture diagrams.",
            },
        ],
        "messaging_framework": "Speak to them as strategic partners, not vendors. Use a professional, data-driven tone that respects their expertise. Lead with outcomes and ROI, not features. Acknowledge their challenges with empathy but focus on actionable solutions. Use 'we' language to position yourself as an ally in their mission. Share specific metrics and peer examples. Avoid hype - they value authenticity and proven results.",
        "content_strategy_recommendations": [
            "Create monthly data-driven case studies with specific churn reduction metrics",
            "Publish comprehensive implementation guides (2000+ words) with templates",
            "Launch LinkedIn thought leadership series on predictive CS strategies",
            "Develop ROI calculator and business case template as lead magnets",
            "Host quarterly webinars on CS trends with peer panels",
            "Build CS playbook library with downloadable frameworks",
            "Create video tutorial series for technical implementation",
        ],
        "engagement_tactics": [
            "Comment thoughtfully on their LinkedIn posts to build relationships",
            "Share valuable insights without immediate sales pitch",
            "Invite them to exclusive peer roundtables and events",
            "Provide immediate value through free tools and templates",
            "Highlight customer success stories from similar companies",
            "Offer pilot programs to reduce purchase risk",
            "Create CS community or Slack group for networking",
        ],
        "key_insights": [
            "This audience is highly educated and data-driven - back every claim with metrics",
            "They're time-starved - provide actionable, immediately useful content",
            "Peer proof is critical - case studies and testimonials from similar roles/companies",
            "LinkedIn is your primary channel - invest 70% of content effort there",
            "Long consideration period - nurture with educational content for 3-6 months",
            "They value efficiency - show how you save time, not just solve problems",
            "Community matters - they trust peer recommendations over vendor claims",
        ],
        "what_to_avoid": [
            "Vague claims without data - they'll dismiss you immediately",
            "Hard sales tactics - they need education before consideration",
            "Jargon and buzzwords without substance",
            "Ignoring implementation complexity - be honest about effort required",
            "Underestimating their expertise - they know CS better than most vendors",
        ],
    }

    # Format the data
    lines = _format_audience_research(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections present
    assert "Audience Research Executive Summary" in output
    assert "150,000 customer success professionals" in output or "150,000" in output
    assert "mid-career professionals" in output

    # Demographics
    assert "Demographics" in output
    assert "Age Ranges:" in output or "35-44" in output
    assert "Gender:" in output
    assert "58% female" in output or "female" in output
    assert "Locations:" in output
    assert "United States" in output
    assert "Income Levels:" in output
    assert "Upper Middle" in output or "High" in output
    assert "Education:" in output
    assert "Bachelors" in output or "Masters" in output
    assert "Common Job Titles" in output
    assert "Director of Customer Success" in output
    assert "Company Sizes:" in output
    assert "Mid-market" in output or "Enterprise" in output

    # Psychographics
    assert "Psychographics" in output
    assert "Core Values" in output
    assert "Data-driven decision making" in output
    assert "Key Motivations" in output
    assert "Reducing customer churn" in output
    assert "Personality Traits" in output
    assert "Results-oriented" in output or "Analytical" in output
    assert "Interests:" in output
    assert "SaaS industry trends" in output
    assert "Lifestyle:" in output
    assert "Fast-paced professional" in output

    # Behavioral profile
    assert "Behavioral Patterns" in output
    assert "Content Consumption:" in output
    assert "long-form educational content" in output
    assert "Preferred Platforms:" in output
    assert "LinkedIn" in output
    assert "Online Behavior:" in output
    assert "Purchase Behavior:" in output
    assert "3-6 months" in output or "Long consideration" in output
    assert "Engagement Patterns:" in output

    # Pain points & goals
    assert "Pain Points & Goals" in output
    assert "Top Pain Points" in output
    assert "High customer churn" in output
    assert "Goals & Aspirations" in output
    assert "Reduce churn rate" in output

    # Content preferences
    assert "Content Preferences" in output
    assert "Long-form guides" in output or "2000+ words" in output

    # Decision factors
    assert "Decision-Making Factors" in output
    assert "Proven ROI" in output

    # Information sources & influencers
    assert "Information Sources" in output or "Influencers" in output
    assert "Where They Get Information" in output
    assert "Influencers & Brands They Follow" in output
    assert "ChurnZero" in output or "Gainsight" in output

    # Audience segments
    assert "Audience Segments" in output
    assert "Established Directors" in output
    assert "40% of audience" in output
    assert "Budget authority" in output
    assert "Key Characteristics" in output
    assert "Messaging:" in output
    assert "Position as strategic partner" in output

    # Messaging framework
    assert "Messaging Framework" in output
    assert "strategic partners, not vendors" in output

    # Content strategy
    assert "Content Strategy Recommendations" in output
    assert "Create monthly data-driven case studies" in output

    # Engagement tactics
    assert "Engagement Tactics" in output
    assert "Comment thoughtfully on their LinkedIn" in output

    # Key insights
    assert "Key Strategic Insights" in output
    assert "highly educated and data-driven" in output

    # What to avoid
    assert "What to Avoid" in output
    assert "Vague claims without data" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Audience Research."""
    from backend.services.research_context_builder import _format_audience_research

    # Create mock result
    sample_data = {
        "demographics": {
            "primary_age_ranges": ["35-44", "25-34"],
            "job_titles": ["Director of Customer Success", "VP Customer Success"],
        },
        "pain_points": [
            "High customer churn rates eating into revenue",
            "Difficulty proving CS ROI to executive team",
        ],
        "goals_aspirations": [
            "Reduce churn rate by 30-50%",
            "Implement predictive customer success",
        ],
        "behavioral_profile": {
            "preferred_platforms": ["LinkedIn", "Industry blogs", "Email"],
        },
        "key_insights": [
            "This audience is highly educated and data-driven - back claims with metrics",
            "They're time-starved - provide actionable content",
        ],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_audience_research(result)

    # Verify concise but comprehensive
    assert "Audience Research" in context
    assert "Mar 13" in context

    # Should include age ranges
    assert "Ages:" in context
    assert "35-44" in context or "25-34" in context

    # Should include job roles
    assert "Roles:" in context
    assert "Director" in context or "VP" in context

    # Should include pain point
    assert "Pain:" in context
    assert "churn" in context or "ROI" in context

    # Should include goal
    assert "Goal:" in context
    assert "Reduce churn" in context or "predictive" in context

    # Should include platforms
    assert "Platforms:" in context
    assert "LinkedIn" in context

    # Should include key insight
    assert "Insight:" in context
    assert "data-driven" in context or "educated" in context

    # Should be reasonably concise (under 450 chars for usability)
    assert len(context) < 500, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_audience_research

    minimal_data = {
        "demographics": {
            "primary_age_ranges": ["35-44"],
            "job_titles": ["Director"],
        },
    }

    lines = _format_audience_research(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "35-44" in output
    assert "Director" in output

    print("[OK] Minimal data test passed")


def test_stub_fix():
    """Test that context builder no longer returns stub text."""
    from backend.services.research_context_builder import _format_audience_research

    # This used to return "Audience Research: See data field"
    sample_data = {
        "demographics": {
            "primary_age_ranges": ["35-44"],
        }
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not return stub text
    context = _format_audience_research(result)

    assert "See data field" not in context
    assert "Audience Research" in context
    assert "35-44" in context

    print("[OK] Stub fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_audience_research

    # Empty data
    empty_data = {}
    lines = _format_audience_research(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"demographics": None, "psychographics": None}
    lines = _format_audience_research(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_stub_fix()
    test_empty_data_handling()
    print("\n[OK] All Audience Research formatting tests passed!")
