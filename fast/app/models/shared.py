"""Shared schema definitions for Context Relay System.

This module provides unified data structures that can be used across
FastAPI logic layer, CLI, and frontend components.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class AgentType(str, Enum):
    """Types of agents in the context relay system."""
    AI_ASSISTANT = "ai_assistant"
    HUMAN = "human"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"


class FragmentType(str, Enum):
    """Types of context fragments."""
    TEXT = "text"
    CODE = "code"
    DATA = "data"
    METADATA = "metadata"
    DECISION = "decision"


class ConflictResolution(str, Enum):
    """Strategies for resolving context conflicts."""
    UNION = "union"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    OVERWRITE = "overwrite"
    MERGE = "merge"


class PruningStrategy(str, Enum):
    """Strategies for pruning context fragments."""
    RECENCY = "recency"
    SEMANTIC_DIVERSITY = "semantic_diversity"
    IMPORTANCE_BASED = "importance_based"
    SIZE_LIMIT = "size_limit"


class ContextFragment(BaseModel):
    """Individual context piece with metadata."""
    model_config = ConfigDict(extra='forbid')

    id: str = Field(..., description="Unique fragment identifier")
    type: FragmentType = Field(..., description="Type of fragment content")
    content: str = Field(..., description="Fragment content")
    source_agent: AgentType = Field(..., description="Agent that created this fragment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic similarity")
    importance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance score for pruning")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional fragment metadata")
    tags: List[str] = Field(default_factory=list, description="Fragment tags for categorization")


class DecisionTrace(BaseModel):
    """Trace of decisions made during context operations."""
    model_config = ConfigDict(extra='forbid')

    operation: str = Field(..., description="Operation type")
    context_id: str = Field(..., description="Context ID involved")
    decision: str = Field(..., description="Decision made")
    reasoning: str = Field(..., description="Reasoning behind decision")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Decision timestamp")
    affected_fragments: List[str] = Field(default_factory=list, description="IDs of affected fragments")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")


class ContextPacket(BaseModel):
    """Core context container with fragments."""
    model_config = ConfigDict(extra='forbid')

    id: str = Field(..., description="Unique context identifier")
    session_id: str = Field(..., description="Session identifier")
    fragments: List[ContextFragment] = Field(default_factory=list, description="Context fragments")
    version: int = Field(default=0, description="Context version number")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")
    # Provide a decision trace field for compatibility with tests
    decision_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Decision trace entries")

    def add_fragment(self, fragment: ContextFragment) -> None:
        """Add a fragment to the context."""
        self.fragments.append(fragment)
        self.updated_at = datetime.now(timezone.utc)

    def remove_fragment(self, fragment_id: str) -> bool:
        """Remove a fragment by ID."""
        original_length = len(self.fragments)
        self.fragments = [f for f in self.fragments if f.id != fragment_id]
        if len(self.fragments) < original_length:
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def get_fragment_by_id(self, fragment_id: str) -> Optional[ContextFragment]:
        """Get a fragment by ID."""
        for fragment in self.fragments:
            if fragment.id == fragment_id:
                return fragment
        return None


class VisualizationEvent(BaseModel):
    """UI-friendly event payload for frontend visualization."""
    model_config = ConfigDict(extra='forbid')

    type: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    ui: Dict[str, Any] = Field(..., description="UI-specific data for visualization")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")


# Export schema for JSON generation
def get_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all model schemas for JSON export."""
    return {
        "ContextFragment": ContextFragment.model_json_schema(),
        "ContextPacket": ContextPacket.model_json_schema(),
        "DecisionTrace": DecisionTrace.model_json_schema(),
        "VisualizationEvent": VisualizationEvent.model_json_schema(),
        "AgentType": {"type": "string", "enum": [e.value for e in AgentType]},
        "FragmentType": {"type": "string", "enum": [e.value for e in FragmentType]},
        "ConflictResolution": {"type": "string", "enum": [e.value for e in ConflictResolution]},
        "PruningStrategy": {"type": "string", "enum": [e.value for e in PruningStrategy]},
    }