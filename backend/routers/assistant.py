"""
AI Assistant API endpoints.

Provides context-aware AI assistance throughout the operator dashboard.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import standard_limiter, lenient_limiter
from src.validators.prompt_injection_defense import sanitize_prompt_input

# Will use Claude API directly for assistant conversations
try:
    from src.utils.anthropic_client import get_default_client
    from src.utils.response_cache import ResponseCache

    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    logger.warning("Claude API client not available for assistant")

# Initialize chat response cache with 1-hour TTL (Phase 3: Performance optimization)
chat_cache = (
    ResponseCache(
        ttl_seconds=3600,  # 1 hour cache for chat responses
        enabled=CLAUDE_AVAILABLE,
    )
    if CLAUDE_AVAILABLE
    else None
)

router = APIRouter()


class Message(BaseModel):
    """Chat message"""

    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to chat with AI assistant"""

    message: str
    context: Optional[dict] = {}  # Current page context (page name, project ID, etc.)
    conversation_history: List[Message] = []


class ChatResponse(BaseModel):
    """Response from AI assistant"""

    message: str
    suggestions: List[str] = []  # Context-aware quick actions


class ContextRequest(BaseModel):
    """Request for context-aware suggestions"""

    page: str  # Current page name
    data: Optional[dict] = {}  # Current page data (project, client, etc.)


class ContextResponse(BaseModel):
    """Context-aware suggestions"""

    suggestions: List[str]
    quick_actions: List[dict] = []  # [{label, action, icon}]


# Context-aware system prompts for different pages
PAGE_CONTEXTS = {
    "wizard": """You are an AI assistant helping operators use the Content Jumpstart wizard.

Key capabilities you can help with:
- Creating client profiles (business description, ideal customer, pain points)
- Selecting post templates (15 templates available, explain each type)
- Generating content (30 posts, multi-platform support)
- Running quality assurance (hooks, CTAs, length, keywords)
- Managing deliverables (exporting, packaging)

Be concise and actionable. Suggest next steps based on current wizard stage.""",
    "projects": """You are an AI assistant helping operators manage content projects.

Key capabilities:
- Creating new projects for clients
- Viewing project status and progress
- Managing project platforms (LinkedIn, Twitter, Blog, etc.)
- Tracking project deadlines
- Viewing generated content

Provide quick answers about project management workflows.""",
    "clients": """You are an AI assistant helping operators manage client information.

Key capabilities:
- Creating new client profiles
- Editing client business descriptions
- Managing client pain points and ideal customers
- Viewing client projects
- Running research tools on client data

Help operators understand client profile requirements.""",
    "content-review": """You are an AI assistant helping operators review generated content.

Key capabilities:
- Reviewing QA results (hooks, CTAs, length, headlines, keywords)
- Filtering content by quality status
- Requesting revisions
- Approving content for delivery

Guide operators through the QA workflow.""",
    "deliverables": """You are an AI assistant helping operators manage client deliverables.

Key capabilities:
- Viewing completed deliverables
- Downloading deliverable packages
- Tracking delivery status
- Managing revisions

Explain deliverable formats and export options.""",
    "settings": """You are an AI assistant helping operators configure system settings.

Key capabilities:
- Managing API keys and credentials
- Configuring generation settings (platforms, templates)
- Setting quality thresholds
- Managing user preferences

Provide guidance on configuration options.""",
    "overview": """You are an AI assistant for the Content Jumpstart operator dashboard.

This is the main overview page showing:
- Recent projects
- Pending tasks
- System metrics
- Quick actions

I can help you navigate the system and explain any features.""",
}


def build_assistant_prompt(
    page: str, context: dict, user_message: str, history: List[Message]
) -> str:
    """Build context-aware system prompt for assistant"""

    # Get page-specific context
    page_context = PAGE_CONTEXTS.get(page, PAGE_CONTEXTS["overview"])

    # Build conversation context from history
    conversation = ""
    if history:
        conversation = "\n\nConversation history:\n"
        for msg in history[-5:]:  # Last 5 messages for context
            conversation += f"{msg.role}: {msg.content}\n"

    # Add current page data context
    data_context = ""
    if context:
        data_context = f"\n\nCurrent page data:\n{context}"

    # Combine into full prompt
    full_prompt = f"""{page_context}

Current page: {page}{data_context}{conversation}

User question: {user_message}

Provide a helpful, concise response. If the user's question is about something outside your scope, politely redirect them to the appropriate page or documentation."""

    return full_prompt


@router.post("/chat", response_model=ChatResponse)
@standard_limiter.limit("50/hour")  # TR-004: Moderate limit for Claude API chat
async def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chat with AI assistant.

    Provides context-aware help based on current page and conversation history.

    Rate limit: 50/hour per IP+user (moderate limit for AI chat)
    """
    if not CLAUDE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is not available (Claude API client not configured)",
        )

    try:
        # SECURITY (TR-020): Sanitize user message before passing to LLM
        try:
            sanitized_message = sanitize_prompt_input(request.message, strict=False)
            logger.info(f"Sanitized assistant chat message for user {current_user.email}")
        except ValueError as e:
            logger.warning(f"Prompt injection detected in assistant chat: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your message contains potentially unsafe content. Please rephrase and try again.",
            )

        # Get current page from context
        page = request.context.get("page", "overview")

        # Build context-aware prompt
        system_prompt = build_assistant_prompt(
            page=page,
            context=request.context,
            user_message=sanitized_message,  # Use sanitized message
            history=request.conversation_history,
        )

        # PERFORMANCE (Phase 3): Check cache before calling Claude API
        messages = [{"role": "user", "content": sanitized_message}]
        cached_response = chat_cache.get(messages, system_prompt, 0.7) if chat_cache else None

        if cached_response:
            assistant_message = cached_response
            logger.info(f"AI assistant cache hit for user {current_user.email} on page {page}")
        else:
            # Call Claude API
            client = get_default_client()
            response = client.create_message(
                model="claude-3-5-sonnet-latest",
                max_tokens=1024,
                temperature=0.7,
                system=system_prompt,
                messages=messages,
            )

            assistant_message = response.content[0].text

            # Cache the response for future requests
            if chat_cache:
                chat_cache.put(messages, system_prompt, 0.7, assistant_message)
                logger.debug("AI assistant response cached")

            logger.info(f"AI assistant API call for user {current_user.email} on page {page}")

        # Generate context-aware suggestions
        suggestions = generate_suggestions(page, request.context)

        logger.info(f"AI assistant responded to user {current_user.email} on page {page}")

        return ChatResponse(message=assistant_message, suggestions=suggestions)

    except Exception as e:
        logger.error(f"AI assistant error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI assistant error: {str(e)}",
        )


@router.post("/context", response_model=ContextResponse)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap operation, no AI calls
async def get_context_suggestions(
    request: ContextRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Get context-aware suggestions for current page.

    Returns quick actions and helpful suggestions based on what page the user is viewing.

    Rate limit: 1000/hour (cheap operation, no AI calls)
    """
    suggestions = generate_suggestions(request.page, request.data)
    quick_actions = generate_quick_actions(request.page, request.data)

    return ContextResponse(suggestions=suggestions, quick_actions=quick_actions)


@router.post("/reset")
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap operation, no AI calls
async def reset_conversation(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Reset AI assistant conversation.

    Clears conversation history for a fresh start.

    Rate limit: 1000/hour (cheap operation)
    """
    # In a production system, this would clear session storage
    # For now, it's a client-side operation
    return {"success": True, "message": "Conversation reset"}


def generate_suggestions(page: str, context: dict) -> List[str]:
    """Generate context-aware suggestions based on current page"""

    suggestions_map = {
        "wizard": [
            "Need help filling out the client brief? Ask me about required fields.",
            "Want to know which templates work best for a specific industry? Just ask!",
            "Confused about template selection? I can explain each template type.",
        ],
        "projects": [
            "Want to create a new project? I can walk you through the process.",
            "Need to check project status? Ask me about project states.",
            "Looking for a specific project? I can help you search.",
        ],
        "clients": [
            "Need to create a new client profile? I can guide you through it.",
            "Want to know what makes a good business description? Ask me!",
            "Running research tools? I can explain each research option.",
        ],
        "content-review": [
            "Need help interpreting QA scores? I can explain each validator.",
            "Want to filter content by quality? Ask me about filter options.",
            "Ready to approve content? I can walk you through the process.",
        ],
        "deliverables": [
            "Need to download a deliverable? I can show you how.",
            "Want to understand deliverable formats? Just ask!",
            "Managing revisions? I can explain the revision workflow.",
        ],
        "settings": [
            "Need to configure API keys? I can guide you through it.",
            "Want to adjust quality thresholds? Ask me about the settings.",
            "Curious about parallel generation? I can explain the feature.",
        ],
        "overview": [
            "New to the dashboard? Ask me for a quick tour!",
            "Want to see your recent activity? Check the metrics above.",
            "Need to start a new project? I can guide you to the wizard.",
        ],
    }

    return suggestions_map.get(page, suggestions_map["overview"])


def generate_quick_actions(page: str, context: dict) -> List[dict]:
    """Generate quick action buttons based on current page"""

    actions_map = {
        "wizard": [
            {"label": "Start New Project", "action": "create_project", "icon": "plus"},
            {"label": "Load Template", "action": "load_template", "icon": "file"},
            {"label": "Run QA", "action": "run_qa", "icon": "check"},
        ],
        "projects": [
            {"label": "New Project", "action": "create_project", "icon": "plus"},
            {"label": "View All", "action": "view_all", "icon": "list"},
        ],
        "clients": [
            {"label": "New Client", "action": "create_client", "icon": "plus"},
            {"label": "Run Research", "action": "run_research", "icon": "search"},
        ],
        "content-review": [
            {"label": "Approve All", "action": "approve_all", "icon": "check"},
            {"label": "Request Revision", "action": "request_revision", "icon": "edit"},
        ],
    }

    return actions_map.get(page, [])
