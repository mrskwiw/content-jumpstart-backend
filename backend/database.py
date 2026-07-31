"""
Database configuration and session management.
"""

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from backend.config import settings
from backend.utils.query_profiler import enable_sqlalchemy_profiling
from src.config.pricing import PricingConfig


def _build_engine() -> Engine:
    """Create the SQLAlchemy engine from ``settings.DATABASE_URL``.

    SQLite: enables WAL mode so reads aren't blocked by a concurrent writer.
    PostgreSQL/MySQL: applies pool tuning and verifies connectivity at startup.
    If the production connection fails, this raises rather than silently
    degrading to ephemeral in-memory SQLite (a silent fallback once hid a prod
    outage for months — see BUGS.md / DATA-01), unless
    ``settings.ALLOW_SQLITE_FALLBACK`` explicitly opts into the dev-only fallback.
    """
    database_url = make_url(settings.DATABASE_URL)
    print(f">> DEBUG: Creating database engine for {database_url.drivername}")

    # SQLite-specific connection args (single-threaded, no real pooling)
    if database_url.drivername.startswith("sqlite"):
        try:
            eng = create_engine(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo_pool=settings.DB_ECHO_POOL,
            )
            # WAL mode so readers (e.g. login) aren't blocked by concurrent
            # writers (e.g. a 60s research tool holding an open session).
            with eng.connect() as _wal_conn:
                _wal_conn.execute(text("PRAGMA journal_mode=WAL"))
                _wal_conn.execute(text("PRAGMA busy_timeout=5000"))
            print(">> DEBUG: SQLite engine created successfully (WAL mode enabled)")
            return eng
        except Exception as e:
            print(f">> ERROR: Failed to create SQLite engine: {e}")
            raise

    # PostgreSQL/MySQL connection pooling (production)
    try:
        eng = create_engine(
            settings.DATABASE_URL,
            connect_args={},
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo_pool=settings.DB_ECHO_POOL,
            pool_timeout=settings.DB_POOL_TIMEOUT,
        )
        print(">> DEBUG: PostgreSQL engine created successfully")

        # Test the connection immediately so a bad DATABASE_URL surfaces now,
        # at startup, rather than on the first request.
        print(">> DEBUG: Testing PostgreSQL connection...")
        with eng.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        print(">> DEBUG: PostgreSQL connection test PASSED")
        return eng
    except Exception as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        print(">> ERROR: PostgreSQL connection FAILED")
        print(f">> ERROR: Details: {error_msg}")

        if not settings.ALLOW_SQLITE_FALLBACK:
            raise RuntimeError(
                "Could not connect to the configured PostgreSQL database and "
                "ALLOW_SQLITE_FALLBACK is disabled. Refusing to start on an "
                "ephemeral in-memory SQLite database. Check DATABASE_URL and "
                f"database connectivity. Original error: {error_msg}"
            ) from e

        print("=" * 60)
        print(">> FALLBACK: ALLOW_SQLITE_FALLBACK=true — using in-memory SQLite")
        print(">> WARNING: Data will NOT persist between restarts")
        print(">> WARNING: This is suitable for development/testing only")
        print("=" * 60)
        eng = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo_pool=settings.DB_ECHO_POOL,
        )
        print(">> DEBUG: In-memory SQLite fallback engine created")
        return eng


# Create SQLAlchemy engine with optimized connection pooling
engine = _build_engine()

# Enable query profiling for performance monitoring
enable_sqlalchemy_profiling(engine)

# Create SessionLocal class
# expire_on_commit=False prevents objects from being detached after commit
# This is critical for long-running operations where objects need to remain accessible
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this on application startup.
    Handles existing indexes gracefully to support database persistence.
    """
    from sqlalchemy import text, inspect

    # Import all models to ensure they're registered with SQLAlchemy
    # This must happen before Base.metadata.create_all() or mapper configuration
    from backend.models import Project
    from backend.migrations import load_migration_rules
    from backend.services.schema_inspector import get_schema_version, set_schema_version

    # Get current schema version
    current_version = get_schema_version(engine)
    print(f">> DEBUG: Current database schema version: v{current_version}")

    # Create all tables (handles existing indexes gracefully)
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        # Ignore "index already exists" errors (common with persistent databases)
        if "already exists" in str(e):
            print(
                f">> Note: Some database objects already exist (expected for persistent storage): {e}"
            )
            # Create tables individually to work around index errors
            for table in Base.metadata.sorted_tables:
                try:
                    table.create(bind=engine, checkfirst=True)
                except OperationalError as table_error:
                    if "already exists" not in str(table_error):
                        raise  # Re-raise if it's not an "already exists" error
        else:
            raise  # Re-raise if it's a different error

    # Run migrations (add missing columns)
    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if deliverables table exists
        if "deliverables" in inspector.get_table_names():
            # Check if file_size_bytes column exists
            columns = [col["name"] for col in inspector.get_columns("deliverables")]

            if "file_size_bytes" not in columns:
                print(">> Running migration: Adding file_size_bytes column to deliverables table")
                try:
                    conn.execute(
                        text("ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER")
                    )
                    conn.commit()
                    print(">> Migration completed successfully")
                except Exception as e:
                    print(f">> Migration failed: {e}")
                    # Non-critical - continue startup

        # Check if clients table exists
        if "clients" in inspector.get_table_names():
            # Check for ClientBrief columns
            columns = [col["name"] for col in inspector.get_columns("clients")]

            # List of columns to add
            new_columns = [
                ("business_description", "TEXT"),
                ("ideal_customer", "TEXT"),
                ("main_problem_solved", "TEXT"),
                ("tone_preference", "VARCHAR"),
                ("platforms", "JSON"),
                ("customer_pain_points", "JSON"),
                ("customer_questions", "JSON"),
                ("industry", "VARCHAR"),  # Industry/sector for research tools
                (
                    "keywords",
                    "JSON",
                ),  # SEO keywords (array of strings). 5+ keywords can skip SEO tool.
                (
                    "competitors",
                    "JSON",
                ),  # List of competitor names (1-5) for competitive analysis
                (
                    "location",
                    "VARCHAR",
                ),  # Geographic location/region for market context
                (
                    "founder_name",
                    "VARCHAR",
                ),  # Founder/owner name for personal brand content
                (
                    "brand_personality",
                    "JSON",
                ),  # Brand personality traits (array of strings)
                ("tone_to_avoid", "TEXT"),  # Tone/style the client does NOT want
                ("data_usage", "VARCHAR"),  # heavy / moderate / minimal
                (
                    "stories",
                    "JSON",
                ),  # Founder journey, customer wins, anecdotes (array)
                ("misconceptions", "JSON"),  # Industry myths / topics to avoid (array)
                ("measurable_results", "TEXT"),  # Stats and proof points
                ("posting_frequency", "VARCHAR"),  # Desired posting cadence
                ("main_cta", "VARCHAR"),  # Primary call-to-action text
                (
                    "key_phrases",
                    "JSON",
                ),  # Key brand/product phrases extracted from brief
            ]

            # SECURITY FIX: Whitelist of allowed SQL column types (TR-015)
            ALLOWED_TYPES = {
                "TEXT",
                "VARCHAR",
                "INTEGER",
                "REAL",
                "JSON",
                "BOOLEAN",
                "TIMESTAMP",
            }

            for col_name, col_type in new_columns:
                if col_name not in columns:
                    # SECURITY FIX: Validate SQL identifiers to prevent injection (TR-015)
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue

                    # SECURITY FIX: Validate column type against whitelist (TR-015)
                    # Extract base type (handle "REAL DEFAULT 40.0" -> "REAL")
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(f">> Running migration: Adding {col_name} column to clients table")
                    try:
                        # SECURITY: Use parameterized SQL to prevent injection (TR-015)
                        # SQLite doesn't support parameterized DDL, so we use validated identifiers
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type  # Already validated against whitelist

                        # Build DDL statement with validated, quoted identifiers
                        ddl_stmt = text(
                            f"ALTER TABLE clients ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")
                        # Non-critical - continue startup

        # Check if projects table exists (template quantities & pricing migration)
        if "projects" in inspector.get_table_names():
            # Check for new template quantities and pricing columns
            columns = [col["name"] for col in inspector.get_columns("projects")]

            # List of new columns to add for template quantities and pricing refactor
            new_project_columns = [
                ("template_quantities", "JSON"),  # Dict mapping template_id -> quantity
                ("num_posts", "INTEGER"),  # Total post count
                ("price_per_post", "REAL DEFAULT 40.0"),  # Base price per post
                (
                    "research_price_per_post",
                    "REAL DEFAULT 0.0",
                ),  # Research add-on per post
                ("total_price", "REAL"),  # Total calculated price
                (
                    "target_platform",
                    "VARCHAR DEFAULT 'blog'",
                ),  # Target platform for generation
            ]

            # SECURITY FIX: Whitelist of allowed SQL column types (TR-015)
            # Reuse same whitelist from clients table migration
            ALLOWED_TYPES = {
                "TEXT",
                "VARCHAR",
                "INTEGER",
                "REAL",
                "JSON",
                "BOOLEAN",
                "TIMESTAMP",
            }

            for col_name, col_type in new_project_columns:
                if col_name not in columns:
                    # SECURITY FIX: Validate SQL identifiers to prevent injection (TR-015)
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue

                    # SECURITY FIX: Validate column type against whitelist (TR-015)
                    # Extract base type (handle "REAL DEFAULT 40.0" -> "REAL")
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(f">> Running migration: Adding {col_name} column to projects table")
                    try:
                        # SECURITY: Use parameterized SQL to prevent injection (TR-015)
                        # SQLite doesn't support parameterized DDL, so we use validated identifiers
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type  # Already validated against whitelist

                        # Build DDL statement with validated, quoted identifiers
                        ddl_stmt = text(
                            f"ALTER TABLE projects ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")
                        # Non-critical - continue startup

            # Migrate existing projects: convert templates array to template_quantities dict
            # Only migrate projects that have templates but no template_quantities
            if "templates" in columns and "template_quantities" in columns:
                print(">> Running data migration: Converting templates to template_quantities")
                try:
                    # This SQL is database-agnostic for projects with legacy data
                    # We'll handle the conversion in Python for better control
                    from sqlalchemy.orm import Session

                    session = Session(bind=engine)
                    try:
                        # Project already imported at line 131
                        projects = (
                            session.query(Project)
                            .filter(
                                Project.templates.isnot(None),
                                Project.template_quantities.is_(None),
                            )
                            .all()
                        )

                        migrated_count = 0
                        for project in projects:
                            if project.templates and isinstance(project.templates, list):
                                # Equal distribution (legacy behavior)
                                num_templates = len(project.templates)
                                if num_templates > 0:
                                    default_total_posts = 30  # Assume 30 posts for legacy projects
                                    quantity_per_template = default_total_posts // num_templates
                                    remainder = default_total_posts % num_templates

                                    # Create template_quantities dict
                                    template_quantities = {}
                                    for i, template_id in enumerate(project.templates):
                                        # Distribute remainder to first templates
                                        quantity = quantity_per_template + (
                                            1 if i < remainder else 0
                                        )
                                        template_quantities[str(template_id)] = quantity

                                    # Update project
                                    project.template_quantities = template_quantities
                                    project.num_posts = default_total_posts
                                    project.price_per_post = PricingConfig().PRICE_PER_POST
                                    project.research_price_per_post = 0.0
                                    project.total_price = (
                                        default_total_posts * PricingConfig().PRICE_PER_POST
                                    )

                                    migrated_count += 1

                        if migrated_count > 0:
                            session.commit()
                            print(
                                f">> Data migration completed: Migrated {migrated_count} projects"
                            )
                        else:
                            print(">> No projects to migrate")

                    finally:
                        session.close()

                except Exception as e:
                    print(f">> Data migration failed: {e}")
                    # Non-critical - continue startup

        # Token usage tracking migration (runs, posts, research_results)
        # Add token and cost columns for API usage transparency
        if "runs" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("runs")]
            new_run_columns = [
                ("total_input_tokens", "INTEGER"),
                ("total_output_tokens", "INTEGER"),
                ("total_cache_creation_tokens", "INTEGER"),
                ("total_cache_read_tokens", "INTEGER"),
                ("total_cost_usd", "REAL"),
                ("estimated_cost_usd", "REAL"),
            ]

            for col_name, col_type in new_run_columns:
                if col_name not in columns:
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(f">> Running migration: Adding {col_name} column to runs table")
                    try:
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type
                        ddl_stmt = text(
                            f"ALTER TABLE runs ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")

        if "posts" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("posts")]
            new_post_columns = [
                ("input_tokens", "INTEGER"),
                ("output_tokens", "INTEGER"),
                ("cache_read_tokens", "INTEGER"),
                ("cost_usd", "REAL"),
                ("twitter_share_copy", "VARCHAR"),
            ]

            for col_name, col_type in new_post_columns:
                if col_name not in columns:
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(f">> Running migration: Adding {col_name} column to posts table")
                    try:
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type
                        ddl_stmt = text(
                            f"ALTER TABLE posts ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")

        if "research_results" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("research_results")]
            new_research_columns = [
                ("input_tokens", "INTEGER"),
                ("output_tokens", "INTEGER"),
                ("cache_creation_tokens", "INTEGER"),
                ("cache_read_tokens", "INTEGER"),
                ("actual_cost_usd", "REAL"),
            ]

            for col_name, col_type in new_research_columns:
                if col_name not in columns:
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(
                        f">> Running migration: Adding {col_name} column to research_results table"
                    )
                    try:
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type
                        ddl_stmt = text(
                            f"ALTER TABLE research_results ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")

        # NOTE: ResearchResult table is auto-created by Base.metadata.create_all()
        # No manual migration needed - table will be created on first startup

        # Credit system migration (users table)
        if "users" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("users")]
            new_user_columns = [
                ("credit_balance", "INTEGER DEFAULT 0"),
                ("total_credits_purchased", "INTEGER DEFAULT 0"),
                ("total_credits_used", "INTEGER DEFAULT 0"),
                ("is_enterprise", "BOOLEAN DEFAULT FALSE"),
                ("custom_credit_rate", "REAL"),
                ("enterprise_notes", "TEXT"),
                # GAP-AUTH-02: email verification (existing DBs get these on boot).
                # DEFAULT TRUE grandfathers pre-existing accounts as verified so that
                # enabling REQUIRE_EMAIL_VERIFICATION can never lock out incumbents; the
                # ORM model default is False, so NEW signups still start unverified.
                ("email_verified", "BOOLEAN DEFAULT TRUE"),
                ("email_verified_at", "TIMESTAMP"),
            ]

            for col_name, col_type in new_user_columns:
                if col_name not in columns:
                    import re

                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                        print(f">> ERROR: Invalid column name '{col_name}' (security check failed)")
                        continue
                    base_type = col_type.split()[0] if " " in col_type else col_type
                    if base_type not in ALLOWED_TYPES:
                        print(f">> ERROR: Invalid column type '{col_type}' (security check failed)")
                        continue

                    print(f">> Running migration: Adding {col_name} column to users table")
                    try:
                        from sqlalchemy.sql import quoted_name

                        safe_col_name = quoted_name(col_name, quote=True)
                        safe_col_type = col_type
                        ddl_stmt = text(
                            f"ALTER TABLE users ADD COLUMN {safe_col_name} {safe_col_type}"
                        )
                        conn.execute(ddl_stmt)
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")

            # GAP-AUTH-02 one-time grandfather backfill (schema v7). The add-column
            # DEFAULT TRUE only grandfathers when the column is freshly added; this
            # covers deployments where users.email_verified already exists with FALSE
            # incumbents. Gated on the version bump so it runs exactly once and never
            # re-flips genuinely-unverified NEW signups on a later boot.
            if current_version < 7:
                try:
                    conn.execute(
                        text(
                            "UPDATE users SET email_verified = TRUE "
                            "WHERE email_verified = FALSE OR email_verified IS NULL"
                        )
                    )
                    conn.commit()
                    print(">> GAP-AUTH-02: grandfathered pre-existing users to email_verified=TRUE")
                except Exception as e:
                    print(f">> email_verified grandfather backfill skipped/failed: {e}")

        # Seed credit packages (only if table is empty)
        # CreditPackage table is auto-created by Base.metadata.create_all()
        if "credit_packages" in inspector.get_table_names():
            # Check if packages already exist
            result = conn.execute(text("SELECT COUNT(*) FROM credit_packages"))
            count = result.scalar()

            if count == 0:
                print(">> Seeding credit_packages table with initial data")
                try:
                    import uuid

                    # Standard packages ($2/credit)
                    standard_packages = [
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Starter Pack",
                            "credits": 100,
                            "price_usd": 200.0,
                            "package_type": "package",
                            "description": "Perfect for trying out the platform",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Basic Pack",
                            "credits": 300,
                            "price_usd": 600.0,
                            "package_type": "package",
                            "description": "Great for small businesses",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Pro Pack",
                            "credits": 600,
                            "price_usd": 1200.0,
                            "package_type": "package",
                            "description": "Ideal for regular content creation",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Business Pack",
                            "credits": 1200,
                            "price_usd": 2400.0,
                            "package_type": "package",
                            "description": "Best for agencies and teams",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Premium Pack",
                            "credits": 2500,
                            "price_usd": 5000.0,
                            "package_type": "package",
                            "description": "Maximum value for high-volume users",
                        },
                    ]

                    # Additional credits ($2.50/credit in 100-credit batches)
                    additional_packages = [
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Additional 100 Credits",
                            "credits": 100,
                            "price_usd": 250.0,
                            "package_type": "additional",
                            "description": "Top-up credits at $2.50 each",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Additional 200 Credits",
                            "credits": 200,
                            "price_usd": 500.0,
                            "package_type": "additional",
                            "description": "Top-up credits at $2.50 each",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Additional 300 Credits",
                            "credits": 300,
                            "price_usd": 750.0,
                            "package_type": "additional",
                            "description": "Top-up credits at $2.50 each",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Additional 500 Credits",
                            "credits": 500,
                            "price_usd": 1250.0,
                            "package_type": "additional",
                            "description": "Top-up credits at $2.50 each",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "name": "Additional 1000 Credits",
                            "credits": 1000,
                            "price_usd": 2500.0,
                            "package_type": "additional",
                            "description": "Top-up credits at $2.50 each",
                        },
                    ]

                    all_packages = standard_packages + additional_packages

                    for pkg in all_packages:
                        insert_stmt = text(
                            """
                            INSERT INTO credit_packages
                            (id, name, credits, price_usd, package_type, is_active, description)
                            VALUES
                            (:id, :name, :credits, :price_usd, :package_type, TRUE, :description)
                            """
                        )
                        conn.execute(insert_stmt, pkg)

                    conn.commit()
                    print(f">> Seeded {len(all_packages)} credit packages successfully")

                except Exception as e:
                    print(f">> Seeding credit_packages failed: {e}")

        # Soft delete migration (GDPR/CCPA compliance - TR-XXX)
        # Add deleted_at and is_deleted columns to tables containing PII
        soft_delete_tables = [
            "clients",
            "projects",
            "users",
            "posts",
            "research_results",
        ]

        for table_name in soft_delete_tables:
            if table_name in inspector.get_table_names():
                columns = [col["name"] for col in inspector.get_columns(table_name)]

                soft_delete_columns = [
                    ("deleted_at", "TIMESTAMP"),
                    ("is_deleted", "BOOLEAN DEFAULT FALSE"),
                ]

                for col_name, col_type in soft_delete_columns:
                    if col_name not in columns:
                        import re

                        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                            print(
                                f">> ERROR: Invalid column name '{col_name}' (security check failed)"
                            )
                            continue
                        base_type = col_type.split()[0] if " " in col_type else col_type
                        if base_type not in ALLOWED_TYPES:
                            print(
                                f">> ERROR: Invalid column type '{col_type}' (security check failed)"
                            )
                            continue

                        print(
                            f">> Running migration: Adding {col_name} to {table_name} (GDPR compliance)"
                        )
                        try:
                            from sqlalchemy.sql import quoted_name

                            safe_col_name = quoted_name(col_name, quote=True)
                            safe_col_type = col_type
                            ddl_stmt = text(
                                f"ALTER TABLE {table_name} ADD COLUMN {safe_col_name} {safe_col_type}"
                            )
                            conn.execute(ddl_stmt)
                            conn.commit()
                            print(f">> Migration for {table_name}.{col_name} completed")
                        except Exception as e:
                            print(f">> Migration for {table_name}.{col_name} failed: {e}")

    # Update schema version to latest after all migrations
    config = load_migration_rules()
    latest_version = config["current_version"]

    if current_version < latest_version:
        set_schema_version(engine, latest_version)
        print(f">> DEBUG: Schema version updated: v{current_version} -> v{latest_version}")
    elif current_version == latest_version:
        print(f">> DEBUG: Schema version is current: v{latest_version}")
    else:
        print(
            f">> WARNING: Database schema version v{current_version} is newer than "
            f"expected v{latest_version}. This may indicate a downgrade."
        )
