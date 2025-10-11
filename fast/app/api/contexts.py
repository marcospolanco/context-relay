"""Context API endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.models.context import (
    ContextPacket,
    ContextFragment,
    InitializeRequest,
    InitializeResponse,
    RelayRequest,
    RelayResponse,
    MergeRequest,
    MergeResponse,
    PruneRequest,
    PruneResponse,
    VersionRequest,
    VersionInfo,
    ContextVersion
)
from datetime import datetime
from uuid import uuid4

router = APIRouter(prefix="/context", tags=["contexts"])


@router.post("/initialize", response_model=InitializeResponse)
async def initialize_context(request: InitializeRequest):
    """
    Initialize a new context with initial input.

    Creates a new ContextPacket with the initial input wrapped as a fragment,
    stores it in MongoDB, and returns the context_id.
    """
    try:
        # Create initial fragment from input
        initial_fragment = ContextFragment(
            fragment_id=str(uuid4()),
            content=request.initial_input,
            embedding=None,  # TODO: Generate embedding via Voyage AI
            metadata={
                "source": "initial_input",
                "session_id": request.session_id,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Create context packet
        context_packet = ContextPacket(
            context_id=str(uuid4()),
            fragments=[initial_fragment],
            decision_trace=[],
            metadata={
                "session_id": request.session_id,
                **request.metadata
            },
            version=0
        )

        # Save to MongoDB
        await context_packet.insert()

        # TODO: Broadcast "contextInitialized" SSE event

        # Return response
        return InitializeResponse(
            context_id=context_packet.context_id,
            context_packet=context_packet.model_dump(mode="json")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize context: {str(e)}")


@router.get("/{context_id}")
async def get_context(context_id: str):
    """
    Retrieve a context packet by ID.
    """
    try:
        context = await ContextPacket.find_one(ContextPacket.context_id == context_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")

        return context.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {str(e)}")


@router.post("/relay", response_model=RelayResponse)
async def relay_context(request: RelayRequest):
    """
    Relay context from one agent to another.

    Applies delta (new fragments, removals, decision updates),
    detects conflicts, and returns updated context.
    """
    try:
        # Fetch existing context
        context = await ContextPacket.find_one(ContextPacket.context_id == request.context_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Context {request.context_id} not found")

        # TODO: Generate embeddings for new fragments

        # Apply delta: add new fragments
        context.fragments.extend(request.delta.new_fragments)

        # Apply delta: remove fragments
        if request.delta.removed_fragment_ids:
            context.fragments = [
                f for f in context.fragments
                if f.fragment_id not in request.delta.removed_fragment_ids
            ]

        # Apply delta: update decision trace
        context.decision_trace.extend(request.delta.decision_updates)

        # Increment version
        context.version += 1
        context.updated_at = datetime.utcnow()

        # TODO: Detect conflicts using embeddings

        # Save updated context
        await context.save()

        # TODO: Broadcast SSE events (relaySent, relayReceived)

        return RelayResponse(
            context_packet=context.model_dump(),
            conflicts=None  # TODO: Implement conflict detection
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to relay context: {str(e)}")


@router.post("/merge", response_model=MergeResponse)
async def merge_contexts(request: MergeRequest):
    """
    Merge multiple contexts into one.

    Supports different merge strategies: union, overwrite, semantic_similarity.
    """
    try:
        # TODO: Implement merge logic
        raise HTTPException(status_code=501, detail="Merge endpoint not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge contexts: {str(e)}")


@router.post("/prune", response_model=PruneResponse)
async def prune_context(request: PruneRequest):
    """
    Prune context to fit within budget constraints.

    Supports different pruning strategies: recency, semantic_diversity, importance.
    """
    try:
        # TODO: Implement pruning logic
        raise HTTPException(status_code=501, detail="Prune endpoint not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prune context: {str(e)}")


@router.post("/version", response_model=VersionInfo)
async def create_version(request: VersionRequest):
    """
    Create a snapshot/version of a context.
    """
    try:
        # Fetch context
        context = await ContextPacket.find_one(ContextPacket.context_id == request.context_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Context {request.context_id} not found")

        # Create version snapshot
        version = ContextVersion(
            version_id=str(uuid4()),
            context_id=request.context_id,
            version_number=context.version,
            snapshot=context.model_dump(),
            summary=request.version_label if request.version_label else f"Version {context.version}",
            timestamp=datetime.utcnow()
        )

        # Save version
        await version.insert()

        # TODO: Broadcast "versionCreated" SSE event

        return VersionInfo(
            version_id=version.version_id,
            context_id=version.context_id,
            timestamp=version.timestamp,
            summary=version.summary,
            version_number=version.version_number
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")


@router.get("/versions/{context_id}")
async def list_versions(context_id: str):
    """
    List all versions for a context.
    """
    try:
        versions = await ContextVersion.find(
            ContextVersion.context_id == context_id
        ).sort(-ContextVersion.timestamp).to_list()

        return [
            VersionInfo(
                version_id=v.version_id,
                context_id=v.context_id,
                timestamp=v.timestamp,
                summary=v.summary,
                version_number=v.version_number
            )
            for v in versions
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {str(e)}")
