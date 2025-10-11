"""Event models for SSE streaming and visualization."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .shared import VisualizationEvent


class SSEEvent(BaseModel):
    """Base Server-Sent Event model."""
    model_config = ConfigDict(extra='forbid')

    type: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    id: Optional[str] = Field(None, description="Event ID for deduplication")


# Business Event Types
class ContextInitializedEvent(SSEEvent):
    """Event fired when a new context is initialized."""

    def __init__(self, context_id: str, session_id: str, fragment_count: int, **kwargs):
        super().__init__(
            type="contextInitialized",
            data={
                "contextId": context_id,
                "sessionId": session_id,
                "fragmentCount": fragment_count
            },
            **kwargs
        )


class RelaySentEvent(SSEEvent):
    """Event fired when context relay is initiated."""

    def __init__(self, context_id: str, from_agent: str, to_agent: str, fragment_count: int, **kwargs):
        super().__init__(
            type="relaySent",
            data={
                "contextId": context_id,
                "fromAgent": from_agent,
                "toAgent": to_agent,
                "fragmentCount": fragment_count
            },
            **kwargs
        )


class RelayReceivedEvent(SSEEvent):
    """Event fired when context relay is received."""

    def __init__(self, context_id: str, from_agent: str, to_agent: str,
                 accepted_fragments: int, rejected_fragments: int, conflicts: List[str] = None, **kwargs):
        super().__init__(
            type="relayReceived",
            data={
                "contextId": context_id,
                "fromAgent": from_agent,
                "toAgent": to_agent,
                "acceptedFragments": accepted_fragments,
                "rejectedFragments": rejected_fragments,
                "conflicts": conflicts or []
            },
            **kwargs
        )


class ContextMergedEvent(SSEEvent):
    """Event fired when contexts are merged."""

    def __init__(self, context_id: str, source_context_ids: List[str],
                 merged_fragment_count: int, conflict_count: int, **kwargs):
        super().__init__(
            type="contextMerged",
            data={
                "contextId": context_id,
                "sourceContextIds": source_context_ids,
                "mergedFragmentCount": merged_fragment_count,
                "conflictCount": conflict_count
            },
            **kwargs
        )


class ContextPrunedEvent(SSEEvent):
    """Event fired when context is pruned."""

    def __init__(self, context_id: str, original_count: int, remaining_count: int,
                 pruning_strategy: str, **kwargs):
        super().__init__(
            type="contextPruned",
            data={
                "contextId": context_id,
                "originalFragmentCount": original_count,
                "remainingFragmentCount": remaining_count,
                "pruningStrategy": pruning_strategy
            },
            **kwargs
        )


class VersionCreatedEvent(SSEEvent):
    """Event fired when a new version is created."""

    def __init__(self, context_id: str, version_id: str, version_label: Optional[str],
                 fragment_count: int, **kwargs):
        super().__init__(
            type="versionCreated",
            data={
                "contextId": context_id,
                "versionId": version_id,
                "versionLabel": version_label,
                "fragmentCount": fragment_count
            },
            **kwargs
        )


# Visualization Event Factory
class VisualizationEventFactory:
    """Factory for creating UI-friendly visualization events."""

    @staticmethod
    def create_context_initialized_event(context_id: str, session_id: str, fragment_count: int) -> VisualizationEvent:
        """Create visualization event for context initialization."""
        return VisualizationEvent(
            type="contextInitialized",
            ui={
                "nodeId": context_id,
                "color": "purple",
                "animate": True,
                "effect": "pulse"
            },
            data={
                "contextId": context_id,
                "sessionId": session_id,
                "fragmentCount": fragment_count
            }
        )

    @staticmethod
    def create_relay_sent_event(context_id: str, from_agent: str, to_agent: str, fragment_count: int) -> VisualizationEvent:
        """Create visualization event for relay sent."""
        return VisualizationEvent(
            type="relaySent",
            ui={
                "sourceNode": from_agent,
                "targetNode": to_agent,
                "color": "blue",
                "animate": True,
                "edgeId": f"relay-{context_id}",
                "effect": "flow"
            },
            data={
                "contextId": context_id,
                "fragmentCount": fragment_count
            }
        )

    @staticmethod
    def create_relay_received_event(context_id: str, from_agent: str, to_agent: str,
                                   accepted: int, rejected: int, conflicts: List[str]) -> VisualizationEvent:
        """Create visualization event for relay received."""
        return VisualizationEvent(
            type="relayReceived",
            ui={
                "sourceNode": from_agent,
                "targetNode": to_agent,
                "color": "green" if len(conflicts) == 0 else "orange",
                "animate": True,
                "edgeId": f"relay-{context_id}",
                "effect": "highlight"
            },
            data={
                "contextId": context_id,
                "acceptedFragments": accepted,
                "rejectedFragments": rejected,
                "conflictCount": len(conflicts)
            }
        )

    @staticmethod
    def create_context_merged_event(context_id: str, source_contexts: List[str],
                                   fragment_count: int, conflict_count: int) -> VisualizationEvent:
        """Create visualization event for context merge."""
        return VisualizationEvent(
            type="contextMerged",
            ui={
                "sourceNodes": source_contexts,
                "targetNode": context_id,
                "color": "orange" if conflict_count > 0 else "green",
                "animate": True,
                "effect": "merge"
            },
            data={
                "contextId": context_id,
                "sourceContextCount": len(source_contexts),
                "fragmentCount": fragment_count,
                "conflictCount": conflict_count
            }
        )

    @staticmethod
    def create_context_pruned_event(context_id: str, original_count: int,
                                   remaining_count: int, strategy: str) -> VisualizationEvent:
        """Create visualization event for context pruning."""
        return VisualizationEvent(
            type="contextPruned",
            ui={
                "nodeId": context_id,
                "color": "red",
                "animate": True,
                "effect": "shrink"
            },
            data={
                "contextId": context_id,
                "originalCount": original_count,
                "remainingCount": remaining_count,
                "removedCount": original_count - remaining_count,
                "strategy": strategy
            }
        )

    @staticmethod
    def create_version_created_event(context_id: str, version_id: str, version_label: Optional[str],
                                    fragment_count: int) -> VisualizationEvent:
        """Create visualization event for version creation."""
        return VisualizationEvent(
            type="versionCreated",
            ui={
                "nodeId": context_id,
                "color": "gray",
                "animate": False,
                "effect": "snapshot"
            },
            data={
                "contextId": context_id,
                "versionId": version_id,
                "fragmentCount": fragment_count
            }
        )


# Event type mapping for easy reference
EVENT_TYPES = {
    "contextInitialized": ContextInitializedEvent,
    "relaySent": RelaySentEvent,
    "relayReceived": RelayReceivedEvent,
    "contextMerged": ContextMergedEvent,
    "contextPruned": ContextPrunedEvent,
    "versionCreated": VersionCreatedEvent,
}