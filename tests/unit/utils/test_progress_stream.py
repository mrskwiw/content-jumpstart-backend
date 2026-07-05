"""Tests for Progress Stream"""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.progress_stream import (
    AsyncProgressStream,
    ProgressStream,
    SimpleProgress,
    batch_progress,
    simple_spinner,
)


class TestProgressStreamInit:
    """Test ProgressStream initialization"""

    def test_init_with_total(self):
        """Test initialization with total"""
        progress = ProgressStream("Test Task", total=10)

        assert progress.title == "Test Task"
        assert progress.total == 10
        assert progress.show_cost is True
        assert progress.show_tokens is True
        assert progress.current == 0
        assert progress.total_cost == 0.0
        assert progress.total_input_tokens == 0
        assert progress.total_output_tokens == 0

    def test_init_without_total(self):
        """Test initialization without total (indeterminate)"""
        progress = ProgressStream("Test Task")

        assert progress.title == "Test Task"
        assert progress.total is None

    def test_init_custom_flags(self):
        """Test initialization with custom show flags"""
        progress = ProgressStream("Test Task", show_cost=False, show_tokens=False)

        assert progress.show_cost is False
        assert progress.show_tokens is False


class TestProgressStreamContextManager:
    """Test ProgressStream context manager"""

    @patch("src.utils.progress_stream.Live")
    @patch("src.utils.progress_stream.time.time")
    def test_enter_starts_display(self, mock_time, mock_live_class):
        """Test __enter__ starts the live display"""
        mock_time.return_value = 100.0
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)

        with progress:
            # Should have started
            assert progress.start_time == 100.0
            assert progress.task_id is not None
            mock_live.start.assert_called_once()

    @patch("src.utils.progress_stream.Live")
    @patch("src.utils.progress_stream.time.time")
    def test_exit_stops_display(self, mock_time, mock_live_class):
        """Test __exit__ stops the live display"""
        mock_time.side_effect = [100.0, 110.0]  # Start and end times
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)

        with progress:
            pass

        # Should have stopped
        mock_live.stop.assert_called_once()

    @patch("src.utils.progress_stream.Live")
    @patch("src.utils.progress_stream.Console")
    @patch("src.utils.progress_stream.time.time")
    def test_exit_shows_completion(self, mock_time, mock_console_class, mock_live_class):
        """Test __exit__ shows completion message"""
        mock_time.side_effect = [100.0, 110.0]  # 10 seconds elapsed
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)

        with progress:
            pass

        # Should print completion
        mock_console.print.assert_called_once()
        call_args = str(mock_console.print.call_args)
        assert "10.0s" in call_args  # Shows elapsed time

    @patch("src.utils.progress_stream.Live")
    @patch("src.utils.progress_stream.time.time")
    def test_exit_on_exception_doesnt_suppress(self, mock_time, mock_live_class):
        """Test __exit__ doesn't suppress exceptions"""
        mock_time.return_value = 100.0
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)

        with pytest.raises(ValueError):
            with progress:
                raise ValueError("Test error")

        # Should have stopped but not suppressed exception
        mock_live.stop.assert_called_once()


class TestProgressStreamUpdate:
    """Test ProgressStream update method"""

    @patch("src.utils.progress_stream.Live")
    def test_update_current(self, mock_live_class):
        """Test updating current progress"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.update(5)

            assert progress.current == 5

    @patch("src.utils.progress_stream.Live")
    def test_update_total(self, mock_live_class):
        """Test updating total dynamically"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.update(5, total=20)

            assert progress.total == 20

    @patch("src.utils.progress_stream.Live")
    def test_update_status(self, mock_live_class):
        """Test updating status message"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.update(5, status="Processing item 5")

            assert progress.status_message == "Processing item 5"

    @patch("src.utils.progress_stream.Live")
    def test_update_refreshes_display(self, mock_live_class):
        """Test update refreshes the live display"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            initial_update_count = mock_live.update.call_count
            progress.update(5)

            # Should have refreshed
            assert mock_live.update.call_count > initial_update_count


class TestProgressStreamAddCost:
    """Test ProgressStream add_cost method"""

    @patch("src.utils.progress_stream.Live")
    def test_add_cost_only(self, mock_live_class):
        """Test adding cost only"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.add_cost(0.15)

            assert progress.total_cost == 0.15
            assert progress.total_input_tokens == 0
            assert progress.total_output_tokens == 0

    @patch("src.utils.progress_stream.Live")
    def test_add_cost_with_tokens(self, mock_live_class):
        """Test adding cost with token counts"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.add_cost(0.15, input_tokens=1000, output_tokens=500)

            assert progress.total_cost == 0.15
            assert progress.total_input_tokens == 1000
            assert progress.total_output_tokens == 500

    @patch("src.utils.progress_stream.Live")
    def test_add_cost_accumulates(self, mock_live_class):
        """Test multiple add_cost calls accumulate"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.add_cost(0.10, input_tokens=500, output_tokens=250)
            progress.add_cost(0.05, input_tokens=300, output_tokens=150)

            # Use approximate comparison for floating point
            assert abs(progress.total_cost - 0.15) < 0.0001
            assert progress.total_input_tokens == 800
            assert progress.total_output_tokens == 400


class TestProgressStreamSetStatus:
    """Test ProgressStream set_status method"""

    @patch("src.utils.progress_stream.Live")
    def test_set_status(self, mock_live_class):
        """Test setting status message"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.set_status("New status")

            assert progress.status_message == "New status"


class TestProgressStreamRender:
    """Test ProgressStream rendering methods"""

    @patch("src.utils.progress_stream.Live")
    def test_render_with_cost_and_tokens(self, mock_live_class):
        """Test rendering with cost and tokens enabled"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10, show_cost=True, show_tokens=True)
        with progress:
            progress.add_cost(0.25, input_tokens=1000, output_tokens=500)
            renderable = progress._render()

            # Should return Columns with progress + stats
            assert renderable is not None

    @patch("src.utils.progress_stream.Live")
    def test_render_without_stats(self, mock_live_class):
        """Test rendering without cost/tokens"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10, show_cost=False, show_tokens=False)
        with progress:
            renderable = progress._render()

            # Should return just progress bar
            assert renderable == progress.progress

    @patch("src.utils.progress_stream.Live")
    def test_create_stats_table(self, mock_live_class):
        """Test stats table creation"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = ProgressStream("Test Task", total=10)
        with progress:
            progress.add_cost(0.50, input_tokens=2000, output_tokens=1000)
            progress.update(5)

            table = progress._create_stats_table()

            assert table is not None


class TestSimpleProgress:
    """Test SimpleProgress class"""

    @patch("src.utils.progress_stream.Console")
    @patch("src.utils.progress_stream.time.time")
    def test_simple_progress_enter(self, mock_time, mock_console_class):
        """Test SimpleProgress __enter__"""
        mock_time.return_value = 100.0
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        progress = SimpleProgress("Loading")

        with progress:
            assert progress.start_time == 100.0
            # Should print starting message
            mock_console.print.assert_called_once()

    @patch("src.utils.progress_stream.Console")
    @patch("src.utils.progress_stream.time.time")
    def test_simple_progress_exit_success(self, mock_time, mock_console_class):
        """Test SimpleProgress __exit__ on success"""
        mock_time.side_effect = [100.0, 105.0]  # 5 seconds elapsed
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        progress = SimpleProgress("Loading")

        with progress:
            pass

        # Should print completion (2 calls: start + end)
        assert mock_console.print.call_count == 2

    @patch("src.utils.progress_stream.Console")
    @patch("src.utils.progress_stream.time.time")
    def test_simple_progress_exit_error(self, mock_time, mock_console_class):
        """Test SimpleProgress __exit__ on error"""
        mock_time.return_value = 100.0
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        progress = SimpleProgress("Loading")

        with pytest.raises(ValueError):
            with progress:
                raise ValueError("Test error")

        # Should print error marker
        assert mock_console.print.call_count == 2

    @patch("src.utils.progress_stream.Console")
    @patch("src.utils.progress_stream.time.time")
    def test_simple_progress_update(self, mock_time, mock_console_class):
        """Test SimpleProgress update method"""
        # Need enough values for enter, update, and exit
        mock_time.side_effect = [100.0, 102.0, 105.0]
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        progress = SimpleProgress("Loading")

        with progress:
            progress.update("Step 1 complete")

        # Should print update message (start + update + end)
        assert mock_console.print.call_count >= 2

    @patch("src.utils.progress_stream.Console")
    def test_simple_progress_custom_console(self, mock_console_class):
        """Test SimpleProgress with custom console"""
        custom_console = MagicMock()

        progress = SimpleProgress("Loading", console=custom_console)

        assert progress.console == custom_console


class TestAsyncProgressStream:
    """Test AsyncProgressStream class"""

    @patch("src.utils.progress_stream.Live")
    @pytest.mark.asyncio
    async def test_aupdate(self, mock_live_class):
        """Test async update method"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = AsyncProgressStream("Test Task", total=10)
        with progress:
            await progress.aupdate(5, status="Async update")

            assert progress.current == 5
            assert progress.status_message == "Async update"

    @patch("src.utils.progress_stream.Live")
    @pytest.mark.asyncio
    async def test_aadd_cost(self, mock_live_class):
        """Test async add_cost method"""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        progress = AsyncProgressStream("Test Task", total=10)
        with progress:
            await progress.aadd_cost(0.20, input_tokens=800, output_tokens=400)

            assert progress.total_cost == 0.20
            assert progress.total_input_tokens == 800
            assert progress.total_output_tokens == 400


class TestBatchProgress:
    """Test batch_progress context manager"""

    @patch("src.utils.progress_stream.ProgressStream")
    def test_batch_progress(self, mock_progress_class):
        """Test batch_progress context manager"""
        mock_progress = MagicMock()
        mock_progress_class.return_value.__enter__.return_value = mock_progress

        with batch_progress("Batch Task", 30) as progress:
            assert progress == mock_progress

        # Should create ProgressStream with correct params
        mock_progress_class.assert_called_once_with("Batch Task", 30, True, True)

    @patch("src.utils.progress_stream.ProgressStream")
    def test_batch_progress_custom_flags(self, mock_progress_class):
        """Test batch_progress with custom flags"""
        mock_progress = MagicMock()
        mock_progress_class.return_value.__enter__.return_value = mock_progress

        with batch_progress("Batch Task", 30, show_cost=False, show_tokens=False):
            pass

        # Should pass flags through
        mock_progress_class.assert_called_once_with("Batch Task", 30, False, False)


class TestSimpleSpinner:
    """Test simple_spinner context manager"""

    @patch("src.utils.progress_stream.SimpleProgress")
    def test_simple_spinner(self, mock_simple_progress_class):
        """Test simple_spinner context manager"""
        mock_progress = MagicMock()
        mock_simple_progress_class.return_value.__enter__.return_value = mock_progress

        with simple_spinner("Loading") as progress:
            assert progress == mock_progress

        # Should create SimpleProgress
        mock_simple_progress_class.assert_called_once_with("Loading")
