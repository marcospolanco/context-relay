"""Mock data service for generating realistic test data."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..models.shared import (
    ContextFragment,
    ContextPacket,
    DecisionTrace,
    AgentType,
    FragmentType
)
from ..models.context import (
    InitializeContextRequest,
    RelayRequest,
    MergeRequest,
    PruneRequest,
    VersionRequest
)


class MockDataService:
    """Service for generating realistic mock data for BDD scenarios."""

    def __init__(self):
        """Initialize mock data service with sample content."""
        self._sample_texts = [
            "The user needs help with debugging a Python function that processes JSON data.",
            "Analysis shows the function has type conversion issues when handling nested objects.",
            "Recommended solution involves adding proper error handling and type validation.",
            "The system should log all conversion attempts for debugging purposes.",
            "Performance testing suggests the current implementation is efficient for small datasets.",
            "Documentation should be updated to reflect the expected input format.",
            "Integration tests are needed to verify compatibility with existing codebase.",
            "The fix should maintain backward compatibility with previous versions."
        ]

        self._sample_code_snippets = [
            "def process_json(data: dict) -> dict:\n    return json.loads(json.dumps(data))",
            "try:\n    result = complex_operation(input_data)\nexcept Exception as e:\n    logger.error(f\"Processing failed: {e}\")",
            "class DataProcessor:\n    def __init__(self, config: dict):\n        self.config = config",
            "async def fetch_data(url: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()"
        ]

    def generate_context_fragment(
        self,
        fragment_type: FragmentType = FragmentType.TEXT,
        source_agent: Optional[AgentType] = None,
        importance_score: Optional[float] = None,
        with_embedding: bool = True
    ) -> ContextFragment:
        """Generate a realistic context fragment."""
        if source_agent is None:
            source_agent = random.choice(list(AgentType))

        if importance_score is None:
            importance_score = random.uniform(0.3, 1.0)

        # Generate content based on type
        if fragment_type == FragmentType.TEXT:
            content = random.choice(self._sample_texts)
        elif fragment_type == FragmentType.CODE:
            content = random.choice(self._sample_code_snippets)
        elif fragment_type == FragmentType.DECISION:
            content = f"Decision: {random.choice(['approve', 'reject', 'modify', 'defer'])} based on analysis"
        else:
            content = f"Metadata: {uuid.uuid4().hex[:8]}"

        fragment = ContextFragment(
            id=str(uuid.uuid4()),
            type=fragment_type,
            content=content,
            source_agent=source_agent,
            importance_score=importance_score,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "mock_data": True
            }
        )

        # Add mock embedding for semantic similarity testing
        if with_embedding:
            fragment.embedding = self._generate_mock_embedding(content)

        return fragment

    def generate_context_packet(
        self,
        session_id: Optional[str] = None,
        fragment_count: int = 5,
        version: int = 1
    ) -> ContextPacket:
        """Generate a realistic context packet."""
        if session_id is None:
            session_id = f"session-{uuid.uuid4().hex[:8]}"

        fragments = [
            self.generate_context_fragment()
            for _ in range(fragment_count)
        ]

        return ContextPacket(
            id=str(uuid.uuid4()),
            session_id=session_id,
            fragments=fragments,
            version=version,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "mock_data": True,
                "total_fragments": fragment_count
            }
        )

    def generate_conflicting_fragments(self) -> Tuple[ContextFragment, ContextFragment]:
        """Generate a pair of fragments that might conflict."""
        base_text = "The system should process user requests efficiently"

        fragment1 = ContextFragment(
            id=str(uuid.uuid4()),
            type=FragmentType.TEXT,
            content=base_text + " with priority on speed",
            source_agent=AgentType.AI_ASSISTANT,
            importance_score=0.8,
            embedding=self._generate_mock_embedding("speed priority"),
            metadata={"priority": "speed"}
        )

        fragment2 = ContextFragment(
            id=str(uuid.uuid4()),
            type=FragmentType.TEXT,
            content=base_text + " with priority on accuracy",
            source_agent=AgentType.HUMAN,
            importance_score=0.9,
            embedding=self._generate_mock_embedding("accuracy priority"),
            metadata={"priority": "accuracy"}
        )

        return fragment1, fragment2

    def generate_decision_trace(
        self,
        operation: str,
        context_id: str,
        decision: str,
        reasoning: str,
        affected_fragments: Optional[List[str]] = None
    ) -> DecisionTrace:
        """Generate a realistic decision trace."""
        return DecisionTrace(
            operation=operation,
            context_id=context_id,
            decision=decision,
            reasoning=reasoning,
            affected_fragments=affected_fragments or [],
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "mock_data": True
            }
        )

    def generate_initialize_request(
        self,
        session_id: Optional[str] = None,
        fragment_count: int = 3
    ) -> InitializeContextRequest:
        """Generate a context initialization request."""
        if session_id is None:
            session_id = f"session-{uuid.uuid4().hex[:8]}"

        fragments = [
            self.generate_context_fragment()
            for _ in range(fragment_count)
        ]

        return InitializeContextRequest(
            session_id=session_id,
            initial_fragments=fragments,
            metadata={
                "test_scenario": "context_initialization",
                "mock_data": True
            }
        )

    def generate_relay_request(
        self,
        context_id: Optional[str] = None,
        from_agent: Optional[AgentType] = None,
        to_agent: Optional[AgentType] = None
    ) -> RelayRequest:
        """Generate a context relay request."""
        if context_id is None:
            context_id = str(uuid.uuid4())

        if from_agent is None:
            from_agent = random.choice([AgentType.AI_ASSISTANT, AgentType.HUMAN])

        if to_agent is None:
            to_agent = random.choice([AgentType.AI_ASSISTANT, AgentType.HUMAN])
            # Ensure different agents
            while to_agent == from_agent:
                to_agent = random.choice([AgentType.AI_ASSISTANT, AgentType.HUMAN])

        # Generate fragments that might create conflicts
        fragments = [
            self.generate_context_fragment()
            for _ in range(random.randint(1, 4))
        ]

        return RelayRequest(
            context_id=context_id,
            from_agent=from_agent,
            to_agent=to_agent,
            delta_fragments=fragments,
            metadata={
                "test_scenario": "context_relay",
                "mock_data": True
            }
        )

    def generate_merge_request(
        self,
        context_count: int = 2
    ) -> MergeRequest:
        """Generate a context merge request."""
        context_ids = [str(uuid.uuid4()) for _ in range(context_count)]

        return MergeRequest(
            context_ids=context_ids,
            target_context_id=str(uuid.uuid4()),
            metadata={
                "test_scenario": "context_merging",
                "mock_data": True
            }
        )

    def generate_prune_request(
        self,
        context_id: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> PruneRequest:
        """Generate a context prune request."""
        if context_id is None:
            context_id = str(uuid.uuid4())

        return PruneRequest(
            context_id=context_id,
            strategy=strategy or "recency",
            max_fragments=random.randint(3, 10),
            metadata={
                "test_scenario": "context_pruning",
                "mock_data": True
            }
        )

    def generate_version_request(
        self,
        context_id: Optional[str] = None
    ) -> VersionRequest:
        """Generate a version creation request."""
        if context_id is None:
            context_id = str(uuid.uuid4())

        return VersionRequest(
            context_id=context_id,
            version_metadata={
                "reason": "checkpoint",
                "test_scenario": "versioning",
                "mock_data": True
            }
        )

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a mock embedding vector for semantic similarity testing."""
        # Create a deterministic but realistic-looking embedding based on text
        seed = hash(text) % 1000
        random.seed(seed)

        # Generate 1536-dimensional vector (like OpenAI embeddings)
        embedding = [random.uniform(-1, 1) for _ in range(1536)]

        # Normalize to unit vector
        magnitude = sum(x*x for x in embedding) ** 0.5
        embedding = [x/magnitude for x in embedding]

        random.seed()  # Reset seed
        return embedding

    def generate_similar_embeddings(self, base_embedding: List[float], similarity: float = 0.8) -> List[float]:
        """Generate an embedding similar to the base embedding."""
        # Create a vector with specified cosine similarity
        import math

        # Generate random orthogonal vector
        random_vec = [random.uniform(-1, 1) for _ in range(len(base_embedding))]

        # Make it orthogonal to base
        dot_product = sum(a*b for a, b in zip(base_embedding, random_vec))
        random_vec = [x - dot_product * base_embedding[i] for i, x in enumerate(random_vec)]

        # Normalize
        magnitude = sum(x*x for x in random_vec) ** 0.5
        if magnitude > 0:
            random_vec = [x/magnitude for x in random_vec]

        # Combine with base embedding to achieve desired similarity
        theta = math.acos(similarity)
        result = [
            math.cos(theta) * base_embedding[i] + math.sin(theta) * random_vec[i]
            for i in range(len(base_embedding))
        ]

        return result

    def get_sample_contexts_for_testing(self) -> List[ContextPacket]:
        """Get a set of pre-configured contexts for BDD testing."""
        contexts = []

        # Context 1: Simple text context
        contexts.append(self.generate_context_packet(
            session_id="test-session-1",
            fragment_count=3
        ))

        # Context 2: Mixed content types
        mixed_fragments = [
            self.generate_context_fragment(FragmentType.TEXT),
            self.generate_context_fragment(FragmentType.CODE),
            self.generate_context_fragment(FragmentType.DECISION)
        ]
        contexts.append(ContextPacket(
            id=str(uuid.uuid4()),
            session_id="test-session-2",
            fragments=mixed_fragments,
            metadata={"test_type": "mixed_content"}
        ))

        # Context 3: High importance context
        important_fragments = [
            self.generate_context_fragment(importance_score=0.9)
            for _ in range(5)
        ]
        contexts.append(ContextPacket(
            id=str(uuid.uuid4()),
            session_id="test-session-3",
            fragments=important_fragments,
            metadata={"test_type": "high_importance"}
        ))

        return contexts