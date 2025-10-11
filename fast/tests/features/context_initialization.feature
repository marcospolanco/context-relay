Feature: Context Initialization
  As a system user
  I want to initialize a new context with initial input
  So that I can start a context relay session

  Background:
    Given the embedding service is available
    And MongoDB is connected and ready
    And the SSE event system is initialized

  Scenario: Successful context initialization with minimal data
    Given I have a session ID "session-123"
    And I have initial input "User wants to plan a trip to Japan"
    And I have metadata {"user_type": "traveler", "priority": "normal"}
    When I POST to "/context/initialize" with:
      """
      {
        "session_id": "session-123",
        "initial_input": "User wants to plan a trip to Japan",
        "metadata": {"user_type": "traveler", "priority": "normal"}
      }
      """
    Then the response status should be 200
    And the response should contain a "context_id"
    And the response should contain a "context_packet"
    And the context packet should have fragments
    And the context packet should have decision_trace
    And the context packet should have metadata
    And the context packet should have version 0
    And an embedding should be computed for the initial fragment
    And a "contextInitialized" event should be broadcast

  Scenario: Context initialization with complex initial input
    Given I have a session ID "session-456"
    And I have complex initial input:
      """
      {
        "query": "Plan a 7-day Japan itinerary",
        "constraints": ["budget <= $3000", "must include Tokyo", "prefer cultural sites"],
        "preferences": {"food": "local cuisine", "transport": "public transit"}
      }
      """
    And I have metadata {"user_type": "detailed_planner", "priority": "high"}
    When I POST to "/context/initialize" with the above data
    Then the response status should be 200
    And the context packet should contain fragments for each constraint and preference
    And embeddings should be computed for all fragments
    And metadata should preserve the complex input structure

  Scenario: Context initialization failure due to invalid input
    Given I have a session ID "session-789"
    And I have invalid initial input null
    When I POST to "/context/initialize" with invalid data
    Then the response status should be 400
    And the response should contain an error message
    And an "error" event should be broadcast