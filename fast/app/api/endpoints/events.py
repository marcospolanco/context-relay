"""Server-Sent Events (SSE) endpoint for real-time event streaming."""

import asyncio
import json
import logging
from typing import AsyncGenerator, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ...models.events import EVENT_TYPES
from ...services.event_broadcaster import event_broadcaster

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)


@router.get("/relay")
async def event_stream(
    event_types: Optional[List[str]] = Query(None, description="Event types to subscribe to"),
    client_id: Optional[str] = Query(None, description="Client identifier")
) -> EventSourceResponse:
    """Server-Sent Events endpoint for real-time context events.

    This endpoint provides a persistent connection for streaming context-related events
    to frontend clients for real-time visualization and updates.

    Query Parameters:
    - event_types: List of specific event types to subscribe to. If not provided, subscribes to all events.
                   Valid values: contextInitialized, relaySent, relayReceived, contextMerged, contextPruned, versionCreated
    - client_id: Optional client identifier for debugging and connection tracking.

    Example usage:
    - Subscribe to all events: GET /events/relay
    - Subscribe to specific events: GET /events/relay?event_types=relaySent&event_types=relayReceived
    """
    try:
        # Validate event types
        if event_types:
            invalid_types = [et for et in event_types if et not in EVENT_TYPES]
            if invalid_types:
                return EventSourceResponse(
                    generate_error_event(f"Invalid event types: {invalid_types}")
                )

        # Generate client ID if not provided
        if not client_id:
            import uuid
            client_id = f"client-{uuid.uuid4().hex[:8]}"

        logger.info(f"Client {client_id} connecting to event stream with types: {event_types or 'all'}")

        # Subscribe client to events
        queue = await event_broadcaster.subscribe(client_id, event_types)

        # Return SSE response
        return EventSourceResponse(
            generate_events(queue, client_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Client-Id": client_id
            }
        )

    except Exception as e:
        logger.error(f"Error setting up event stream: {e}")
        return EventSourceResponse(
            generate_error_event(f"Failed to establish event stream: {str(e)}")
        )


async def generate_events(queue: asyncio.Queue, client_id: str) -> AsyncGenerator[str, None]:
    """Generate events for SSE streaming."""
    try:
        # Send initial connection event
        yield format_sse_event({
            "type": "connected",
            "data": {
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Connected to Context Relay event stream"
            }
        })

        # Send available event types
        yield format_sse_event({
            "type": "event_types",
            "data": {
                "available_types": list(EVENT_TYPES.keys()),
                "subscribed_types": "all"  # This would be tracked in a real implementation
            }
        })

        # Stream events from queue
        while True:
            try:
                # Wait for event with timeout
                event_data = await asyncio.wait_for(queue.get(), timeout=30.0)

                # Send event
                yield format_sse_event({
                    "type": "event",
                    "data": json.loads(event_data) if isinstance(event_data, str) else event_data
                })

                # Mark task as done
                queue.task_done()

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                yield format_sse_event({
                    "type": "ping",
                    "data": {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "client_id": client_id
                    }
                })

    except asyncio.CancelledError:
        logger.info(f"Client {client_id} disconnected from event stream")
    except Exception as e:
        logger.error(f"Error in event stream for client {client_id}: {e}")
        yield format_sse_event({
            "type": "error",
            "data": {
                "error": str(e),
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
    finally:
        # Clean up subscription
        await event_broadcaster.unsubscribe(client_id)


def format_sse_event(data: dict) -> str:
    """Format data as SSE event."""
    event_type = data.get("type", "message")
    event_data = json.dumps(data.get("data", {}), default=str)

    lines = [
        f"event: {event_type}",
        f"data: {event_data}",
        "",  # Empty line to end the event
        ""
    ]

    return "\n".join(lines)


def generate_error_event(error_message: str) -> AsyncGenerator[str, None]:
    """Generate an error event."""
    async def error_generator():
        yield format_sse_event({
            "type": "error",
            "data": {
                "error": error_message,
                "timestamp": asyncio.get_event_loop().time()
            }
        })

    return error_generator()


@router.get("/types")
async def get_event_types():
    """Get available event types and their descriptions."""
    return {
        "event_types": {
            "contextInitialized": "Fired when a new context is created",
            "relaySent": "Fired when context relay is initiated",
            "relayReceived": "Fired when context relay is received and processed",
            "contextMerged": "Fired when multiple contexts are merged",
            "contextPruned": "Fired when context fragments are pruned",
            "versionCreated": "Fired when a new context version is created",
            "viz:*": "Visualization events (prefixed with 'viz:') for UI updates"
        },
        "visualization_events": {
            "viz:contextInitialized": "UI event for context initialization animation",
            "viz:relaySent": "UI event for relay animation from source to target",
            "viz:relayReceived": "UI event for relay completion animation",
            "viz:contextMerged": "UI event for context merge animation",
            "viz:contextPruned": "UI event for context pruning animation",
            "viz:versionCreated": "UI event for version creation indicator"
        }
    }


@router.get("/history")
async def get_event_history(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    since: Optional[str] = Query(None, description="ISO datetime to filter events since")
):
    """Get event history for debugging and testing."""
    try:
        # Parse since parameter
        since_dt = None
        if since:
            from datetime import datetime
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))

        # Get history from event broadcaster
        history = event_broadcaster.get_event_history(
            event_type=event_type,
            limit=limit,
            since=since_dt
        )

        return {
            "history": history,
            "count": len(history),
            "filters": {
                "event_type": event_type,
                "limit": limit,
                "since": since
            }
        }

    except Exception as e:
        raise ValueError(f"Invalid request parameters: {str(e)}")


@router.get("/stats")
async def get_event_stats():
    """Get event streaming statistics."""
    history = event_broadcaster.get_event_history()
    last_event_id = history[-1]["id"] if history else None
    return {
        "active_subscribers": event_broadcaster.get_client_count(),
        "subscriptions": event_broadcaster.get_active_subscriptions(),
        "available_event_types": list(EVENT_TYPES.keys()),
        "history_size": len(history),
        "total_events": len(history),
        "last_event_id": last_event_id,
    }