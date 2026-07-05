"""
Integration tests for Token Tracking (PostgreSQL-direct implementation).

TokenSyncService now queries the api_calls table in the same SQLAlchemy
session as the rest of the app — no separate SQLite bridge file.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import Post, ResearchResult, Run
from backend.models.client import Client
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.post import PostResponse
from backend.schemas.research_schemas import ResearchResultResponse
from backend.schemas.run import RunResponse
from backend.services.token_sync_service import TokenSyncService


# ---------------------------------------------------------------------------
# api_calls DDL (not an ORM model — must be created manually)
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


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(_API_CALLS_DDL))
        conn.commit()
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def setup_test_data(test_db: Session):
    user = User(id="user-integration", email="integration@test.com", hashed_password="hashed")
    test_db.add(user)

    client = Client(
        id="client-integration",
        user_id=user.id,
        name="Integration Client",
        email="client@test.com",
        business_description="Test business",
        ideal_customer="Test users",
        main_problem_solved="Testing",
    )
    test_db.add(client)

    project = Project(
        id="proj-integration",
        user_id=user.id,
        client_id=client.id,
        name="Integration Project",
        status="ready",
        platforms=["linkedin"],
    )
    test_db.add(project)
    test_db.commit()
    return {"user": user, "client": client, "project": project}


def _insert_api_call(
    db: Session,
    project_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation: int = 0,
    cache_read: int = 0,
    timestamp: datetime = None,
):
    """Insert an api_call row into the test database."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    import uuid

    cost = (
        (input_tokens / 1_000_000 * 3.0)
        + (output_tokens / 1_000_000 * 15.0)
        + (cache_creation / 1_000_000 * 3.75)
        + (cache_read / 1_000_000 * 0.30)
    )
    db.execute(
        text(
            """
            INSERT INTO api_calls
                (call_id, project_id, operation, model,
                 input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
                 cost, timestamp)
            VALUES
                (:cid, :pid, 'post_generation', 'claude-3-5-sonnet-20241022',
                 :inp, :out, :cc, :cr, :cost, :ts)
        """
        ),
        {
            "cid": uuid.uuid4().hex,
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


class TestTokenTrackingIntegration:

    def test_run_token_tracking_end_to_end(self, test_db: Session, setup_test_data):
        """Run creation → API calls → Token sync → Response schema."""
        project = setup_test_data["project"]
        now = datetime.utcnow()

        run = Run(
            id="run-e2e-test",
            project_id=project.id,
            is_batch=True,
            started_at=now,
            completed_at=now + timedelta(seconds=60),
            status="succeeded",
        )
        test_db.add(run)
        test_db.commit()

        ts = now + timedelta(seconds=5)
        _insert_api_call(test_db, project.id, 1500, 800, cache_read=100, timestamp=ts)
        _insert_api_call(
            test_db, project.id, 1800, 900, cache_read=120, timestamp=ts + timedelta(seconds=5)
        )
        _insert_api_call(
            test_db, project.id, 1600, 850, cache_read=110, timestamp=ts + timedelta(seconds=10)
        )

        svc = TokenSyncService()
        usage = svc.sync_run_token_usage(db=test_db, run_id=run.id, project_id=project.id)

        assert usage["total_input_tokens"] == 4900
        assert usage["total_output_tokens"] == 2550
        assert usage["total_cache_read_tokens"] == 330

        test_db.refresh(run)
        assert run.total_input_tokens == 4900
        assert run.total_output_tokens == 2550
        assert run.total_cost_usd is not None and run.total_cost_usd > 0

        run_response = RunResponse.model_validate(run)
        assert run_response.total_input_tokens == 4900
        assert run_response.total_output_tokens == 2550

    def test_post_token_tracking_with_estimation(self, test_db: Session, setup_test_data):
        """Post token usage distributed proportionally by word count."""
        project = setup_test_data["project"]
        now = datetime.utcnow()

        run = Run(
            id="run-post-est",
            project_id=project.id,
            is_batch=True,
            started_at=now,
            completed_at=now,
            status="succeeded",
            total_input_tokens=3000,
            total_output_tokens=1500,
            total_cost_usd=0.10,
        )
        test_db.add(run)

        posts = [
            Post(
                id="post-1",
                project_id=project.id,
                run_id=run.id,
                content="S",
                word_count=50,
                status="approved",
            ),
            Post(
                id="post-2",
                project_id=project.id,
                run_id=run.id,
                content="M",
                word_count=100,
                status="approved",
            ),
            Post(
                id="post-3",
                project_id=project.id,
                run_id=run.id,
                content="L",
                word_count=150,
                status="approved",
            ),
        ]
        for p in posts:
            test_db.add(p)
        test_db.commit()

        svc = TokenSyncService()
        updated = svc.estimate_post_token_usage(db=test_db, run_id=run.id)
        assert updated == 3

        for p in posts:
            test_db.refresh(p)

        # 50:100:150 ratio over totals
        assert posts[0].input_tokens == pytest.approx(500, abs=10)
        assert posts[1].input_tokens == pytest.approx(1000, abs=10)
        assert posts[2].input_tokens == pytest.approx(1500, abs=10)
        assert posts[0].cost_usd == pytest.approx(0.0167, abs=0.005)

        for p in posts:
            resp = PostResponse.model_validate(p)
            assert resp.input_tokens is not None
            assert resp.output_tokens is not None
            assert resp.cost_usd is not None

    def test_research_token_tracking_end_to_end(self, test_db: Session, setup_test_data):
        """Research tool token tracking: API cost vs business model price."""
        client = setup_test_data["client"]
        project = setup_test_data["project"]
        now = datetime.utcnow()

        research = ResearchResult(
            id="res-e2e",
            user_id=client.user_id,
            client_id=client.id,
            project_id=project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
            duration_seconds=62.5,
            created_at=now,
        )
        test_db.add(research)
        test_db.commit()

        _insert_api_call(
            test_db,
            project.id,
            2500,
            1200,
            cache_creation=200,
            cache_read=150,
            timestamp=now + timedelta(seconds=10),
        )

        svc = TokenSyncService()
        usage = svc.sync_research_token_usage(
            db=test_db, research_result_id=research.id, client_id=client.id
        )

        assert usage["total_input_tokens"] == 2500
        assert usage["total_output_tokens"] == 1200
        assert usage["total_cache_creation_tokens"] == 200
        assert usage["total_cache_read_tokens"] == 150

        test_db.refresh(research)
        assert research.input_tokens == 2500
        assert research.output_tokens == 1200
        assert research.actual_cost_usd != research.tool_price

        resp = ResearchResultResponse.model_validate(research)
        assert resp.tool_price == 400.0
        assert resp.actual_cost_usd is not None
        assert resp.input_tokens == 2500

    def test_cache_token_tracking(self, test_db: Session, setup_test_data):
        """Cache token counts tracked separately."""
        project = setup_test_data["project"]
        now = datetime.utcnow()

        run = Run(
            id="run-cache",
            project_id=project.id,
            is_batch=True,
            started_at=now,
            completed_at=now + timedelta(seconds=60),
            status="succeeded",
        )
        test_db.add(run)
        test_db.commit()

        ts = now + timedelta(seconds=5)
        _insert_api_call(
            test_db, project.id, 1000, 500, cache_creation=500, cache_read=0, timestamp=ts
        )
        _insert_api_call(
            test_db,
            project.id,
            100,
            500,
            cache_creation=0,
            cache_read=900,
            timestamp=ts + timedelta(seconds=5),
        )
        _insert_api_call(
            test_db,
            project.id,
            100,
            500,
            cache_creation=0,
            cache_read=900,
            timestamp=ts + timedelta(seconds=10),
        )

        svc = TokenSyncService()
        usage = svc.sync_run_token_usage(db=test_db, run_id=run.id, project_id=project.id)

        assert usage["total_input_tokens"] == 1200
        assert usage["total_cache_creation_tokens"] == 500
        assert usage["total_cache_read_tokens"] == 1800

        test_db.refresh(run)
        assert run.total_cache_creation_tokens == 500
        assert run.total_cache_read_tokens == 1800

    def test_multiple_projects_isolation(self, test_db: Session, setup_test_data):
        """Each project's tokens are tracked independently."""
        user = setup_test_data["user"]
        client = setup_test_data["client"]
        now = datetime.utcnow()

        p1 = Project(
            id="proj-iso-1", user_id=user.id, client_id=client.id, name="P1", status="ready"
        )
        p2 = Project(
            id="proj-iso-2", user_id=user.id, client_id=client.id, name="P2", status="ready"
        )
        test_db.add_all([p1, p2])

        r1 = Run(
            id="run-iso-1",
            project_id=p1.id,
            is_batch=True,
            started_at=now,
            completed_at=now + timedelta(seconds=60),
            status="succeeded",
        )
        r2 = Run(
            id="run-iso-2",
            project_id=p2.id,
            is_batch=True,
            started_at=now,
            completed_at=now + timedelta(seconds=60),
            status="succeeded",
        )
        test_db.add_all([r1, r2])
        test_db.commit()

        ts = now + timedelta(seconds=5)
        _insert_api_call(test_db, p1.id, 1000, 500, timestamp=ts)
        _insert_api_call(test_db, p1.id, 1500, 750, timestamp=ts + timedelta(seconds=5))
        _insert_api_call(test_db, p2.id, 2000, 1000, timestamp=ts)

        svc = TokenSyncService()
        u1 = svc.sync_run_token_usage(db=test_db, run_id=r1.id, project_id=p1.id)
        u2 = svc.sync_run_token_usage(db=test_db, run_id=r2.id, project_id=p2.id)

        assert u1["total_input_tokens"] == 2500
        assert u2["total_input_tokens"] == 2000

        test_db.refresh(r1)
        test_db.refresh(r2)
        assert r1.total_input_tokens == 2500
        assert r2.total_input_tokens == 2000

    def test_token_tracking_with_failed_run(self, test_db: Session, setup_test_data):
        """Partial token tracking works even for failed runs."""
        project = setup_test_data["project"]
        now = datetime.utcnow()

        run = Run(
            id="run-failed",
            project_id=project.id,
            is_batch=True,
            started_at=now,
            completed_at=now + timedelta(seconds=30),
            status="failed",
            error_message="Failed after 2 posts",
        )
        test_db.add(run)
        test_db.commit()

        ts = now + timedelta(seconds=5)
        _insert_api_call(test_db, project.id, 1500, 800, timestamp=ts)
        _insert_api_call(test_db, project.id, 1600, 850, timestamp=ts + timedelta(seconds=5))

        svc = TokenSyncService()
        usage = svc.sync_run_token_usage(db=test_db, run_id=run.id, project_id=project.id)

        assert usage["total_input_tokens"] == 3100
        assert usage["total_output_tokens"] == 1650

        test_db.refresh(run)
        assert run.total_input_tokens == 3100
        assert run.total_cost_usd is not None
