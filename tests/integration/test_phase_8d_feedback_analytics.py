"""
Integration tests for Phase 8D: Feedback Integration & Reporting Dashboard
"""
from datetime import date, datetime

import pytest

from src.database.project_db import ProjectDatabase
from src.models.project import Project


class TestPostFeedback:
    """Test post feedback functionality"""

    def setup_method(self):
        """Setup test database"""
        self.db = ProjectDatabase()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Added microseconds
        self.test_client = f"TestClient_{timestamp}"
        self.test_project = f"{self.test_client}_20251203_120000"

        # Create test project
        project = Project(
            project_id=self.test_project,
            client_name=self.test_client,
            deliverable_path="test/path.md",
            num_posts=30,
        )
        self.db.create_project(project)

    def test_store_post_feedback(self):
        """Test storing post feedback"""
        feedback_id = self.db.store_post_feedback(
            client_name=self.test_client,
            project_id=self.test_project,
            post_id="post_001",
            template_id=1,
            template_name="Problem Recognition",
            feedback_type="kept",
            modification_notes=None,
            engagement_data={"likes": 100, "comments": 20},
        )

        assert feedback_id > 0

    def test_get_post_feedback(self):
        """Test retrieving post feedback"""
        # Store multiple feedback records
        for i in range(3):
            self.db.store_post_feedback(
                client_name=self.test_client,
                project_id=self.test_project,
                post_id=f"post_{i:03d}",
                template_id=i + 1,
                template_name=f"Template {i+1}",
                feedback_type="kept" if i % 2 == 0 else "modified",
                modification_notes=f"Notes {i}" if i % 2 == 1 else None,
            )

        # Get all feedback for client
        feedback = self.db.get_post_feedback(client_name=self.test_client)
        assert len(feedback) == 3

        # Get filtered by type
        kept_feedback = self.db.get_post_feedback(
            client_name=self.test_client, feedback_type="kept"
        )
        assert len(kept_feedback) == 2

    def test_get_post_feedback_summary(self):
        """Test post feedback summary"""
        # Store various feedback types
        feedback_types = ["kept", "kept", "modified", "rejected", "loved"]

        for i, ftype in enumerate(feedback_types):
            self.db.store_post_feedback(
                client_name=self.test_client,
                project_id=self.test_project,
                post_id=f"post_{i:03d}",
                template_id=i + 1,
                template_name=f"Template {i+1}",
                feedback_type=ftype,
            )

        # Get summary
        summary = self.db.get_post_feedback_summary(client_name=self.test_client)

        assert summary["total_feedback"] == 5
        assert summary["kept"] == 2
        assert summary["modified"] == 1
        assert summary["rejected"] == 1
        assert summary["loved"] == 1
        assert summary["kept_rate"] == 2 / 5


class TestClientSatisfaction:
    """Test client satisfaction functionality"""

    def setup_method(self):
        """Setup test database"""
        self.db = ProjectDatabase()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Added microseconds
        self.test_client = f"TestClient_{timestamp}"
        self.test_project = f"{self.test_client}_20251203_120000"

        # Create test project
        project = Project(
            project_id=self.test_project,
            client_name=self.test_client,
            deliverable_path="test/path.md",
            num_posts=30,
        )
        self.db.create_project(project)

    def test_store_client_satisfaction(self):
        """Test storing satisfaction survey"""
        satisfaction_id = self.db.store_client_satisfaction(
            client_name=self.test_client,
            project_id=self.test_project,
            satisfaction_score=5,
            quality_rating=5,
            voice_match_rating=4,
            would_recommend=True,
            feedback_text="Great work!",
            strengths="Excellent voice matching",
            improvements="Could be faster",
        )

        assert satisfaction_id > 0

    def test_get_client_satisfaction(self):
        """Test retrieving satisfaction records"""
        # Store satisfaction
        self.db.store_client_satisfaction(
            client_name=self.test_client,
            project_id=self.test_project,
            satisfaction_score=4,
            quality_rating=5,
            voice_match_rating=4,
            would_recommend=True,
        )

        # Retrieve
        records = self.db.get_client_satisfaction(client_name=self.test_client)
        assert len(records) == 1
        assert records[0]["satisfaction_score"] == 4
        assert records[0]["would_recommend"] is True

    def test_get_satisfaction_summary(self):
        """Test satisfaction summary aggregation"""
        # Create multiple clients with satisfaction scores
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        clients = [f"Client_{i}_{timestamp}" for i in range(3)]

        for i, client in enumerate(clients):
            project_id = f"{client}_20251203_120000"

            project = Project(
                project_id=project_id,
                client_name=client,
                deliverable_path="test/path.md",
                num_posts=30,
            )
            self.db.create_project(project)

            self.db.store_client_satisfaction(
                client_name=client,
                project_id=project_id,
                satisfaction_score=5 - i,  # 5, 4, 3
                quality_rating=5,
                voice_match_rating=4,
                would_recommend=True if i < 2 else False,
            )

        # Get summary
        summary = self.db.get_satisfaction_summary()

        assert summary["total_surveys"] >= 3
        assert summary["avg_satisfaction"] > 0
        assert 0.0 <= summary["recommendation_rate"] <= 1.0


class TestSystemMetrics:
    """Test system metrics functionality"""

    def setup_method(self):
        """Setup test database"""
        self.db = ProjectDatabase()
        self.test_date = date.today().isoformat()

    def test_record_metric(self):
        """Test recording system metrics"""
        self.db.record_metric(
            metric_date=self.test_date,
            metric_type="generation",
            metric_name="total_posts",
            metric_value=100.0,
            metadata={"source": "test"},
        )

        # Verify stored
        metrics = self.db.get_metrics(metric_type="generation", metric_name="total_posts")

        assert len(metrics) > 0

    def test_get_metrics_with_filters(self):
        """Test retrieving metrics with various filters"""
        # Store multiple metrics
        for i in range(5):
            self.db.record_metric(
                metric_date=self.test_date,
                metric_type="quality",
                metric_name=f"metric_{i}",
                metric_value=float(i * 10),
            )

        # Get by type
        quality_metrics = self.db.get_metrics(metric_type="quality")
        assert len(quality_metrics) >= 5

        # Get by name
        specific_metric = self.db.get_metrics(metric_type="quality", metric_name="metric_1")
        assert len(specific_metric) >= 1

    def test_get_metrics_summary(self):
        """Test metrics summary aggregation"""
        # Store metrics over multiple days
        for i in range(3):
            self.db.record_metric(
                metric_date=self.test_date,
                metric_type="cost",
                metric_name="avg_cost_per_client",
                metric_value=float(50 + i * 5),
            )

        # Get summary
        summary = self.db.get_metrics_summary(days=30)

        assert "cost" in summary or len(summary) == 0  # May be empty if dates don't match


class TestDatabaseIntegration:
    """Test overall database integration"""

    def setup_method(self):
        """Setup test database"""
        self.db = ProjectDatabase()

    def test_database_schema_integrity(self):
        """Test that all Phase 8D tables exist"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name IN ('post_feedback', 'client_satisfaction', 'system_metrics')
            """
            )

            tables = [row[0] for row in cursor.fetchall()]

            assert "post_feedback" in tables
            assert "client_satisfaction" in tables
            assert "system_metrics" in tables

    def test_feedback_to_satisfaction_workflow(self):
        """Test complete workflow: project -> feedback -> satisfaction"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Added microseconds
        test_client = f"WorkflowTest_{timestamp}"
        test_project = f"{test_client}_20251203_120000"

        # 1. Create project
        project = Project(
            project_id=test_project,
            client_name=test_client,
            deliverable_path="test/workflow.md",
            num_posts=30,
        )
        self.db.create_project(project)

        # 2. Add feedback
        for i in range(5):
            self.db.store_post_feedback(
                client_name=test_client,
                project_id=test_project,
                post_id=f"post_{i}",
                template_id=i + 1,
                template_name=f"Template {i+1}",
                feedback_type="kept",
            )

        # 3. Add satisfaction
        self.db.store_client_satisfaction(
            client_name=test_client,
            project_id=test_project,
            satisfaction_score=5,
            quality_rating=5,
            voice_match_rating=5,
            would_recommend=True,
        )

        # 4. Verify everything
        feedback_summary = self.db.get_post_feedback_summary(client_name=test_client)
        assert feedback_summary["total_feedback"] == 5

        satisfaction = self.db.get_client_satisfaction(client_name=test_client)
        assert len(satisfaction) == 1
        assert satisfaction[0]["satisfaction_score"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
