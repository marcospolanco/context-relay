Feature: Server-Sent Events for Real-time Updates
  As a frontend application
  I want to receive real-time event streams from the logic layer
  So that I can provide live visualizations of context operations

  Background:
    Given the SSE endpoint is available at "/events/relay"
    And the event broadcasting system is initialized

  Scenario: Successful SSE connection and event reception
    Given I have a frontend client connecting to the SSE endpoint
    When I GET to "/events/relay" with Accept: "text/event-stream"
    Then the response status should be 200
    And the response content-type should be "text/event-stream"
    And the connection should remain open
    And I should receive events in SSE format

  Scenario: Multiple clients receive same events
    Given I have multiple frontend clients connected
    When a context operation occurs
    Then all connected clients should receive the same events
    And events should be delivered in the same order to all clients

  Scenario: Client disconnection handling
    Given a client is connected to the SSE endpoint
    When the client disconnects
    Then the server should detect the disconnection
    And the client's queue should be removed from subscribers

  Scenario: Event broadcasting during system errors
    Given a critical error occurs in the logic layer
    When the error is handled
    Then an "error" event should be broadcast to all clients
    And the error event should contain error_code and message
    And client connections should remain stable