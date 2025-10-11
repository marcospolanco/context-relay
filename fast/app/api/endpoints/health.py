"""Health check endpoint."""

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter

from ...models.context import HealthResponse
from ...services.event_broadcaster import event_broadcaster

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring service status."""
    components = {
        "event_broadcaster": "healthy",
        "mock_data_service": "healthy",
        "storage": "in-memory",
        "sse_streaming": "active"
    }

    # Check event broadcaster
    try:
        client_count = event_broadcaster.get_client_count()
        components["active_connections"] = str(client_count)
    except Exception:
        components["event_broadcaster"] = "unhealthy"

    response = HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
        components=components
    )

    # Add services field for backward compatibility with tests
    response_dict = response.model_dump()
    response_dict["services"] = components

    return response_dict