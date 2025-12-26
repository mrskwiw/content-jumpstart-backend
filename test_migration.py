"""
Test database migration for template quantities and pricing fields.
"""
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

print("=" * 60)
print("DATABASE MIGRATION TEST")
print("=" * 60)

# Import database components
from database import init_db, engine
from sqlalchemy import inspect

print("\n>> Running database initialization and migrations...")
try:
    init_db()
    print("✓ Database initialization completed")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify the migration worked
print("\n>> Verifying projects table structure...")
inspector = inspect(engine)

if 'projects' not in inspector.get_table_names():
    print("❌ Projects table does not exist!")
    sys.exit(1)

columns = {col['name']: col['type'] for col in inspector.get_columns('projects')}
print(f"✓ Projects table found with {len(columns)} columns")

# Check for new columns
expected_columns = [
    'template_quantities',
    'num_posts',
    'price_per_post',
    'research_price_per_post',
    'total_price',
]

print("\n>> Checking for new columns:")
all_present = True
for col_name in expected_columns:
    if col_name in columns:
        print(f"  ✓ {col_name}: {columns[col_name]}")
    else:
        print(f"  ❌ {col_name}: MISSING")
        all_present = False

# Check legacy column still exists
if 'templates' in columns:
    print(f"  ✓ templates (legacy): {columns['templates']} - preserved for backward compatibility")
else:
    print(f"  ❌ templates (legacy): MISSING - backward compatibility may be broken")
    all_present = False

if all_present:
    print("\n" + "=" * 60)
    print("✓✓✓ MIGRATION SUCCESSFUL ✓✓✓")
    print("=" * 60)
    print("\nAll required columns added to projects table.")
    print("Database is ready for template quantities and pricing features.")
else:
    print("\n" + "=" * 60)
    print("❌ MIGRATION INCOMPLETE")
    print("=" * 60)
    sys.exit(1)
