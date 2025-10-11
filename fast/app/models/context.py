from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document
from datetime import datetime, timezone
from uuid import uuid4

from .shared import (
    ContextFragment as SharedContextFragment,
    ContextPacket as SharedContextPacket,
    DecisionTrace,
    ConflictResolution,
    PruningStrategy,
    AgentType,
    FragmentType
)


class ContextFragment(SharedContextFragment):
    """Enhanced context fragment with MongoDB support."""
    # Inherit all fields from shared schema
    pass


class ContextPacket(SharedContextPacket, Document):
    """Enhanced context packet with MongoDB support."""
    # Inherit all fields from shared schema and add MongoDB support

    class Settings:
        name = "context_packets"  # MongoDB collection name


class VersionInfo(Document):
    """Version information for context packets."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    version_number: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    label: Optional[str] = None
    snapshot: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "context_versions"


class ContextDelta(BaseModel):
    """Changes to be applied to a context."""
    new_fragments: List[ContextFragment] = Field(default_factory=list)
    removed_fragment_ids: List[str] = Field(default_factory=list)
    decision_updates: List[Dict[str, Any]] = Field(default_factory=list)


# API Request/Response Models
class InitializeContextRequest(BaseModel):
    """Request to initialize a new context.

    Test-suite compatibility: supports either `initial_input` (str|object)
    or `initial_fragments` (List[ContextFragment]).
    """
    model_config = ConfigDict(extra='allow')

    session_id: str = Field(..., description="Session identifier")
    initial_input: Optional[Any] = Field(None, description="Initial input as string or structured object")
    initial_fragments: Optional[List[ContextFragment]] = Field(None, description="Initial context fragments")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InitializeContextResponse(BaseModel):
    """Response for context initialization.

    For compatibility, the actual endpoint returns a dict with `context_id`
    and `context_packet`. We keep this model for OpenAPI completeness but do
    not enforce it at runtime.
    """
    model_config = ConfigDict(extra='allow')

    context: Optional[SharedContextPacket] = Field(None, description="Created context packet")
    context_id: Optional[str] = Field(None, description="Created context ID")
    success: bool = Field(True, description="Operation success status")
    message: str = Field(default="Context initialized successfully", description="Response message")


class RelayRequest(BaseModel):
    """Request to relay context between agents.

    Test-suite compatibility: accepts `delta` object containing
    `new_fragments`, `removed_fragment_ids`, `decision_updates`.
    """
    model_config = ConfigDict(extra='allow')

    context_id: str = Field(..., description="Context ID to relay")
    from_agent: AgentType | str = Field(..., description="Source agent")
    to_agent: AgentType | str = Field(..., description="Target agent")
    delta: Dict[str, Any] = Field(default_factory=dict, description="Delta payload (new/removals/updates)")
    conflict_resolution: ConflictResolution | str = Field(ConflictResolution.UNION, description="Conflict resolution strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional relay metadata")


class RelayResponse(BaseModel):
    """Response for context relay operation."""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(..., description="Operation success status")
    context: SharedContextPacket = Field(..., description="Updated context after relay")
    decision_trace: DecisionTrace = Field(..., description="Trace of decisions made")
    conflicts_detected: List[str] = Field(default_factory=list, description="IDs of conflicting fragments")
    message: str = Field(..., description="Response message")


class MergeRequest(BaseModel):
    """Request to merge multiple contexts."""
    model_config = ConfigDict(extra='forbid')

    context_ids: List[str] = Field(..., min_length=2, description="Context IDs to merge")
    target_context_id: Optional[str] = Field(None, description="Target context ID (creates new if None)")
    merge_strategy: ConflictResolution = Field(ConflictResolution.UNION, description="Merge strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional merge metadata")


class MergeResponse(BaseModel):
    """Response for context merge operation."""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(..., description="Operation success status")
    merged_context: SharedContextPacket = Field(..., description="Resulting merged context")
    decision_trace: DecisionTrace = Field(..., description="Trace of decisions made")
    source_contexts: List[str] = Field(..., description="IDs of merged source contexts")
    conflicts_resolved: List[str] = Field(default_factory=list, description="IDs of resolved conflicts")
    message: str = Field(..., description="Response message")


class PruneRequest(BaseModel):
    """Request to prune context fragments."""
    model_config = ConfigDict(extra='forbid')

    context_id: str = Field(..., description="Context ID to prune")
    strategy: PruningStrategy = Field(..., description="Pruning strategy")
    max_fragments: Optional[int] = Field(None, ge=1, description="Maximum number of fragments to keep")
    max_age_hours: Optional[int] = Field(None, ge=1, description="Maximum age in hours")
    importance_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional prune metadata")


class PruneResponse(BaseModel):
    """Response for context prune operation."""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(..., description="Operation success status")
    context: SharedContextPacket = Field(..., description="Context after pruning")
    decision_trace: DecisionTrace = Field(..., description="Trace of decisions made")
    removed_fragments: List[str] = Field(..., description="IDs of removed fragments")
    fragment_count_before: int = Field(..., description="Fragment count before pruning")
    fragment_count_after: int = Field(..., description="Fragment count after pruning")
    message: str = Field(..., description="Response message")


class VersionRequest(BaseModel):
    """Request to create a new context version."""
    model_config = ConfigDict(extra='forbid')

    context_id: str = Field(..., description="Context ID to version")
    version_metadata: Dict[str, Any] = Field(default_factory=dict, description="Version-specific metadata")


class VersionResponse(BaseModel):
    """Response for context version creation."""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(..., description="Operation success status")
    context: SharedContextPacket = Field(..., description="Context with new version")
    previous_version: int = Field(..., description="Previous version number")
    new_version: int = Field(..., description="New version number")
    message: str = Field(..., description="Response message")


class GetContextResponse(BaseModel):
    """Response for getting a specific context."""
    model_config = ConfigDict(extra='forbid')

    context: Optional[SharedContextPacket] = Field(None, description="Requested context")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class ListVersionsResponse(BaseModel):
    """Response for listing context versions."""
    model_config = ConfigDict(extra='forbid')

    versions: List[Dict[str, Any]] = Field(default_factory=list, description="Available versions")
    current_version: int = Field(..., description="Current version number")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(extra='forbid')

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Health check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, str] = Field(default_factory=dict, description="Component health status")
