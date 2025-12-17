"""
Internal CLI Agent for 30-Day Content Jumpstart

This module provides a Claude Code-style conversational agent interface
for content generation workflows.

Week 1: Foundation
- ContentAgentCore: Basic conversational agent
- ConversationContext: Session management
- AgentTools: CLI command wrappers

Week 2: Intelligence
- ContentAgentCoreEnhanced: Agent with intelligence features
- WorkflowPlanner: Multi-step workflow planning
- SuggestionEngine: Proactive suggestions
- ErrorRecoverySystem: Retry logic with exponential backoff
- TaskScheduler: Delayed task execution
- EmailSystem: Email integration
"""

from .context import ConversationContext
from .core import ContentAgentCore

# Week 2 intelligence components
from .core_enhanced import ContentAgentCoreEnhanced
from .email_system import EmailSystem, EmailType
from .error_recovery import ErrorCategory, ErrorRecoverySystem, RetryConfig
from .planner import PlannedTask, TaskType, WorkflowPlan, WorkflowPlanner
from .scheduler import ScheduledTask, ScheduleFrequency, TaskScheduler
from .suggestions import Suggestion, SuggestionEngine, SuggestionType
from .tools import AgentTools

__all__ = [
    # Week 1
    "ContentAgentCore",
    "ConversationContext",
    "AgentTools",
    # Week 2
    "ContentAgentCoreEnhanced",
    "WorkflowPlanner",
    "WorkflowPlan",
    "PlannedTask",
    "TaskType",
    "SuggestionEngine",
    "Suggestion",
    "SuggestionType",
    "ErrorRecoverySystem",
    "RetryConfig",
    "ErrorCategory",
    "TaskScheduler",
    "ScheduledTask",
    "ScheduleFrequency",
    "EmailSystem",
    "EmailType",
]
