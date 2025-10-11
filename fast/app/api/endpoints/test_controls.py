"""Test control endpoints for toggling service states and clearing data."""

from typing import Dict
from fastapi import APIRouter, Body

from ...services.mongodb_service import get_mongodb_service
from ...services.voyage_embedding_service import get_voyage_service

# Import in-memory stores from context endpoints for clearing
from .context import _context_storage, _context_versions

router = APIRouter(prefix="/test", tags=["test-controls"])


# Local flags to simulate external service availability during tests
_embedding_service_available: bool = True
_mongodb_connected: bool = True


@router.post("/embedding-service/availability")
async def set_embedding_service_availability(available: bool = Body(..., embed=True)) -> Dict[str, bool]:
    """Set embedding service availability flag (accepts JSON body)."""
    global _embedding_service_available
    _embedding_service_available = bool(available)

    # Set the availability on the actual Voyage service instance if it exists
    try:
        voyage_service = get_voyage_service()
        voyage_service.set_availability(_embedding_service_available)
    except Exception:
        # Voyage service not properly initialized, just update the flag
        pass

    return {"embedding_service_available": _embedding_service_available}


@router.post("/mongodb-service/connection")
async def set_mongodb_connection_status(connected: bool = Body(..., embed=True)) -> Dict[str, bool]:
    """Set MongoDB connection status (accepts JSON body)."""
    global _mongodb_connected
    _mongodb_connected = bool(connected)

    # Propagate to the MongoDB service singleton if available
    try:
        get_mongodb_service().set_connection_status(_mongodb_connected)
    except Exception:
        # Ignore infrastructure errors in test controls; surface flag only
        pass

    return {"mongodb_connected": _mongodb_connected}


@router.post("/clear-all-data")
async def clear_all_data() -> Dict[str, str]:
    """Clear all in-memory context data for a clean test state."""
    _context_storage.clear()
    _context_versions.clear()
    return {"message": "All data cleared"}
