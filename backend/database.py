"""
Database configuration and session management.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine.url import make_url

from config import settings
from utils.query_profiler import enable_sqlalchemy_profiling

# Create SQLAlchemy engine with optimized connection pooling
database_url = make_url(settings.DATABASE_URL)

# SQLite-specific connection args (single-threaded, no real pooling)
if database_url.drivername.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite uses NullPool or SingletonThreadPool by default
    # Connection pooling settings don't apply
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        echo_pool=settings.DB_ECHO_POOL,
    )
else:
    # PostgreSQL/MySQL connection pooling (production)
    connect_args = {}
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
    """
    from sqlalchemy import text, inspect

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Run migrations (add missing columns)
    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if deliverables table exists
        if 'deliverables' in inspector.get_table_names():
            # Check if file_size_bytes column exists
            columns = [col['name'] for col in inspector.get_columns('deliverables')]

            if 'file_size_bytes' not in columns:
                print(">> Running migration: Adding file_size_bytes column to deliverables table")
                try:
                    conn.execute(text("ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER"))
                    conn.commit()
                    print(">> Migration completed successfully")
                except Exception as e:
                    print(f">> Migration failed: {e}")
                    # Non-critical - continue startup
                    pass

        # Check if clients table exists
        if 'clients' in inspector.get_table_names():
            # Check for ClientBrief columns
            columns = [col['name'] for col in inspector.get_columns('clients')]

            # List of columns to add
            new_columns = [
                ('business_description', 'TEXT'),
                ('ideal_customer', 'TEXT'),
                ('main_problem_solved', 'TEXT'),
                ('tone_preference', 'VARCHAR'),
                ('platforms', 'JSON'),
                ('customer_pain_points', 'JSON'),
                ('customer_questions', 'JSON'),
            ]

            for col_name, col_type in new_columns:
                if col_name not in columns:
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
        if 'projects' in inspector.get_table_names():
            # Check for new template quantities and pricing columns
            columns = [col['name'] for col in inspector.get_columns('projects')]

            # List of new columns to add for template quantities and pricing refactor
            new_project_columns = [
                ('template_quantities', 'JSON'),  # Dict mapping template_id -> quantity
                ('num_posts', 'INTEGER'),  # Total post count
                ('price_per_post', 'REAL DEFAULT 40.0'),  # Base price per post
                ('research_price_per_post', 'REAL DEFAULT 0.0'),  # Research add-on per post
                ('total_price', 'REAL'),  # Total calculated price
            ]

            for col_name, col_type in new_project_columns:
                if col_name not in columns:
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
            if 'templates' in columns and 'template_quantities' in columns:
                print(">> Running data migration: Converting templates to template_quantities")
                try:
                    # This SQL is database-agnostic for projects with legacy data
                    # We'll handle the conversion in Python for better control
                    from sqlalchemy.orm import Session
                    session = Session(bind=engine)
                    try:
                        from models.project import Project
                        import json

                        projects = session.query(Project).filter(
                            Project.templates.isnot(None),
                            Project.template_quantities.is_(None)
                        ).all()

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
                                        quantity = quantity_per_template + (1 if i < remainder else 0)
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
                            print(f">> Data migration completed: Migrated {migrated_count} projects")
                        else:
                            print(">> No projects to migrate")

                    finally:
                        session.close()

                except Exception as e:
                    print(f">> Data migration failed: {e}")
                    # Non-critical - continue startup
                    pass
