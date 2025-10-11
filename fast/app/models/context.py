from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class ContextFragment(BaseModel):
    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: Any
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    fragments: List[ContextFragment] = Field(default_factory=list)
    decision_trace: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=0)


class ContextDelta(BaseModel):
    new_fragments: List[ContextFragment] = Field(default_factory=list)
    removed_fragment_ids: List[str] = Field(default_factory=list)
    decision_updates: List[Dict[str, Any]] = Field(default_factory=list)


class RelayRequest(BaseModel):
    from_agent: str
    to_agent: str
    context_id: str
    delta: ContextDelta


class RelayResponse(BaseModel):
    context_packet: ContextPacket
    conflicts: Optional[List[str]] = None


class MergeRequest(BaseModel):
    context_ids: List[str]
    merge_strategy: str = Field(default="union")


class MergeResponse(BaseModel):
    merged_context: ContextPacket
    conflict_report: Optional[List[str]] = None


class PruneRequest(BaseModel):
    context_id: str
    pruning_strategy: str
    budget: int


class PruneResponse(BaseModel):
    pruned_context: ContextPacket


class VersionRequest(BaseModel):
    context_id: str
    version_label: Optional[str] = None


class VersionInfo(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: Optional[str] = None


class InitializeRequest(BaseModel):
    session_id: str
    initial_input: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InitializeResponse(BaseModel):
    context_id: str
    context_packet: ContextPacket


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