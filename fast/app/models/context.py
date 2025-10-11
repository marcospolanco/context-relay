from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class ContextFragment(BaseModel):
    """A single fragment of context information."""
    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: Any  # JSON representing fact/summary/outline piece
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    """Main context packet document."""
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    fragments: List[ContextFragment] = Field(default_factory=list)
    decision_trace: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=0)


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


class VersionInfo(BaseModel):
    """Information about a context version."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: Optional[str] = None


# SSE Event Models
class EventPayload(BaseModel):
    class Config:
        extra = "allow"  # Allow additional fields for different event types


class SSEEvent(BaseModel):
    type: str
    payload: EventPayload
