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
    Base.metadata.create_all(bind=engine)
