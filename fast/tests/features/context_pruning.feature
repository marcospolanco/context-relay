Feature: Context Pruning
  As a system optimizer
  I want to prune context to fit within specified budgets
  So that I can maintain performance while preserving important information

  Background:
    Given a context exists with ID "ctx-large" containing 100 fragments
    And fragments have varying importance scores and timestamps
    And vector embeddings are available for all fragments

  Scenario: Successful pruning by recency strategy
    Given I want to prune context using "recency" strategy
    And the context budget is 50 fragments
    And the context contains fragments from the last 30 days
    When I POST to "/context/prune" with:
      """
      {
        "context_id": "ctx-large",
        "pruning_strategy": "recency",
        "budget": 50
      }
      """
    Then the response status should be 200
    And the pruned context should contain exactly 50 fragments
    And the remaining fragments should be the most recent ones
    And the decision trace should record which fragments were removed and why
    And a "contextPruned" event should be broadcast

  Scenario: Pruning fails due to insufficient context
    Given I try to prune a context with only 5 fragments
    And the budget is set to 10 fragments
    When I POST to "/context/prune" with budget larger than current size
    Then the response status should be 400
    And the error message should indicate budget exceeds current context size
    And no pruning should occur