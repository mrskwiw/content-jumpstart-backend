"""Data models for question generation"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Types of questions to ask"""

    OPEN_ENDED = "open_ended"  # "Tell me about..."
    SPECIFIC = "specific"  # "What is your main CTA?"
    CLARIFYING = "clarifying"  # "You mentioned X, can you elaborate?"
    CHOICE = "choice"  # "Do you prefer A or B?"


class Question(BaseModel):
    """A single question to ask the client"""

    text: str = Field(..., description="The question text")
    field_name: str = Field(..., description="Which ClientBrief field it fills")
    question_type: QuestionType = Field(..., description="Type of question")
    context: Optional[str] = Field(None, description="Why we're asking (for display)")
    example_answer: Optional[str] = Field(None, description="Example to guide client")
    priority: int = Field(..., ge=1, le=3, description="1=critical, 2=important, 3=nice-to-have")

    def to_display_text(self, show_context: bool = True, show_example: bool = True) -> str:
        """
        Format question for display

        Args:
            show_context: Include context line
            show_example: Include example answer

        Returns:
            Formatted question string
        """
        lines = []

        if show_context and self.context:
            lines.append(f"[Context: {self.context}]")

        lines.append(self.text)

        if show_example and self.example_answer:
            lines.append(f"Example: {self.example_answer}")

        return "\n".join(lines)
