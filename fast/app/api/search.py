"""Vector similarity search endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.services.vector_search_service import get_vector_search_service

router = APIRouter(prefix="/search", tags=["search"])


class SimilarFragmentsRequest(BaseModel):
    """Request to find similar fragments."""
    query_embedding: List[float] = Field(..., description="Query vector (384 dimensions)")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results")
    min_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    context_id: Optional[str] = Field(default=None, description="Filter by context ID")


class SimilarContextsRequest(BaseModel):
    """Request to find similar contexts."""
    query_embedding: List[float] = Field(..., description="Query vector (384 dimensions)")
    session_id: Optional[str] = Field(default=None, description="Filter by session")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results")
    min_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class ConflictDetectionRequest(BaseModel):
    """Request to detect conflicts."""
    new_fragments: List[Dict[str, Any]] = Field(..., description="New fragments to check")
    context_id: str = Field(..., description="Context to check against")
    similarity_threshold: float = Field(default=0.9, ge=0.0, le=1.0, description="Conflict threshold")


class SearchResult(BaseModel):
    """Generic search result."""
    results: List[Dict[str, Any]]
    count: int


@router.post("/fragments/similar", response_model=SearchResult)
async def search_similar_fragments(request: SimilarFragmentsRequest):
    """
    Find semantically similar fragments using vector search.

    This endpoint uses MongoDB Atlas Vector Search to find fragments
    that are semantically similar to the query embedding.

    Returns:
        List of similar fragments with scores
    """
    try:
        vector_search = get_vector_search_service()

        results = await vector_search.find_similar_fragments(
            query_embedding=request.query_embedding,
            limit=request.limit,
            min_score=request.min_score,
            context_id=request.context_id
        )

        return SearchResult(
            results=results,
            count=len(results)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vector search failed: {str(e)}"
        )


@router.post("/contexts/similar", response_model=SearchResult)
async def search_similar_contexts(request: SimilarContextsRequest):
    """
    Find semantically similar contexts using vector search.

    Searches for entire context packets that contain similar fragments.

    Returns:
        List of similar contexts with scores
    """
    try:
        vector_search = get_vector_search_service()

        results = await vector_search.find_similar_contexts(
            query_embedding=request.query_embedding,
            session_id=request.session_id,
            limit=request.limit,
            min_score=request.min_score
        )

        return SearchResult(
            results=results,
            count=len(results)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Context search failed: {str(e)}"
        )


@router.post("/conflicts/detect", response_model=SearchResult)
async def detect_conflicts(request: ConflictDetectionRequest):
    """
    Detect conflicting fragments using semantic similarity.

    High similarity (>0.9) between fragments may indicate conflicts
    or redundant information.

    Returns:
        List of detected conflicts
    """
    try:
        vector_search = get_vector_search_service()

        conflicts = await vector_search.detect_conflicts(
            new_fragments=request.new_fragments,
            context_id=request.context_id,
            similarity_threshold=request.similarity_threshold
        )

        return SearchResult(
            results=conflicts,
            count=len(conflicts)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Conflict detection failed: {str(e)}"
        )
