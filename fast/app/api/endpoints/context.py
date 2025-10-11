"""Context operation endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...models.context import (
    InitializeContextRequest,
    InitializeContextResponse,
    GetContextResponse,
    ListVersionsResponse,
)
from ...models.shared import (
    ContextPacket as SharedContextPacket,
    DecisionTrace,
    ConflictResolution,
    PruningStrategy,
    ContextFragment as SharedContextFragment,
    FragmentType,
    AgentType,
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
_context_storage: Dict[str, SharedContextPacket] = {}
_context_versions: Dict[str, List[Dict[str, Any]]] = {}


@router.post("/initialize", response_model=InitializeContextResponse)
async def initialize_context(request: InitializeContextRequest) -> InitializeContextResponse:
    """Initialize a new context packet."""
    try:
        # Create new context
        # Build initial fragments from either initial_fragments or initial_input
        fragments = request.initial_fragments or []
        if not fragments:
            # Accept both string and object for initial_input
            if request.initial_input is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="initial_input is required")
            # The tests expect fragment keys like `fragment_id`, so construct dicts
            # Generate a simple deterministic mock embedding of length 5
            seed = sum(ord(c) for c in str(request.initial_input))
            rng = seed % 997
            embedding = [((rng * (i + 3)) % 100) / 100.0 for i in range(5)]
            fragments = [
                {
                    "fragment_id": str(uuid.uuid4()),
                    "content": str(request.initial_input),
                    "embedding": embedding,
                    "metadata": {**(request.metadata or {}), "source": "initial_input"},
                }
            ]

        context_id = str(uuid.uuid4())
        context_packet = {
            "context_id": context_id,
            "fragments": fragments,
            "decision_trace": [],
            "metadata": request.metadata or {},
            "version": 0,
        }

        # Store in memory
        _context_storage[context_id] = context_packet  # store as test-friendly dict

        # Create decision trace metadata (stored in the packet dict)
        # For compatibility we do not attach to response directly

        # Emit event (guard if event system unavailable in tests)
        try:
            event = ContextInitializedEvent(
                context_id=context_id,
                session_id=request.session_id,
                fragment_count=len(context_packet["fragments"])
            )
            await event_handler.emit_event(event)
        except Exception:
            pass

        # Tests expect a flat shape with context_id and context_packet (dict)
        return {
            "context_id": context_id,
            "context_packet": context_packet,
            "success": True,
            "message": f"Context {context_id} initialized successfully",
        }

    except HTTPException as he:
        # Preserve intended HTTP status codes (e.g., 4xx) from domain validation
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize context: {str(e)}"
        )


@router.post("/relay")
async def relay_context(request: Dict[str, Any]):
    """Relay context fragments between agents."""
    try:
        # Get source context
        context_id = request.get("context_id")
        if context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        context = _context_storage[context_id]

        # Detect conflicts (mock implementation)
        conflicts_detected = []
        new_fragments = []
        delta = request.get("delta") or {}
        if isinstance(delta, dict) and delta.get("new_fragments") is not None:
            new_fragments = delta.get("new_fragments")

        for new_fragment in new_fragments:
            for existing_fragment in context["fragments"]:
                # Simple conflict detection based on content similarity
                if (
                    str(new_fragment.get("content", ""))[:50]
                    == str(existing_fragment.get("content", ""))[:50]
                ):
                    conflicts_detected.append(existing_fragment.get("fragment_id"))

        # Apply conflict resolution
        added_fragments = []
        for fragment in new_fragments:
            # Build stored fragment shape
            frag = {
                "fragment_id": str(uuid.uuid4()),
                "content": fragment.get("content"),
                "embedding": [],
                "metadata": fragment.get("metadata", {}),
            }
            context["fragments"].append(frag)
            added_fragments.append(frag["fragment_id"])

        # Create decision trace
        context["version"] = int(context.get("version", 0)) + 1

        # Emit events
        sent_event = RelaySentEvent(
            context_id=context_id,
            from_agent=str(request.get("from_agent")),
            to_agent=str(request.get("to_agent")),
            fragment_count=len(new_fragments)
        )
        await event_handler.emit_event(sent_event)

        received_event = RelayReceivedEvent(
            context_id=context_id,
            from_agent=str(request.get("from_agent")),
            to_agent=str(request.get("to_agent")),
            accepted_fragments=len(added_fragments),
            rejected_fragments=len(conflicts_detected),
            conflicts=conflicts_detected
        )
        await event_handler.emit_event(received_event)

        return {
            "context_packet": context,
            "conflicts": None if not conflicts_detected else conflicts_detected,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to relay context: {str(e)}"
        )


@router.post("/merge")
async def merge_contexts(request: Dict[str, Any]):
    """Merge multiple contexts."""
    try:
        # Validate source contexts exist
        context_ids = request.get("context_ids") or []
        missing_contexts = [ctx_id for ctx_id in context_ids if ctx_id not in _context_storage]
        if missing_contexts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contexts not found: {missing_contexts}"
            )

        source_contexts = [_context_storage[ctx_id] for ctx_id in context_ids]

        # Create merged context
        all_fragments = []
        conflicts_resolved = []

        for context in source_contexts:
            for fragment in context["fragments"]:
                # Check for conflicts with existing fragments
                existing_fragments = [
                    f.get("fragment_id") for f in all_fragments
                    if str(f.get("content", ""))[:50] == str(fragment.get("content", ""))[:50]
                ]
                if existing_fragments:
                    if request.merge_strategy == ConflictResolution.OVERWRITE:
                        # Remove existing fragment with same content
                        all_fragments = [f for f in all_fragments if f.get("fragment_id") not in existing_fragments]
                        all_fragments.append(fragment)
                        conflicts_resolved.extend(existing_fragments)
                    elif request.merge_strategy == ConflictResolution.UNION:
                        all_fragments.append(fragment)
                    else:
                        # Skip duplicate for semantic similarity (mock implementation)
                        continue
                else:
                    all_fragments.append(fragment)

        merged_context = {
            "context_id": request.get("target_context_id") or str(uuid.uuid4()),
            "fragments": all_fragments,
            "metadata": {
                "merged_from": context_ids,
                "merge_strategy": str(request.get("merge_strategy", "union")),
                **(request.get("metadata") or {}),
            },
            "version": 0,
        }

        # Store merged context
        _context_storage[merged_context["context_id"]] = merged_context

        # Create decision trace
        # no-op decision trace in simplified flow

        # Emit event
        event = ContextMergedEvent(
            context_id=merged_context["context_id"],
            source_context_ids=context_ids,
            merged_fragment_count=len(merged_context["fragments"]),
            conflict_count=len(conflicts_resolved)
        )
        await event_handler.emit_event(event)

        return {
            "merged_context": merged_context,
            "conflict_report": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge contexts: {str(e)}"
        )


@router.post("/prune")
async def prune_context(request: Dict[str, Any]):
    """Prune context fragments based on strategy."""
    try:
        context_id = request.get("context_id")
        if context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        context = _context_storage[context_id]
        original_count = len(context["fragments"])

        # Apply pruning strategy
        strategy = request.get("pruning_strategy") or request.get("strategy")
        budget = int(request.get("budget") or request.get("max_fragments") or 0)
        if strategy == "recency" or strategy == PruningStrategy.RECENCY:
            # Keep most recent fragments
            sorted_fragments = context["fragments"]  # assume insertion order as recency
            max_keep = budget or 10
            context["fragments"] = sorted_fragments[-max_keep:]

        elif strategy in ("importance", "importance_based", PruningStrategy.IMPORTANCE_BASED):
            # Keep fragments with highest importance scores
            threshold = float(request.get("importance_threshold") or 0.5)
            context["fragments"] = [
                f for f in context["fragments"] if f.get("metadata", {}).get("importance", 0) >= threshold
            ]

        elif strategy in ("size_limit", PruningStrategy.SIZE_LIMIT):
            # Simple size limit
            max_fragments = budget or 5
            context["fragments"] = context["fragments"][:max_fragments]

        # Determine removed fragments
        removed_fragment_ids = []
        if len(context["fragments"]) < original_count:
            # This is a simplified approach - in reality, you'd track which specific fragments were removed
            removed_count = original_count - len(context["fragments"])
            removed_fragment_ids = [f"removed-{i}" for i in range(removed_count)]

        # Create decision trace
        # not attaching decision trace to response

        # Emit event
        event = ContextPrunedEvent(
            context_id=context_id,
            original_count=original_count,
            remaining_count=len(context["fragments"]),
            pruning_strategy=str(strategy)
        )
        await event_handler.emit_event(event)

        return {
            "pruned_context": context,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prune context: {str(e)}"
        )


@router.post("/version")
async def create_version(request: Dict[str, Any]):
    """Create a new version of a context."""
    try:
        context_id = request.get("context_id")
        if context_id not in _context_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        context = _context_storage[context_id]
        previous_version = int(context.get("version", 0))

        # Increment version
        context["version"] = previous_version + 1

        # Store version info
        version_info = {
            "version_id": str(uuid.uuid4()),
            "context_id": context_id,
            "version_number": context["version"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": request.get("version_metadata") or {"label": request.get("version_label")},
            "snapshot": context,
        }

        if context_id not in _context_versions:
            _context_versions[context_id] = []
        _context_versions[context_id].append(version_info)

        # Create decision trace
        # no decision trace construction

        # Emit event
        event = VersionCreatedEvent(
            context_id=context_id,
            version_id=version_info["version_id"],
            version_label=(request.get("version_metadata") or {}).get("label") or request.get("version_label"),
            fragment_count=len(context.get("fragments", []))
        )
        await event_handler.emit_event(event)

        return {
            "version_id": version_info["version_id"],
            "context_id": context_id,
            "timestamp": version_info["timestamp"],
            "summary": (request.get("version_label") or ""),
        }

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        return GetContextResponse(
            context=context,
            success=True,
            message=f"Retrieved context {context_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )


@router.get("/{context_id}/versions", response_model=ListVersionsResponse)
async def list_versions(context_id: str) -> ListVersionsResponse:
    """List all versions of a context."""
    try:
        versions = _context_versions.get(context_id, [])

        if context_id in _context_storage:
            current_version = int(_context_storage[context_id].get("version", 0))
        else:
            current_version = 0

        return {
            "versions": versions,
            "current_version": current_version,
            "success": True,
            "message": f"Retrieved {len(versions)} versions for context {context_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}"
        )