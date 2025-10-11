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

  Scenario: Merge with one or more non-existent contexts
    Given context "ctx-A" exists
    And context "non-existent" does not exist
    When I POST to "/context/merge" with ["ctx-A", "non-existent"]
    Then the response status should be 404
    And the error message should specify which contexts were not found
    And no merge operation should be performed