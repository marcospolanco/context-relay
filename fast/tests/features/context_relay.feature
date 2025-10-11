Feature: Context Relay Between Agents
  As a system orchestrator
  I want to relay context packets between agents
  So that agents can collaborate with shared context

  Background:
    Given a context exists with ID "ctx-123"
    And Agent A has the current context packet with version 2
    And Agent B is ready to receive context
    And the embedding service is available

  Scenario: Successful context relay without conflicts
    Given Agent A wants to send new information to Agent B
    And I have a relay request:
      """
      {
        "from_agent": "Agent A",
        "to_agent": "Agent B",
        "context_id": "ctx-123",
        "delta": {
          "new_fragments": [
            {
              "fragment_id": "frag-456",
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
      """
    When I POST to "/context/relay" with the relay request
    Then the response status should be 200
    And the response should contain the updated context packet with version 3
    And the response should contain "conflicts": null
    And embeddings should be computed for the new fragment
    And a "relaySent" event should be broadcast
    And a "relayReceived" event should be broadcast

  Scenario: Context relay with semantic conflicts detected
    Given Agent A and Agent B have contradictory information
    And the existing context contains: "User budget is $2000 total"
    And Agent A sends new fragment: "User budget is $5000 total"
    When I POST to "/context/relay" with the contradictory fragment
    Then the response status should be 200
    And the response should contain the updated context packet
    And the response should contain conflicts
    And a "relayReceived" event should be broadcast with conflicts listed

  Scenario: Context relay to non-existent context
    Given I try to relay to context ID "non-existent-ctx"
    When I POST to "/context/relay" with invalid context_id
    Then the response status should be 404
    And an "error" event should be broadcast