"""Core event handling infrastructure."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.events import SSEEvent
from ..services.event_broadcaster import event_broadcaster

logger = logging.getLogger(__name__)


class EventHandler:
    """Central event handler for the application."""

    def __init__(self):
        """Initialize the event handler."""
        self._event_handlers: Dict[str, List[callable]] = {}
        self._middleware: List[callable] = []

    def register_handler(self, event_type: str, handler: callable):
        """Register an event handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def register_middleware(self, middleware: callable):
        """Register middleware to process all events."""
        self._middleware.append(middleware)

    async def emit_event(self, event: SSEEvent):
        """Emit an event to all registered handlers and broadcast to clients."""
        try:
            # Process middleware
            for middleware in self._middleware:
                event = await middleware(event) if asyncio.iscoroutinefunction(middleware) else middleware(event)
                if event is None:
                    return  # Middleware can block events

            # Handle registered handlers
            handlers = self._event_handlers.get(event.type, [])
            if handlers:
                tasks = []
                for handler in handlers:
                    if asyncio.iscoroutinefunction(handler):
                        task = asyncio.create_task(handler(event))
                        tasks.append(task)
                    else:
                        # Run sync handlers in thread pool
                        task = asyncio.create_task(asyncio.to_thread(handler, event))
                        tasks.append(task)

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Broadcast to SSE clients
            await event_broadcaster.broadcast_event(event)

        except Exception as e:
            logger.error(f"Error emitting event {event.type}: {e}")


# Global event handler instance
event_handler = EventHandler()