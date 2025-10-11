Feature: Context Versioning
  As a system user
  I want to create version snapshots of contexts
  So that I can track changes and revert to previous states if needed

  Background:
    Given a context exists with ID "ctx-versioned" at version 5
    And the context has a history of modifications

  Scenario: Successful version creation with label
    Given I want to create a version snapshot
    And I have version metadata:
      """
      {
        "context_id": "ctx-versioned",
        "version_label": "After agent relay from Research to Planning"
      }
      """
    When I POST to "/context/version" with the version request
    Then the response status should be 200
    And the response should contain version info with version_id, context_id, timestamp, and summary
    And the version snapshot should be stored in the versions collection
    And a "versionCreated" event should be broadcast

  Scenario: List all versions for a context
    Given context "ctx-versioned" has multiple versions created
    When I GET to "/context/versions/ctx-versioned"
    Then the response status should be 200
    And the response should be an array of version info objects
    And versions should be ordered by timestamp (newest first)
    And each version should contain version_id, context_id, timestamp, and summary

  Scenario: Version creation for non-existent context
    Given I try to create a version for context "non-existent"
    When I POST to "/context/version" with invalid context_id
    Then the response status should be 404
    And an "error" event should be broadcast