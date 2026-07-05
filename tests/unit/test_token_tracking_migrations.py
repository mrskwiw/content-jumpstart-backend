"""
Unit tests for Token Tracking Database Migrations

Tests that new token/cost columns are added correctly via migrations.
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base, init_db


class TestTokenTrackingMigrations:
    """Test suite for token tracking database migrations"""

    def test_run_model_has_token_columns(self):
        """Test that Run model has all token tracking columns"""
        from backend.models.run import Run

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Inspect Run table
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("runs")]

        # Verify token columns exist
        assert "total_input_tokens" in columns
        assert "total_output_tokens" in columns
        assert "total_cache_creation_tokens" in columns
        assert "total_cache_read_tokens" in columns
        assert "total_cost_usd" in columns
        assert "estimated_cost_usd" in columns

    def test_post_model_has_token_columns(self):
        """Test that Post model has all token tracking columns"""
        from backend.models.post import Post

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Inspect Post table
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("posts")]

        # Verify token columns exist
        assert "input_tokens" in columns
        assert "output_tokens" in columns
        assert "cache_read_tokens" in columns
        assert "cost_usd" in columns

    def test_research_result_model_has_token_columns(self):
        """Test that ResearchResult model has all token tracking columns"""
        from backend.models.research_result import ResearchResult

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Inspect ResearchResult table
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("research_results")]

        # Verify token columns exist
        assert "input_tokens" in columns
        assert "output_tokens" in columns
        assert "cache_creation_tokens" in columns
        assert "cache_read_tokens" in columns
        assert "actual_cost_usd" in columns

    def test_token_columns_are_nullable(self):
        """Test that token columns allow NULL values (backward compatibility)"""
        from backend.models.run import Run
        from backend.models.post import Post
        from backend.models.research_result import ResearchResult

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)

        # Check Run columns
        run_columns = {col["name"]: col for col in inspector.get_columns("runs")}
        assert run_columns["total_input_tokens"]["nullable"] is True
        assert run_columns["total_cost_usd"]["nullable"] is True

        # Check Post columns
        post_columns = {col["name"]: col for col in inspector.get_columns("posts")}
        assert post_columns["input_tokens"]["nullable"] is True
        assert post_columns["cost_usd"]["nullable"] is True

        # Check ResearchResult columns
        research_columns = {col["name"]: col for col in inspector.get_columns("research_results")}
        assert research_columns["input_tokens"]["nullable"] is True
        assert research_columns["actual_cost_usd"]["nullable"] is True

    def test_token_columns_have_correct_types(self):
        """Test that token columns have correct SQL types"""
        from backend.models.run import Run

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)

        # Check Run column types
        run_columns = {col["name"]: col for col in inspector.get_columns("runs")}

        # Integer columns
        assert "INTEGER" in str(run_columns["total_input_tokens"]["type"]).upper()
        assert "INTEGER" in str(run_columns["total_output_tokens"]["type"]).upper()

        # Float/Real columns
        assert any(
            t in str(run_columns["total_cost_usd"]["type"]).upper()
            for t in ["FLOAT", "REAL", "NUMERIC"]
        )

    def test_run_model_accepts_token_values(self):
        """Test that Run model accepts and stores token values correctly"""
        from backend.models.run import Run
        from backend.models.project import Project
        from backend.models.client import Client
        from backend.models.user import User

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create test data
        user = User(id="user-1", email="test@test.com", hashed_password="hash")
        client = Client(
            id="client-1",
            user_id=user.id,
            name="Test",
            email="client@test.com",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        project = Project(
            id="proj-1",
            user_id=user.id,
            client_id=client.id,
            name="Test",
            status="draft",
            platforms=["linkedin"],
        )
        session.add(user)
        session.add(client)
        session.add(project)

        # Create run with token data
        run = Run(
            id="run-1",
            project_id=project.id,
            is_batch=True,
            status="succeeded",
            total_input_tokens=5000,
            total_output_tokens=2500,
            total_cache_creation_tokens=500,
            total_cache_read_tokens=1000,
            total_cost_usd=0.125,
            estimated_cost_usd=0.120,
        )
        session.add(run)
        session.commit()

        # Verify data was stored
        saved_run = session.query(Run).filter(Run.id == "run-1").first()
        assert saved_run.total_input_tokens == 5000
        assert saved_run.total_output_tokens == 2500
        assert saved_run.total_cache_creation_tokens == 500
        assert saved_run.total_cache_read_tokens == 1000
        assert saved_run.total_cost_usd == pytest.approx(0.125)
        assert saved_run.estimated_cost_usd == pytest.approx(0.120)

        session.close()

    def test_post_model_accepts_token_values(self):
        """Test that Post model accepts and stores token values correctly"""
        from backend.models.post import Post
        from backend.models.run import Run
        from backend.models.project import Project
        from backend.models.client import Client
        from backend.models.user import User

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create test data
        user = User(id="user-1", email="test@test.com", hashed_password="hash")
        client = Client(
            id="client-1",
            user_id=user.id,
            name="Test",
            email="client@test.com",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        project = Project(
            id="proj-1",
            user_id=user.id,
            client_id=client.id,
            name="Test",
            status="draft",
            platforms=["linkedin"],
        )
        run = Run(id="run-1", project_id=project.id, is_batch=True, status="succeeded")
        session.add(user)
        session.add(client)
        session.add(project)
        session.add(run)

        # Create post with token data
        post = Post(
            id="post-1",
            project_id=project.id,
            run_id=run.id,
            content="Test post",
            status="approved",
            input_tokens=1500,
            output_tokens=800,
            cache_read_tokens=200,
            cost_usd=0.025,
        )
        session.add(post)
        session.commit()

        # Verify data was stored
        saved_post = session.query(Post).filter(Post.id == "post-1").first()
        assert saved_post.input_tokens == 1500
        assert saved_post.output_tokens == 800
        assert saved_post.cache_read_tokens == 200
        assert saved_post.cost_usd == pytest.approx(0.025)

        session.close()

    def test_research_result_model_accepts_token_values(self):
        """Test that ResearchResult model accepts and stores token values correctly"""
        from backend.models.research_result import ResearchResult
        from backend.models.project import Project
        from backend.models.client import Client
        from backend.models.user import User

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create test data
        user = User(id="user-1", email="test@test.com", hashed_password="hash")
        client = Client(
            id="client-1",
            user_id=user.id,
            name="Test",
            email="client@test.com",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        project = Project(
            id="proj-1",
            user_id=user.id,
            client_id=client.id,
            name="Test",
            status="draft",
            platforms=["linkedin"],
        )
        session.add(user)
        session.add(client)
        session.add(project)

        # Create research result with token data
        research = ResearchResult(
            id="res-1",
            user_id=user.id,
            client_id=client.id,
            project_id=project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keywords",
            tool_price=400.0,
            params={"topics": ["AI"]},
            outputs={"report": "/path/to/report.md"},
            status="completed",
            input_tokens=2500,
            output_tokens=1200,
            cache_creation_tokens=300,
            cache_read_tokens=150,
            actual_cost_usd=0.045,
        )
        session.add(research)
        session.commit()

        # Verify data was stored
        saved_research = session.query(ResearchResult).filter(ResearchResult.id == "res-1").first()
        assert saved_research.input_tokens == 2500
        assert saved_research.output_tokens == 1200
        assert saved_research.cache_creation_tokens == 300
        assert saved_research.cache_read_tokens == 150
        assert saved_research.actual_cost_usd == pytest.approx(0.045)
        assert saved_research.tool_price == 400.0  # Business model price still tracked

        session.close()

    def test_backward_compatibility_null_values(self):
        """Test that existing records without token data work correctly"""
        from backend.models.run import Run
        from backend.models.project import Project
        from backend.models.client import Client
        from backend.models.user import User

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create test data
        user = User(id="user-1", email="test@test.com", hashed_password="hash")
        client = Client(
            id="client-1",
            user_id=user.id,
            name="Test",
            email="client@test.com",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )
        project = Project(
            id="proj-1",
            user_id=user.id,
            client_id=client.id,
            name="Test",
            status="draft",
            platforms=["linkedin"],
        )
        session.add(user)
        session.add(client)
        session.add(project)

        # Create run WITHOUT token data (simulating old record)
        run = Run(
            id="run-legacy",
            project_id=project.id,
            is_batch=True,
            status="succeeded",
            # No token fields set
        )
        session.add(run)
        session.commit()

        # Verify record was created successfully
        saved_run = session.query(Run).filter(Run.id == "run-legacy").first()
        assert saved_run is not None
        assert saved_run.total_input_tokens is None
        assert saved_run.total_output_tokens is None
        assert saved_run.total_cost_usd is None

        session.close()

    def test_new_schema_has_all_columns(self):
        """Test that newly created schema includes all token tracking columns"""
        from backend.models.run import Run

        # Create fresh database with latest schema
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("runs")]

        # Verify all token columns exist in new schema
        assert "total_input_tokens" in columns
        assert "total_output_tokens" in columns
        assert "total_cache_creation_tokens" in columns
        assert "total_cache_read_tokens" in columns
        assert "total_cost_usd" in columns
        assert "estimated_cost_usd" in columns

        # Also verify original columns still exist (backward compatibility)
        assert "id" in columns
        assert "project_id" in columns
        assert "status" in columns
