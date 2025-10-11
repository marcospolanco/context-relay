from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from beanie import Document
from datetime import datetime
from uuid import uuid4


class ContextFragment(BaseModel):
    """A single fragment of context information."""
    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: Any  # JSON representing fact/summary/outline piece
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextPacket(Document):
    """Main context packet document stored in MongoDB."""
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    fragments: List[ContextFragment] = Field(default_factory=list)
    decision_trace: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=0)

    class Settings:
        name = "context_packets"  # MongoDB collection name


class ContextDelta(BaseModel):
    """Changes to be applied to a context."""
    new_fragments: List[ContextFragment] = Field(default_factory=list)
    removed_fragment_ids: List[str] = Field(default_factory=list)
    decision_updates: List[Dict[str, Any]] = Field(default_factory=list)


class InitializeRequest(BaseModel):
    """Request to initialize a new context."""
    session_id: str
    initial_input: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InitializeResponse(BaseModel):
    """Response after initializing a context."""
    context_id: str
    context_packet: ContextPacket


class RelayRequest(BaseModel):
    """Request to relay context between agents."""
    from_agent: str
    to_agent: str
    context_id: str
    delta: ContextDelta


class RelayResponse(BaseModel):
    """Response after relaying context."""
    context_packet: ContextPacket
    conflicts: Optional[List[str]] = None


class MergeRequest(BaseModel):
    """Request to merge multiple contexts."""
    context_ids: List[str]
    merge_strategy: str = Field(default="union")  # "union", "overwrite", "semantic_similarity"


class MergeResponse(BaseModel):
    """Response after merging contexts."""
    merged_context: ContextPacket
    conflict_report: Optional[List[str]] = None


class PruneRequest(BaseModel):
    """Request to prune a context."""
    context_id: str
    pruning_strategy: str  # "recency", "semantic_diversity", "importance"
    budget: int  # Maximum number of fragments to keep


class PruneResponse(BaseModel):
    """Response after pruning context."""
    pruned_context: ContextPacket


class VersionRequest(BaseModel):
    """Request to create a version snapshot."""
    context_id: str
    version_label: Optional[str] = None


class VersionInfo(Document):
    """Information about a context version stored in MongoDB."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: Optional[str] = None
    snapshot: Optional[Dict[str, Any]] = None  # Store the full context snapshot

    class Settings:
        name = "context_versions"  # MongoDB collection name


# SSE Event Models
class EventPayload(BaseModel):
    class Config:
        extra = "allow"  # Allow additional fields for different event types


class SSEEvent(BaseModel):
    type: str
    payload: EventPayload
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Visualization-specific event payloads for frontend
class VisualizationEvent(BaseModel):
    type: str
    ui: Dict[str, Any] = Field(default_factory=dict)


class RelaySentEvent(BaseModel):
    context_id: str
    from_agent: str
    to_agent: str
    fragment_count: int
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "sourceNode": "",
        "targetNode": "",
        "color": "blue",
        "animate": True
    })


class RelayReceivedEvent(BaseModel):
    context_id: str
    from_agent: str
    to_agent: str
    accepted_fragments: int
    rejected_fragments: int
    conflicts: List[str] = Field(default_factory=list)
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "sourceNode": "",
        "targetNode": "",
        "color": "green",
        "animate": True
    })


class ContextInitializedEvent(BaseModel):
    context_id: str
    session_id: str
    initial_fragment_count: int
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "nodeId": "",
        "color": "purple",
        "animate": True
    })


class ContextMergedEvent(BaseModel):
    context_id: str
    source_context_ids: List[str]
    merged_fragment_count: int
    conflict_count: int
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "sourceNodes": [],
        "targetNode": "",
        "color": "orange",
        "animate": True
    })


class ContextPrunedEvent(BaseModel):
    context_id: str
    original_fragment_count: int
    remaining_fragment_count: int
    pruning_strategy: str
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "nodeId": "",
        "color": "red",
        "animate": True
    })


class VersionCreatedEvent(BaseModel):
    context_id: str
    version_id: str
    version_label: Optional[str] = None
    fragment_count: int
    ui: Dict[str, Any] = Field(default_factory=lambda: {
        "nodeId": "",
        "color": "gray",
        "animate": False
    })
