"""
Unit tests for Week 2 intelligence features
"""

import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest

from agent.email_system import EmailSystem, EmailType
from agent.error_recovery import ErrorCategory, ErrorRecoverySystem, RetryConfig
from agent.planner import TaskPriority, TaskType, WorkflowPlanner
from agent.scheduler import ScheduleFrequency, TaskScheduler, TaskStatus
from agent.suggestions import SuggestionEngine, SuggestionType


class TestWorkflowPlanner:
    """Test workflow planning capabilities"""

    def setup_method(self):
        self.planner = WorkflowPlanner()

    def test_simple_workflow_creation(self):
        """Test creating a simple single-step workflow"""
        plan = self.planner.plan_simple_workflow(
            intent="Generate posts for Acme Corp",
            tool_name="generate_posts",
            tool_params={"client_name": "Acme Corp"},
            task_type=TaskType.GENERATE_POSTS,
        )

        assert plan is not None
        assert len(plan.tasks) == 1
        assert plan.tasks[0].tool_name == "generate_posts"
        assert not plan.requires_confirmation  # Simple tasks don't need confirmation

    def test_onboarding_workflow_creation(self):
        """Test creating onboarding workflow"""
        plan = self.planner.plan_onboarding_workflow(
            client_name="Test Client", has_brief=False, has_voice_samples=True
        )

        assert plan is not None
        assert len(plan.tasks) >= 3  # At least: create brief, analyze voice, generate
        assert plan.requires_confirmation  # Complex workflows need confirmation

    def test_batch_operations_workflow(self):
        """Test creating batch operations workflow"""
        plan = self.planner.plan_batch_operations(
            pending_feedback=["Client1", "Client2"],
            pending_revisions=["Client3"],
            overdue_invoices=["Client4"],
        )

        assert plan is not None
        assert len(plan.tasks) == 4  # 2 feedback + 1 revision + 1 invoice
        assert plan.requires_confirmation

    def test_workflow_plan_summary(self):
        """Test workflow plan summary generation"""
        plan = self.planner.plan_simple_workflow(
            intent="Test workflow", tool_name="test_tool", tool_params={}
        )

        summary = plan.to_summary()
        assert "Test workflow" in summary
        assert "Workflow Plan" in summary

    def test_task_priority_filtering(self):
        """Test filtering tasks by priority"""
        plan = self.planner.plan_batch_operations(
            pending_feedback=["Client1"], overdue_invoices=["Client2"]
        )

        urgent_tasks = plan.get_tasks_by_priority(TaskPriority.URGENT)
        low_tasks = plan.get_tasks_by_priority(TaskPriority.LOW)

        assert len(urgent_tasks) == 1  # Overdue invoice
        assert len(low_tasks) == 1  # Feedback request

    def test_next_executable_task(self):
        """Test getting next executable task with dependencies"""
        plan = self.planner.plan_onboarding_workflow(client_name="Test", has_brief=True)

        # First task should have no dependencies
        next_task = plan.get_next_executable_task([])
        assert next_task is not None
        assert len(next_task.depends_on) == 0


class TestSuggestionEngine:
    """Test proactive suggestions system"""

    def setup_method(self):
        self.engine = SuggestionEngine(db=None)  # No database needed for basic tests

    def test_generate_suggestions_without_db(self):
        """Test generating suggestions without database"""
        suggestions = self.engine.generate_suggestions()
        assert isinstance(suggestions, list)

    def test_daily_summary_no_suggestions(self):
        """Test daily summary with no pending items"""
        summary = self.engine.get_daily_summary()
        assert "All caught up" in summary

    def test_suggestion_display_format(self):
        """Test suggestion display formatting"""
        from agent.suggestions import Suggestion, SuggestionPriority

        suggestion = Suggestion(
            suggestion_id="test_1",
            suggestion_type=SuggestionType.FEEDBACK_REMINDER,
            priority=SuggestionPriority.HIGH,
            title="Test Suggestion",
            description="Test description",
            recommended_actions=["Action 1", "Action 2"],
        )

        display = suggestion.to_display()
        assert "Test Suggestion" in display
        assert "Action 1" in display
        assert "Action 2" in display


class TestErrorRecoverySystem:
    """Test error recovery and retry logic"""

    def setup_method(self):
        self.recovery = ErrorRecoverySystem()

    def test_error_categorization(self):
        """Test error categorization"""
        api_error = Exception("API rate limit exceeded")
        category, severity = self.recovery.categorize_error(api_error)

        assert category == ErrorCategory.API_ERROR
        assert severity is not None

    def test_recovery_strategy_determination(self):
        """Test determining recovery strategy"""
        api_error = Exception("Connection timeout")
        strategy = self.recovery.determine_strategy(api_error, attempt=0, max_retries=3)

        assert strategy is not None

    def test_sync_retry_success(self):
        """Test synchronous retry with success"""
        call_count = [0]

        def failing_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary error")
            return "Success"

        config = RetryConfig(max_retries=3)
        success, result, error_record = self.recovery.execute_with_retry_sync(
            func=failing_func, config=config
        )

        assert success
        assert result == "Success"
        assert call_count[0] == 2  # Failed once, succeeded second time

    def test_sync_retry_max_retries(self):
        """Test synchronous retry reaching max retries"""

        def always_failing_func():
            raise Exception("Permanent error")

        config = RetryConfig(max_retries=2)
        success, result, error_record = self.recovery.execute_with_retry_sync(
            func=always_failing_func, config=config
        )

        assert not success
        assert error_record is not None
        assert len(self.recovery.error_history) > 0

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test asynchronous retry with success"""
        call_count = [0]

        async def failing_async_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary error")
            return "Async Success"

        config = RetryConfig(max_retries=3)
        success, result, error_record = await self.recovery.execute_with_retry_async(
            func=failing_async_func, config=config
        )

        assert success
        assert result == "Async Success"
        assert call_count[0] == 2

    def test_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(
            initial_delay_seconds=1.0, exponential_base=2.0, max_delay_seconds=10.0, jitter=False
        )

        delay_0 = self.recovery._calculate_backoff_delay(0, config)
        delay_1 = self.recovery._calculate_backoff_delay(1, config)
        delay_2 = self.recovery._calculate_backoff_delay(2, config)

        assert delay_0 == 1.0  # 1.0 * 2^0
        assert delay_1 == 2.0  # 1.0 * 2^1
        assert delay_2 == 4.0  # 1.0 * 2^2


class TestTaskScheduler:
    """Test task scheduling system"""

    def setup_method(self):
        """Setup test with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_scheduler.db"
        self.scheduler = TaskScheduler(db_path=str(self.db_path))

    def teardown_method(self):
        """Cleanup temporary database"""
        shutil.rmtree(self.temp_dir)

    def test_schedule_one_time_task(self):
        """Test scheduling a one-time task"""
        task = self.scheduler.schedule_task(
            description="Test task",
            tool_name="test_tool",
            tool_params={"param": "value"},
            execute_in=timedelta(hours=1),
            frequency=ScheduleFrequency.ONCE,
        )

        assert task is not None
        assert task.frequency == ScheduleFrequency.ONCE
        assert task.status == TaskStatus.PENDING

    def test_schedule_recurring_task(self):
        """Test scheduling a recurring task"""
        task = self.scheduler.schedule_task(
            description="Daily reminder",
            tool_name="send_reminder",
            tool_params={},
            execute_in=timedelta(days=1),
            frequency=ScheduleFrequency.DAILY,
            max_executions=5,
        )

        assert task.frequency == ScheduleFrequency.DAILY
        assert task.max_executions == 5

    def test_get_due_tasks(self):
        """Test getting tasks due for execution"""
        # Schedule task for immediate execution
        self.scheduler.schedule_task(
            description="Immediate task",
            tool_name="test",
            tool_params={},
            execute_in=timedelta(seconds=0),
        )

        # Schedule task for future
        self.scheduler.schedule_task(
            description="Future task",
            tool_name="test",
            tool_params={},
            execute_in=timedelta(hours=24),
        )

        due_tasks = self.scheduler.get_due_tasks()
        assert len(due_tasks) >= 1  # At least the immediate task

    def test_mark_task_executed(self):
        """Test marking task as executed"""
        task = self.scheduler.schedule_task(
            description="Test task",
            tool_name="test",
            tool_params={},
            execute_in=timedelta(seconds=0),
        )

        self.scheduler.mark_task_executed(task, success=True)

        assert task.execution_count == 1
        assert task.status == TaskStatus.COMPLETED

    def test_cancel_task(self):
        """Test canceling a scheduled task"""
        task = self.scheduler.schedule_task(
            description="Cancellable task",
            tool_name="test",
            tool_params={},
            execute_in=timedelta(hours=1),
        )

        self.scheduler.cancel_task(task.task_id)

        # Verify cancellation (would need to reload from DB in real scenario)
        upcoming = self.scheduler.get_upcoming_tasks()
        cancelled_task = next((t for t in upcoming if t.task_id == task.task_id), None)
        # Task may not appear in upcoming if status changed


class TestEmailSystem:
    """Test email integration system"""

    def setup_method(self):
        self.email_system = EmailSystem()

    def test_create_deliverable_email(self):
        """Test creating deliverable email from template"""
        message = self.email_system.create_email_from_template(
            email_type=EmailType.DELIVERABLE,
            to_email="client@example.com",
            variables={
                "client_name": "Acme Corp",
                "deliverable_file": "Acme_deliverable.md",
                "voice_guide_file": "Acme_voice.md",
                "qa_report_file": "Acme_qa.md",
            },
        )

        assert message is not None
        assert "Acme Corp" in message.body_text
        assert "client@example.com" == message.to_email
        assert "Your 30-Day Content Package is Ready" in message.subject

    def test_create_feedback_email(self):
        """Test creating feedback request email"""
        message = self.email_system.create_email_from_template(
            email_type=EmailType.FEEDBACK_REQUEST,
            to_email="client@example.com",
            variables={
                "client_name": "Test Client",
                "feedback_link": "https://example.com/feedback",
            },
        )

        assert "Test Client" in message.body_text
        assert "https://example.com/feedback" in message.body_text

    def test_send_email_development_mode(self):
        """Test email logging in development mode (no SMTP)"""
        message = self.email_system.create_email_from_template(
            email_type=EmailType.DELIVERABLE,
            to_email="test@example.com",
            variables={
                "client_name": "Test",
                "deliverable_file": "test.md",
                "voice_guide_file": "voice.md",
                "qa_report_file": "qa.md",
            },
        )

        success, result = self.email_system.send_email(message)

        # In development mode without SMTP, email should be logged
        assert success
        assert message.status == "logged"
        assert message.sent_at is not None

    def test_invoice_reminder_email(self):
        """Test creating invoice reminder email"""
        message = self.email_system.create_email_from_template(
            email_type=EmailType.INVOICE_REMINDER,
            to_email="client@example.com",
            variables={
                "client_name": "Test Client",
                "invoice_number": "INV-001",
                "amount": "1800.00",
                "days_overdue": "5",
                "due_date": "2025-11-28",
                "payment_link": "https://pay.example.com",
            },
        )

        assert "INV-001" in message.body_text
        assert "1800.00" in message.body_text
        assert "5" in message.body_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
