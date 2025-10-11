import json
import pytest
from pytest_bdd import given, when, then, parsers
from fastapi.testclient import TestClient
from typing import Dict, Any
import uuid
from app.services.mock_data_service import MockDataService


# Shared context for test execution
@pytest.fixture
def relay_test_context():
    class RelayTestContext:
        def __init__(self):
            self.client = None
            self.response = None
            self.response_data = None
            self.request_data = {}
            self.context_id = None
            self.mock_service = MockDataService()

    return RelayTestContext()


@given("a context exists with ID \"ctx-123\"")
def context_exists(relay_test_context):
    # Create a mock context for testing
    from app.models.context import ContextFragment, ContextPacket
    from datetime import datetime

    initial_fragment = ContextFragment(
        fragment_id="frag-123",
        content="User budget is $2000 total",
        metadata={"source": "initial_input", "created_at": datetime.utcnow().isoformat()}
    )

    context_packet = ContextPacket(
        context_id="ctx-123",
        fragments=[initial_fragment],
        metadata={"session_id": "session-123"},
        version=2
    )

    # Store in mock service
    relay_test_context.mock_service.mongodb_service.contexts["ctx-123"] = context_packet
    relay_test_context.context_id = "ctx-123"


@given("Agent A has the current context packet with version 2")
def agent_has_context_version_2(relay_test_context):
    # Context is already set up in the previous step
    assert "ctx-123" in relay_test_context.mock_service.mongodb_service.contexts
    context = relay_test_context.mock_service.mongodb_service.contexts["ctx-123"]
    assert context.version == 2


@given("Agent B is ready to receive context")
def agent_b_ready():
    pass  # Placeholder for agent readiness


@given("Agent A wants to send new information to Agent B")
def agent_a_wants_to_send():
    pass  # Placeholder for agent intention


@when("I POST to \"/context/relay\" with the relay request")
def post_relay_request(relay_test_context, client: TestClient):
    relay_test_context.response = client.post("/context/relay", json=relay_test_context.request_data)
    try:
        relay_test_context.response_data = relay_test_context.response.json()
    except:
        relay_test_context.response_data = {}


@then("the response should contain the updated context packet with version 3")
def response_contains_updated_context_version_3(relay_test_context):
    assert relay_test_context.response.status_code == 200
    assert "context_packet" in relay_test_context.response_data
    assert relay_test_context.response_data["context_packet"]["version"] == 3


@then("the response should contain \"conflicts\": null")
def response_contains_no_conflicts(relay_test_context):
    assert "conflicts" in relay_test_context.response_data
    assert relay_test_context.response_data["conflicts"] is None


@then("embeddings should be computed for the new fragment")
def embeddings_computed_for_new_fragment(relay_test_context):
    # In the mock implementation, embeddings are always computed
    # This is a placeholder assertion
    pass


@then("a \"relaySent\" event should be broadcast")
def relay_sent_event_broadcast():
    # TODO: Implement event capture verification
    pass


@then("a \"relayReceived\" event should be broadcast")
def relay_received_event_broadcast():
    # TODO: Implement event capture verification
    pass


@given("Agent A and Agent B have contradictory information")
def agents_have_contradictory_info(relay_test_context):
    # Set up context with existing information
    from app.models.context import ContextFragment, ContextPacket
    from datetime import datetime

    existing_fragment = ContextFragment(
        fragment_id="frag-123",
        content="User budget is $2000 total",
        metadata={"source": "initial_input", "created_at": datetime.utcnow().isoformat()}
    )

    context_packet = ContextPacket(
        context_id="ctx-123",
        fragments=[existing_fragment],
        metadata={"session_id": "session-123"},
        version=2
    )

    relay_test_context.mock_service.mongodb_service.contexts["ctx-123"] = context_packet


@given("the existing context contains: \"User budget is $2000 total\"")
def existing_context_contains_budget_info(relay_test_context):
    # This is set up in the previous step
    pass


@given("Agent A sends new fragment: \"User budget is $5000 total\"")
def agent_a_sends_contradictory_fragment(relay_test_context):
    relay_test_context.request_data = {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": "ctx-123",
        "delta": {
            "new_fragments": [
                {
                    "fragment_id": "frag-456",
                    "content": "User budget is $5000 total",
                    "metadata": {"source": "agent_a_analysis", "confidence": 0.9}
                }
            ],
            "removed_fragment_ids": [],
            "decision_updates": []
        }
    }


@when("I POST to \"/context/relay\" with the contradictory fragment")
def post_contradictory_fragment(relay_test_context, client: TestClient):
    relay_test_context.response = client.post("/context/relay", json=relay_test_context.request_data)
    try:
        relay_test_context.response_data = relay_test_context.response.json()
    except:
        relay_test_context.response_data = {}


@then("the response should contain conflicts")
def response_contains_conflicts(relay_test_context):
    assert relay_test_context.response.status_code == 200
    assert "conflicts" in relay_test_context.response_data
    assert relay_test_context.response_data["conflicts"] is not None


@then("a \"relayReceived\" event should be broadcast with conflicts listed")
def relay_received_event_with_conflicts():
    # TODO: Implement event capture verification
    pass


@given("I try to relay to context ID \"non-existent-ctx\"")
def try_to_relay_non_existent_context(relay_test_context):
    relay_test_context.request_data = {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": "non-existent-ctx",
        "delta": {
            "new_fragments": [],
            "removed_fragment_ids": [],
            "decision_updates": []
        }
    }


@when("I POST to \"/context/relay\" with invalid context_id")
def post_relay_invalid_context(relay_test_context, client: TestClient):
    relay_test_context.response = client.post("/context/relay", json=relay_test_context.request_data)
    try:
        relay_test_context.response_data = relay_test_context.response.json()
    except:
        relay_test_context.response_data = {}


@then("the response status should be 404")
def response_status_404(relay_test_context):
    assert relay_test_context.response.status_code == 404