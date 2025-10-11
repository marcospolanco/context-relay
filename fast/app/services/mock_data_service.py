import asyncio
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
import random

from app.models.context import (
    ContextFragment, ContextPacket, ContextDelta,
    RelayRequest, RelayResponse, MergeRequest, MergeResponse,
    PruneRequest, PruneResponse, VersionRequest, VersionInfo,
    InitializeRequest, InitializeResponse
)


class MockEmbeddingService:
    """Mock embedding service that generates realistic-looking embeddings"""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.service_available = True

    async def generate_embedding(self, content: Any) -> List[float]:
        """Generate a mock embedding for the given content"""
        if not self.service_available:
            raise Exception("Embedding service unavailable")

        # Simulate some processing time
        await asyncio.sleep(0.01)

        # Generate a deterministic but realistic-looking embedding
        content_str = str(content)
        seed = sum(ord(c) for c in content_str)
        random.seed(seed)

        embedding = [random.uniform(-1, 1) for _ in range(self.embedding_dim)]
        # Normalize the embedding
        norm = sum(x*x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x/norm for x in embedding]

        return embedding

    async def generate_batch_embeddings(self, contents: List[Any]) -> List[List[float]]:
        """Generate embeddings for multiple contents"""
        return await asyncio.gather(*[
            self.generate_embedding(content) for content in contents
        ])

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if len(embedding1) != len(embedding2):
            return 0.0

        dot_product = sum(a*b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a*a for a in embedding1) ** 0.5
        norm2 = sum(b*b for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def set_availability(self, available: bool):
        """Set service availability for testing"""
        self.service_available = available


class MockMongoDBService:
    """Mock MongoDB service for storing and retrieving context data"""

    def __init__(self):
        self.contexts: Dict[str, ContextPacket] = {}
        self.versions: Dict[str, List[VersionInfo]] = {}
        self.connected = True

    async def store_context(self, context: ContextPacket) -> bool:
        """Store a context packet"""
        if not self.connected:
            raise Exception("Database connection failed")

        await asyncio.sleep(0.005)  # Simulate DB latency
        self.contexts[context.context_id] = context
        return True

    async def get_context(self, context_id: str) -> Optional[ContextPacket]:
        """Retrieve a context packet by ID"""
        if not self.connected:
            raise Exception("Database connection failed")

        await asyncio.sleep(0.005)  # Simulate DB latency
        return self.contexts.get(context_id)

    async def update_context(self, context: ContextPacket) -> bool:
        """Update an existing context packet"""
        if not self.connected:
            raise Exception("Database connection failed")

        await asyncio.sleep(0.005)  # Simulate DB latency
        if context.context_id in self.contexts:
            self.contexts[context.context_id] = context
            return True
        return False

    async def store_version(self, version_info: VersionInfo, context: ContextPacket) -> bool:
        """Store a version snapshot"""
        if not self.connected:
            raise Exception("Database connection failed")

        await asyncio.sleep(0.005)  # Simulate DB latency

        if context.context_id not in self.versions:
            self.versions[context.context_id] = []

        self.versions[context.context_id].append(version_info)
        return True

    async def get_versions(self, context_id: str) -> List[VersionInfo]:
        """Get all versions for a context"""
        if not self.connected:
            raise Exception("Database connection failed")

        await asyncio.sleep(0.005)  # Simulate DB latency
        return self.versions.get(context_id, [])

    def set_connection_status(self, connected: bool):
        """Set database connection status for testing"""
        self.connected = connected

    def clear_all(self):
        """Clear all stored data"""
        self.contexts.clear()
        self.versions.clear()


class MockDataService:
    """Combined mock data service that orchestrates all mock operations"""

    def __init__(self):
        self.embedding_service = MockEmbeddingService()
        self.mongodb_service = MockMongoDBService()

    async def initialize_context(self, request: InitializeRequest) -> InitializeResponse:
        """Initialize a new context with the given request"""
        # Create initial fragment
        initial_fragment = ContextFragment(
            content=request.initial_input,
            metadata={
                **request.metadata,
                "source": "initial_input",
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Generate embedding for the initial fragment
        initial_fragment.embedding = await self.embedding_service.generate_embedding(
            request.initial_input
        )

        # Create context packet
        context_packet = ContextPacket(
            fragments=[initial_fragment],
            metadata={
                **request.metadata,
                "session_id": request.session_id,
                "created_at": datetime.utcnow().isoformat()
            },
            version=0
        )

        # Store in mock database
        await self.mongodb_service.store_context(context_packet)

        return InitializeResponse(
            context_id=context_packet.context_id,
            context_packet=context_packet
        )

    async def relay_context(self, request: RelayRequest) -> RelayResponse:
        """Relay context from one agent to another"""
        # Get existing context
        existing_context = await self.mongodb_service.get_context(request.context_id)
        if not existing_context:
            raise ValueError(f"Context {request.context_id} not found")

        # Process new fragments
        processed_fragments = []
        for fragment in request.delta.new_fragments:
            if not fragment.embedding:
                fragment.embedding = await self.embedding_service.generate_embedding(
                    fragment.content
                )
            processed_fragments.append(fragment)

        # Detect conflicts (mock implementation)
        conflicts = self._detect_conflicts(existing_context.fragments, processed_fragments)

        # Update context
        updated_fragments = existing_context.fragments + processed_fragments
        for fragment_id in request.delta.removed_fragment_ids:
            updated_fragments = [
                f for f in updated_fragments if f.fragment_id != fragment_id
            ]

        updated_context = ContextPacket(
            context_id=request.context_id,
            fragments=updated_fragments,
            decision_trace=existing_context.decision_trace + request.delta.decision_updates,
            metadata={
                **existing_context.metadata,
                "last_relay": {
                    "from_agent": request.from_agent,
                    "to_agent": request.to_agent,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            version=existing_context.version + 1
        )

        await self.mongodb_service.update_context(updated_context)

        return RelayResponse(
            context_packet=updated_context,
            conflicts=conflicts if conflicts else None
        )

    async def merge_contexts(self, request: MergeRequest) -> MergeResponse:
        """Merge multiple contexts into one"""
        # Get all contexts
        contexts = []
        for context_id in request.context_ids:
            context = await self.mongodb_service.get_context(context_id)
            if context:
                contexts.append(context)
            else:
                raise ValueError(f"Context {context_id} not found")

        if not contexts:
            raise ValueError("No valid contexts to merge")

        # Merge based on strategy
        merged_context = self._merge_contexts_by_strategy(contexts, request.merge_strategy)

        # Store merged context
        await self.mongodb_service.store_context(merged_context)

        return MergeResponse(
            merged_context=merged_context,
            conflict_report=None  # TODO: Implement conflict reporting
        )

    async def prune_context(self, request: PruneRequest) -> PruneResponse:
        """Prune context to fit within budget"""
        context = await self.mongodb_service.get_context(request.context_id)
        if not context:
            raise ValueError(f"Context {request.context_id} not found")

        # Prune based on strategy
        pruned_fragments = self._prune_fragments_by_strategy(
            context.fragments, request.pruning_strategy, request.budget
        )

        pruned_context = ContextPacket(
            context_id=request.context_id,
            fragments=pruned_fragments,
            decision_trace=context.decision_trace + [{
                "agent": "system",
                "decision": "pruned_context",
                "timestamp": datetime.utcnow().isoformat(),
                "strategy": request.pruning_strategy,
                "original_count": len(context.fragments),
                "pruned_count": len(pruned_fragments)
            }],
            metadata={
                **context.metadata,
                "pruned": {
                    "strategy": request.pruning_strategy,
                    "budget": request.budget,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            version=context.version + 1
        )

        await self.mongodb_service.update_context(pruned_context)

        return PruneResponse(pruned_context=pruned_context)

    async def create_version(self, request: VersionRequest) -> VersionInfo:
        """Create a version snapshot of a context"""
        context = await self.mongodb_service.get_context(request.context_id)
        if not context:
            raise ValueError(f"Context {request.context_id} not found")

        version_info = VersionInfo(
            context_id=request.context_id,
            summary=request.version_label or self._generate_version_summary(context)
        )

        await self.mongodb_service.store_version(version_info, context)

        return version_info

    def _detect_conflicts(self, existing_fragments: List[ContextFragment],
                         new_fragments: List[ContextFragment]) -> List[str]:
        """Mock conflict detection based on semantic similarity"""
        conflicts = []
        similarity_threshold = 0.8

        for new_frag in new_fragments:
            if not new_frag.embedding:
                continue

            for existing_frag in existing_fragments:
                if not existing_frag.embedding:
                    continue

                similarity = self.embedding_service.calculate_similarity(
                    new_frag.embedding, existing_frag.embedding
                )

                # High similarity but different content indicates potential conflict
                if similarity > similarity_threshold and new_frag.content != existing_frag.content:
                    conflicts.extend([new_frag.fragment_id, existing_frag.fragment_id])

        return list(set(conflicts))  # Remove duplicates

    def _merge_contexts_by_strategy(self, contexts: List[ContextPacket],
                                   strategy: str) -> ContextPacket:
        """Merge contexts using the specified strategy"""
        if strategy == "union":
            all_fragments = []
            for context in contexts:
                all_fragments.extend(context.fragments)

            return ContextPacket(
                fragments=all_fragments,
                decision_trace=[],
                metadata={
                    "merge_strategy": strategy,
                    "source_contexts": [c.context_id for c in contexts],
                    "merge_timestamp": datetime.utcnow().isoformat()
                },
                version=0
            )

        # TODO: Implement other strategies
        raise ValueError(f"Merge strategy '{strategy}' not implemented")

    def _prune_fragments_by_strategy(self, fragments: List[ContextFragment],
                                    strategy: str, budget: int) -> List[ContextFragment]:
        """Prune fragments using the specified strategy"""
        if len(fragments) <= budget:
            return fragments

        if strategy == "recency":
            # Sort by creation time (newest first) and take the first budget
            sorted_fragments = sorted(
                fragments,
                key=lambda f: f.metadata.get("created_at", ""),
                reverse=True
            )
            return sorted_fragments[:budget]

        if strategy == "semantic_diversity":
            # Simple diversity: take every n-th fragment to ensure variety
            step = len(fragments) // budget
            return fragments[::max(1, step)][:budget]

        if strategy == "importance":
            # Sort by importance score if available, otherwise by fragment_id
            sorted_fragments = sorted(
                fragments,
                key=lambda f: f.metadata.get("importance", 0.5),
                reverse=True
            )
            return sorted_fragments[:budget]

        raise ValueError(f"Pruning strategy '{strategy}' not implemented")

    def _generate_version_summary(self, context: ContextPacket) -> str:
        """Generate an automatic version summary based on recent changes"""
        if not context.decision_trace:
            return "Initial version"

        recent_decisions = context.decision_trace[-3:]  # Last 3 decisions
        decision_types = [d.get("decision", "unknown") for d in recent_decisions]

        return f"Version after: {', '.join(decision_types)}"