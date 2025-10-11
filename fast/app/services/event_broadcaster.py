"""Event broadcasting service for Server-Sent Events (SSE)."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from ..models.events import (
    SSEEvent,
    VisualizationEventFactory,
    EVENT_TYPES
)


class EventBroadcaster:
    """Service for broadcasting SSE events to connected clients."""

    def __init__(self):
        """Initialize the event broadcaster."""
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._event_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        self._throttle_counter = defaultdict(int)
        self._throttle_threshold = 10  # Max events per second per type

    async def subscribe(self, client_id: str, event_types: Optional[List[str]] = None) -> asyncio.Queue:
        """Subscribe a client to events."""
        queue = asyncio.Queue()
        self._queues[client_id] = queue

        # Subscribe to specific event types or all if none specified
        if event_types:
            for event_type in event_types:
                self._subscriptions[event_type].add(client_id)
        else:
            # Subscribe to all event types
            for event_type in EVENT_TYPES.keys():
                self._subscriptions[event_type].add(client_id)

        return queue

    async def unsubscribe(self, client_id: str):
        """Unsubscribe a client from events."""
        if client_id in self._queues:
            del self._queues[client_id]

        # Remove from all subscriptions
        for event_type in EVENT_TYPES.keys():
            self._subscriptions[event_type].discard(client_id)

    async def broadcast_event(self, event: SSEEvent):
        """Broadcast an event to all subscribed clients."""
        # Check throttling
        if self._is_throttled(event.type):
            return

        # Store event in history
        event_data = {
            "type": event.type,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "id": event.id
        }
        self._add_to_history(event_data)

        # Serialize event for transmission
        event_json = json.dumps(event_data, default=str)

        # Send to subscribed clients
        subscribers = self._subscriptions.get(event.type, set())
        tasks = []
        for client_id in subscribers:
            if client_id in self._queues:
                queue = self._queues[client_id]
                if not queue.full():
                    task = asyncio.create_task(queue.put(event_json))
                    tasks.append(task)
                else:
                    # Client queue is full, consider disconnecting
                    await self._handle_full_queue(client_id, event.type)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Also broadcast visualization event
        await self._broadcast_visualization_event(event)

    async def _broadcast_visualization_event(self, event: SSEEvent):
        """Broadcast corresponding visualization event."""
        viz_factory = VisualizationEventFactory()
        viz_event = None

        # Create appropriate visualization event based on business event type
        if event.type == "contextInitialized":
            viz_event = viz_factory.create_context_initialized_event(
                event.data.get("contextId"),
                event.data.get("sessionId"),
                event.data.get("fragmentCount", 0)
            )
        elif event.type == "relaySent":
            viz_event = viz_factory.create_relay_sent_event(
                event.data.get("contextId"),
                event.data.get("fromAgent"),
                event.data.get("toAgent"),
                event.data.get("fragmentCount", 0)
            )
        elif event.type == "relayReceived":
            viz_event = viz_factory.create_relay_received_event(
                event.data.get("contextId"),
                event.data.get("fromAgent"),
                event.data.get("toAgent"),
                event.data.get("acceptedFragments", 0),
                event.data.get("rejectedFragments", 0),
                event.data.get("conflicts", [])
            )
        elif event.type == "contextMerged":
            viz_event = viz_factory.create_context_merged_event(
                event.data.get("contextId"),
                event.data.get("sourceContextIds", []),
                event.data.get("mergedFragmentCount", 0),
                event.data.get("conflictCount", 0)
            )
        elif event.type == "contextPruned":
            viz_event = viz_factory.create_context_pruned_event(
                event.data.get("contextId"),
                event.data.get("originalFragmentCount", 0),
                event.data.get("remainingFragmentCount", 0),
                event.data.get("pruningStrategy", "unknown")
            )
        elif event.type == "versionCreated":
            viz_event = viz_factory.create_version_created_event(
                event.data.get("contextId"),
                event.data.get("versionId"),
                event.data.get("versionLabel"),
                event.data.get("fragmentCount", 0)
            )

        if viz_event:
            viz_data = {
                "type": f"viz:{viz_event.type}",
                "timestamp": viz_event.timestamp.isoformat(),
                "ui": viz_event.ui,
                "data": viz_event.data
            }
            viz_json = json.dumps(viz_data, default=str)

            # Send to all clients (visualization events go to everyone)
            tasks = []
            for client_id, queue in self._queues.items():
                if not queue.full():
                    task = asyncio.create_task(queue.put(viz_json))
                    tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _is_throttled(self, event_type: str) -> bool:
        """Check if event type should be throttled."""
        now = datetime.utcnow()
        key = f"{event_type}_{now.strftime('%Y-%m-%d_%H:%M:%S')}"

        self._throttle_counter[key] += 1

        # Clean old entries
        current_second = now.strftime('%Y-%m-%d_%H:%M:%S')
        keys_to_remove = []
        for k in self._throttle_counter.keys():
            if k.split('_')[2] != current_second:
                keys_to_remove.append(k)

        for k in keys_to_remove:
            del self._throttle_counter[k]

        return self._throttle_counter.get(key, 0) > self._throttle_threshold

    def _add_to_history(self, event_data: Dict[str, Any]):
        """Add event to history with size limit."""
        self._event_history.append(event_data)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

    async def _handle_full_queue(self, client_id: str, event_type: str):
        """Handle client queue that is full."""
        # Log the issue
        print(f"Warning: Client {client_id} queue full for event type {event_type}")

        # Consider unsubscribing the client if this happens repeatedly
        # This is a simple implementation - in production, you might want
        # more sophisticated handling

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get event history with optional filtering."""
        history = self._event_history

        # Filter by event type
        if event_type:
            history = [e for e in history if e.get("type") == event_type]

        # Filter by timestamp
        if since:
            history = [
                e for e in history
                if datetime.fromisoformat(e.get("timestamp", "")) >= since
            ]

        # Limit and return
        return history[-limit:]

    def get_active_subscriptions(self) -> Dict[str, List[str]]:
        """Get current active subscriptions by event type."""
        return {
            event_type: list(subscribers)
            for event_type, subscribers in self._subscriptions.items()
            if subscribers
        }

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._queues)

    async def cleanup_stale_clients(self):
        """Clean up clients with full queues or no activity."""
        stale_clients = []
        for client_id, queue in self._queues.items():
            if queue.full():
                stale_clients.append(client_id)

        for client_id in stale_clients:
            await self.unsubscribe(client_id)

    async def ping_clients(self):
        """Send ping events to all connected clients."""
        ping_event = SSEEvent(
            type="ping",
            data={"timestamp": datetime.utcnow().isoformat()}
        )
        await self.broadcast_event(ping_event)


# Global event broadcaster instance
event_broadcaster = EventBroadcaster()