import asyncio
import json
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
from fastapi import Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.models.context import SSEEvent, EventPayload


class EventService:
    """Manages Server-Sent Events for real-time frontend updates"""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        self._last_event_id = 0

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to event stream"""
        queue = asyncio.Queue(maxsize=100)  # Limit queue size to prevent memory issues
        self._subscribers.add(queue)

        # Send recent events to new subscriber (optional, for recovery)
        for event in self._event_history[-10:]:  # Send last 10 events
            await queue.put(event)

        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from event stream"""
        self._subscribers.discard(queue)

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Broadcast an event to all subscribers"""
        event_id = str(self._last_event_id + 1)
        self._last_event_id += 1

        event = {
            "id": event_id,
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Broadcast to all subscribers
        disconnected_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Queue is full, mark for removal
                disconnected_queues.append(queue)
            except Exception:
                # Queue is broken, mark for removal
                disconnected_queues.append(queue)

        # Clean up disconnected queues
        for queue in disconnected_queues:
            self._subscribers.discard(queue)

        return event_id

    async def create_context_initialized_event(self, context_id: str, context_packet: Dict[str, Any]) -> str:
        """Create and broadcast contextInitialized event"""
        return await self.broadcast_event("contextInitialized", {
            "context_id": context_id,
            "context_packet": context_packet
        })

    async def create_relay_sent_event(self, from_agent: str, to_agent: str,
                                     context_id: str, delta: Dict[str, Any]) -> str:
        """Create and broadcast relaySent event"""
        return await self.broadcast_event("relaySent", {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "context_id": context_id,
            "delta": delta
        })

    async def create_relay_received_event(self, to_agent: str, context_id: str,
                                         new_packet: Dict[str, Any],
                                         conflicts: Optional[List[str]] = None) -> str:
        """Create and broadcast relayReceived event"""
        payload = {
            "to_agent": to_agent,
            "context_id": context_id,
            "new_packet": new_packet
        }
        if conflicts:
            payload["conflicts"] = conflicts

        return await self.broadcast_event("relayReceived", payload)

    async def create_context_merged_event(self, input_context_ids: List[str],
                                         merged_context: Dict[str, Any],
                                         conflict_report: Optional[List[str]] = None) -> str:
        """Create and broadcast contextMerged event"""
        payload = {
            "input_context_ids": input_context_ids,
            "merged_context": merged_context
        }
        if conflict_report:
            payload["conflict_report"] = conflict_report

        return await self.broadcast_event("contextMerged", payload)

    async def create_context_pruned_event(self, context_id: str,
                                         pruned_context: Dict[str, Any]) -> str:
        """Create and broadcast contextPruned event"""
        return await self.broadcast_event("contextPruned", {
            "context_id": context_id,
            "pruned_context": pruned_context
        })

    async def create_context_updated_event(self, context_id: str,
                                          new_packet: Dict[str, Any],
                                          delta: Dict[str, Any]) -> str:
        """Create and broadcast contextUpdated event"""
        return await self.broadcast_event("contextUpdated", {
            "context_id": context_id,
            "new_packet": new_packet,
            "delta": delta
        })

    async def create_version_created_event(self, version_info: Dict[str, Any]) -> str:
        """Create and broadcast versionCreated event"""
        return await self.broadcast_event("versionCreated", {
            "version_info": version_info
        })

    async def create_error_event(self, context_id: Optional[str],
                                error_code: str, message: str) -> str:
        """Create and broadcast error event"""
        payload = {
            "error_code": error_code,
            "message": message
        }
        if context_id:
            payload["context_id"] = context_id

        return await self.broadcast_event("error", payload)

    def create_sse_generator(self, last_event_id: Optional[str] = None):
        """Create a generator for SSE streaming"""
        async def event_generator():
            queue = await self.subscribe()
            try:
                # If last_event_id is provided, find events after that ID
                start_index = 0
                if last_event_id:
                    try:
                        last_id = int(last_event_id)
                        for i, event in enumerate(self._event_history):
                            if int(event["id"]) > last_id:
                                start_index = i
                                break
                    except (ValueError, TypeError):
                        pass

                # Send historical events first
                for event in self._event_history[start_index:]:
                    yield {
                        "event": event["type"],
                        "data": json.dumps(event["payload"]),
                        "id": event["id"]
                    }

                # Then stream live events
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=1.0)
                        yield {
                            "event": event["type"],
                            "data": json.dumps(event["payload"]),
                            "id": event["id"]
                        }
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        yield {
                            "event": "ping",
                            "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                        }
                    except Exception:
                        break

            finally:
                await self.unsubscribe(queue)

        return event_generator

    def get_stats(self) -> Dict[str, Any]:
        """Get event service statistics"""
        return {
            "active_subscribers": len(self._subscribers),
            "total_events": len(self._event_history),
            "last_event_id": self._last_event_id
        }

    async def cleanup(self):
        """Clean up resources"""
        # Clear all subscribers
        self._subscribers.clear()
        self._event_history.clear()


# Global event service instance
event_service = EventService()