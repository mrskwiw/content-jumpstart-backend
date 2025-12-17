"""
Integration tests for Week 3 polish and testing features
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from agent.context import ContextManager, ConversationContext


class TestConversationHistoryPersistence:
    """Test conversation history persistence features"""

    def setup_method(self):
        """Setup test with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_sessions.db"
        self.manager = ContextManager(db_path=str(self.db_path))

    def teardown_method(self):
        """Cleanup temporary database"""
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_message(self):
        """Test saving and loading a single message"""
        session_id = "test_session_1"

        # Save a message
        self.manager.save_message(
            session_id=session_id, role="user", content="Hello, agent!", metadata={"test": True}
        )

        # Load conversation
        messages = self.manager.load_conversation(session_id)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, agent!"

    def test_save_multiple_messages(self):
        """Test saving multiple messages in conversation"""
        session_id = "test_session_2"

        # Save multiple messages
        self.manager.save_message(session_id, "user", "Question 1")
        self.manager.save_message(session_id, "assistant", "Answer 1")
        self.manager.save_message(session_id, "user", "Question 2")
        self.manager.save_message(session_id, "assistant", "Answer 2")

        # Load conversation
        messages = self.manager.load_conversation(session_id)

        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"

    def test_load_conversation_with_limit(self):
        """Test loading conversation with message limit"""
        session_id = "test_session_3"

        # Save 10 messages
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            self.manager.save_message(session_id, role, f"Message {i}")

        # Load with limit
        messages = self.manager.load_conversation(session_id, limit=3)

        assert len(messages) == 3

    def test_export_conversation_markdown(self):
        """Test exporting conversation to markdown"""
        session_id = "test_session_4"

        # Create context
        context = ConversationContext(session_id=session_id)
        context.current_client = "Test Client"
        context.current_project = "Test Project"
        self.manager.save_context(context)

        # Save messages
        self.manager.save_message(session_id, "user", "Hello")
        self.manager.save_message(session_id, "assistant", "Hi there!")

        # Export to markdown
        output_path = Path(self.temp_dir) / "conversation.md"
        markdown = self.manager.export_conversation_markdown(session_id, output_path=output_path)

        # Verify markdown content
        assert "# Conversation Export" in markdown
        assert "Test Client" in markdown
        assert "Test Project" in markdown
        assert "Hello" in markdown
        assert "Hi there!" in markdown

        # Verify file was created
        assert output_path.exists()

    def test_search_conversation(self):
        """Test searching conversation messages"""
        session_id = "test_session_5"

        # Save messages with searchable content
        self.manager.save_message(session_id, "user", "Generate posts for Acme Corp")
        self.manager.save_message(session_id, "assistant", "I'll generate posts now")
        self.manager.save_message(session_id, "user", "Send invoice to client")
        self.manager.save_message(session_id, "assistant", "Invoice sent successfully")

        # Search for "posts"
        results = self.manager.search_conversation(session_id, "posts")
        assert len(results) == 2  # Found in both user and assistant messages

        # Search for "invoice"
        results = self.manager.search_conversation(session_id, "invoice")
        assert len(results) == 2

        # Search with role filter
        results = self.manager.search_conversation(session_id, "posts", role="user")
        assert len(results) == 1
        assert results[0]["role"] == "user"

    def test_get_conversation_summary(self):
        """Test getting conversation summary statistics"""
        session_id = "test_session_6"

        # Save messages
        self.manager.save_message(session_id, "user", "Message 1")
        self.manager.save_message(session_id, "assistant", "Response 1")
        self.manager.save_message(session_id, "user", "Message 2")

        # Get summary
        summary = self.manager.get_conversation_summary(session_id)

        assert summary["session_id"] == session_id
        assert summary["total_messages"] == 3
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 1
        assert summary["first_message"] is not None
        assert summary["last_message"] is not None

    def test_empty_conversation_summary(self):
        """Test summary for conversation with no messages"""
        session_id = "test_session_empty"

        summary = self.manager.get_conversation_summary(session_id)

        assert summary["total_messages"] == 0


class TestToolWrappers:
    """Test new tool wrapper methods"""

    def setup_method(self):
        """Setup test environment"""
        from agent.tools import AgentTools

        self.tools = AgentTools()

    def test_get_available_tools_includes_new_tools(self):
        """Test that new tools are included in available tools list"""
        tools = self.tools.get_available_tools()
        tool_names = [t["name"] for t in tools]

        # Check that new Week 3 tools are present
        assert "process_revision" in tool_names
        assert "generate_analytics_report" in tool_names
        assert "create_posting_schedule" in tool_names

    def test_process_revision_tool_structure(self):
        """Test process_revision tool has correct structure"""
        tools = self.tools.get_available_tools()
        revision_tool = next((t for t in tools if t["name"] == "process_revision"), None)

        assert revision_tool is not None
        assert "description" in revision_tool
        assert "parameters" in revision_tool
        assert "client_name" in revision_tool["parameters"]
        assert "project_id" in revision_tool["parameters"]

    def test_generate_analytics_report_tool_structure(self):
        """Test generate_analytics_report tool has correct structure"""
        tools = self.tools.get_available_tools()
        analytics_tool = next((t for t in tools if t["name"] == "generate_analytics_report"), None)

        assert analytics_tool is not None
        assert "description" in analytics_tool
        assert "parameters" in analytics_tool

    def test_create_posting_schedule_tool_structure(self):
        """Test create_posting_schedule tool has correct structure"""
        tools = self.tools.get_available_tools()
        schedule_tool = next((t for t in tools if t["name"] == "create_posting_schedule"), None)

        assert schedule_tool is not None
        assert "description" in schedule_tool
        assert "parameters" in schedule_tool
        assert "client_name" in schedule_tool["parameters"]


class TestAgentConversationIntegration:
    """Test agent integration with conversation history"""

    def setup_method(self):
        """Setup test with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_agent_sessions.db"

        # Create a mock agent (without API key for testing)
        # Note: We'll need to mock API calls in real tests
        self.session_id = "test_integration_session"

    def teardown_method(self):
        """Cleanup temporary database"""
        shutil.rmtree(self.temp_dir)

    def test_agent_export_conversation(self):
        """Test agent's export_conversation method"""
        # This test would require a real agent instance with API key
        # For now, we test the context manager directly
        manager = ContextManager(db_path=str(self.db_path))

        # Create session with messages
        manager.save_message(self.session_id, "user", "Test message")
        manager.save_message(self.session_id, "assistant", "Test response")

        # Export conversation
        markdown = manager.export_conversation_markdown(self.session_id)

        assert "Test message" in markdown
        assert "Test response" in markdown

    def test_agent_search_conversation(self):
        """Test agent's search_conversation method"""
        manager = ContextManager(db_path=str(self.db_path))

        # Create session with searchable messages
        manager.save_message(self.session_id, "user", "Generate content")
        manager.save_message(self.session_id, "assistant", "Content generated")

        # Search conversation
        results = manager.search_conversation(self.session_id, "content")

        assert len(results) >= 1


class TestRichConsoleOutputFunctions:
    """Test rich console display functions"""

    def test_display_message_with_code_blocks(self):
        """Test message display with code block detection"""
        from agent_cli_enhanced import display_message

        # Message with Python code block
        message = """
Here's a Python example:

```python
def hello():
    print("Hello, World!")
```

That's how you do it!
"""

        # This test just verifies the function doesn't crash
        # Actual visual testing would require manual inspection
        try:
            display_message(message)
            assert True  # Function executed without error
        except Exception as e:
            pytest.fail(f"display_message raised exception: {e}")

    def test_display_message_without_code_blocks(self):
        """Test message display without code blocks"""
        from agent_cli_enhanced import display_message

        message = "This is a simple message without any code."

        try:
            display_message(message)
            assert True
        except Exception as e:
            pytest.fail(f"display_message raised exception: {e}")


class TestEndToEndWorkflow:
    """End-to-end integration tests for Week 3 features"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_e2e.db"

    def teardown_method(self):
        """Cleanup temporary database"""
        shutil.rmtree(self.temp_dir)

    def test_conversation_persistence_workflow(self):
        """Test complete conversation persistence workflow"""
        manager = ContextManager(db_path=str(self.db_path))
        session_id = "e2e_session"

        # 1. Create context
        context = ConversationContext(session_id=session_id)
        context.current_client = "E2E Test Client"
        manager.save_context(context)

        # 2. Save conversation messages
        manager.save_message(session_id, "user", "Generate posts")
        manager.save_message(session_id, "assistant", "Generating posts...")
        manager.save_message(session_id, "user", "Send deliverable")
        manager.save_message(session_id, "assistant", "Deliverable sent")

        # 3. Load conversation
        messages = manager.load_conversation(session_id)
        assert len(messages) == 4

        # 4. Search conversation
        results = manager.search_conversation(session_id, "posts")
        assert len(results) >= 1

        # 5. Export to markdown
        output_path = Path(self.temp_dir) / "e2e_export.md"
        manager.export_conversation_markdown(session_id, output_path)
        assert output_path.exists()

        # 6. Get summary
        summary = manager.get_conversation_summary(session_id)
        assert summary["total_messages"] == 4
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
