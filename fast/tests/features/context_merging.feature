Feature: Context Merging
  As a system coordinator
  I want to merge multiple contexts into one
  So that I can consolidate information from different agents or sessions

  Background:
    Given context "ctx-A" exists with fragments about travel preferences
    And context "ctx-B" exists with fragments about budget constraints
    And the embedding service is available for similarity detection

  Scenario: Successful union merge of two contexts
    Given I want to merge contexts using "union" strategy
    And context "ctx-A" has fragments: ["prefers cultural sites", "likes Japanese food"]
    And context "ctx-B" has fragments: ["budget <= $3000", "7-day duration"]
    When I POST to "/context/merge" with:
      """
      {
        "context_ids": ["ctx-A", "ctx-B"],
        "merge_strategy": "union"
      }
      """
    Then the response status should be 200
    And the merged context should contain all fragments from both contexts
    And the merged context metadata should record the merge operation
    And a "contextMerged" event should be broadcast

  Scenario: Semantic similarity merge with deduplication
    Given I want to merge contexts using "semantic_similarity" strategy
    And context "ctx-A" has fragment: "User wants to visit temples"
    And context "ctx-B" has fragment: "User interested in religious sites"
    And the embedding similarity between these fragments is > 0.8
    When I POST to "/context/merge" with semantic_similarity strategy
    Then the response status should be 200
    And the merged context should contain only one of the similar fragments
    And the decision trace should record the deduplication decision
    And the conflict_report should list the deduplicated fragments

  Scenario: Overwrite merge with conflict resolution
    Given I want to merge contexts using "overwrite" strategy
    And context "ctx-A" has fragment: "Budget is $2000" (priority: normal)
    And context "ctx-B" has fragment: "Budget is $5000" (priority: high)
    When I POST to "/context/merge" with overwrite strategy
    Then the response status should be 200
    And the merged context should prefer fragments from higher priority context
    And the conflict_report should list the overwritten fragments

  Scenario: Merge with one or more non-existent contexts
    Given context "ctx-A" exists
    And context "non-existent" does not exist
    When I POST to "/context/merge" with ["ctx-A", "non-existent"]
    Then the response status should be 404
    And the error message should specify which contexts were not found
    And no merge operation should be performed