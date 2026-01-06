"""
Database configuration and session management.
"""

import sys
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from backend.config import settings
from backend.utils.query_profiler import enable_sqlalchemy_profiling

# Create SQLAlchemy engine with optimized connection pooling
database_url = make_url(settings.DATABASE_URL)

print(f">> DEBUG: Creating database engine for {database_url.drivername}")

# SQLite-specific connection args (single-threaded, no real pooling)
if database_url.drivername.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite uses NullPool or SingletonThreadPool by default
    # Connection pooling settings don't apply
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            echo_pool=settings.DB_ECHO_POOL,
        )
        print(">> DEBUG: SQLite engine created successfully")
    except Exception as e:
        print(f">> ERROR: Failed to create SQLite engine: {e}")
        raise
else:
    # PostgreSQL/MySQL connection pooling (production)
    connect_args = {}
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo_pool=settings.DB_ECHO_POOL,
            pool_timeout=settings.DB_POOL_TIMEOUT,
        )
        print(">> DEBUG: PostgreSQL engine created successfully")

        # Test connection immediately
        print(">> DEBUG: Testing PostgreSQL connection...")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            print(">> DEBUG: PostgreSQL connection test PASSED")
        except OperationalError as e:
            error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
            print(">> ERROR: PostgreSQL connection FAILED")
            print(">> ERROR: Cannot connect to database")
            print(f">> ERROR: Details: {error_msg}")

            # Provide helpful troubleshooting tips
            if "could not connect to server" in error_msg.lower():
                print(">> ERROR: Database server unreachable. Check:")
                print(">>   1. DATABASE_URL is correct (internal URL for Render)")
                print(">>   2. PostgreSQL service is running")
                print(">>   3. Network/firewall allows connection")
            elif "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                print(">> ERROR: Authentication failed. Check:")
                print(">>   1. Username is correct")
                print(">>   2. Password is correct")
                print(">>   3. User has access to the database")
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                print(">> ERROR: Database does not exist. Check:")
                print(">>   1. Database name in DATABASE_URL is correct")
                print(">>   2. Database has been created")

            print(">> FATAL: Cannot start application without database connection")
            sys.exit(1)
        except Exception as e:
            print(f">> ERROR: Unexpected database error: {e}")
            print(">> FATAL: Cannot start application without database connection")
            sys.exit(1)

    except Exception as e:
        print(f">> ERROR: Failed to create PostgreSQL engine: {e}")
        print(">> ERROR: DATABASE_URL format may be invalid")
        print(">> ERROR: Expected format: postgresql://user:pass@host:port/dbname")
        raise

# Enable query profiling for performance monitoring
enable_sqlalchemy_profiling(engine)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
    from sqlalchemy.exc import OperationalError

    # Import all models to ensure they're registered with SQLAlchemy
    # This must happen before Base.metadata.create_all() or mapper configuration
    from backend.models import Project

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
                    pass

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
            ]

            # SECURITY FIX: Whitelist of allowed SQL column types (TR-015)
            ALLOWED_TYPES = {"TEXT", "VARCHAR", "INTEGER", "REAL", "JSON", "BOOLEAN", "TIMESTAMP"}

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
                        conn.execute(text(f"ALTER TABLE clients ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")
                        # Non-critical - continue startup
                        pass

        # Check if projects table exists (template quantities & pricing migration)
        if "projects" in inspector.get_table_names():
            # Check for new template quantities and pricing columns
            columns = [col["name"] for col in inspector.get_columns("projects")]

            # List of new columns to add for template quantities and pricing refactor
            new_project_columns = [
                ("template_quantities", "JSON"),  # Dict mapping template_id -> quantity
                ("num_posts", "INTEGER"),  # Total post count
                ("price_per_post", "REAL DEFAULT 40.0"),  # Base price per post
                ("research_price_per_post", "REAL DEFAULT 0.0"),  # Research add-on per post
                ("total_price", "REAL"),  # Total calculated price
            ]

            # SECURITY FIX: Whitelist of allowed SQL column types (TR-015)
            # Reuse same whitelist from clients table migration
            ALLOWED_TYPES = {"TEXT", "VARCHAR", "INTEGER", "REAL", "JSON", "BOOLEAN", "TIMESTAMP"}

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
                        conn.execute(text(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f">> Migration for {col_name} completed successfully")
                    except Exception as e:
                        print(f">> Migration for {col_name} failed: {e}")
                        # Non-critical - continue startup
                        pass

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
                                Project.templates.isnot(None), Project.template_quantities.is_(None)
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
                                    project.price_per_post = 40.0
                                    project.research_price_per_post = 0.0
                                    project.total_price = default_total_posts * 40.0

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
                    pass
