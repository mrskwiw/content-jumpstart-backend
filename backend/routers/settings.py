"""API endpoints for user settings and integrations"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import settings_service
from backend.middleware.auth_dependency import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ===== Schemas =====


class WebSearchConfigResponse(BaseModel):
    """Web search configuration"""

    provider: str = Field(..., description="Active provider: brave, tavily, serpapi, or stub")
    brave_api_key_configured: bool = Field(..., description="Whether Brave API key is set")
    tavily_api_key_configured: bool = Field(..., description="Whether Tavily API key is set")
    serpapi_api_key_configured: bool = Field(..., description="Whether SerpAPI key is set")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "brave",
                "brave_api_key_configured": True,
                "tavily_api_key_configured": False,
                "serpapi_api_key_configured": False,
            }
        }


class WebSearchConfigUpdate(BaseModel):
    """Update web search configuration"""

    provider: str = Field(..., description="Provider: brave, tavily, serpapi, or stub")
    brave_api_key: Optional[str] = Field(None, description="Brave Search API key (optional)")
    tavily_api_key: Optional[str] = Field(None, description="Tavily API key (optional)")
    serpapi_api_key: Optional[str] = Field(None, description="SerpAPI key (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "brave",
                "brave_api_key": "BSA1234567890...",  # pragma: allowlist secret
                "tavily_api_key": None,
                "serpapi_api_key": None,
            }
        }


class TestConnectionRequest(BaseModel):
    """Test web search connection"""

    provider: str = Field(..., description="Provider to test: brave, tavily, or serpapi")
    api_key: str = Field(..., description="API key to test")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "brave",
                "api_key": "BSA1234567890...",  # pragma: allowlist secret
            }
        }


class TestConnectionResponse(BaseModel):
    """Connection test result"""

    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Result message")
    provider: str = Field(..., description="Provider tested")
    results_count: Optional[int] = Field(
        None, description="Number of results returned (if successful)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully connected to Brave Search API",
                "provider": "brave",
                "results_count": 10,
            }
        }


class IntegrationStatusResponse(BaseModel):
    """Integration availability status"""

    web_search: bool = Field(..., description="Whether any web search provider is configured")
    brave: bool = Field(..., description="Whether Brave Search is configured")
    tavily: bool = Field(..., description="Whether Tavily is configured")
    serpapi: bool = Field(..., description="Whether SerpAPI is configured")
    dataforseo: bool = Field(..., description="Whether DataForSEO Trends fallback is configured")

    class Config:
        json_schema_extra = {
            "example": {
                "web_search": True,
                "brave": True,
                "tavily": False,
                "serpapi": False,
                "dataforseo": False,
            }
        }


# ===== Endpoints =====


@router.get("/web-search", response_model=WebSearchConfigResponse)
async def get_web_search_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get current web search configuration.

    Returns provider and whether API keys are configured (not the keys themselves).
    """
    config = settings_service.get_web_search_config(db, current_user.id)

    return WebSearchConfigResponse(
        provider=config["provider"],
        brave_api_key_configured=bool(config["brave_api_key"]),
        tavily_api_key_configured=bool(config["tavily_api_key"]),
        serpapi_api_key_configured=bool(config.get("serpapi_api_key")),
    )


@router.post("/web-search", response_model=WebSearchConfigResponse)
async def update_web_search_config(
    update: WebSearchConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update web search configuration.

    - Set provider (brave, tavily, serpapi, or stub)
    - Update API keys (encrypted in database)
    - Empty string or null removes the key
    """
    # Validate provider
    if update.provider not in ["brave", "tavily", "serpapi", "stub"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be 'brave', 'tavily', 'serpapi', or 'stub'",
        )

    # Update configuration
    config = settings_service.set_web_search_config(
        db,
        current_user.id,
        provider=update.provider,
        brave_api_key=update.brave_api_key,
        tavily_api_key=update.tavily_api_key,
        serpapi_api_key=update.serpapi_api_key,
    )

    return WebSearchConfigResponse(
        provider=config["provider"],
        brave_api_key_configured=bool(config["brave_api_key"]),
        tavily_api_key_configured=bool(config["tavily_api_key"]),
        serpapi_api_key_configured=bool(config.get("serpapi_api_key")),
    )


@router.post("/web-search/test", response_model=TestConnectionResponse)
async def test_web_search_connection(
    test_request: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test web search API connection.

    Makes a test query to verify the API key works.
    Does not save the key - use update endpoint to save.
    """
    from src.utils.web_search import WebSearchClient

    if test_request.provider not in ["brave", "tavily", "serpapi"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be 'brave', 'tavily', or 'serpapi' for testing",
        )

    try:
        # Create temporary client with provided key
        client = WebSearchClient(provider=test_request.provider, api_key=test_request.api_key)

        # Test search
        response = client.search("test query", max_results=5)

        # Check if we got real results (not stub fallback)
        if response.results and response.results[0].source == test_request.provider:
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to {test_request.provider.title()} Search API",
                provider=test_request.provider,
                results_count=len(response.results),
            )
        else:
            return TestConnectionResponse(
                success=False,
                message=f"API key may be invalid - received stub results instead of {test_request.provider} results",
                provider=test_request.provider,
                results_count=0,
            )

    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            provider=test_request.provider,
            results_count=0,
        )


@router.delete("/web-search/keys/{provider}")
async def delete_web_search_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete API key for a specific provider.

    Args:
        provider: "brave" or "tavily"
    """
    if provider not in ["brave", "tavily", "serpapi"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be 'brave', 'tavily', or 'serpapi'",
        )

    key_name = f"{provider}_api_key"
    deleted = settings_service.delete_setting(db, current_user.id, key_name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for {provider}",
        )

    return {"message": f"{provider.title()} API key deleted successfully"}


@router.get("/integrations/status", response_model=IntegrationStatusResponse)
async def get_integrations_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get integration availability status for research tools.

    Returns which integrations are configured and available for use.
    Used by frontend to disable tools that require missing integrations.
    """
    from backend.config import settings as app_settings

    # Get web search configuration
    config = settings_service.get_web_search_config(db, current_user.id)

    # Check if API keys are configured (non-empty strings)
    brave_configured = bool(config.get("brave_api_key", ""))
    tavily_configured = bool(config.get("tavily_api_key", ""))
    serpapi_configured = bool(config.get("serpapi_api_key", ""))

    # DataForSEO is env-var only — not stored per-user in the database
    dataforseo_configured = bool(app_settings.DATAFORSEO_LOGIN and app_settings.DATAFORSEO_PASSWORD)

    # web_search is true if ANY web search provider is configured
    web_search = brave_configured or tavily_configured or serpapi_configured

    return IntegrationStatusResponse(
        web_search=web_search,
        brave=brave_configured,
        tavily=tavily_configured,
        serpapi=serpapi_configured,
        dataforseo=dataforseo_configured,
    )
