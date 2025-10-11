"""Context operation endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
from ...services.mongodb_service import get_mongodb_service
from ...services.voyage_embedding_service import get_voyage_service
from ...core.events import event_handler

router = APIRouter(prefix="/context", tags=["context"])
mock_service = MockDataService()
mongodb_service = get_mongodb_service()
voyage_service = get_voyage_service()

# In-memory storage for fallback (Phase 1)
_context_storage: Dict[str, SharedContextPacket] = {}
_context_versions: Dict[str, List[Dict[str, Any]]] = {}

# Global flag to determine storage mode
_mongodb_enabled = False


def is_mongodb_enabled() -> bool:
    """Check if MongoDB is available and enabled."""
    try:
        # Check if MongoDB service is connected
        return mongodb_service.connected and mongodb_service is not None
    except Exception:
        return False


async def store_context_packet(context_id: str, context_packet: Dict[str, Any]):
    """Store context packet using available storage method."""
    global _mongodb_enabled

    if is_mongodb_enabled() and not _mongodb_enabled:
        # Try to switch to MongoDB mode
        try:
            # Convert dict to MongoDB ContextPacket model
            from ...models.context import ContextPacket, ContextFragment
            from datetime import datetime, timezone

            # Convert fragments to ContextFragment objects
            fragments = []
            for frag_data in context_packet.get("fragments", []):
                fragment = ContextFragment(
                    id=frag_data.get("fragment_id") or frag_data.get("id"),
                    type=FragmentType.TEXT,  # Default to TEXT type
                    content=frag_data.get("content"),
                    source_agent=AgentType.SYSTEM,  # Default to SYSTEM agent
                    embedding=frag_data.get("embedding", []),
                    metadata=frag_data.get("metadata", {})
                )
                fragments.append(fragment)

            mongodb_context = ContextPacket(
                id=context_id,
                session_id=context_packet.get("session_id", "default-session"),
                fragments=fragments,
                decision_trace=context_packet.get("decision_trace", []),
                metadata=context_packet.get("metadata", {}),
                version=context_packet.get("version", 0)
            )

            await mongodb_service.store_context(mongodb_context)
            _mongodb_enabled = True
            return
        except Exception as e:
            print(f"Failed to switch to MongoDB, staying in-memory: {e}")
            _mongodb_enabled = False

    if _mongodb_enabled:
        # Continue using MongoDB
        try:
            from ...models.context import ContextPacket, ContextFragment
            from datetime import datetime, timezone

            # Convert and store to MongoDB
            fragments = []
            for frag_data in context_packet.get("fragments", []):
                fragment = ContextFragment(
                    id=frag_data.get("fragment_id") or frag_data.get("id"),
                    type=FragmentType.TEXT,  # Default to TEXT type
                    content=frag_data.get("content"),
                    source_agent=AgentType.SYSTEM,  # Default to SYSTEM agent
                    embedding=frag_data.get("embedding", []),
                    metadata=frag_data.get("metadata", {})
                )
                fragments.append(fragment)

            mongodb_context = ContextPacket(
                id=context_id,
                session_id=context_packet.get("session_id", "default-session"),
                fragments=fragments,
                decision_trace=context_packet.get("decision_trace", []),
                metadata=context_packet.get("metadata", {}),
                version=context_packet.get("version", 0)
            )

            await mongodb_service.store_context(mongodb_context)
            return
        except Exception as e:
            print(f"MongoDB storage failed, falling back to memory: {e}")
            _mongodb_enabled = False

    # Use in-memory storage
    _context_storage[context_id] = context_packet


async def get_context_packet(context_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve context packet using available storage method."""
    global _mongodb_enabled

    if is_mongodb_enabled() or _mongodb_enabled:
        try:
            # Try MongoDB first
            mongodb_context = await mongodb_service.get_context(context_id)
            if mongodb_context:
                _mongodb_enabled = True
                # Convert MongoDB model to dict
                return {
                    "context_id": mongodb_context.id,
                    "fragments": [f.model_dump(mode="json") for f in mongodb_context.fragments],
                    "decision_trace": mongodb_context.decision_trace,
                    "metadata": mongodb_context.metadata,
                    "version": mongodb_context.version,
                    "session_id": mongodb_context.session_id
                }
        except Exception as e:
            print(f"MongoDB retrieval failed, trying memory: {e}")
            _mongodb_enabled = False

    # Try in-memory storage
    return _context_storage.get(context_id)


async def update_context_packet(context_id: str, context_packet: Dict[str, Any]):
    """Update context packet using available storage method."""
    global _mongodb_enabled

    if _mongodb_enabled:
        try:
            # Update in MongoDB
            from ...models.context import ContextPacket, ContextFragment

            # Convert fragments to ContextFragment objects
            fragments = []
            for frag_data in context_packet.get("fragments", []):
                fragment = ContextFragment(
                    id=frag_data.get("fragment_id") or frag_data.get("id"),
                    type=FragmentType.TEXT,  # Default to TEXT type
                    content=frag_data.get("content"),
                    source_agent=AgentType.SYSTEM,  # Default to SYSTEM agent
                    embedding=frag_data.get("embedding", []),
                    metadata=frag_data.get("metadata", {})
                )
                fragments.append(fragment)

            mongodb_context = ContextPacket(
                id=context_id,
                session_id=context_packet.get("session_id", "default-session"),
                fragments=fragments,
                decision_trace=context_packet.get("decision_trace", []),
                metadata=context_packet.get("metadata", {}),
                version=context_packet.get("version", 0)
            )

            await mongodb_service.update_context(mongodb_context)
            return
        except Exception as e:
            print(f"MongoDB update failed, falling back to memory: {e}")
            _mongodb_enabled = False

    # Update in-memory storage
    _context_storage[context_id] = context_packet


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

            # Generate real embedding using Voyage service
            try:
                embedding = await voyage_service.generate_embedding(str(request.initial_input))
            except Exception as e:
                # Fallback to mock embedding if Voyage service fails
                print(f"Failed to generate embedding with Voyage service, using fallback: {e}")
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
            "session_id": request.session_id,
            "fragments": fragments,
            "decision_trace": [],
            "metadata": request.metadata or {},
            "version": 0,
        }

        # Store using available storage method (MongoDB or in-memory)
        await store_context_packet(context_id, context_packet)

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

    except HTTPException:
        raise
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
        context = await get_context_packet(context_id)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )

        # Detect conflicts using real semantic similarity
        conflicts_detected = []
        new_fragments = []
        delta = request.get("delta") or {}
        if isinstance(delta, dict) and delta.get("new_fragments") is not None:
            new_fragments = delta.get("new_fragments")

        # Generate embeddings for new fragments and detect conflicts
        for new_fragment in new_fragments:
            new_content = str(new_fragment.get("content", ""))

            # Generate embedding for new fragment
            try:
                new_embedding = await voyage_service.generate_embedding(new_content)
            except Exception as e:
                # Fallback to mock embedding if Voyage service fails
                print(f"Failed to generate embedding for new fragment, using fallback: {e}")
                seed = sum(ord(c) for c in new_content)
                rng = seed % 997
                new_embedding = [((rng * (i + 3)) % 100) / 100.0 for i in range(5)]

            # Check for conflicts with existing fragments using semantic similarity
            conflict_threshold = 0.85  # High threshold for conflict detection

            for existing_fragment in context["fragments"]:
                existing_content = str(existing_fragment.get("content", ""))
                existing_embedding = existing_fragment.get("embedding", [])

                if existing_embedding:
                    try:
                        similarity = await voyage_service.compute_similarity(new_embedding, existing_embedding)
                        if similarity >= conflict_threshold:
                            conflicts_detected.append(existing_fragment.get("fragment_id"))
                    except Exception as e:
                        print(f"Failed to compute similarity, using fallback content comparison: {e}")
                        # Fallback to simple content comparison
                        if new_content[:50] == existing_content[:50]:
                            conflicts_detected.append(existing_fragment.get("fragment_id"))

        # Apply conflict resolution and add new fragments
        added_fragments = []
        for fragment in new_fragments:
            fragment_content = fragment.get("content")

            # Generate embedding for this fragment
            try:
                fragment_embedding = await voyage_service.generate_embedding(str(fragment_content))
            except Exception as e:
                # Fallback to mock embedding if Voyage service fails
                print(f"Failed to generate embedding for fragment storage, using fallback: {e}")
                seed = sum(ord(c) for c in str(fragment_content))
                rng = seed % 997
                fragment_embedding = [((rng * (i + 3)) % 100) / 100.0 for i in range(5)]

            # Build stored fragment shape
            frag = {
                "fragment_id": str(uuid.uuid4()),
                "content": fragment_content,
                "embedding": fragment_embedding,
                "metadata": fragment.get("metadata", {}),
            }
            context["fragments"].append(frag)
            added_fragments.append(frag["fragment_id"])

        # Create decision trace
        context["version"] = int(context.get("version", 0)) + 1

        # Save updated context
        await update_context_packet(context_id, context)

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

        # Check for minimum number of contexts
        if len(context_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 contexts are required for merging"
            )

        # Check if all contexts exist
        missing_contexts = []
        source_contexts = []
        for ctx_id in context_ids:
            context = await get_context_packet(ctx_id)
            if not context:
                missing_contexts.append(ctx_id)
            else:
                source_contexts.append(context)

        if missing_contexts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contexts not found: {missing_contexts}"
            )

        # Create merged context using real semantic similarity
        all_fragments = []
        conflicts_resolved = []
        similarity_threshold = 0.8  # Threshold for considering fragments as duplicates

        for context in source_contexts:
            for fragment in context["fragments"]:
                fragment_content = str(fragment.get("content", ""))
                fragment_embedding = fragment.get("embedding", [])

                # Check for conflicts with existing fragments using semantic similarity
                conflicting_fragment_ids = []

                for existing_fragment in all_fragments:
                    existing_content = str(existing_fragment.get("content", ""))
                    existing_embedding = existing_fragment.get("embedding", [])

                    if fragment_embedding and existing_embedding:
                        try:
                            similarity = await voyage_service.compute_similarity(fragment_embedding, existing_embedding)
                            if similarity >= similarity_threshold:
                                conflicting_fragment_ids.append(existing_fragment.get("fragment_id"))
                        except Exception as e:
                            print(f"Failed to compute similarity during merge, using fallback content comparison: {e}")
                            # Fallback to simple content comparison
                            if fragment_content[:50] == existing_content[:50]:
                                conflicting_fragment_ids.append(existing_fragment.get("fragment_id"))
                    else:
                        # Fallback if embeddings are not available
                        if fragment_content[:50] == existing_content[:50]:
                            conflicting_fragment_ids.append(existing_fragment.get("fragment_id"))

                if conflicting_fragment_ids:
                    # Handle conflicts based on merge strategy
                    merge_strategy = request.get("merge_strategy", "union")
                    if merge_strategy == ConflictResolution.OVERWRITE or merge_strategy == "overwrite":
                        # Remove existing fragments and add the new one
                        all_fragments = [f for f in all_fragments if f.get("fragment_id") not in conflicting_fragment_ids]
                        all_fragments.append(fragment)
                        conflicts_resolved.extend(conflicting_fragment_ids)
                    elif merge_strategy == ConflictResolution.UNION or merge_strategy == "union":
                        # Keep both fragments (union approach)
                        all_fragments.append(fragment)
                    else:
                        # Skip duplicate (default behavior)
                        continue
                else:
                    # No conflicts, add the fragment
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
        await store_context_packet(merged_context["context_id"], merged_context)

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
        context = await get_context_packet(context_id)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )
        original_count = len(context["fragments"])

        # Apply pruning strategy using semantic analysis where appropriate
        strategy = request.get("pruning_strategy") or request.get("strategy")
        budget = int(request.get("budget") or request.get("max_fragments") or 0)

        if strategy == "recency" or strategy == PruningStrategy.RECENCY:
            # Keep most recent fragments
            sorted_fragments = context["fragments"]  # assume insertion order as recency
            max_keep = budget or 10
            context["fragments"] = sorted_fragments[-max_keep:]

        elif strategy in ("importance", "importance_based", PruningStrategy.IMPORTANCE_BASED):
            # Enhanced importance-based pruning using semantic diversity
            threshold = float(request.get("importance_threshold") or 0.5)
            max_fragments = budget or 5

            # First filter by explicit importance scores if available
            fragments_by_importance = [
                f for f in context["fragments"]
                if f.get("metadata", {}).get("importance", 0) >= threshold
            ]

            if not fragments_by_importance:
                # If no fragments meet importance threshold, use semantic diversity to select
                fragments_by_importance = context["fragments"]

            if len(fragments_by_importance) <= max_fragments:
                # If we're already under the limit, keep all qualifying fragments
                context["fragments"] = fragments_by_importance
            else:
                # Use semantic diversity to select diverse fragments
                try:
                    selected_fragments = []
                    remaining_fragments = fragments_by_importance.copy()

                    # Add first fragment
                    selected_fragments.append(remaining_fragments.pop(0))

                    # Select fragments that are semantically diverse
                    while len(selected_fragments) < max_fragments and remaining_fragments:
                        best_fragment = None
                        min_max_similarity = float('inf')

                        for candidate in remaining_fragments:
                            candidate_embedding = candidate.get("embedding", [])
                            if not candidate_embedding:
                                # Skip fragments without embeddings
                                continue

                            # Find maximum similarity to already selected fragments
                            max_similarity = 0
                            for selected in selected_fragments:
                                selected_embedding = selected.get("embedding", [])
                                if selected_embedding:
                                    similarity = await voyage_service.compute_similarity(
                                        candidate_embedding, selected_embedding
                                    )
                                    max_similarity = max(max_similarity, similarity)

                            # Prefer fragments with low maximum similarity (more diverse)
                            if max_similarity < min_max_similarity:
                                min_max_similarity = max_similarity
                                best_fragment = candidate

                        if best_fragment:
                            selected_fragments.append(best_fragment)
                            remaining_fragments.remove(best_fragment)
                        else:
                            # If no fragment has embeddings, just add by importance
                            selected_fragments.append(remaining_fragments.pop(0))

                    context["fragments"] = selected_fragments

                except Exception as e:
                    print(f"Failed to perform semantic diversity pruning, using simple threshold: {e}")
                    # Fallback to simple importance threshold
                    context["fragments"] = fragments_by_importance[:max_fragments]

        elif strategy in ("size_limit", PruningStrategy.SIZE_LIMIT):
            # Enhanced size limit with semantic diversity consideration
            max_fragments = budget or 5

            if len(context["fragments"]) <= max_fragments:
                # Already under limit
                pass
            else:
                try:
                    # Use semantic diversity to select fragments to keep
                    selected_fragments = []
                    remaining_fragments = context["fragments"].copy()

                    # Always keep the first fragment
                    selected_fragments.append(remaining_fragments.pop(0))

                    # Select fragments that are semantically diverse
                    while len(selected_fragments) < max_fragments and remaining_fragments:
                        best_fragment = None
                        min_max_similarity = float('inf')

                        for candidate in remaining_fragments:
                            candidate_embedding = candidate.get("embedding", [])
                            if not candidate_embedding:
                                continue

                            max_similarity = 0
                            for selected in selected_fragments:
                                selected_embedding = selected.get("embedding", [])
                                if selected_embedding:
                                    similarity = await voyage_service.compute_similarity(
                                        candidate_embedding, selected_embedding
                                    )
                                    max_similarity = max(max_similarity, similarity)

                            if max_similarity < min_max_similarity:
                                min_max_similarity = max_similarity
                                best_fragment = candidate

                        if best_fragment:
                            selected_fragments.append(best_fragment)
                            remaining_fragments.remove(best_fragment)
                        else:
                            # If no fragment has embeddings, add by order
                            selected_fragments.append(remaining_fragments.pop(0))

                    context["fragments"] = selected_fragments

                except Exception as e:
                    print(f"Failed to perform semantic diversity size limit, using simple truncation: {e}")
                    # Fallback to simple truncation
                    context["fragments"] = context["fragments"][:max_fragments]

        # Determine removed fragments
        removed_fragment_ids = []
        if len(context["fragments"]) < original_count:
            # This is a simplified approach - in reality, you'd track which specific fragments were removed
            removed_count = original_count - len(context["fragments"])
            removed_fragment_ids = [f"removed-{i}" for i in range(removed_count)]

        # Save pruned context
        await update_context_packet(context_id, context)

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
        context = await get_context_packet(context_id)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context {context_id} not found"
            )
        previous_version = int(context.get("version", 0))

        # Increment version
        context["version"] = previous_version + 1

        # Store updated context
        await update_context_packet(context_id, context)

        # Store version info
        version_info = {
            "version_id": str(uuid.uuid4()),
            "context_id": context_id,
            "version_number": context["version"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": request.get("version_metadata") or {"label": request.get("version_label")},
            "snapshot": context,
        }

        # Try to store in MongoDB if available
        if _mongodb_enabled:
            try:
                from ...models.context import VersionInfo
                from datetime import datetime, timezone

                mongodb_version = VersionInfo(
                    version_id=version_info["version_id"],
                    context_id=version_info["context_id"],
                    version_number=version_info["version_number"],
                    timestamp=datetime.now(timezone.utc),
                    metadata=version_info["metadata"],
                    label=version_info["metadata"].get("label"),
                    snapshot=version_info["snapshot"]
                )

                await mongodb_service.store_version(mongodb_version, None)  # Context already stored
            except Exception as e:
                print(f"MongoDB version storage failed, using memory: {e}")

        # Store in memory as fallback
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
        context = await get_context_packet(context_id)
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
        versions = []

        # Try to get versions from MongoDB first
        if _mongodb_enabled:
            try:
                mongodb_versions = await mongodb_service.get_versions(context_id)
                for version in mongodb_versions:
                    versions.append({
                        "version_id": version.version_id,
                        "context_id": version.context_id,
                        "version_number": version.version_number,
                        "timestamp": version.timestamp.isoformat(),
                        "metadata": version.metadata,
                        "label": version.label
                    })
            except Exception as e:
                print(f"MongoDB version retrieval failed, using memory: {e}")

        # Fallback to memory versions
        if not versions:
            versions = _context_versions.get(context_id, [])

        context = await get_context_packet(context_id)
        if context:
            current_version = int(context.get("version", 0))
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