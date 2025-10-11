from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.models.context import (
    InitializeRequest, InitializeResponse,
    RelayRequest, RelayResponse,
    MergeRequest, MergeResponse,
    PruneRequest, PruneResponse,
    VersionRequest, VersionInfo,
    ContextPacket
)
from app.services.mock_data_service import MockDataService
from app.services.event_service import event_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Context Relay API",
    description="A FastAPI application for context relay functionality with BDD testing",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
mock_data_service = MockDataService()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Context Relay API")
    logger.info(f"Event service stats: {event_service.get_stats()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down Context Relay API")
    await event_service.cleanup()


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Context Relay API",
        "version": "1.0.0",
        "docs": "/docs",
        "events": "/events/relay"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "embedding_service": mock_data_service.embedding_service.service_available,
            "mongodb_service": mock_data_service.mongodb_service.connected,
            "event_service": event_service.get_stats()
        }
    }


# Context initialization endpoint
@app.post("/context/initialize", response_model=InitializeResponse)
async def initialize_context(request: InitializeRequest):
    """Initialize a new context with initial input"""
    try:
        logger.info(f"Initializing context for session: {request.session_id}")

        # Validate input
        if not request.session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")

        if request.initial_input is None:
            raise HTTPException(status_code=400, detail="Initial input cannot be null")

        # Initialize context
        response = await mock_data_service.initialize_context(request)

        # Broadcast event
        await event_service.create_context_initialized_event(
            response.context_id,
            response.context_packet.dict()
        )

        logger.info(f"Context initialized: {response.context_id}")
        return response

    except Exception as e:
        logger.error(f"Error initializing context: {str(e)}")
        await event_service.create_error_event(
            None,
            "INITIALIZATION_ERROR",
            f"Failed to initialize context: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Context relay endpoint
@app.post("/context/relay", response_model=RelayResponse)
async def relay_context(request: RelayRequest):
    """Relay context from one agent to another"""
    try:
        logger.info(f"Relaying context {request.context_id} from {request.from_agent} to {request.to_agent}")

        # Check if context exists
        existing_context = await mock_data_service.mongodb_service.get_context(request.context_id)
        if not existing_context:
            raise HTTPException(status_code=404, detail=f"Context {request.context_id} not found")

        # Broadcast relaySent event
        await event_service.create_relay_sent_event(
            request.from_agent,
            request.to_agent,
            request.context_id,
            request.delta.dict()
        )

        # Process relay
        response = await mock_data_service.relay_context(request)

        # Broadcast relayReceived event
        await event_service.create_relay_received_event(
            request.to_agent,
            request.context_id,
            response.context_packet.dict(),
            response.conflicts
        )

        logger.info(f"Context relayed successfully: {request.context_id}")
        return response

    except ValueError as e:
        logger.error(f"Context not found: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "CONTEXT_NOT_FOUND",
            str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error relaying context: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "RELAY_ERROR",
            f"Failed to relay context: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Context merge endpoint
@app.post("/context/merge", response_model=MergeResponse)
async def merge_contexts(request: MergeRequest):
    """Merge multiple contexts into one"""
    try:
        logger.info(f"Merging contexts: {request.context_ids} with strategy: {request.merge_strategy}")

        if not request.context_ids or len(request.context_ids) < 2:
            raise HTTPException(status_code=400, detail="At least two context IDs are required for merging")

        # Process merge
        response = await mock_data_service.merge_contexts(request)

        # Broadcast contextMerged event
        await event_service.create_context_merged_event(
            request.context_ids,
            response.merged_context.dict(),
            response.conflict_report
        )

        logger.info(f"Contexts merged successfully: {response.merged_context.context_id}")
        return response

    except ValueError as e:
        logger.error(f"Merge error: {str(e)}")
        await event_service.create_error_event(
            None,
            "MERGE_ERROR",
            str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error merging contexts: {str(e)}")
        await event_service.create_error_event(
            None,
            "MERGE_ERROR",
            f"Failed to merge contexts: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Context prune endpoint
@app.post("/context/prune", response_model=PruneResponse)
async def prune_context(request: PruneRequest):
    """Prune context to fit within budget"""
    try:
        logger.info(f"Pruning context {request.context_id} with strategy: {request.pruning_strategy}, budget: {request.budget}")

        # Check if context exists
        existing_context = await mock_data_service.mongodb_service.get_context(request.context_id)
        if not existing_context:
            raise HTTPException(status_code=404, detail=f"Context {request.context_id} not found")

        if request.budget >= len(existing_context.fragments):
            raise HTTPException(status_code=400, detail="Budget exceeds current context size")

        # Process pruning
        response = await mock_data_service.prune_context(request)

        # Broadcast contextPruned event
        await event_service.create_context_pruned_event(
            request.context_id,
            response.pruned_context.dict()
        )

        logger.info(f"Context pruned successfully: {request.context_id}")
        return response

    except ValueError as e:
        logger.error(f"Prune error: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "PRUNE_ERROR",
            str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error pruning context: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "PRUNE_ERROR",
            f"Failed to prune context: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Create version endpoint
@app.post("/context/version", response_model=VersionInfo)
async def create_version(request: VersionRequest):
    """Create a version snapshot of a context"""
    try:
        logger.info(f"Creating version for context: {request.context_id}")

        # Check if context exists
        existing_context = await mock_data_service.mongodb_service.get_context(request.context_id)
        if not existing_context:
            raise HTTPException(status_code=404, detail=f"Context {request.context_id} not found")

        # Create version
        response = await mock_data_service.create_version(request)

        # Broadcast versionCreated event
        await event_service.create_version_created_event(response.dict())

        logger.info(f"Version created: {response.version_id}")
        return response

    except ValueError as e:
        logger.error(f"Version creation error: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "VERSION_ERROR",
            str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error creating version: {str(e)}")
        await event_service.create_error_event(
            request.context_id,
            "VERSION_ERROR",
            f"Failed to create version: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Get versions endpoint
@app.get("/context/versions/{context_id}", response_model=list[VersionInfo])
async def get_versions(context_id: str):
    """Get all versions for a context"""
    try:
        logger.info(f"Getting versions for context: {context_id}")

        # Check if context exists
        existing_context = await mock_data_service.mongodb_service.get_context(context_id)
        if not existing_context:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")

        # Get versions
        versions = await mock_data_service.mongodb_service.get_versions(context_id)

        logger.info(f"Retrieved {len(versions)} versions for context: {context_id}")
        return versions

    except ValueError as e:
        logger.error(f"Get versions error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting versions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get context endpoint
@app.get("/context/{context_id}", response_model=ContextPacket)
async def get_context(context_id: str):
    """Get a context packet by ID"""
    try:
        logger.info(f"Getting context: {context_id}")

        context = await mock_data_service.mongodb_service.get_context(context_id)
        if not context:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")

        logger.info(f"Retrieved context: {context_id}")
        return context

    except ValueError as e:
        logger.error(f"Get context error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# SSE events endpoint
@app.get("/events/relay")
async def event_stream(request: Request):
    """Server-Sent Events endpoint for real-time updates"""
    try:
        # Get last event ID for recovery
        last_event_id = request.headers.get("last-event-id")

        logger.info(f"New SSE connection established, last_event_id: {last_event_id}")

        # Create SSE response
        return EventSourceResponse(
            event_service.create_sse_generator(last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control, Last-Event-ID"
            }
        )

    except Exception as e:
        logger.error(f"Error establishing SSE connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Event service stats endpoint (for debugging)
@app.get("/events/stats")
async def get_event_stats():
    """Get event service statistics"""
    return event_service.get_stats()


# Test endpoints for simulating service failures
@app.post("/test/embedding-service/availability")
async def set_embedding_service_availability(available: bool):
    """Set embedding service availability for testing"""
    mock_data_service.embedding_service.set_availability(available)
    return {"embedding_service_available": available}


@app.post("/test/mongodb-service/connection")
async def set_mongodb_connection_status(connected: bool):
    """Set MongoDB connection status for testing"""
    mock_data_service.mongodb_service.set_connection_status(connected)
    return {"mongodb_connected": connected}


@app.post("/test/clear-all-data")
async def clear_all_data():
    """Clear all stored data (for testing)"""
    mock_data_service.mongodb_service.clear_all()
    await event_service.cleanup()
    return {"message": "All data cleared"}


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    await event_service.create_error_event(
        None,
        "INTERNAL_SERVER_ERROR",
        f"Internal server error: {str(exc)}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )