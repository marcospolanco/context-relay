import asyncio
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
import uuid


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_session_id():
    return "session-123"


@pytest.fixture
def sample_context_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_fragment():
    return {
        "fragment_id": str(uuid.uuid4()),
        "content": "User wants to plan a trip to Japan",
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "metadata": {"source": "initial_input"}
    }


@pytest.fixture
def sample_initial_request():
    return {
        "session_id": "session-123",
        "initial_input": "User wants to plan a trip to Japan",
        "metadata": {"user_type": "traveler", "priority": "normal"}
    }


@pytest.fixture
def sample_relay_request():
    return {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": str(uuid.uuid4()),
        "delta": {
            "new_fragments": [
                {
                    "fragment_id": str(uuid.uuid4()),
                    "content": "User prefers budget accommodation under $100/night",
                    "metadata": {"source": "agent_a_analysis", "confidence": 0.9}
                }
            ],
            "removed_fragment_ids": [],
            "decision_updates": [
                {
                    "agent": "Agent A",
                    "decision": "added_budget_constraint",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "reasoning": "extracted from user preferences"
                }
            ]
        }
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()