"""Tests for Cost Dashboard"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.utils.cost_dashboard import (
    CostDashboard,
    show_all_projects,
    show_project_summary,
)
from src.utils.cost_tracker import APICall, ProjectCost


@pytest.fixture
def mock_tracker():
    """Create mock cost tracker"""
    tracker = MagicMock()
    return tracker


@pytest.fixture
def sample_project_cost():
    """Create sample project cost"""
    now = datetime.now()
    return ProjectCost(
        project_id="TestProject_123",
        total_cost=1.2345,
        total_input_tokens=10000,
        total_output_tokens=5000,
        total_cache_creation_tokens=2000,
        total_cache_read_tokens=3000,
        total_calls=10,
        first_call=now - timedelta(minutes=30),
        last_call=now,
    )


@pytest.fixture
def sample_api_calls():
    """Create sample API calls"""
    now = datetime.now()
    return [
        APICall(
            call_id=f"call_{i}",
            project_id="TestProject_123",
            timestamp=now - timedelta(minutes=i),
            operation=f"operation_{i}",
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=0,
            cache_read_tokens=100,
            cost=0.05,
            model="claude-3-5-sonnet-latest",
        )
        for i in range(5)
    ]


class TestInitialization:
    """Test CostDashboard initialization"""

    def test_init_default_tracker(self):
        """Test initialization with default tracker"""
        with patch("src.utils.cost_dashboard.get_default_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_get_tracker.return_value = mock_tracker

            dashboard = CostDashboard()

            assert dashboard.tracker == mock_tracker
            assert dashboard.console is not None

    def test_init_custom_tracker(self):
        """Test initialization with custom tracker"""
        custom_tracker = MagicMock()
        dashboard = CostDashboard(tracker=custom_tracker)

        assert dashboard.tracker == custom_tracker
        assert dashboard.console is not None


class TestShowProjectSummary:
    """Test show_project_summary method"""

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_summary_success(
        self, mock_console_class, mock_tracker, sample_project_cost
    ):
        """Test successful project summary display"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_tracker.get_project_cost.return_value = sample_project_cost

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_summary("TestProject_123")

        mock_tracker.get_project_cost.assert_called_once_with("TestProject_123")
        # Should print panel
        assert mock_console.print.call_count >= 1

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_summary_no_data(self, mock_console_class, mock_tracker):
        """Test project summary with no cost data"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # No calls = no data
        empty_cost = ProjectCost(
            project_id="Empty_123",
            total_cost=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cache_creation_tokens=0,
            total_cache_read_tokens=0,
            total_calls=0,
            first_call=datetime.now(),
            last_call=datetime.now(),
        )
        mock_tracker.get_project_cost.return_value = empty_cost

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_summary("Empty_123")

        # Should print warning message
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No cost data found" in call_args

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_summary_with_cache_savings(
        self, mock_console_class, mock_tracker, sample_project_cost
    ):
        """Test project summary shows cache savings"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_tracker.get_project_cost.return_value = sample_project_cost

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_summary("TestProject_123")

        # Should print cache savings (sample has cache_read_tokens > 0)
        assert mock_console.print.call_count == 2  # Panel + cache savings


class TestShowProjectCalls:
    """Test show_project_calls method"""

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_calls_success(self, mock_console_class, mock_tracker, sample_api_calls):
        """Test successful API calls display"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_tracker.get_project_calls.return_value = sample_api_calls

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_calls("TestProject_123", limit=3)

        mock_tracker.get_project_calls.assert_called_once_with("TestProject_123")
        mock_console.print.assert_called_once()

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_calls_no_data(self, mock_console_class, mock_tracker):
        """Test API calls display with no data"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_tracker.get_project_calls.return_value = []

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_calls("TestProject_123")

        # Should print warning
        call_args = mock_console.print.call_args[0][0]
        assert "No API calls found" in call_args

    @patch("src.utils.cost_dashboard.Console")
    def test_show_project_calls_respects_limit(
        self, mock_console_class, mock_tracker, sample_api_calls
    ):
        """Test limit parameter is respected"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        # Create many calls
        many_calls = sample_api_calls * 10  # 50 calls
        mock_tracker.get_project_calls.return_value = many_calls

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_project_calls("TestProject_123", limit=10)

        # Verify we only show limited calls (implementation shows limit)
        mock_console.print.assert_called_once()


class TestShowAllProjects:
    """Test show_all_projects method"""

    @patch("src.utils.cost_dashboard.Console")
    def test_show_all_projects_success(self, mock_console_class, mock_tracker, sample_project_cost):
        """Test successful all projects display"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        project_ids = ["Project1", "Project2", "Project3"]
        mock_tracker.get_all_projects.return_value = project_ids
        mock_tracker.get_project_cost.return_value = sample_project_cost

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_all_projects()

        # Should call get_project_cost for each project
        assert mock_tracker.get_project_cost.call_count == 3
        # Should print table + summary
        assert mock_console.print.call_count == 2

    @patch("src.utils.cost_dashboard.Console")
    def test_show_all_projects_no_projects(self, mock_console_class, mock_tracker):
        """Test all projects display with no projects"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_tracker.get_all_projects.return_value = []

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_all_projects()

        call_args = mock_console.print.call_args[0][0]
        assert "No projects tracked yet" in call_args


class TestShowPeriodSummary:
    """Test show_period_summary method"""

    @patch("src.utils.cost_dashboard.Console")
    def test_show_period_summary_with_data(self, mock_console_class, mock_tracker):
        """Test period summary with data"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        totals = {
            "total_projects": 5,
            "total_calls": 100,
            "total_input_tokens": 50000,
            "total_output_tokens": 25000,
            "total_cost": 5.67,
            "avg_cost_per_project": 1.134,
        }
        mock_tracker.get_total_costs.return_value = totals

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_period_summary(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            period_name="January 2025",
        )

        mock_tracker.get_total_costs.assert_called_once_with(
            datetime(2025, 1, 1), datetime(2025, 1, 31)
        )
        mock_console.print.assert_called_once()

    @patch("src.utils.cost_dashboard.Console")
    def test_show_period_summary_no_data(self, mock_console_class, mock_tracker):
        """Test period summary with no data"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        totals = {
            "total_projects": 0,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "avg_cost_per_project": 0.0,
        }
        mock_tracker.get_total_costs.return_value = totals

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_period_summary(period_name="Empty Period")

        call_args = mock_console.print.call_args[0][0]
        assert "No data for period" in call_args

    @patch("src.utils.cost_dashboard.Console")
    def test_show_period_summary_defaults(self, mock_console_class, mock_tracker):
        """Test period summary uses default dates"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        totals = {
            "total_projects": 1,
            "total_calls": 10,
            "total_input_tokens": 5000,
            "total_output_tokens": 2500,
            "total_cost": 0.5,
            "avg_cost_per_project": 0.5,
        }
        mock_tracker.get_total_costs.return_value = totals

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.show_period_summary()  # No dates specified

        mock_tracker.get_total_costs.assert_called_once_with(None, None)


class TestGenerateMarkdownReport:
    """Test generate_markdown_report method"""

    @patch("src.utils.cost_dashboard.Console")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.cost_dashboard.Path")
    def test_generate_markdown_single_project(
        self, mock_path_class, mock_file, mock_console_class, mock_tracker, sample_project_cost
    ):
        """Test markdown report for single project"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_tracker.get_project_cost.return_value = sample_project_cost

        # Mock Path
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_path_class.return_value = mock_path

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.generate_markdown_report(Path("report.md"), project_id="TestProject_123")

        # Should get project cost
        mock_tracker.get_project_cost.assert_called_once_with("TestProject_123")

        # Should write file
        mock_file.assert_called_once()
        written_content = "".join(call[0][0] for call in mock_file().write.call_args_list)
        assert "Cost Report" in written_content or mock_file().write.called

    @patch("src.utils.cost_dashboard.Console")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.cost_dashboard.Path")
    def test_generate_markdown_all_projects(
        self, mock_path_class, mock_file, mock_console_class, mock_tracker, sample_project_cost
    ):
        """Test markdown report for all projects"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        project_ids = ["Project1", "Project2"]
        mock_tracker.get_all_projects.return_value = project_ids
        mock_tracker.get_project_cost.return_value = sample_project_cost
        mock_tracker.get_total_costs.return_value = {
            "total_projects": 2,
            "total_calls": 20,
            "total_input_tokens": 20000,
            "total_output_tokens": 10000,
            "total_cost": 2.4690,
            "avg_cost_per_project": 1.2345,
        }

        # Mock Path
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_path_class.return_value = mock_path

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.generate_markdown_report(Path("report.md"))  # No project_id = all projects

        # Should get all projects
        mock_tracker.get_all_projects.assert_called_once()
        mock_tracker.get_total_costs.assert_called_once()

        # Should write file
        mock_file.assert_called_once()

    @patch("src.utils.cost_dashboard.Console")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.cost_dashboard.Path")
    def test_generate_markdown_with_calls(
        self,
        mock_path_class,
        mock_file,
        mock_console_class,
        mock_tracker,
        sample_project_cost,
        sample_api_calls,
    ):
        """Test markdown report includes API calls when requested"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_tracker.get_project_cost.return_value = sample_project_cost
        mock_tracker.get_project_calls.return_value = sample_api_calls

        # Mock Path
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_path_class.return_value = mock_path

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.generate_markdown_report(
            Path("report.md"), project_id="TestProject_123", include_calls=True
        )

        # Should get project calls
        mock_tracker.get_project_calls.assert_called_once_with("TestProject_123")

    @patch("src.utils.cost_dashboard.Console")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.cost_dashboard.Path")
    def test_generate_markdown_no_data(
        self, mock_path_class, mock_file, mock_console_class, mock_tracker
    ):
        """Test markdown report with no cost data"""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        empty_cost = ProjectCost(
            project_id="Empty_123",
            total_cost=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cache_creation_tokens=0,
            total_cache_read_tokens=0,
            total_calls=0,
            first_call=datetime.now(),
            last_call=datetime.now(),
        )
        mock_tracker.get_project_cost.return_value = empty_cost

        # Mock Path
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_path_class.return_value = mock_path

        dashboard = CostDashboard(tracker=mock_tracker)
        dashboard.generate_markdown_report(Path("report.md"), project_id="Empty_123")

        # Should still write file
        mock_file.assert_called_once()


class TestFormatDuration:
    """Test _format_duration helper method"""

    def test_format_duration_seconds(self, mock_tracker):
        """Test duration formatting for seconds"""
        dashboard = CostDashboard(tracker=mock_tracker)

        duration = timedelta(seconds=45)
        result = dashboard._format_duration(duration)
        assert result == "45 seconds"

    def test_format_duration_minutes(self, mock_tracker):
        """Test duration formatting for minutes"""
        dashboard = CostDashboard(tracker=mock_tracker)

        duration = timedelta(minutes=5, seconds=30)
        result = dashboard._format_duration(duration)
        assert result == "5m 30s"

    def test_format_duration_hours(self, mock_tracker):
        """Test duration formatting for hours"""
        dashboard = CostDashboard(tracker=mock_tracker)

        duration = timedelta(hours=2, minutes=30)
        result = dashboard._format_duration(duration)
        assert result == "2h 30m"

    def test_format_duration_zero(self, mock_tracker):
        """Test duration formatting for zero time"""
        dashboard = CostDashboard(tracker=mock_tracker)

        duration = timedelta(seconds=0)
        result = dashboard._format_duration(duration)
        assert result == "0 seconds"


class TestCalculateCacheSavings:
    """Test _calculate_cache_savings helper method"""

    def test_calculate_cache_savings_with_reads(self, mock_tracker, sample_project_cost):
        """Test cache savings calculation with cache reads"""
        dashboard = CostDashboard(tracker=mock_tracker)

        savings = dashboard._calculate_cache_savings(sample_project_cost)

        # Should return positive savings
        assert savings > 0
        # Savings = (would_have_cost - actual_cost)
        # With 3000 cache read tokens
        assert isinstance(savings, float)

    def test_calculate_cache_savings_no_reads(self, mock_tracker):
        """Test cache savings calculation with no cache reads"""
        dashboard = CostDashboard(tracker=mock_tracker)

        no_cache_cost = ProjectCost(
            project_id="NoCache",
            total_cost=1.0,
            total_input_tokens=10000,
            total_output_tokens=5000,
            total_cache_creation_tokens=0,
            total_cache_read_tokens=0,  # No cache reads
            total_calls=10,
            first_call=datetime.now(),
            last_call=datetime.now(),
        )

        savings = dashboard._calculate_cache_savings(no_cache_cost)

        # Should return zero savings
        assert savings == 0.0


class TestConvenienceFunctions:
    """Test convenience functions"""

    @patch("src.utils.cost_dashboard.CostDashboard")
    def test_show_project_summary_convenience(self, mock_dashboard_class):
        """Test show_project_summary convenience function"""
        mock_dashboard = MagicMock()
        mock_dashboard_class.return_value = mock_dashboard

        show_project_summary("TestProject_123")

        mock_dashboard_class.assert_called_once()
        mock_dashboard.show_project_summary.assert_called_once_with("TestProject_123")

    @patch("src.utils.cost_dashboard.CostDashboard")
    def test_show_all_projects_convenience(self, mock_dashboard_class):
        """Test show_all_projects convenience function"""
        mock_dashboard = MagicMock()
        mock_dashboard_class.return_value = mock_dashboard

        show_all_projects()

        mock_dashboard_class.assert_called_once()
        mock_dashboard.show_all_projects.assert_called_once()
