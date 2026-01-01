"""
Pydantic models for brief file import feature.

Used for parsing uploaded client brief files and extracting structured data.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FieldExtraction(BaseModel):
    """
    Represents a single extracted field from a client brief.

    Attributes:
        value: The extracted value (can be string, list, etc.)
        confidence: Confidence level of the extraction (high/medium/low)
        source: Optional line number or location in the source file
    """
    value: Any = Field(..., description="Extracted field value")
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="Confidence level of extraction"
    )
    source: Optional[str] = Field(
        None,
        description="Source location in file (e.g., 'line 42')"
    )


class ParsedBriefResponse(BaseModel):
    """
    Response model for brief file parsing endpoint.

    Contains all extracted fields with confidence scores, warnings, and metadata.
    """
    success: bool = Field(..., description="Whether parsing succeeded")
    fields: Dict[str, FieldExtraction] = Field(
        ...,
        description="Extracted fields with confidence scores"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical warnings during parsing"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the parsing operation"
    )

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "fields": {
                    "companyName": {
                        "value": "Acme Corp",
                        "confidence": "high",
                        "source": "line 3"
                    },
                    "businessDescription": {
                        "value": "B2B SaaS platform for customer analytics",
                        "confidence": "high",
                        "source": "line 7"
                    },
                    "platforms": {
                        "value": ["LinkedIn", "Twitter"],
                        "confidence": "medium",
                        "source": "line 42"
                    }
                },
                "warnings": [
                    "tonePreference not found, defaulting to 'professional'"
                ],
                "metadata": {
                    "filename": "client_brief.txt",
                    "parseTimeMs": 2340,
                    "fieldsExtracted": 6,
                    "fieldsTotal": 8
                }
            }
        }


class ParseError(BaseModel):
    """
    Error response for failed brief parsing.

    Provides structured error information with error codes.
    """
    code: Literal[
        "INVALID_FILE_TYPE",
        "FILE_TOO_LARGE",
        "ENCODING_ERROR",
        "PARSE_FAILED",
        "NETWORK_ERROR"
    ] = Field(..., description="Error code for client-side handling")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Technical details for debugging"
    )

    class Config:
        schema_extra = {
            "example": {
                "code": "FILE_TOO_LARGE",
                "message": "File must be less than 50KB",
                "details": {
                    "filename": "large_brief.txt",
                    "sizeBytes": 102400,
                    "maxSizeBytes": 51200
                }
            }
        }
