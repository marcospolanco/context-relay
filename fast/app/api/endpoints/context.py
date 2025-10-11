"""Context operation endpoints."""

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...models.context import (
    ContextPacket,
    InitializeContextRequest,
    InitializeContextResponse,
    RelayRequest,
    RelayResponse,
    MergeRequest,
    MergeResponse,
    PruneRequest,
    PruneResponse,
    VersionRequest,
    VersionResponse,
    GetContextResponse,
    ListVersionsResponse
)
from ...models.shared import (
    DecisionTrace,
    ConflictResolution,
    PruningStrategy
)
from ...models.events import (
    ContextInitializedEvent,
    RelaySentEvent,
    RelayReceivedEvent,
    ContextMergedEvent,
    ContextPrunedEvent,
    VersionCreatedEvent
)
from ...services.mock_data import MockDataService
from ...core.events import event_handler

router = APIRouter(prefix="/context", tags=["context"])
mock_service = MockDataService()

# In-memory storage for mock contexts (in Phase 1)
_context_storage: Dict[str, ContextPacket] = {}
_context_versions: Dict[str, List[Dict[str, Any]]] = {}


@router.post("/initialize", response_model=InitializeContextResponse, status_code=status.HTTP_201_CREATED)
async def initialize_context(request: InitializeContextRequest) -> InitializeContextResponse:
    """Initialize a new context packet."""
    try:
        # Create new context
        context = ContextPacket(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            fragments=request.initial_fragments or [],
            metadata=request.metadata
        )

        # Store in memory
        _context_storage[context.id] = context

        # Create decision trace
        decision_trace = DecisionTrace(
            operation="initialize_context",
            context_id=context.id,
            decision="context_created",
            reasoning=f"Initialized context with {len(context.fragments)} fragments for session {request.session_id}",
            affected_fragments=[f.id for f in context.fragments]
        )

        # Emit event
        event = ContextInitializedEvent(
            context_id=context.id,
            session_id=request.session_id,
            fragment_count=len(context.fragments)
        )
        await event_handler.emit_event(event)

        return InitializeContextResponse(
            context=context,
            success=True,
            message=f"Context {context.id} initialized successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize context: {str(e)}"
        )


@router.post("/relay", response_model=RelayResponse)
async def relay_context(request: RelayRequest) -> RelayResponse:
    """Relay context fragments between agents."""
    try:
        # Get source context
        if request.context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {request.context_id} not found"
            )

        context = _context_storage[request.context_id]

        # Detect conflicts (mock implementation)
        conflicts_detected = []
        for new_fragment in request.delta_fragments:
            for existing_fragment in context.fragments:
                # Simple conflict detection based on content similarity
                if new_fragment.content[:50] == existing_fragment.content[:50] and new_fragment.id != existing_fragment.id:
                    conflicts_detected.append(new_fragment.id)

        # Apply conflict resolution
        added_fragments = []
        for fragment in request.delta_fragments:
            if fragment.id not in conflicts_detected or request.conflict_resolution != ConflictResolution.UNION:
                context.add_fragment(fragment)
                added_fragments.append(fragment.id)

        # Create decision trace
        decision_trace = DecisionTrace(
            operation="relay_context",
            context_id=request.context_id,
            decision=f"relayed_{len(added_fragments)}_fragments",
            reasoning=f"Relayed {len(request.delta_fragments)} fragments from {request.from_agent} to {request.to_agent} using {request.conflict_resolution} strategy",
            affected_fragments=added_fragments
        )

        # Emit events
        sent_event = RelaySentEvent(
            context_id=request.context_id,
            from_agent=request.from_agent.value,
            to_agent=request.to_agent.value,
            fragment_count=len(request.delta_fragments)
        )
        await event_handler.emit_event(sent_event)

        received_event = RelayReceivedEvent(
            context_id=request.context_id,
            from_agent=request.from_agent.value,
            to_agent=request.to_agent.value,
            accepted_fragments=len(added_fragments),
            rejected_fragments=len(conflicts_detected),
            conflicts=conflicts_detected
        )
        await event_handler.emit_event(received_event)

        return RelayResponse(
            success=True,
            context=context,
            decision_trace=decision_trace,
            conflicts_detected=conflicts_detected,
            message=f"Relayed {len(added_fragments)} fragments from {request.from_agent} to {request.to_agent}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to relay context: {str(e)}"
        )


@router.post("/merge", response_model=MergeResponse)
async def merge_contexts(request: MergeRequest) -> MergeResponse:
    """Merge multiple contexts."""
    try:
        # Validate source contexts exist
        missing_contexts = [ctx_id for ctx_id in request.context_ids if ctx_id not in _context_storage]
        if missing_contexts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contexts not found: {missing_contexts}"
            )

        source_contexts = [_context_storage[ctx_id] for ctx_id in request.context_ids]

        # Create merged context
        all_fragments = []
        conflicts_resolved = []

        for context in source_contexts:
            for fragment in context.fragments:
                # Check for conflicts with existing fragments
                existing_fragments = [f.id for f in all_fragments if f.content[:50] == fragment.content[:50]]
                if existing_fragments:
                    if request.merge_strategy == ConflictResolution.OVERWRITE:
                        # Remove existing fragment with same content
                        all_fragments = [f for f in all_fragments if f.id not in existing_fragments]
                        all_fragments.append(fragment)
                        conflicts_resolved.extend(existing_fragments)
                    elif request.merge_strategy == ConflictResolution.UNION:
                        all_fragments.append(fragment)
                    else:
                        # Skip duplicate for semantic similarity (mock implementation)
                        continue
                else:
                    all_fragments.append(fragment)

        merged_context = ContextPacket(
            id=request.target_context_id or str(uuid.uuid4()),
            session_id=f"merged-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            fragments=all_fragments,
            metadata={
                "merged_from": request.context_ids,
                "merge_strategy": request.merge_strategy.value,
                **request.metadata
            }
        )

        # Store merged context
        _context_storage[merged_context.id] = merged_context

        # Create decision trace
        decision_trace = DecisionTrace(
            operation="merge_contexts",
            context_id=merged_context.id,
            decision=f"merged_{len(source_contexts)}_contexts",
            reasoning=f"Merged {len(source_contexts)} contexts using {request.merge_strategy} strategy",
            affected_fragments=[f.id for f in merged_context.fragments]
        )

        # Emit event
        event = ContextMergedEvent(
            context_id=merged_context.id,
            source_context_ids=request.context_ids,
            merged_fragment_count=len(merged_context.fragments),
            conflict_count=len(conflicts_resolved)
        )
        await event_handler.emit_event(event)

        return MergeResponse(
            success=True,
            merged_context=merged_context,
            decision_trace=decision_trace,
            source_contexts=request.context_ids,
            conflicts_resolved=conflicts_resolved,
            message=f"Merged {len(source_contexts)} contexts into {merged_context.id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge contexts: {str(e)}"
        )


@router.post("/prune", response_model=PruneResponse)
async def prune_context(request: PruneRequest) -> PruneResponse:
    """Prune context fragments based on strategy."""
    try:
        if request.context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {request.context_id} not found"
            )

        context = _context_storage[request.context_id]
        original_count = len(context.fragments)

        # Apply pruning strategy
        if request.strategy == PruningStrategy.RECENCY:
            # Keep most recent fragments
            sorted_fragments = sorted(context.fragments, key=lambda f: f.timestamp, reverse=True)
            max_keep = request.max_fragments or 10
            context.fragments = sorted_fragments[:max_keep]

        elif request.strategy == PruningStrategy.IMPORTANCE_BASED:
            # Keep fragments with highest importance scores
            threshold = request.importance_threshold or 0.5
            context.fragments = [f for f in context.fragments if f.importance_score >= threshold]

        elif request.strategy == PruningStrategy.SIZE_LIMIT:
            # Simple size limit
            max_fragments = request.max_fragments or 5
            context.fragments = context.fragments[:max_fragments]

        # Determine removed fragments
        removed_fragment_ids = []
        if len(context.fragments) < original_count:
            # This is a simplified approach - in reality, you'd track which specific fragments were removed
            removed_count = original_count - len(context.fragments)
            removed_fragment_ids = [f"removed-{i}" for i in range(removed_count)]

        # Create decision trace
        decision_trace = DecisionTrace(
            operation="prune_context",
            context_id=request.context_id,
            decision=f"pruned_{original_count - len(context.fragments)}_fragments",
            reasoning=f"Applied {request.strategy} pruning strategy to reduce from {original_count} to {len(context.fragments)} fragments",
            affected_fragments=removed_fragment_ids
        )

        # Emit event
        event = ContextPrunedEvent(
            context_id=request.context_id,
            original_count=original_count,
            remaining_count=len(context.fragments),
            pruning_strategy=request.strategy.value
        )
        await event_handler.emit_event(event)

        return PruneResponse(
            success=True,
            context=context,
            decision_trace=decision_trace,
            removed_fragments=removed_fragment_ids,
            fragment_count_before=original_count,
            fragment_count_after=len(context.fragments),
            message=f"Pruned context from {original_count} to {len(context.fragments)} fragments using {request.strategy} strategy"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prune context: {str(e)}"
        )


@router.post("/{context_id}/version", response_model=VersionResponse)
async def create_version(context_id: str, request: VersionRequest) -> VersionResponse:
    """Create a new version of a context."""
    try:
        if context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        context = _context_storage[context_id]
        previous_version = context.version

        # Increment version
        context.version += 1
        context.updated_at = datetime.utcnow()

        # Store version info
        version_info = {
            "version_id": str(uuid.uuid4()),
            "context_id": context_id,
            "version_number": context.version,
            "timestamp": context.updated_at.isoformat(),
            "metadata": request.version_metadata,
            "snapshot": context.model_dump()
        }

        if context_id not in _context_versions:
            _context_versions[context_id] = []
        _context_versions[context_id].append(version_info)

        # Create decision trace
        decision_trace = DecisionTrace(
            operation="create_version",
            context_id=context_id,
            decision=f"version_{context.version}_created",
            reasoning=f"Created version {context.version} with {len(context.fragments)} fragments",
            affected_fragments=[f.id for f in context.fragments]
        )

        # Emit event
        event = VersionCreatedEvent(
            context_id=context_id,
            version_id=version_info["version_id"],
            version_label=request.version_metadata.get("label"),
            fragment_count=len(context.fragments)
        )
        await event_handler.emit_event(event)

        return VersionResponse(
            success=True,
            context=context,
            previous_version=previous_version,
            new_version=context.version,
            message=f"Created version {context.version} for context {context_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create version: {str(e)}"
        )


@router.get("/{context_id}", response_model=GetContextResponse)
async def get_context(context_id: str) -> GetContextResponse:
    """Get a specific context."""
    try:
        context = _context_storage.get(context_id)
        if not context:
            return GetContextResponse(
                context=None,
                success=False,
                message=f"Context {context_id} not found"
            )

        return GetContextResponse(
            context=context,
            success=True,
            message=f"Retrieved context {context_id}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )


@router.get("/{context_id}/versions", response_model=ListVersionsResponse)
async def list_versions(context_id: str) -> ListVersionsResponse:
    """List all versions of a context."""
    try:
        if context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        context = _context_storage[context_id]
        versions = _context_versions.get(context_id, [])

        return ListVersionsResponse(
            versions=versions,
            current_version=context.version,
            success=True,
            message=f"Retrieved {len(versions)} versions for context {context_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}"
        )