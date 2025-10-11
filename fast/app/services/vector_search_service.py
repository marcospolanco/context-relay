"""MongoDB Atlas Vector Search service for semantic similarity queries."""
import logging
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.database import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for performing vector similarity searches using MongoDB Atlas."""

    def __init__(self):
        """Initialize vector search service."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
        logger.info("✅ Vector Search Service initialized")

    def set_client(self, client: AsyncIOMotorClient):
        """
        Set MongoDB client for vector search operations.

        Args:
            client: Motor async client
        """
        self.client = client
        self.db = client[settings.MONGO_DB]
        self.collection = self.db["context_packets"]
        logger.info(f"Vector search using database: {settings.MONGO_DB}")

    async def find_similar_fragments(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_score: float = 0.7,
        context_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar fragments using vector search.

        Args:
            query_embedding: Query vector (384 dimensions for Voyage AI)
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            context_id: Optional context ID to filter results

        Returns:
            List of matching fragments with scores
        """
        if self.collection is None:
            logger.error("MongoDB client not initialized")
            return []

        try:
            # Build vector search pipeline
            pipeline = [
                {
                    "$search": {
                        "index": "vector_search_index",
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "fragments.embedding",
                            "k": limit * 2,  # Get more candidates
                            "filter": {}  # Add filters here if needed
                        }
                    }
                },
                {
                    "$addFields": {
                        "search_score": {"$meta": "searchScore"}
                    }
                },
                {
                    "$match": {
                        "search_score": {"$gte": min_score}
                    }
                },
                {
                    "$limit": limit
                },
                {
                    "$project": {
                        "context_id": 1,
                        "fragments": 1,
                        "metadata": 1,
                        "search_score": 1
                    }
                }
            ]

            # Execute search
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)

            logger.info(f"Vector search found {len(results)} results (min_score: {min_score})")

            # Flatten fragments from results
            flattened_results = []
            for doc in results:
                for fragment in doc.get("fragments", []):
                    if fragment.get("embedding"):
                        flattened_results.append({
                            "context_id": doc["context_id"],
                            "fragment_id": fragment["fragment_id"],
                            "content": fragment["content"],
                            "embedding": fragment["embedding"],
                            "metadata": fragment.get("metadata", {}),
                            "score": doc["search_score"]
                        })

            return flattened_results[:limit]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def find_similar_contexts(
        self,
        query_embedding: List[float],
        session_id: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find similar contexts (full packets) using vector search.

        Args:
            query_embedding: Query vector
            session_id: Optional session filter
            limit: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of similar contexts with scores
        """
        if self.collection is None:
            logger.error("MongoDB client not initialized")
            return []

        try:
            # Build pipeline with optional session filter
            match_filter = {}
            if session_id:
                match_filter["metadata.session_id"] = session_id

            pipeline = [
                {
                    "$search": {
                        "index": "vector_search_index",
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "fragments.embedding",
                            "k": limit * 2,
                            "filter": match_filter
                        }
                    }
                },
                {
                    "$addFields": {
                        "search_score": {"$meta": "searchScore"}
                    }
                },
                {
                    "$match": {
                        "search_score": {"$gte": min_score}
                    }
                },
                {
                    "$limit": limit
                },
                {
                    "$project": {
                        "context_id": 1,
                        "fragments": 1,
                        "decision_trace": 1,
                        "metadata": 1,
                        "version": 1,
                        "search_score": 1
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)

            logger.info(f"Found {len(results)} similar contexts")
            return results

        except Exception as e:
            logger.error(f"Context similarity search failed: {e}")
            return []

    async def detect_conflicts(
        self,
        new_fragments: List[Dict[str, Any]],
        context_id: str,
        similarity_threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicting fragments using semantic similarity.

        Args:
            new_fragments: New fragments to check
            context_id: Context ID to check against
            similarity_threshold: High similarity = potential conflict

        Returns:
            List of conflicts with details
        """
        conflicts = []

        for fragment in new_fragments:
            if not fragment.get("embedding"):
                continue

            # Search for highly similar fragments
            similar = await self.find_similar_fragments(
                query_embedding=fragment["embedding"],
                limit=3,
                min_score=similarity_threshold,
                context_id=context_id
            )

            # If we find very similar fragments, it's a potential conflict
            if similar:
                conflicts.append({
                    "new_fragment_id": fragment["fragment_id"],
                    "conflicting_fragments": [
                        {
                            "fragment_id": s["fragment_id"],
                            "score": s["score"]
                        }
                        for s in similar
                    ]
                })

        logger.info(f"Detected {len(conflicts)} potential conflicts")
        return conflicts


# Singleton instance
_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create singleton vector search service."""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service
