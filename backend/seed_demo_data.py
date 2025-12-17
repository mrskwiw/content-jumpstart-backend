"""
Database seeding script for demo/development data.

WARNING: This script is for DEVELOPMENT/TESTING ONLY.
DO NOT run this in production. All data created by this script
must be purged before production deployment.

Usage:
    python seed_demo_data.py [--clear-only]

Options:
    --clear-only    Only clear existing demo data without seeding
"""
import io
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, init_db
from models.client import Client
from models.project import Project
from models.run import Run
from models.post import Post
from models.deliverable import Deliverable


def check_environment():
    """Ensure we're not running in production."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        print("❌ ERROR: Cannot run seed script in PRODUCTION environment!")
        print("   Set ENVIRONMENT=development to proceed.")
        sys.exit(1)
    print(f"✓ Running in {env.upper()} environment")


def clear_demo_data(db):
    """Clear all existing data from database."""
    print("\n🧹 Clearing existing data...")

    # Delete in reverse order of dependencies
    db.query(Post).delete()
    db.query(Deliverable).delete()
    db.query(Run).delete()
    db.query(Project).delete()
    db.query(Client).delete()

    db.commit()
    print("✓ All existing data cleared")


def seed_clients(db):
    """Seed client data."""
    print("\n👥 Seeding clients...")

    clients = [
        Client(id="client-1", name="Acme Corp", email="contact@acmecorp.com"),
        Client(id="client-2", name="TechVision AI", email="hello@techvision.ai"),
        Client(id="client-3", name="GrowthLab Marketing", email="info@growthlab.io"),
        Client(id="client-4", name="FinanceFlow Solutions", email="contact@financeflow.com"),
        Client(id="client-5", name="HealthTech Innovations", email="info@healthtech-inn.com"),
        Client(id="client-6", name="EduPro Learning", email="hello@edupro.edu"),
        Client(id="client-7", name="SecureNet Cybersecurity", email="contact@securenet.io"),
        Client(id="client-8", name="WanderLust Travel", email="info@wanderlust.travel"),
        Client(id="client-9", name="CloudScale Infrastructure", email="hello@cloudscale.cloud"),
        Client(id="client-10", name="RetailBoost POS", email="support@retailboost.com"),
        Client(id="client-11", name="ContentCraft Agency", email="team@contentcraft.agency"),
        Client(id="client-12", name="FitWell Wellness", email="info@fitwell.health"),
        Client(id="client-13", name="DataSense Analytics", email="contact@datasense.io"),
        Client(id="client-14", name="UrbanSpace Real Estate", email="hello@urbanspace.realty"),
        Client(id="client-15", name="NextGen Startups", email="founders@nextgen.ventures"),
    ]

    db.add_all(clients)
    db.commit()
    print(f"✓ Seeded {len(clients)} clients")


def seed_projects(db):
    """Seed project data."""
    print("\n📁 Seeding projects...")

    base_time = datetime.now()

    projects = [
        # Acme Corp Projects
        Project(
            id="project-1",
            client_id="client-1",
            name="LinkedIn Campaign Q1 2025",
            status="delivered",
            templates=["Problem Recognition", "Statistic + Insight", "How-To"],
            platforms=["linkedin"],
            tone="professional",
            created_at=base_time - timedelta(days=7),
            updated_at=base_time - timedelta(days=1),
        ),
        Project(
            id="project-2",
            client_id="client-1",
            name="Twitter Thought Leadership",
            status="ready",
            templates=["Contrarian Take", "Future Thinking"],
            platforms=["twitter"],
            tone="conversational",
            created_at=base_time - timedelta(days=5),
            updated_at=base_time - timedelta(days=2),
        ),
        Project(
            id="project-3",
            client_id="client-1",
            name="Blog Series - Industry Insights",
            status="qa",
            templates=["What Changed", "Myth Busting"],
            platforms=["blog"],
            tone="professional",
            created_at=base_time - timedelta(days=3),
            updated_at=base_time - timedelta(hours=12),
        ),

        # TechVision AI Projects
        Project(
            id="project-4",
            client_id="client-2",
            name="AI Product Launch - LinkedIn",
            status="delivered",
            templates=["Personal Story", "Inside Look"],
            platforms=["linkedin"],
            tone="innovative",
            created_at=base_time - timedelta(days=14),
            updated_at=base_time - timedelta(days=10),
        ),
        Project(
            id="project-17",
            client_id="client-2",
            name="AI Innovation Series",
            status="generating",
            templates=["Future Thinking", "Statistic + Insight", "Myth Busting"],
            platforms=["linkedin", "blog"],
            tone="innovative",
            created_at=base_time - timedelta(days=2),
            updated_at=base_time - timedelta(minutes=10),
        ),

        # GrowthLab Marketing Projects
        Project(
            id="project-5",
            client_id="client-3",
            name="Social Media Strategy Package",
            status="ready",
            templates=["How-To", "Question Post"],
            platforms=["linkedin", "twitter", "facebook"],
            tone="conversational",
            created_at=base_time - timedelta(days=6),
            updated_at=base_time - timedelta(days=1),
        ),
        Project(
            id="project-18",
            client_id="client-3",
            name="Client Success Stories",
            status="draft",
            templates=["Personal Story", "Milestone"],
            platforms=["linkedin"],
            tone="empathetic",
            created_at=base_time - timedelta(hours=8),
            updated_at=base_time - timedelta(hours=6),
        ),

        # FinanceFlow Solutions Projects
        Project(
            id="project-6",
            client_id="client-4",
            name="Fintech Trends 2025",
            status="delivered",
            templates=["Statistic + Insight", "Comparison"],
            platforms=["linkedin"],
            tone="professional",
            created_at=base_time - timedelta(days=20),
            updated_at=base_time - timedelta(days=18),
        ),
        Project(
            id="project-19",
            client_id="client-4",
            name="Investment Tips Series",
            status="ready",
            templates=["How-To", "Myth Busting"],
            platforms=["blog", "linkedin"],
            tone="educational",
            created_at=base_time - timedelta(days=4),
            updated_at=base_time - timedelta(days=1),
        ),

        # HealthTech Innovations Projects
        Project(
            id="project-7",
            client_id="client-5",
            name="Patient Care Innovation",
            status="qa",
            templates=["Inside Look", "What Changed"],
            platforms=["linkedin"],
            tone="empathetic",
            created_at=base_time - timedelta(days=9),
            updated_at=base_time - timedelta(hours=18),
        ),
        Project(
            id="project-20",
            client_id="client-5",
            name="Healthcare Technology Blog",
            status="draft",
            templates=["Future Thinking", "How-To"],
            platforms=["blog"],
            tone="professional",
            created_at=base_time - timedelta(hours=24),
            updated_at=base_time - timedelta(hours=20),
        ),

        # EduPro Learning Projects
        Project(
            id="project-8",
            client_id="client-6",
            name="Online Learning Tips",
            status="delivered",
            templates=["How-To", "Reader Q Response"],
            platforms=["blog", "linkedin"],
            tone="educational",
            created_at=base_time - timedelta(days=12),
            updated_at=base_time - timedelta(days=11),
        ),
        Project(
            id="project-21",
            client_id="client-6",
            name="Student Success Stories",
            status="ready",
            templates=["Personal Story", "Milestone"],
            platforms=["facebook", "instagram"],
            tone="motivational",
            created_at=base_time - timedelta(days=5),
            updated_at=base_time - timedelta(days=2),
        ),

        # SecureNet Cybersecurity Projects
        Project(
            id="project-9",
            client_id="client-7",
            name="Cybersecurity Awareness",
            status="delivered",
            templates=["Problem Recognition", "Myth Busting"],
            platforms=["linkedin"],
            tone="technical",
            created_at=base_time - timedelta(days=16),
            updated_at=base_time - timedelta(days=15),
        ),
        Project(
            id="project-22",
            client_id="client-7",
            name="Security Best Practices",
            status="qa",
            templates=["How-To", "What Changed"],
            platforms=["blog"],
            tone="professional",
            created_at=base_time - timedelta(days=3),
            updated_at=base_time - timedelta(hours=10),
        ),

        # WanderLust Travel Projects
        Project(
            id="project-10",
            client_id="client-8",
            name="Travel Destination Guides",
            status="ready",
            templates=["Personal Story", "Inside Look"],
            platforms=["instagram", "blog"],
            tone="inspirational",
            created_at=base_time - timedelta(days=8),
            updated_at=base_time - timedelta(days=3),
        ),
        Project(
            id="project-23",
            client_id="client-8",
            name="Travel Tips & Hacks",
            status="draft",
            templates=["How-To", "Question Post"],
            platforms=["twitter", "facebook"],
            tone="conversational",
            created_at=base_time - timedelta(hours=16),
            updated_at=base_time - timedelta(hours=12),
        ),

        # CloudScale Infrastructure Projects
        Project(
            id="project-11",
            client_id="client-9",
            name="Cloud Migration Guide",
            status="delivered",
            templates=["How-To", "Comparison"],
            platforms=["linkedin", "blog"],
            tone="technical",
            created_at=base_time - timedelta(days=10),
            updated_at=base_time - timedelta(days=8),
        ),
        Project(
            id="project-24",
            client_id="client-9",
            name="Infrastructure Optimization",
            status="generating",
            templates=["Statistic + Insight", "Future Thinking"],
            platforms=["linkedin"],
            tone="analytical",
            created_at=base_time - timedelta(hours=6),
            updated_at=base_time - timedelta(minutes=15),
        ),

        # RetailBoost POS Projects
        Project(
            id="project-12",
            client_id="client-10",
            name="Retail Technology Trends",
            status="ready",
            templates=["What Changed", "Future Thinking"],
            platforms=["linkedin"],
            tone="professional",
            created_at=base_time - timedelta(days=7),
            updated_at=base_time - timedelta(days=2),
        ),
        Project(
            id="project-25",
            client_id="client-10",
            name="POS System Success Stories",
            status="draft",
            templates=["Personal Story", "Milestone"],
            platforms=["blog"],
            tone="conversational",
            created_at=base_time - timedelta(hours=30),
            updated_at=base_time - timedelta(hours=24),
        ),

        # ContentCraft Agency Projects
        Project(
            id="project-13",
            client_id="client-11",
            name="Content Strategy Workshop",
            status="delivered",
            templates=["How-To", "Inside Look"],
            platforms=["linkedin", "blog"],
            tone="professional",
            created_at=base_time - timedelta(days=18),
            updated_at=base_time - timedelta(days=17),
        ),
        Project(
            id="project-26",
            client_id="client-11",
            name="Agency Growth Tips",
            status="qa",
            templates=["Contrarian Take", "What I Learned From"],
            platforms=["twitter", "linkedin"],
            tone="conversational",
            created_at=base_time - timedelta(days=4),
            updated_at=base_time - timedelta(hours=8),
        ),

        # FitWell Wellness Projects
        Project(
            id="project-14",
            client_id="client-12",
            name="Wellness Tips Series",
            status="ready",
            templates=["How-To", "Myth Busting"],
            platforms=["instagram", "facebook"],
            tone="motivational",
            created_at=base_time - timedelta(days=6),
            updated_at=base_time - timedelta(days=2),
        ),
        Project(
            id="project-27",
            client_id="client-12",
            name="Fitness Transformation Stories",
            status="draft",
            templates=["Personal Story", "Before/After"],
            platforms=["blog", "instagram"],
            tone="empathetic",
            created_at=base_time - timedelta(hours=20),
            updated_at=base_time - timedelta(hours=16),
        ),

        # DataSense Analytics Project
        Project(
            id="project-15",
            client_id="client-13",
            name="Data-Driven Marketing",
            status="delivered",
            templates=["Statistic + Insight", "How-To"],
            platforms=["linkedin"],
            tone="analytical",
            created_at=base_time - timedelta(days=22),
            updated_at=base_time - timedelta(days=21),
        ),

        # UrbanSpace Real Estate Project
        Project(
            id="project-16",
            client_id="client-14",
            name="Real Estate Market Insights",
            status="ready",
            templates=["What Changed", "Comparison"],
            platforms=["blog", "linkedin"],
            tone="professional",
            created_at=base_time - timedelta(days=11),
            updated_at=base_time - timedelta(days=5),
        ),
    ]

    db.add_all(projects)
    db.commit()
    print(f"✓ Seeded {len(projects)} projects")


def seed_runs(db):
    """Seed run data."""
    print("\n🚀 Seeding runs...")

    base_time = datetime.now()

    runs = [
        Run(
            id="run-1",
            project_id="project-1",
            is_batch=True,
            started_at=base_time - timedelta(days=3),
            completed_at=base_time - timedelta(days=3, hours=1),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=3)).isoformat(), "message": "Generation started"},
                {"timestamp": (base_time - timedelta(days=3, hours=-0.5)).isoformat(), "message": "Generated 15/30 posts"},
                {"timestamp": (base_time - timedelta(days=3, hours=-1)).isoformat(), "message": "Generation completed successfully"},
            ],
        ),
        Run(
            id="run-2",
            project_id="project-4",
            is_batch=True,
            started_at=base_time - timedelta(days=12),
            completed_at=base_time - timedelta(days=12, hours=1, minutes=15),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=12)).isoformat(), "message": "Batch generation initiated"},
                {"timestamp": (base_time - timedelta(days=12, hours=-1)).isoformat(), "message": "All posts generated"},
            ],
        ),
        Run(
            id="run-3",
            project_id="project-6",
            is_batch=False,
            started_at=base_time - timedelta(days=20),
            completed_at=base_time - timedelta(days=20, hours=0, minutes=45),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=20)).isoformat(), "message": "Single post generation"},
            ],
        ),
        Run(
            id="run-4",
            project_id="project-8",
            is_batch=True,
            started_at=base_time - timedelta(days=12),
            completed_at=base_time - timedelta(days=12, hours=1, minutes=5),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=12)).isoformat(), "message": "Educational content generation"},
                {"timestamp": (base_time - timedelta(days=12, hours=-1)).isoformat(), "message": "Completed successfully"},
            ],
        ),
        Run(
            id="run-5",
            project_id="project-9",
            is_batch=True,
            started_at=base_time - timedelta(days=16),
            completed_at=base_time - timedelta(days=16, hours=1, minutes=20),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=16)).isoformat(), "message": "Security content generation"},
            ],
        ),
        Run(
            id="run-6",
            project_id="project-11",
            is_batch=True,
            started_at=base_time - timedelta(days=9),
            completed_at=base_time - timedelta(days=9, hours=1, minutes=10),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=9)).isoformat(), "message": "Technical content generated"},
            ],
        ),
        Run(
            id="run-7",
            project_id="project-13",
            is_batch=True,
            started_at=base_time - timedelta(days=18),
            completed_at=base_time - timedelta(days=18, hours=1),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=18)).isoformat(), "message": "Workshop content complete"},
            ],
        ),
        Run(
            id="run-8",
            project_id="project-15",
            is_batch=False,
            started_at=base_time - timedelta(days=22),
            completed_at=base_time - timedelta(days=22, hours=0, minutes=30),
            status="succeeded",
            logs=[
                {"timestamp": (base_time - timedelta(days=22)).isoformat(), "message": "Analytics post generated"},
            ],
        ),
        Run(
            id="run-9",
            project_id="project-17",
            is_batch=True,
            started_at=base_time - timedelta(minutes=20),
            completed_at=None,
            status="running",
            logs=[
                {"timestamp": (base_time - timedelta(minutes=20)).isoformat(), "message": "AI innovation series started"},
                {"timestamp": (base_time - timedelta(minutes=15)).isoformat(), "message": "Processing template 1 of 3"},
            ],
        ),
        Run(
            id="run-10",
            project_id="project-24",
            is_batch=True,
            started_at=base_time - timedelta(minutes=10),
            completed_at=None,
            status="running",
            logs=[
                {"timestamp": (base_time - timedelta(minutes=10)).isoformat(), "message": "Infrastructure optimization started"},
            ],
        ),
    ]

    db.add_all(runs)
    db.commit()
    print(f"✓ Seeded {len(runs)} runs")


def seed_posts(db):
    """Seed post data."""
    print("\n📝 Seeding posts...")

    base_time = datetime.now()

    posts = [
        Post(
            id="post-1",
            project_id="project-1",
            run_id="run-1",
            content="Are you struggling with customer retention? Most B2B SaaS companies focus on acquisition, but retention is where the real growth happens. Here's what changed our approach...",
            template_id="1",
            template_name="Problem Recognition",
            variant=1,
            word_count=245,
            readability_score=72.5,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=3, hours=1),
        ),
        Post(
            id="post-2",
            project_id="project-1",
            run_id="run-1",
            content="87% of enterprise customers say personalization influences their purchasing decisions. Yet only 23% of B2B companies deliver truly personalized experiences. The gap is your opportunity.",
            template_id="2",
            template_name="Statistic + Insight",
            variant=2,
            word_count=198,
            readability_score=68.3,
            has_cta=False,
            status="flagged",
            flags=["missing_cta"],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=3, hours=1),
        ),
        Post(
            id="post-3",
            project_id="project-4",
            run_id="run-2",
            content="Building AI products taught me this: Your first version will feel embarrassingly simple. Ship it anyway. I launched our MVP with just 3 features. Customers loved its simplicity. Complexity came later, guided by real feedback.",
            template_id="6",
            template_name="Personal Story",
            variant=1,
            word_count=312,
            readability_score=75.8,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=12, hours=1),
        ),
        Post(
            id="post-4",
            project_id="project-4",
            run_id="run-2",
            content="Behind the scenes of our AI model training: 6 months, 500GB of data, countless late nights. But the real challenge wasn't the technology—it was deciding what NOT to build.",
            template_id="12",
            template_name="Inside Look",
            variant=2,
            word_count=267,
            readability_score=71.2,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=12, hours=1),
        ),
        Post(
            id="post-5",
            project_id="project-6",
            run_id="run-3",
            content="The fintech landscape in 2025: What changed? Open banking went from nice-to-have to table stakes. Embedded finance became the default. And AI-powered risk assessment replaced traditional credit scoring for 40% of lenders.",
            template_id="4",
            template_name="What Changed",
            variant=1,
            word_count=289,
            readability_score=69.7,
            has_cta=False,
            status="flagged",
            flags=["missing_cta"],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=20, hours=1),
        ),
        Post(
            id="post-6",
            project_id="project-8",
            run_id="run-4",
            content="How to create effective online courses: 5 steps from 10 years of teaching. 1) Start with outcomes, not content. 2) Build in accountability systems. 3) Make it interactive. 4) Keep videos under 8 minutes. 5) Provide templates, not just theory.",
            template_id="9",
            template_name="How-To",
            variant=1,
            word_count=223,
            readability_score=74.1,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=12, hours=1),
        ),
        Post(
            id="post-7",
            project_id="project-9",
            run_id="run-5",
            content="Myth: Cybersecurity is only for large enterprises. Reality: 43% of cyberattacks target small businesses. Most fail within 6 months of a breach. The cost of prevention is 10x less than the cost of recovery. Protect your business now.",
            template_id="7",
            template_name="Myth Busting",
            variant=1,
            word_count=256,
            readability_score=66.9,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=16, hours=1),
        ),
        Post(
            id="post-8",
            project_id="project-11",
            run_id="run-6",
            content="Migrating to the cloud? Here's your step-by-step guide: 1) Audit your current infrastructure. 2) Choose your cloud model (IaaS vs PaaS vs SaaS). 3) Plan your migration strategy. 4) Test thoroughly. 5) Train your team. 6) Monitor and optimize continuously.",
            template_id="9",
            template_name="How-To",
            variant=2,
            word_count=301,
            readability_score=70.4,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=9, hours=1),
        ),
        Post(
            id="post-9",
            project_id="project-13",
            run_id="run-7",
            content="Content strategy workshop insights: 85% of attendees said their biggest challenge is consistency. Not ideas. Not quality. Consistency. The solution? Systems over motivation. Templates over inspiration. Batch creation over daily scrambling.",
            template_id="2",
            template_name="Statistic + Insight",
            variant=3,
            word_count=234,
            readability_score=73.6,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=18, hours=1),
        ),
        Post(
            id="post-10",
            project_id="project-15",
            run_id="run-8",
            content="Data-driven marketing works. But only if you're measuring the right things. Vanity metrics like impressions and likes feel good but don't drive growth. Focus on: conversion rate, customer acquisition cost, lifetime value, and engagement depth.",
            template_id="1",
            template_name="Problem Recognition",
            variant=3,
            word_count=278,
            readability_score=71.8,
            has_cta=True,
            status="approved",
            flags=[],
            target_platform="linkedin",
            created_at=base_time - timedelta(days=22, hours=1),
        ),
    ]

    db.add_all(posts)
    db.commit()
    print(f"✓ Seeded {len(posts)} posts")


def seed_deliverables(db):
    """Seed deliverable data."""
    print("\n📦 Seeding deliverables...")

    base_time = datetime.now()

    deliverables = [
        # Delivered deliverables
        Deliverable(
            id="deliv-1",
            project_id="project-1",
            client_id="client-1",
            run_id="run-1",
            format="docx",
            path="outputs/acme-corp/linkedin-q1-2025-12-14.docx",
            status="delivered",
            created_at=base_time - timedelta(days=2),
            delivered_at=base_time - timedelta(days=1),
            proof_url="https://example.com/proof/acme-delivered",
            proof_notes="Delivered via email on Dec 14, 2025. Client confirmed receipt.",
            checksum="abc123xyz",
        ),
        Deliverable(
            id="deliv-2",
            project_id="project-4",
            client_id="client-2",
            run_id="run-2",
            format="txt",
            path="outputs/techvision/ai-launch-2024-12-05.txt",
            status="delivered",
            created_at=base_time - timedelta(days=11),
            delivered_at=base_time - timedelta(days=10),
            proof_url="https://example.com/proof/techvision-delivered",
            proof_notes="Successfully delivered to product marketing team",
            checksum="tech456def",
        ),
        Deliverable(
            id="deliv-3",
            project_id="project-6",
            client_id="client-4",
            run_id="run-3",
            format="docx",
            path="outputs/financeflow/fintech-trends-2024-11-27.docx",
            status="delivered",
            created_at=base_time - timedelta(days=19),
            delivered_at=base_time - timedelta(days=18),
            proof_url="https://example.com/proof/financeflow-delivered",
            proof_notes="Client approved and confirmed usage",
            checksum="fin789ghi",
        ),
        Deliverable(
            id="deliv-4",
            project_id="project-8",
            client_id="client-6",
            run_id="run-4",
            format="txt",
            path="outputs/edupro/learning-tips-2024-12-05.txt",
            status="delivered",
            created_at=base_time - timedelta(days=11),
            delivered_at=base_time - timedelta(days=11),
            proof_url="https://example.com/proof/edupro-delivered",
            proof_notes="Integrated into their content calendar",
            checksum="edu012jkl",
        ),
        Deliverable(
            id="deliv-5",
            project_id="project-9",
            client_id="client-7",
            run_id="run-5",
            format="docx",
            path="outputs/securenet/cybersecurity-2024-12-01.docx",
            status="delivered",
            created_at=base_time - timedelta(days=15),
            delivered_at=base_time - timedelta(days=15),
            proof_url="https://example.com/proof/securenet-delivered",
            proof_notes="Delivered to security team lead",
            checksum="sec345mno",
        ),
        Deliverable(
            id="deliv-9",
            project_id="project-11",
            client_id="client-9",
            run_id="run-6",
            format="docx",
            path="outputs/cloudscale/cloud-migration-2024-12-08.docx",
            status="delivered",
            created_at=base_time - timedelta(days=8),
            delivered_at=base_time - timedelta(days=7),
            proof_url="https://example.com/proof/cloudscale-delivered",
            proof_notes="Successfully delivered to client CTO",
            checksum="cloud987jkl",
        ),
        Deliverable(
            id="deliv-10",
            project_id="project-13",
            client_id="client-11",
            run_id="run-7",
            format="txt",
            path="outputs/contentcraft/workshop-2024-11-29.txt",
            status="delivered",
            created_at=base_time - timedelta(days=17),
            delivered_at=base_time - timedelta(days=17),
            proof_url="https://example.com/proof/contentcraft-delivered",
            proof_notes="Client used content for their workshop",
            checksum="content654pqr",
        ),

        # Ready deliverables (not yet delivered)
        Deliverable(
            id="deliv-6",
            project_id="project-2",
            client_id="client-1",
            run_id=None,
            format="txt",
            path="outputs/acme-corp/twitter-leadership-2024-12-12.txt",
            status="ready",
            created_at=base_time - timedelta(days=3),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="twitter678pqr",
        ),
        Deliverable(
            id="deliv-7",
            project_id="project-5",
            client_id="client-3",
            run_id=None,
            format="docx",
            path="outputs/growthlab/social-strategy-2024-12-11.docx",
            status="ready",
            created_at=base_time - timedelta(days=4),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="growth901stu",
        ),
        Deliverable(
            id="deliv-11",
            project_id="project-10",
            client_id="client-8",
            run_id=None,
            format="txt",
            path="outputs/wanderlust/destination-guides-2024-12-09.txt",
            status="ready",
            created_at=base_time - timedelta(days=6),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="travel123vwx",
        ),
        Deliverable(
            id="deliv-12",
            project_id="project-12",
            client_id="client-10",
            run_id=None,
            format="docx",
            path="outputs/retailboost/retail-trends-2024-12-10.docx",
            status="ready",
            created_at=base_time - timedelta(days=5),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="retail456yza",
        ),
        Deliverable(
            id="deliv-13",
            project_id="project-14",
            client_id="client-12",
            run_id=None,
            format="txt",
            path="outputs/fitwell/wellness-tips-2024-12-11.txt",
            status="ready",
            created_at=base_time - timedelta(days=4),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="wellness789bcd",
        ),
        Deliverable(
            id="deliv-14",
            project_id="project-16",
            client_id="client-14",
            run_id=None,
            format="docx",
            path="outputs/urbanspace/market-insights-2024-12-06.docx",
            status="ready",
            created_at=base_time - timedelta(days=9),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="realestate012efg",
        ),
        Deliverable(
            id="deliv-15",
            project_id="project-19",
            client_id="client-4",
            run_id=None,
            format="txt",
            path="outputs/financeflow/investment-tips-2024-12-13.txt",
            status="ready",
            created_at=base_time - timedelta(days=2),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="invest345hij",
        ),

        # Draft deliverable
        Deliverable(
            id="deliv-8",
            project_id="project-3",
            client_id="client-1",
            run_id=None,
            format="docx",
            path="outputs/acme-corp/blog-series-draft.docx",
            status="draft",
            created_at=base_time - timedelta(hours=18),
            delivered_at=None,
            proof_url=None,
            proof_notes=None,
            checksum="blog234vwx",
        ),
    ]

    db.add_all(deliverables)
    db.commit()
    print(f"✓ Seeded {len(deliverables)} deliverables")


def main():
    """Main seeding function."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed database with demo data")
    parser.add_argument("--clear-only", action="store_true", help="Only clear existing data")
    args = parser.parse_args()

    print("=" * 60)
    print("DATABASE SEEDING SCRIPT")
    print("=" * 60)

    # Environment check
    check_environment()

    # Initialize database (create tables if they don't exist)
    print("\n🔧 Initializing database...")
    init_db()
    print("✓ Database initialized")

    # Get database session
    db = SessionLocal()

    try:
        # Clear existing data
        clear_demo_data(db)

        if args.clear_only:
            print("\n✅ Data cleared successfully. Exiting without seeding.")
            return

        # Seed all data
        seed_clients(db)
        seed_projects(db)
        seed_runs(db)
        seed_posts(db)
        seed_deliverables(db)

        print("\n" + "=" * 60)
        print("✅ SEEDING COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nDatabase populated with:")
        print("  • 15 clients")
        print("  • 27 projects")
        print("  • 10 runs (7 succeeded, 2 running)")
        print("  • 10 posts")
        print("  • 15 deliverables (7 delivered, 7 ready, 1 draft)")
        print("\n⚠️  REMINDER: This is demo data. Purge before production deployment!")

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
