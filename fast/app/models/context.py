"""Context-related data models for MongoDB using Beanie ODM."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from beanie import Document
from pydantic import BaseModel, Field
from uuid import uuid4


class ContextFragment(BaseModel):
    """A single fragment of context information."""
    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: Any  # JSON representing fact/summary/outline piece
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContextPacket(Document):
    """Main context packet document stored in MongoDB."""
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    fragments: List[ContextFragment] = Field(default_factory=list)
    decision_trace: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "contexts"  # Collection name in MongoDB
        indexes = [
            "context_id",
            "version",
            "created_at",
        ]
        # Configure Beanie to use string representation for MongoDB ObjectId
        use_state_management = True
        validate_on_save = True

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
        "arbitrary_types_allowed": True
    }


class ContextDelta(BaseModel):
    """Changes to be applied to a context."""
    new_fragments: List[ContextFragment] = Field(default_factory=list)
    removed_fragment_ids: List[str] = Field(default_factory=list)
    decision_updates: List[Dict[str, Any]] = Field(default_factory=list)


# Request/Response Models

class InitializeRequest(BaseModel):
    """Request to initialize a new context."""
    session_id: str
    initial_input: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InitializeResponse(BaseModel):
    """Response after initializing a context."""
    context_id: str
    context_packet: Dict[str, Any]  # Serialized ContextPacket


class RelayRequest(BaseModel):
    """Request to relay context between agents."""
    from_agent: str
    to_agent: str
    context_id: str
    delta: ContextDelta


class RelayResponse(BaseModel):
    """Response after relaying context."""
    context_packet: Dict[str, Any]  # Serialized ContextPacket
    conflicts: Optional[List[str]] = None  # List of conflicting fragment IDs


class MergeRequest(BaseModel):
    """Request to merge multiple contexts."""
    context_ids: List[str]
    merge_strategy: str  # "union", "overwrite", "semantic_similarity"


class MergeResponse(BaseModel):
    """Response after merging contexts."""
    merged_context: Dict[str, Any]  # Serialized ContextPacket
    conflict_report: Optional[List[str]] = None


class PruneRequest(BaseModel):
    """Request to prune a context."""
    context_id: str
    pruning_strategy: str  # "recency", "semantic_diversity", "importance"
    budget: int  # Maximum number of fragments to keep


class PruneResponse(BaseModel):
    """Response after pruning context."""
    pruned_context: Dict[str, Any]  # Serialized ContextPacket


class VersionRequest(BaseModel):
    """Request to create a version snapshot."""
    context_id: str
    version_label: str = ""  # Optional human-readable label


class VersionInfo(BaseModel):
    """Information about a context version."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    summary: Optional[str] = None
    version_number: int = 0


class ContextVersion(Document):
    """Snapshot of a context at a specific version."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    version_number: int
    snapshot: Dict[str, Any]  # Full context state at this version
    summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "context_versions"
        indexes = [
            "version_id",
            "context_id",
            "version_number",
        ]
