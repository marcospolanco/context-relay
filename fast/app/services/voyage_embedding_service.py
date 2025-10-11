"""Voyage AI Embedding Service - Infrastructure Layer
Handles embedding generation using Voyage AI API.
"""
import os
import asyncio
from typing import List, Optional
import voyageai
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class VoyageEmbeddingService:
    """Real Voyage AI embedding service for semantic similarity."""

    def __init__(self):
        """Initialize Voyage AI client."""
        settings = get_settings()
        self.api_key = settings.voyage_api_key
        if not self.api_key:
            logger.warning("VOYAGE_API_KEY not configured - service will not be available")
            self.service_available = False
            return

        # Initialize Voyage AI client
        self.client = voyageai.Client(api_key=self.api_key)
        self.model = "voyage-3"  # Latest model
        self.embedding_dimensions = 1024
        self.service_available = True

        logger.info(f"✅ Voyage AI Embedding Service initialized (model: {self.model}, dimensions: {self.embedding_dimensions})")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats (1024-dimensional vector)
        """
        try:
            # Voyage AI client is synchronous, run in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.embed(
                    texts=[text],
                    model=self.model,
                    input_type="document"
                )
            )

            embedding = result.embeddings[0]
            logger.debug(f"Generated embedding for text (length: {len(text)} chars, dimensions: {len(embedding)})")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch (more efficient).

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        if not texts:
            return []

        try:
            # Voyage AI supports batch processing (up to 128 texts per request)
            BATCH_SIZE = 128
            all_embeddings = []

            for i in range(0, len(texts), BATCH_SIZE):
                batch = texts[i:i + BATCH_SIZE]

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.client.embed(
                        texts=batch,
                        model=self.model,
                        input_type="document"
                    )
                )

                all_embeddings.extend(result.embeddings)
                logger.debug(f"Generated {len(batch)} embeddings (batch {i // BATCH_SIZE + 1})")

            logger.info(f"✅ Generated {len(all_embeddings)} embeddings in total")
            return all_embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    async def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between -1 and 1 (higher is more similar)
        """
        try:
            # Compute dot product
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

            # Compute magnitudes
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5

            # Cosine similarity
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)
            return similarity

        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0

    async def find_similar_fragments(
        self,
        query_embedding: List[float],
        fragment_embeddings: List[tuple[str, List[float]]],
        threshold: float = 0.8,
        top_k: Optional[int] = None
    ) -> List[tuple[str, float]]:
        """
        Find fragments similar to a query embedding.

        Args:
            query_embedding: Query embedding vector
            fragment_embeddings: List of (fragment_id, embedding) tuples
            threshold: Minimum similarity threshold (0-1)
            top_k: Maximum number of results to return

        Returns:
            List of (fragment_id, similarity_score) tuples, sorted by similarity
        """
        try:
            similarities = []

            for fragment_id, embedding in fragment_embeddings:
                similarity = await self.compute_similarity(query_embedding, embedding)

                if similarity >= threshold:
                    similarities.append((fragment_id, similarity))

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Limit to top_k if specified
            if top_k:
                similarities = similarities[:top_k]

            logger.debug(f"Found {len(similarities)} similar fragments (threshold: {threshold})")
            return similarities

        except Exception as e:
            logger.error(f"Failed to find similar fragments: {e}")
            return []

    def set_availability(self, available: bool):
        """Set service availability (for testing)."""
        self.service_available = available
        logger.info(f"Voyage AI service availability set to: {available}")

    def get_status(self) -> dict:
        """Get service status."""
        return {
            "service": "Voyage AI Embedding Service",
            "available": self.service_available,
            "model": self.model,
            "dimensions": self.embedding_dimensions,
            "api_key_set": bool(self.api_key)
        }


# Singleton instance
_voyage_service: Optional[VoyageEmbeddingService] = None


def get_voyage_service() -> VoyageEmbeddingService:
    """Get or create singleton Voyage AI service instance."""
    global _voyage_service
    if _voyage_service is None:
        _voyage_service = VoyageEmbeddingService()
    return _voyage_service
