from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from .core.config import get_settings
from .api.endpoints import context, events, health
from .services.event_broadcaster import event_broadcaster
from app.services.vector_search_service import get_vector_search_service
from app.config.database import connect_to_mongodb, get_database_client
from app.api import search

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs" if not settings.test_mode else None,
    redoc_url="/redoc" if not settings.test_mode else None
)

# Include routers
app.include_router(search.router)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(context.router)
app.include_router(events.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Event broadcaster initialized with history size: {event_broadcaster._max_history_size}")

    # Initialize MongoDB connection
    await connect_to_mongodb()

    # Initialize vector search service with MongoDB client
    vector_search = get_vector_search_service()
    client = get_database_client()
    if client:
        vector_search.set_client(client)
        logger.info("Vector search service initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down Context Relay API")
    await event_broadcaster.cleanup_stale_clients()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "docs": "/docs",
        "health": "/health/",
        "events": "/events/relay",
        "endpoints": {
            "context": {
                "initialize": "POST /context/initialize",
                "relay": "POST /context/relay",
                "merge": "POST /context/merge",
                "prune": "POST /context/prune",
                "version": "POST /context/{context_id}/version",
                "get": "GET /context/{context_id}",
                "versions": "GET /context/{context_id}/versions"
            },
            "events": {
                "stream": "GET /events/relay",
                "types": "GET /events/types",
                "history": "GET /events/history",
                "stats": "GET /events/stats"
            },
            "health": {
                "check": "GET /health/"
            }
        },
        "features": {
            "mock_data": "Enabled (Phase 1)",
            "sse_streaming": "Enabled",
            "visualization_events": "Enabled",
            "bdd_testing": "Ready"
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )