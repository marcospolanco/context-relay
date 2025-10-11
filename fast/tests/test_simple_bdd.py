import pytest
import httpx
import json
import uuid
from datetime import datetime

# Import the app for direct testing
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.mock_data_service import MockDataService


@pytest.fixture
def client():
    """Create a test client using FastAPI's TestClient"""
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_context_initialization_success(client):
    """Test successful context initialization"""
    # Given
    request_data = {
        "session_id": "session-123",
        "initial_input": "User wants to plan a trip to Japan",
        "metadata": {"user_type": "traveler", "priority": "normal"}
    }

    # When
    response = client.post("/context/initialize", json=request_data)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "context_id" in response_data
    assert "context_packet" in response_data

    context_packet = response_data["context_packet"]
    assert context_packet["version"] == 0
    assert len(context_packet["fragments"]) > 0
    assert isinstance(context_packet["decision_trace"], list)
    assert isinstance(context_packet["metadata"], dict)

    # Check fragment structure
    fragment = context_packet["fragments"][0]
    assert "fragment_id" in fragment
    assert "content" in fragment
    assert "metadata" in fragment
    assert fragment["content"] == "User wants to plan a trip to Japan"
    assert "embedding" in fragment
    assert isinstance(fragment["embedding"], list)
    assert len(fragment["embedding"]) > 0


def test_context_initialization_complex_input(client):
    """Test context initialization with complex input"""
    # Given
    request_data = {
        "session_id": "session-456",
        "initial_input": {
            "query": "Plan a 7-day Japan itinerary",
            "constraints": ["budget <= $3000", "must include Tokyo", "prefer cultural sites"],
            "preferences": {"food": "local cuisine", "transport": "public transit"}
        },
        "metadata": {"user_type": "detailed_planner", "priority": "high"}
    }

    # When
    response = client.post("/context/initialize", json=request_data)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "context_id" in response_data
    assert "context_packet" in response_data

    context_packet = response_data["context_packet"]
    assert context_packet["metadata"]["user_type"] == "detailed_planner"
    assert context_packet["metadata"]["priority"] == "high"
    assert len(context_packet["fragments"]) > 0


def test_context_initialization_failure(client):
    """Test context initialization failure due to invalid input"""
    # Given
    request_data = {
        "session_id": "session-789",
        "initial_input": None,
        "metadata": {}
    }

    # When
    response = client.post("/context/initialize", json=request_data)

    # Then
    assert response.status_code == 400


def test_context_relay_success(client):
    """Test successful context relay"""
    # First create a context
    init_response = client.post("/context/initialize", json={
        "session_id": "relay-test-session",
        "initial_input": "User budget is $2000 total",
        "metadata": {"test": True}
    })
    assert init_response.status_code == 200
    context_id = init_response.json()["context_id"]

    # Given
    relay_request = {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": context_id,
        "delta": {
            "new_fragments": [
                {
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

    # When
    response = client.post("/context/relay", json=relay_request)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "context_packet" in response_data
    assert "conflicts" in response_data

    context_packet = response_data["context_packet"]
    assert context_packet["version"] == 1  # Should be incremented
    assert len(context_packet["fragments"]) > 1  # Should have new fragment
    assert response_data["conflicts"] is None


def test_context_relay_nonexistent_context(client):
    """Test context relay to non-existent context"""
    # Given
    relay_request = {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": "non-existent-ctx",
        "delta": {
            "new_fragments": [],
            "removed_fragment_ids": [],
            "decision_updates": []
        }
    }

    # When
    response = client.post("/context/relay", json=relay_request)

    # Then
    assert response.status_code == 404


def test_context_merge(client):
    """Test context merging"""
    # Create two contexts
    ctx1_response = client.post("/context/initialize", json={
        "session_id": "merge-test-1",
        "initial_input": "prefers cultural sites",
        "metadata": {"source": "ctx1"}
    })
    ctx1_id = ctx1_response.json()["context_id"]

    ctx2_response = client.post("/context/initialize", json={
        "session_id": "merge-test-2",
        "initial_input": "budget <= $3000",
        "metadata": {"source": "ctx2"}
    })
    ctx2_id = ctx2_response.json()["context_id"]

    # When
    merge_request = {
        "context_ids": [ctx1_id, ctx2_id],
        "merge_strategy": "union"
    }
    response = client.post("/context/merge", json=merge_request)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "merged_context" in response_data
    assert "conflict_report" in response_data

    merged_context = response_data["merged_context"]
    assert len(merged_context["fragments"]) >= 2  # Should have fragments from both contexts


def test_context_pruning(client):
    """Test context pruning"""
    # Create a context
    init_response = client.post("/context/initialize", json={
        "session_id": "prune-test",
        "initial_input": "Initial fragment",
        "metadata": {"created_at": "2024-01-01T00:00:00Z"}
    })
    context_id = init_response.json()["context_id"]

    # Add more fragments
    for i in range(10):
        relay_request = {
            "from_agent": f"Agent{i}",
            "to_agent": "System",
            "context_id": context_id,
            "delta": {
                "new_fragments": [
                    {
                        "content": f"Fragment {i}",
                        "metadata": {"created_at": f"2024-01-{i+1:02d}T00:00:00Z"}
                    }
                ],
                "removed_fragment_ids": [],
                "decision_updates": []
            }
        }
        client.post("/context/relay", json=relay_request)

    # When - prune to 5 fragments
    prune_request = {
        "context_id": context_id,
        "pruning_strategy": "recency",
        "budget": 5
    }
    response = client.post("/context/prune", json=prune_request)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "pruned_context" in response_data

    pruned_context = response_data["pruned_context"]
    assert len(pruned_context["fragments"]) <= 5


def test_versioning(client):
    """Test versioning operations"""
    # Create a context
    init_response = client.post("/context/initialize", json={
        "session_id": "version-test",
        "initial_input": "Initial content",
        "metadata": {}
    })
    context_id = init_response.json()["context_id"]

    # When - create a version
    version_request = {
        "context_id": context_id,
        "version_label": "Test version snapshot"
    }
    response = client.post("/context/version", json=version_request)

    # Then
    assert response.status_code == 200
    response_data = response.json()
    assert "version_id" in response_data
    assert "context_id" in response_data
    assert "timestamp" in response_data
    assert "summary" in response_data
    assert response_data["context_id"] == context_id
    assert response_data["summary"] == "Test version snapshot"

    # Test listing versions
    versions_response = client.get(f"/context/versions/{context_id}")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) >= 1
    assert versions[0]["context_id"] == context_id


def test_sse_events(client):
    """Test SSE event endpoints"""
    # Test event stats endpoint
    response = client.get("/events/stats")
    assert response.status_code == 200

    stats_data = response.json()
    assert "active_subscribers" in stats_data
    assert "total_events" in stats_data
    assert "last_event_id" in stats_data


def test_error_handling(client):
    """Test error handling scenarios"""
    # Test missing required fields
    response = client.post("/context/initialize", json={})
    assert response.status_code == 422

    # Test non-existent context retrieval
    response = client.get("/context/non-existent")
    assert response.status_code == 404

    # Test non-existent context versioning
    response = client.post("/context/version", json={
        "context_id": "non-existent",
        "version_label": "Test"
    })
    assert response.status_code == 404

    # Test merge with insufficient contexts
    response = client.post("/context/merge", json={
        "context_ids": ["single-context"],
        "merge_strategy": "union"
    })
    assert response.status_code == 400

    # Test prune with invalid budget
    # First create a small context
    init_response = client.post("/context/initialize", json={
        "session_id": "small-prune-test",
        "initial_input": "Small context",
        "metadata": {}
    })
    context_id = init_response.json()["context_id"]

    # Try to prune with budget larger than current size
    prune_request = {
        "context_id": context_id,
        "pruning_strategy": "recency",
        "budget": 100  # Much larger than current size
    }
    response = client.post("/context/prune", json=prune_request)
    assert response.status_code == 400


def test_service_controls(client):
    """Test service control endpoints for testing"""
    # Test embedding service control
    response = client.post("/test/embedding-service/availability", json={"available": False})
    assert response.status_code == 200
    assert response.json()["embedding_service_available"] == False

    # Test MongoDB service control
    response = client.post("/test/mongodb-service/connection", json={"connected": False})
    assert response.status_code == 200
    assert response.json()["mongodb_connected"] == False

    # Reset services
    response = client.post("/test/embedding-service/availability", json={"available": True})
    assert response.status_code == 200

    response = client.post("/test/mongodb-service/connection", json={"connected": True})
    assert response.status_code == 200

    # Test clear all data
    response = client.post("/test/clear-all-data")
    assert response.status_code == 200
    assert response.json()["message"] == "All data cleared"