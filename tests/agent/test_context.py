"""
Unit tests for conversation context management
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agent.context import ContextManager, ConversationContext


class TestConversationContext:
    """Test ConversationContext model"""

    def test_create_context(self):
        """Test creating a new context"""
        context = ConversationContext(session_id="test_session", user_id="test_user")

        assert context.session_id == "test_session"
        assert context.user_id == "test_user"
        assert context.current_client is None
        assert context.current_project is None
        assert len(context.recent_actions) == 0
        assert len(context.pending_decisions) == 0

    def test_add_action(self):
        """Test adding actions to context"""
        context = ConversationContext(session_id="test")

        context.add_action({"type": "generate", "description": "Generated posts for Acme Corp"})

        assert len(context.recent_actions) == 1
        assert context.recent_actions[0]["type"] == "generate"

    def test_action_limit(self):
        """Test that actions are limited to 10"""
        context = ConversationContext(session_id="test")

        # Add 15 actions
        for i in range(15):
            context.add_action({"index": i})

        # Should only keep last 10
        assert len(context.recent_actions) == 10
        assert context.recent_actions[0]["index"] == 5  # First kept action
        assert context.recent_actions[-1]["index"] == 14  # Last action

    def test_add_pending_decision(self):
        """Test adding pending decisions"""
        context = ConversationContext(session_id="test")

        context.add_pending_decision(
            {
                "id": "decision_1",
                "question": "Should I generate posts now?",
                "options": ["yes", "no"],
            }
        )

        assert len(context.pending_decisions) == 1
        assert context.pending_decisions[0]["id"] == "decision_1"

    def test_resolve_pending_decision(self):
        """Test resolving pending decisions"""
        context = ConversationContext(session_id="test")

        context.add_pending_decision({"id": "decision_1", "question": "Should I generate posts?"})
        context.add_pending_decision({"id": "decision_2", "question": "Should I send deliverable?"})

        # Resolve first decision
        context.resolve_pending_decision("decision_1", "yes")

        assert len(context.pending_decisions) == 1
        assert context.pending_decisions[0]["id"] == "decision_2"

    def test_to_dict(self):
        """Test converting context to dictionary"""
        context = ConversationContext(
            session_id="test", user_id="user1", current_client="Acme Corp"
        )

        data = context.to_dict()

        assert isinstance(data, dict)
        assert data["session_id"] == "test"
        assert data["user_id"] == "user1"
        assert data["current_client"] == "Acme Corp"

    def test_from_dict(self):
        """Test creating context from dictionary"""
        data = {
            "session_id": "test",
            "user_id": "user1",
            "current_client": "Acme Corp",
            "current_project": None,
            "recent_actions": [],
            "pending_decisions": [],
            "workflow_state": None,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
        }

        context = ConversationContext.from_dict(data)

        assert context.session_id == "test"
        assert context.user_id == "user1"
        assert context.current_client == "Acme Corp"


class TestContextManager:
    """Test ContextManager with temporary database"""

    def setup_method(self):
        """Setup test with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_sessions.db"
        self.manager = ContextManager(db_path=str(self.db_path))

    def teardown_method(self):
        """Cleanup temporary database"""
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_context(self):
        """Test saving and loading context"""
        context = ConversationContext(
            session_id="test_session", user_id="test_user", current_client="Acme Corp"
        )

        # Save context
        self.manager.save_context(context)

        # Load context
        loaded = self.manager.load_context("test_session")

        assert loaded is not None
        assert loaded.session_id == "test_session"
        assert loaded.user_id == "test_user"
        assert loaded.current_client == "Acme Corp"

    def test_load_nonexistent_context(self):
        """Test loading context that doesn't exist"""
        loaded = self.manager.load_context("nonexistent_session")

        assert loaded is None

    def test_get_recent_sessions(self):
        """Test getting recent sessions"""
        # Create multiple sessions
        for i in range(5):
            context = ConversationContext(session_id=f"session_{i}", user_id="test_user")
            self.manager.save_context(context)

        # Get recent sessions
        recent = self.manager.get_recent_sessions(limit=3)

        assert len(recent) == 3
        assert all(isinstance(ctx, ConversationContext) for ctx in recent)

    def test_delete_context(self):
        """Test deleting a context"""
        context = ConversationContext(session_id="test_session", user_id="test_user")

        # Save and verify
        self.manager.save_context(context)
        loaded = self.manager.load_context("test_session")
        assert loaded is not None

        # Delete
        self.manager.delete_context("test_session")

        # Verify deleted
        loaded_after = self.manager.load_context("test_session")
        assert loaded_after is None

    def test_update_existing_context(self):
        """Test updating an existing context"""
        context = ConversationContext(
            session_id="test_session", user_id="test_user", current_client="Acme Corp"
        )

        # Save
        self.manager.save_context(context)

        # Update
        context.current_client = "New Corp"
        context.add_action({"type": "update"})

        # Save again
        self.manager.save_context(context)

        # Load and verify
        loaded = self.manager.load_context("test_session")
        assert loaded.current_client == "New Corp"
        assert len(loaded.recent_actions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
