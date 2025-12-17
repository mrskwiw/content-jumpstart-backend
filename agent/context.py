"""
Conversation context management for the agent
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationContext(BaseModel):
    """Tracks conversation state and context across messages"""

    session_id: str
    user_id: str = "default_user"
    current_client: Optional[str] = None
    current_project: Optional[str] = None
    recent_actions: List[Dict[str, Any]] = Field(default_factory=list)
    pending_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    workflow_state: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def add_action(self, action: Dict[str, Any]):
        """Add an action to recent history (max 10)"""
        self.recent_actions.append(action)
        if len(self.recent_actions) > 10:
            self.recent_actions.pop(0)
        self.update_activity()

    def add_pending_decision(self, decision: Dict[str, Any]):
        """Add a decision awaiting user input"""
        self.pending_decisions.append(decision)
        self.update_activity()

    def resolve_pending_decision(self, decision_id: str, resolution: Any):
        """Resolve a pending decision"""
        self.pending_decisions = [d for d in self.pending_decisions if d.get("id") != decision_id]
        self.update_activity()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Create from dictionary"""
        # Convert ISO strings back to datetime if they exist
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data and isinstance(data["last_activity"], str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)


class ContextManager:
    """Manages conversation contexts with SQLite persistence"""

    def __init__(self, db_path: str = "data/agent_sessions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """Get database connection with context manager support"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        return conn

    def _init_db(self):
        """Initialize database schema"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_id
                ON sessions(user_id)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_last_activity
                ON sessions(last_activity DESC)
            """
            )

            # NEW: Conversation messages table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_messages
                ON conversation_messages(session_id, timestamp)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_message_content
                ON conversation_messages(content)
            """
            )

            conn.commit()
        finally:
            conn.close()

    def save_context(self, context: ConversationContext):
        """Save context to database"""
        conn = self._get_connection()
        try:
            context_dict = context.to_dict()  # Already JSON-serializable
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, user_id, context_data, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    context.session_id,
                    context.user_id,
                    json.dumps(context_dict),
                    context.created_at.isoformat(),
                    context.last_activity.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load_context(self, session_id: str) -> Optional[ConversationContext]:
        """Load context from database"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT context_data FROM sessions
                WHERE session_id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return ConversationContext.from_dict(data)

            return None
        finally:
            conn.close()

    def get_recent_sessions(
        self, user_id: str = "default_user", limit: int = 5
    ) -> List[ConversationContext]:
        """Get recent sessions for a user"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT context_data FROM sessions
                WHERE user_id = ?
                ORDER BY last_activity DESC
                LIMIT ?
            """,
                (user_id, limit),
            )

            contexts = []
            for row in cursor.fetchall():
                data = json.loads(row[0])
                contexts.append(ConversationContext.from_dict(data))

            return contexts
        finally:
            conn.close()

    def delete_context(self, session_id: str):
        """Delete a context from database"""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def save_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Save a conversation message to database"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO conversation_messages
                (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    role,
                    content,
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load_conversation(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Load conversation history for a session"""
        conn = self._get_connection()
        try:
            if limit:
                cursor = conn.execute(
                    """
                    SELECT role, content, timestamp, metadata
                    FROM conversation_messages
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (session_id, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT role, content, timestamp, metadata
                    FROM conversation_messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """,
                    (session_id,),
                )

            messages = []
            for row in cursor.fetchall():
                message = {"role": row[0], "content": row[1], "timestamp": row[2]}
                if row[3]:
                    message["metadata"] = json.loads(row[3])
                messages.append(message)

            return messages
        finally:
            conn.close()

    def export_conversation_markdown(
        self, session_id: str, output_path: Optional[Path] = None
    ) -> str:
        """Export conversation to markdown format"""
        messages = self.load_conversation(session_id)
        context = self.load_context(session_id)

        # Build markdown
        md_lines = []
        md_lines.append("# Conversation Export")
        md_lines.append("")
        md_lines.append(f"**Session ID:** {session_id}")

        if context:
            md_lines.append(f"**Created:** {context.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            md_lines.append(
                f"**Last Activity:** {context.last_activity.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if context.current_client:
                md_lines.append(f"**Client:** {context.current_client}")
            if context.current_project:
                md_lines.append(f"**Project:** {context.current_project}")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # Add messages
        for msg in messages:
            timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            role = "**User**" if msg["role"] == "user" else "**Agent**"

            md_lines.append(f"### {role} ({timestamp})")
            md_lines.append("")
            md_lines.append(msg["content"])
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

        markdown_content = "\n".join(md_lines)

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding="utf-8")

        return markdown_content

    def search_conversation(
        self, session_id: str, query: str, role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search conversation messages for a query string"""
        conn = self._get_connection()
        try:
            if role:
                cursor = conn.execute(
                    """
                    SELECT role, content, timestamp
                    FROM conversation_messages
                    WHERE session_id = ?
                    AND role = ?
                    AND content LIKE ?
                    ORDER BY timestamp ASC
                """,
                    (session_id, role, f"%{query}%"),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT role, content, timestamp
                    FROM conversation_messages
                    WHERE session_id = ?
                    AND content LIKE ?
                    ORDER BY timestamp ASC
                """,
                    (session_id, f"%{query}%"),
                )

            results = []
            for row in cursor.fetchall():
                results.append({"role": row[0], "content": row[1], "timestamp": row[2]})

            return results
        finally:
            conn.close()

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for a conversation"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message
                FROM conversation_messages
                WHERE session_id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "session_id": session_id,
                    "total_messages": row[0],
                    "user_messages": row[1],
                    "assistant_messages": row[2],
                    "first_message": row[3],
                    "last_message": row[4],
                    "duration": self._calculate_duration(row[3], row[4])
                    if row[3] and row[4]
                    else None,
                }

            return {"session_id": session_id, "total_messages": 0}
        finally:
            conn.close()

    def _calculate_duration(self, start: str, end: str) -> str:
        """Calculate human-readable duration between timestamps"""
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        duration = end_dt - start_dt

        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if duration.days > 0:
            return f"{duration.days} days, {hours} hours"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes"
