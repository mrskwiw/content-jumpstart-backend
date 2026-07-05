"""
Unit tests for the PostgreSQL-direct TokenSyncService.

The new implementation receives a SQLAlchemy Session directly and queries the
api_calls table via raw SQL — no separate SQLite bridge file.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import Post, ResearchResult, Run
from backend.models.project import Project
from backend.models.client import Client
from backend.models.user import User
from backend.services.token_sync_service import TokenSyncService, _aggregate_api_calls


# ---------------------------------------------------------------------------
# Shared DDL (api_calls is not an ORM model — must be created manually)
# ---------------------------------------------------------------------------
_API_CALLS_DDL = """
CREATE TABLE IF NOT EXISTS api_calls (
    call_id   TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    operation  TEXT NOT NULL,
    model      TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0,
    timestamp DATETIME NOT NULL
);
"""

_SCHEMA_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY
);
"""


@pytest.fixture(scope="function")
def db(monkeypatch):
    """In-memory SQLite session with all ORM tables + api_calls."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(_API_CALLS_DDL))
        conn.execute(text(_SCHEMA_VERSIONS_DDL))
        conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    u = User(id="u-tss", email="tss@test.com", hashed_password="h")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def client(db, user):
    c = Client(
        id="client-tss",
        user_id=user.id,
        name="TSS Client",
        email="c@test.com",
        business_description="test",
        ideal_customer="test",
        main_problem_solved="test",
    )
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def project(db, user, client):
    p = Project(id="proj-tss", user_id=user.id, client_id=client.id, name="P", status="draft")
    db.add(p)
    db.commit()
    return p


@pytest.fixture
def run(db, project):
    now = datetime.utcnow()
    r = Run(
        id="run-tss",
        project_id=project.id,
        is_batch=True,
        started_at=now,
        completed_at=now + timedelta(seconds=60),
        status="succeeded",
    )
    db.add(r)
    db.commit()
    return r


@pytest.fixture
def posts(db, run, project):
    created = []
    for i in range(3):
        p = Post(
            id=f"post-tss-{i}",
            project_id=project.id,
            run_id=run.id,
            content=f"Content {i}",
            word_count=100 + i * 50,  # 100, 150, 200
            status="approved",
        )
        db.add(p)
        created.append(p)
    db.commit()
    return created


@pytest.fixture
def research(db, user, client, project):
    r = ResearchResult(
        id="res-tss",
        user_id=user.id,
        client_id=client.id,
        project_id=project.id,
        tool_name="seo_keyword_research",
        tool_label="SEO",
        tool_price=400.0,
        params={},
        outputs={},
        status="completed",
        duration_seconds=45,
        created_at=datetime.utcnow(),
    )
    db.add(r)
    db.commit()
    return r


def _insert_api_call(
    db,
    project_id,
    input_tokens,
    output_tokens,
    cache_creation=0,
    cache_read=0,
    cost=0.01,
    timestamp=None,
):
    if timestamp is None:
        timestamp = datetime.utcnow()
    db.execute(
        text(
            """
            INSERT INTO api_calls
            (call_id, project_id, operation, model,
             input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
             cost, timestamp)
            VALUES (:cid, :pid, 'gen', 'claude-3-5-sonnet-20241022',
                    :inp, :out, :cc, :cr, :cost, :ts)
        """
        ),
        {
            "cid": f"call-{id(timestamp)}",
            "pid": project_id,
            "inp": input_tokens,
            "out": output_tokens,
            "cc": cache_creation,
            "cr": cache_read,
            "cost": cost,
            "ts": timestamp,
        },
    )
    db.commit()


# ---------------------------------------------------------------------------
# _aggregate_api_calls (internal helper)
# ---------------------------------------------------------------------------


class TestAggregateApiCalls:
    def test_basic_aggregation(self, db, project):
        now = datetime.utcnow()
        _insert_api_call(db, project.id, 1_000, 500, cost=0.03, timestamp=now)
        _insert_api_call(
            db, project.id, 2_000, 1_000, cost=0.07, timestamp=now + timedelta(seconds=1)
        )

        result = _aggregate_api_calls(
            db, project.id, now - timedelta(seconds=1), now + timedelta(seconds=10)
        )
        assert result["total_input_tokens"] == 3_000
        assert result["total_output_tokens"] == 1_500
        assert result["total_cost"] == pytest.approx(0.10, abs=0.001)

    def test_time_window_filters(self, db, project):
        now = datetime.utcnow()
        _insert_api_call(
            db, project.id, 1_000, 500, cost=0.03, timestamp=now - timedelta(minutes=10)
        )
        _insert_api_call(db, project.id, 2_000, 1_000, cost=0.07, timestamp=now)

        # Window includes only the second call
        result = _aggregate_api_calls(
            db, project.id, now - timedelta(seconds=30), now + timedelta(seconds=30)
        )
        assert result["total_input_tokens"] == 2_000

    def test_wrong_project_excluded(self, db, project):
        now = datetime.utcnow()
        _insert_api_call(db, "other-proj", 5_000, 2_000, cost=0.10, timestamp=now)
        result = _aggregate_api_calls(
            db, project.id, now - timedelta(seconds=1), now + timedelta(seconds=1)
        )
        assert result == {}

    def test_no_rows_returns_empty(self, db, project):
        result = _aggregate_api_calls(db, project.id, datetime.utcnow(), datetime.utcnow())
        assert result == {}


# ---------------------------------------------------------------------------
# sync_run_token_usage
# ---------------------------------------------------------------------------


class TestSyncRunTokenUsage:
    def test_basic_sync(self, db, run, project):
        ts = run.started_at + timedelta(seconds=5)
        _insert_api_call(
            db, project.id, 1_500, 800, cache_creation=100, cache_read=50, cost=0.05, timestamp=ts
        )
        _insert_api_call(
            db, project.id, 2_000, 1_000, cost=0.07, timestamp=ts + timedelta(seconds=5)
        )

        svc = TokenSyncService()
        result = svc.sync_run_token_usage(db=db, run_id=run.id, project_id=project.id)

        assert result["total_input_tokens"] == 3_500
        assert result["total_output_tokens"] == 1_800
        assert result["total_cache_creation_tokens"] == 100
        assert result["total_cost"] == pytest.approx(0.12, abs=0.001)

        db.refresh(run)
        assert run.total_input_tokens == 3_500
        assert run.total_cost_usd == pytest.approx(0.12, abs=0.001)

    def test_no_api_calls_returns_empty(self, db, run, project):
        svc = TokenSyncService()
        result = svc.sync_run_token_usage(db=db, run_id=run.id, project_id=project.id)
        assert result == {}

    def test_missing_run_returns_empty(self, db):
        svc = TokenSyncService()
        result = svc.sync_run_token_usage(db=db, run_id="no-such-run", project_id="p-x")
        assert result == {}

    def test_time_window_excludes_outside_calls(self, db, run, project):
        before = run.started_at - timedelta(minutes=5)
        during = run.started_at + timedelta(seconds=10)
        after = run.completed_at + timedelta(minutes=5)

        _insert_api_call(db, project.id, 9_000, 9_000, cost=99.0, timestamp=before)
        _insert_api_call(db, project.id, 2_000, 1_000, cost=0.05, timestamp=during)
        _insert_api_call(db, project.id, 9_000, 9_000, cost=99.0, timestamp=after)

        svc = TokenSyncService()
        result = svc.sync_run_token_usage(db=db, run_id=run.id, project_id=project.id)
        assert result["total_input_tokens"] == 2_000


# ---------------------------------------------------------------------------
# sync_research_token_usage
# ---------------------------------------------------------------------------


class TestSyncResearchTokenUsage:
    def test_basic_sync(self, db, research, client):
        ts = research.created_at + timedelta(seconds=10)
        _insert_api_call(
            db,
            research.project_id,
            1_200,
            600,
            cache_creation=80,
            cache_read=40,
            cost=0.04,
            timestamp=ts,
        )

        svc = TokenSyncService()
        result = svc.sync_research_token_usage(
            db=db, research_result_id=research.id, client_id=client.id
        )

        assert result["total_input_tokens"] == 1_200
        assert result["total_output_tokens"] == 600
        assert result["total_cost"] == pytest.approx(0.04, abs=0.001)

        db.refresh(research)
        assert research.input_tokens == 1_200
        assert research.actual_cost_usd == pytest.approx(0.04, abs=0.001)

    def test_missing_research_returns_empty(self, db):
        svc = TokenSyncService()
        result = svc.sync_research_token_usage(db=db, research_result_id="no-such", client_id="c-x")
        assert result == {}

    def test_no_api_calls_returns_empty(self, db, research, client):
        svc = TokenSyncService()
        result = svc.sync_research_token_usage(
            db=db, research_result_id=research.id, client_id=client.id
        )
        assert result == {}


# ---------------------------------------------------------------------------
# estimate_post_token_usage
# ---------------------------------------------------------------------------


class TestEstimatePostTokenUsage:
    def test_proportional_distribution(self, db, run, posts):
        run.total_input_tokens = 4_500  # 100/450, 150/450, 200/450
        run.total_output_tokens = 2_250
        run.total_cache_read_tokens = 450
        run.total_cost_usd = 0.15
        db.commit()

        svc = TokenSyncService()
        updated = svc.estimate_post_token_usage(db=db, run_id=run.id)
        assert updated == 3

        db.refresh(posts[0])
        db.refresh(posts[1])
        db.refresh(posts[2])

        # Word counts: 100, 150, 200 — total 450
        assert posts[0].input_tokens == pytest.approx(1_000, abs=10)  # 100/450 * 4500
        assert posts[1].input_tokens == pytest.approx(1_500, abs=10)  # 150/450 * 4500
        assert posts[2].input_tokens == pytest.approx(2_000, abs=10)  # 200/450 * 4500
        assert posts[0].cost_usd == pytest.approx(0.0333, abs=0.005)

    def test_equal_distribution_when_no_word_counts(self, db, run, posts):
        for p in posts:
            p.word_count = 0
        run.total_input_tokens = 3_000
        run.total_output_tokens = 1_500
        run.total_cost_usd = 0.09
        db.commit()

        svc = TokenSyncService()
        updated = svc.estimate_post_token_usage(db=db, run_id=run.id)
        assert updated == 3

        for p in posts:
            db.refresh(p)
            assert p.input_tokens == 1_000
            assert p.output_tokens == 500
            assert p.cost_usd == pytest.approx(0.03, abs=0.001)

    def test_run_without_tokens_returns_zero(self, db, run):
        svc = TokenSyncService()
        assert svc.estimate_post_token_usage(db=db, run_id=run.id) == 0

    def test_run_with_no_posts_returns_zero(self, db, run):
        run.total_input_tokens = 1_000
        run.total_cost_usd = 0.01
        db.commit()
        svc = TokenSyncService()
        assert svc.estimate_post_token_usage(db=db, run_id=run.id) == 0

    def test_missing_run_returns_zero(self, db):
        svc = TokenSyncService()
        assert svc.estimate_post_token_usage(db=db, run_id="no-such-run") == 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_singleton_import():
    from backend.services.token_sync_service import token_sync_service

    assert isinstance(token_sync_service, TokenSyncService)
