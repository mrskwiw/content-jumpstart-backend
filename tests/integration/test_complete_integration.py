"""
Complete Phase 5 Integration Test
Tests the full workflow: Posts → Voice Guide → Schedule → Analytics → DOCX
"""

from datetime import date
from pathlib import Path

from src.models.client_brief import ClientBrief, DataUsagePreference, Platform, TonePreference
from src.models.post import Post
from src.utils.output_formatter import OutputFormatter

print("=" * 70)
print("PHASE 5 COMPLETE INTEGRATION TEST")
print("Testing OutputFormatter.save_complete_package() with all components")
print("=" * 70)

# Step 1: Create realistic client brief
print("\n[1/4] Creating client brief...")
client_brief = ClientBrief(
    company_name="TechStartup Solutions",
    business_description="AI-powered project management for distributed teams",
    ideal_customer="CTOs and Engineering Managers at 50-500 person tech companies",
    main_problem_solved="Remote teams struggle with project visibility and async collaboration",
    customer_pain_points=[
        "Status updates take hours to compile",
        "Context switching between 10+ tools",
        "Timezone differences cause communication delays",
        "Project delays discovered too late",
    ],
    brand_personality=[
        TonePreference.DIRECT,
        TonePreference.DATA_DRIVEN,
        TonePreference.APPROACHABLE,
    ],
    key_phrases=[
        "Built for distributed teams",
        "Real-time clarity, async-first",
        "Ship on time, every time",
    ],
    customer_questions=[
        "How do you integrate with Slack/GitHub?",
        "Can we try it without migrating from Jira?",
    ],
    target_platforms=[Platform.LINKEDIN, Platform.TWITTER],
    posting_frequency="4x weekly",
    data_usage=DataUsagePreference.MODERATE,
    main_cta="Book a demo",
)

print(f"   Client: {client_brief.company_name}")
print(f"   Platforms: {', '.join(p.value for p in client_brief.target_platforms)}")

# Step 2: Create sample posts (simulating generated content)
print("\n[2/4] Creating sample posts...")
sample_posts_data = [
    (
        "Problem Recognition",
        "Your engineering team spends more time updating Jira tickets than actually coding. Last week, your EM spent 4 hours compiling a status report that was outdated by the time it hit exec's inbox.\n\nThis is the distributed team paradox: more tools for collaboration = less time collaborating.\n\nThe issue isn't remote work. It's that your project management stack was designed for co-located teams. When everyone's in an office, you can just walk over and ask \"what's blocking you?\" In a distributed team across 6 timezones, that question becomes a Slack thread, 3 email chains, and a forgotten Loom video.\n\nReal-time clarity, async-first—that's what TechStartup Solutions solves. Our AI automatically pulls updates from your existing tools (GitHub, Figma, Slack) and creates a living project dashboard. No manual updates. No context switching.\n\nOne CTO told us: \"I got 12 hours per week back. My team ships 30% faster.\"\n\nWhat would you do with 12 extra hours? Book a demo.",
    ),
    (
        "Statistic + Insight",
        "83% of distributed engineering teams miss deadlines by an average of 2.3 weeks (State of Remote Engineering 2024).\n\nThe reason? Not lack of talent. Not scope creep. Information latency.\n\nBy the time you discover a blocker in standup, the engineer has already lost 2 days waiting for unblocking. Multiply that across a 50-person team, and you're hemorrhaging 100 engineering days per quarter.\n\nHere's what high-performing distributed teams do differently: they make project status visible in real-time without requiring manual updates.\n\nTechStartup Solutions uses AI to monitor your GitHub commits, PR reviews, Slack conversations, and CI/CD pipelines. When a deployment is stuck or a critical PR needs review, we surface it automatically.\n\nShip on time, every time. Built for distributed teams who can't afford to wait for Friday's status meeting to discover Monday's problem.\n\nReady to eliminate information latency? Book a demo.",
    ),
    (
        "How-To",
        'How to get engineering project visibility without adding more meetings:\n\n1. Stop asking for status updates\nYour team already documents their work in GitHub PRs, Slack threads, and design docs. TechStartup Solutions aggregates it automatically.\n\n2. Surface blockers proactively\nSet rules: "If PR is open >48 hours with no review" → notify team lead. "If deploy fails 3x" → escalate to DevOps. Built for distributed teams means built for async.\n\n3. Create a single source of truth\nInstead of checking Jira, then GitHub, then Slack, then Figma—everything in one dashboard. Real-time clarity, async-first.\n\n4. Measure what matters\nCycle time, PR review latency, deployment frequency. Track the metrics that actually predict whether you\'ll ship on time.\n\n5. Integrate, don\'t replace\nYou don\'t need to abandon Jira or GitHub. TechStartup Solutions sits on top of your existing stack.\n\nOne engineering team cut their weekly sync from 60 minutes to 15 minutes. The other 45 minutes? They shipped features.\n\nShip on time, every time. Book a demo.',
    ),
    (
        "Contrarian Take",
        "Unpopular opinion: Your distributed team doesn't need better communication.\n\nYou need less communication.\n\nEvery Slack message is a context switch. Every status update meeting is 30 minutes your team could spend coding. The goal isn't more transparency—it's automatic transparency.\n\nHere's the shift: instead of asking your team to report progress, pull it from where they're already working.\n\nGitHub shows what they shipped. Figma shows what they designed. CI/CD shows what deployed. TechStartup Solutions aggregates it in real-time so you can see the full picture without interrupting anyone.\n\nReal-time clarity, async-first. That's how you scale distributed teams without drowning in status updates.\n\nOne VP Eng told us: \"I used to spend 10 hours/week in sync meetings. Now I spend 2 hours. My team's velocity doubled.\"\n\nBuilt for distributed teams who know that shipping > meeting.\n\nReady to stop communicating about work and start shipping? Book a demo.",
    ),
    (
        "What Changed",
        "In 2019, distributed teams were rare. Today, they're the default.\n\nBut our project management tools haven't caught up.\n\nJira was built for co-located teams who could walk to a whiteboard. Slack was designed for offices with 10 people, not 500 people across 30 countries. GitHub is perfect for code collaboration but tells you nothing about project health.\n\nWhat changed: teams went remote. Tools stayed local.\n\nThe gap? Real-time project visibility without manual updates. When your designer in Berlin makes a change, your PM in Austin needs to know immediately—not in tomorrow's standup.\n\nTechStartup Solutions was built for this new reality. We use AI to turn your existing tool activity into a living project dashboard. Built for distributed teams means designed for async-first workflows.\n\nShip on time, every time—no matter where your team works.\n\nOne CTO said: \"It's like having a project manager who never sleeps, across every timezone.\"\n\nReady for project management that matches how you actually work? Book a demo.",
    ),
]

posts = []
for i, (template_name, content) in enumerate(sample_posts_data, 1):
    post = Post(
        content=content,
        template_id=i,
        template_name=template_name,
        variant=1,
        client_name=client_brief.company_name,
        target_platform=Platform.LINKEDIN.value,
    )
    posts.append(post)

print(f"   Created {len(posts)} posts")
print(f"   Average length: {sum(p.word_count for p in posts) // len(posts)} words")
print(f"   Templates: {', '.join(set(p.template_name for p in posts))}")

# Step 3: Test OutputFormatter with all Phase 5 components
print("\n[3/4] Generating complete deliverables package...")
print("   Testing: OutputFormatter.save_complete_package()")

formatter = OutputFormatter()

saved_files = formatter.save_complete_package(
    posts=posts,
    client_brief=client_brief,
    client_name=client_brief.company_name,
    include_analytics_tracker=True,
    include_docx=True,
    start_date=date(2025, 12, 1),
    qa_report=None,  # Optional QA report
)

print(f"\n   Generated {len(saved_files)} deliverable files:")

# Step 4: Verify all files were created
print("\n[4/4] Verifying generated files...")

expected_files = [
    "deliverable",  # Main text deliverable
    "brand_voice",  # Original voice guide
    "brand_voice_enhanced",  # Phase 5 enhanced voice guide
    "schedule_markdown",  # Posting schedule (MD)
    "schedule_csv",  # Posting schedule (CSV)
    "schedule_ical",  # Posting schedule (iCal)
    "analytics_csv",  # Analytics tracker (CSV)
    "analytics_xlsx",  # Analytics tracker (Excel)
    "docx",  # DOCX deliverable
]

success_count = 0
for file_key in expected_files:
    if file_key in saved_files:
        file_path = saved_files[file_key]
        exists = file_path.exists() if isinstance(file_path, Path) else Path(file_path).exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {file_key}: {file_path.name if exists else 'NOT FOUND'}")
        if exists:
            success_count += 1
    else:
        print(f"   [MISSING] {file_key}: NOT GENERATED")

# Summary
print("\n" + "=" * 70)
print("INTEGRATION TEST RESULTS")
print("=" * 70)
print(f"Files Generated: {success_count}/{len(expected_files)}")
print(f"Success Rate: {int(success_count/len(expected_files)*100)}%")

if success_count == len(expected_files):
    print("\n*** ALL PHASE 5 COMPONENTS WORKING PERFECTLY! ***")
    print("\nDeliverables include:")
    print("  - Enhanced Brand Voice Guide (AI-analyzed patterns)")
    print("  - Posting Schedule (Markdown, CSV, iCalendar)")
    print("  - Analytics Tracker (CSV + Excel with formulas)")
    print("  - Complete DOCX Deliverable")
    print("\nPhase 5 integration: COMPLETE [OK]")
else:
    print("\n*** Some components need attention ***")
    print("Check logs above for details")

print("=" * 70)

# Show where files were saved
if saved_files:
    first_file = next(iter(saved_files.values()))
    output_dir = Path(first_file).parent
    print(f"\nAll files saved to: {output_dir}")
    print(f"\nTo view deliverables, open: {output_dir}")
