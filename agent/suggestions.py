"""
Proactive suggestions system for the agent
"""

import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.database.project_db import ProjectDatabase
except ImportError:
    ProjectDatabase = None


class SuggestionType(str, Enum):
    """Types of proactive suggestions"""

    FEEDBACK_REMINDER = "feedback_reminder"
    REVISION_FOLLOWUP = "revision_followup"
    INVOICE_REMINDER = "invoice_reminder"
    DELIVERABLE_READY = "deliverable_ready"
    VOICE_UPDATE = "voice_update"
    TEMPLATE_PERFORMANCE = "template_performance"
    CLIENT_MILESTONE = "client_milestone"


class SuggestionPriority(str, Enum):
    """Suggestion urgency levels"""

    CRITICAL = "critical"  # Requires immediate attention
    HIGH = "high"  # Should address soon
    MEDIUM = "medium"  # Nice to have
    LOW = "low"  # Optional


class Suggestion(BaseModel):
    """A proactive suggestion for the user"""

    suggestion_id: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    recommended_actions: List[str]
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def to_display(self) -> str:
        """Convert to human-readable display"""
        priority_emoji = {
            SuggestionPriority.CRITICAL: "🔴",
            SuggestionPriority.HIGH: "🟠",
            SuggestionPriority.MEDIUM: "🟡",
            SuggestionPriority.LOW: "🟢",
        }

        display = f"{priority_emoji[self.priority]} **{self.title}**\n"
        display += f"{self.description}\n\n"

        if self.recommended_actions:
            display += "**Recommended Actions:**\n"
            for i, action in enumerate(self.recommended_actions, 1):
                display += f"{i}. {action}\n"

        return display


class SuggestionEngine:
    """Generates proactive suggestions based on system state"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or (ProjectDatabase() if ProjectDatabase else None)
        self.suggestion_id_counter = 0

    def generate_suggestions(self) -> List[Suggestion]:
        """Generate all relevant suggestions"""
        suggestions = []

        if not self.db:
            return suggestions

        try:
            # Check for feedback reminders
            suggestions.extend(self._check_missing_feedback())

            # Check for overdue invoices
            suggestions.extend(self._check_overdue_invoices())

            # Check for deliverables ready to send
            suggestions.extend(self._check_pending_deliverables())

            # Check for revision requests
            suggestions.extend(self._check_pending_revisions())

            # Check for client milestones
            suggestions.extend(self._check_client_milestones())

        except Exception:
            # Gracefully handle database errors
            pass

        # Sort by priority
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
        }
        suggestions.sort(key=lambda s: priority_order[s.priority])

        return suggestions

    def _check_missing_feedback(self) -> List[Suggestion]:
        """Check for projects missing feedback"""
        suggestions = []
        now = datetime.now()
        two_weeks_ago = now - timedelta(weeks=2)

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT client_name, project_id, created_at
                    FROM client_history
                    WHERE feedback_count = 0
                    AND created_at < ?
                    ORDER BY created_at ASC
                """,
                    (two_weeks_ago.isoformat(),),
                )

                for row in cursor.fetchall():
                    client_name, project_id, created_at = row
                    days_overdue = (now - datetime.fromisoformat(created_at)).days

                    self.suggestion_id_counter += 1
                    suggestions.append(
                        Suggestion(
                            suggestion_id=f"feedback_{self.suggestion_id_counter}",
                            suggestion_type=SuggestionType.FEEDBACK_REMINDER,
                            priority=SuggestionPriority.HIGH
                            if days_overdue > 21
                            else SuggestionPriority.MEDIUM,
                            title=f"{client_name} hasn't submitted feedback",
                            description=f"Project delivered {days_overdue} days ago. No feedback received yet.",
                            recommended_actions=[
                                "Send gentle reminder email",
                                "Schedule follow-up call",
                                "Check if they need help",
                            ],
                            context_data={
                                "client_name": client_name,
                                "project_id": project_id,
                                "days_overdue": days_overdue,
                            },
                        )
                    )

        except Exception:
            pass

        return suggestions

    def _check_overdue_invoices(self) -> List[Suggestion]:
        """Check for overdue invoices"""
        suggestions = []
        # This would query an invoices table (not yet implemented)
        # Placeholder for future implementation
        return suggestions

    def _check_pending_deliverables(self) -> List[Suggestion]:
        """Check for projects ready to deliver"""
        suggestions = []

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT client_name, project_id, quality_score
                    FROM client_history
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 5
                """,
                    ((datetime.now() - timedelta(hours=24)).isoformat(),),
                )

                for row in cursor.fetchall():
                    client_name, project_id, quality_score = row

                    # Suggest sending if quality is good
                    if quality_score and quality_score >= 85:
                        self.suggestion_id_counter += 1
                        suggestions.append(
                            Suggestion(
                                suggestion_id=f"deliverable_{self.suggestion_id_counter}",
                                suggestion_type=SuggestionType.DELIVERABLE_READY,
                                priority=SuggestionPriority.MEDIUM,
                                title=f"Deliverable ready for {client_name}",
                                description=f"Quality score: {quality_score}% (Excellent). Ready to send.",
                                recommended_actions=[
                                    "Review QA report",
                                    "Send deliverable",
                                    "Schedule feedback collection",
                                ],
                                context_data={
                                    "client_name": client_name,
                                    "project_id": project_id,
                                    "quality_score": quality_score,
                                },
                            )
                        )

        except Exception:
            pass

        return suggestions

    def _check_pending_revisions(self) -> List[Suggestion]:
        """Check for revision requests"""
        suggestions = []
        # This would check for revision requests (not yet fully implemented)
        # Placeholder for future implementation
        return suggestions

    def _check_client_milestones(self) -> List[Suggestion]:
        """Check for client milestones (e.g., 5 projects, 1 year anniversary)"""
        suggestions = []

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT client_name, COUNT(*) as project_count
                    FROM client_history
                    GROUP BY client_name
                    HAVING project_count IN (5, 10, 25, 50)
                    ORDER BY project_count DESC
                """
                )

                for row in cursor.fetchall():
                    client_name, project_count = row

                    self.suggestion_id_counter += 1
                    suggestions.append(
                        Suggestion(
                            suggestion_id=f"milestone_{self.suggestion_id_counter}",
                            suggestion_type=SuggestionType.CLIENT_MILESTONE,
                            priority=SuggestionPriority.LOW,
                            title=f"{client_name} reached {project_count} projects!",
                            description="Consider sending a thank you or offering loyalty discount.",
                            recommended_actions=[
                                "Send congratulations email",
                                "Offer loyalty discount (10% off next project)",
                                "Request testimonial",
                            ],
                            context_data={
                                "client_name": client_name,
                                "project_count": project_count,
                            },
                        )
                    )

        except Exception:
            pass

        return suggestions

    def get_daily_summary(self) -> str:
        """Generate daily summary of pending items"""
        suggestions = self.generate_suggestions()

        if not suggestions:
            return "✅ All caught up! No pending actions."

        critical = [s for s in suggestions if s.priority == SuggestionPriority.CRITICAL]
        high = [s for s in suggestions if s.priority == SuggestionPriority.HIGH]
        medium = [s for s in suggestions if s.priority == SuggestionPriority.MEDIUM]
        low = [s for s in suggestions if s.priority == SuggestionPriority.LOW]

        summary = "**Today's Pending Items:**\n\n"

        if critical:
            summary += f"🔴 **CRITICAL ({len(critical)}):**\n"
            for s in critical:
                summary += f"  • {s.title}\n"
            summary += "\n"

        if high:
            summary += f"🟠 **HIGH PRIORITY ({len(high)}):**\n"
            for s in high:
                summary += f"  • {s.title}\n"
            summary += "\n"

        if medium:
            summary += f"🟡 **THIS WEEK ({len(medium)}):**\n"
            for s in medium:
                summary += f"  • {s.title}\n"
            summary += "\n"

        if low:
            summary += f"🟢 **UPCOMING ({len(low)}):**\n"
            for s in low:
                summary += f"  • {s.title}\n"
            summary += "\n"

        summary += f"**Total:** {len(suggestions)} items\n"
        summary += "\nShould I prioritize the urgent items? (Yes/Show details)"

        return summary
