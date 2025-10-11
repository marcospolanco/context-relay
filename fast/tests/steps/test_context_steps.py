import json
import pytest
from pytest_bdd import given, when, then, parsers
from fastapi.testclient import TestClient
from typing import Dict, Any
import uuid


# Shared context for test execution
class TestContext:
    def __init__(self):
        self.client = None
        self.response = None
        self.response_data = None
        self.request_data = {}
        self.session_id = None
        self.initial_input = None
        self.metadata = None


@pytest.fixture
def test_context():
    return TestContext()


@given("the embedding service is available")
def embedding_service_available():
    pass


@given("MongoDB is connected and ready")
def mongodb_connected():
    pass


@given("the SSE event system is initialized")
def sse_system_initialized():
    pass


@given(parsers.parse('I have a session ID "{session_id}"'))
def have_session_id(test_context, session_id):
    test_context.session_id = session_id


@given(parsers.parse('I have initial input "{input_text}"'))
def have_initial_input(test_context, input_text):
    test_context.initial_input = input_text


@given(parsers.parse('I have metadata {metadata_json}'))
def have_metadata(test_context, metadata_json):
    test_context.metadata = json.loads(metadata_json)


@given("I have complex initial input:")
def have_complex_initial_input(test_context, complex_input):
    test_context.initial_input = json.loads(complex_input)


@given("I have invalid initial input null")
def have_invalid_initial_input(test_context):
    test_context.initial_input = None


@when(parsers.parse('I POST to "{endpoint}" with:'))
@when(parsers.parse('I POST to "{endpoint}" with the above data'))
def post_to_endpoint(test_context, client: TestClient, endpoint, docstring=None):
    if docstring:
        request_data = json.loads(docstring)
    else:
        # Build request from context
        request_data = {
            "session_id": test_context.session_id,
            "initial_input": test_context.initial_input,
            "metadata": test_context.metadata or {}
        }

    test_context.request_data = request_data
    test_context.response = client.post(endpoint, json=request_data)
    test_context.response_data = test_context.response.json()


@then(parsers.parse('the response status should be {status_code:d}'))
def response_status_should_be(test_context, status_code):
    assert test_context.response.status_code == status_code


@then(parsers.parse('the response should contain a "{field}"'))
def response_should_contain_field(test_context, field):
    assert field in test_context.response_data


@then(parsers.parse('the response should contain a "{field}"'))
def response_should_contain_field(test_context, field):
    assert field in test_context.response_data


@then("the response should contain a \"context_packet\"")
def response_should_contain_context_packet(test_context):
    assert "context_packet" in test_context.response_data
    context_packet = test_context.response_data["context_packet"]

    # Verify required fields
    assert "context_id" in context_packet
    assert "fragments" in context_packet
    assert "decision_trace" in context_packet
    assert "metadata" in context_packet
    assert "version" in context_packet


@then("the context packet should have fragments")
def context_packet_should_have_fragments(test_context):
    context_packet = test_context.response_data["context_packet"]
    assert len(context_packet["fragments"]) > 0

    # Check fragment structure
    fragment = context_packet["fragments"][0]
    assert "fragment_id" in fragment
    assert "content" in fragment
    assert "metadata" in fragment


@then("the context packet should have decision_trace")
def context_packet_should_have_decision_trace(test_context):
    context_packet = test_context.response_data["context_packet"]
    assert isinstance(context_packet["decision_trace"], list)


@then("the context packet should have metadata")
def context_packet_should_have_metadata(test_context):
    context_packet = test_context.response_data["context_packet"]
    assert isinstance(context_packet["metadata"], dict)


@then(parsers.parse('the context packet should have version {version:d}'))
def context_packet_should_have_version(test_context, version):
    context_packet = test_context.response_data["context_packet"]
    assert context_packet["version"] == version


@then("an embedding should be computed for the initial fragment")
def embedding_should_be_computed(test_context):
    context_packet = test_context.response_data["context_packet"]
    fragments = context_packet["fragments"]

    # At least one fragment should have embeddings
    has_embedding = any(
        fragment.get("embedding") is not None and len(fragment["embedding"]) > 0
        for fragment in fragments
    )
    assert has_embedding


@then('the context packet should contain fragments for each constraint and preference')
def context_packet_should_have_constraint_fragments(test_context):
    context_packet = test_context.response_data["context_packet"]
    fragments = context_packet["fragments"]

    # Should have fragments for the complex input
    assert len(fragments) >= 3  # query + constraints + preferences


@then("embeddings should be computed for all fragments")
def embeddings_should_be_computed_for_all_fragments(test_context):
    context_packet = test_context.response_data["context_packet"]
    fragments = context_packet["fragments"]

    for fragment in fragments:
        assert fragment.get("embedding") is not None
        assert len(fragment["embedding"]) > 0


@then("metadata should preserve the complex input structure")
def metadata_should_preserve_complex_input(test_context):
    context_packet = test_context.response_data["context_packet"]
    metadata = context_packet["metadata"]

    assert "session_id" in metadata
    assert metadata["user_type"] == "detailed_planner"
    assert metadata["priority"] == "high"


@then("the response should contain an error message")
def response_should_contain_error_message(test_context):
    assert "error" in test_context.response_data or "message" in test_context.response_data


@then('a "contextInitialized" event should be broadcast')
def context_initialized_event_should_be_broadcast():
    # TODO: Implement event capture verification
    # For now, this is a placeholder that will be implemented
    # when we add the SSE event system
    pass


@then('an "error" event should be broadcast')
def error_event_should_be_broadcast():
    # TODO: Implement event capture verification
    pass