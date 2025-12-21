"""
Create demo deliverable files for testing download functionality.
Also updates file_size_bytes in the database.
"""
from pathlib import Path
import sys

# Add parent directory to path so we can import database modules
sys.path.insert(0, str(Path(__file__).parent))

# Demo file paths from seed_demo_data.py
demo_files = [
    "acme-corp/linkedin-q1-2025-12-14.docx",
    "techvision/ai-launch-2024-12-05.txt",
    "financeflow/fintech-trends-2024-11-27.docx",
    "edupro/learning-tips-2024-12-05.txt",
    "securenet/cybersecurity-2024-12-01.docx",
    "cloudscale/cloud-migration-2024-12-08.docx",
    "contentcraft/workshop-2024-11-29.txt",
    "acme-corp/twitter-leadership-2024-12-12.txt",
    "growthlab/social-strategy-2024-12-11.docx",
    "wanderlust/destination-guides-2024-12-09.txt",
    "retailboost/retail-trends-2024-12-10.docx",
    "fitwell/wellness-tips-2024-12-11.txt",
    "urbanspace/market-insights-2024-12-06.docx",
    "financeflow/investment-tips-2024-12-13.txt",
    "acme-corp/blog-series-draft.docx",
]

def create_demo_files():
    """Create demo files in data/outputs/ directory."""
    base_path = Path("data/outputs")
    base_path.mkdir(parents=True, exist_ok=True)

    created_count = 0
    for file_path in demo_files:
        full_path = base_path / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip if file already exists
        if full_path.exists():
            print(f"⏭️  Skipped (already exists): {file_path}")
            continue

        # Create file with sample content
        file_ext = full_path.suffix
        if file_ext == ".txt":
            content = f"""30-Day Content Jumpstart Deliverable
Generated: {file_path}

This is a demo deliverable file for testing the download functionality.

Sample Posts:
1. "Are you making these common mistakes in your content strategy?"
2. "The data doesn't lie: 73% of marketers see better ROI with consistent content."
3. "Here's the contrarian take nobody wants to hear..."

Quality Metrics:
- Unique hooks: 28/30 (93%)
- CTA variety: 85%
- Average length: 187 words
- Readability score: 62 (Plain English)

Brand Voice Analysis:
- Tone: Professional yet approachable
- Formality: 62/100 (balanced)
- Perspective: First person (builds connection)
"""
        else:
            # For .docx files, create a simple text file (in production, use python-docx)
            content = f"""[DOCX PLACEHOLDER]
This is a placeholder for a .docx deliverable: {file_path}

In production, this would be a properly formatted Word document with:
- 30 social media posts
- Brand voice guide
- Content calendar
- QA report
"""

        # Write file
        full_path.write_text(content, encoding="utf-8")
        print(f"✅ Created: {file_path}")
        created_count += 1

    print(f"\n✨ Created {created_count} new demo files")
    print(f"📁 All files are in: {base_path.absolute()}")

    # Update file sizes in database
    try:
        from database import SessionLocal
        from models import Deliverable
        from sqlalchemy import text

        db = SessionLocal()
        try:
            # Update file_size_bytes for all deliverables
            updated = 0
            deliverables = db.query(Deliverable).all()

            for deliv in deliverables:
                full_path = base_path / deliv.path
                if full_path.exists():
                    file_size = full_path.stat().st_size
                    deliv.file_size_bytes = file_size
                    updated += 1

            db.commit()
            print(f"\n📊 Updated file sizes for {updated} deliverables in database")

        finally:
            db.close()

    except Exception as e:
        print(f"\n⚠️  Could not update database: {e}")
        print("   Run this script again after the backend is initialized")

if __name__ == "__main__":
    create_demo_files()
