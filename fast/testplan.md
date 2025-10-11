# Context Relay System - BDD Test Plan

## Executive Summary

This document outlines the Behavior-Driven Development (BDD) test plan for the Context Relay System. The `gherkin.md` document serves as the executable specification. The primary goal of this test plan is to automate all Gherkin scenarios to validate the system's behavior, ensuring alignment with requirements at every stage.

## Test Strategy Overview

### BDD as the Core Strategy
This project will use BDD as its primary testing methodology. The Gherkin scenarios in `gherkin.md` are not just documentation; they are the tests. Our testing pyramid is structured to support this:

- **BDD Scenarios (Integration/E2E)**: 80% - The core of our testing. Each scenario, implemented via `pytest-bdd`, tests a slice of functionality from the API endpoint down to the mock business logic.
- **Unit Tests**: 20% - Focused on complex internal logic (e.g., a specific algorithm) that is not easily expressed or tested through a behavioral scenario.

### Test Focus
- **API Contract Validation**: Ensuring all endpoints, request/response schemas, and status codes match the specification.
- **Behavioral Correctness**: Verifying that the system behaves as described in the Gherkin scenarios.
- **SSE Event Verification**: Confirming that the correct events are emitted in the correct order for each operation.

---

## Phase 1: Mock API BDD Testing (2-3 days)

**Goal**: Achieve 100% pass rate for all Gherkin scenarios against the mock API. The focus is on **validating the API contract and behavior**, not the internal implementation of the mock logic.

### Phase 1.1: BDD Framework & Test Structure

#### 1.1.1 Test Directory Structure
```
tests/
├── features/
│   ├── context_initialization.feature
│   ├── context_relay.feature
│   ├── context_merging.feature
│   ├── context_pruning.feature
│   ├── versioning.feature
│   ├── sse_events.feature
│   └── error_handling.feature
└── steps/
    ├── conftest.py  # Fixtures for API client, DB, etc.
    └── test_gherkin_steps.py # Step definitions
```

#### 1.1.2 Step Definitions & Fixtures
- Step definitions (`@given`, `@when`, `@then`) will be implemented in `test_gherkin_steps.py`.
- **Test Data Alignment**: `Given` steps will be responsible for setting up the precise state described in the scenario. Pytest fixtures, combined with `factory_boy` or helper functions, will generate the necessary mock data (e.g., `given('a context exists with ID "ctx-123"')`).

### Phase 1.2: Automating Gherkin Scenarios

This phase involves creating step definitions for each feature file.

#### 1.2.1 `context_initialization.feature` Tests
- Implement steps to `POST` to `/context/initialize`.
- Assert that the response status and body match the scenario's `Then` clauses.
- Verify that the `contextInitialized` SSE event is broadcast correctly.

#### 1.2.2 `context_relay.feature` Tests
- Implement steps for relaying context between agents.
- Assert on responses, including conflict detection.
- Verify `relaySent`, `relayReceived`, and `contextUpdated` SSE events.

#### 1.2.3 `context_merging.feature` & `context_pruning.feature` Tests
- Implement steps for merge and prune operations with different strategies.
- Assert that the resulting context is correct.
- Verify `contextMerged` and `contextPruned` SSE events.

#### 1.2.4 `versioning.feature` Tests
- Implement steps for creating and listing versions.
- Assert on version information in responses.
- Verify `versionCreated` SSE events.

#### 1.2.5 `error_handling.feature` Tests
- Implement steps that intentionally send invalid requests (bad data, wrong IDs).
- Assert that the correct 4xx/5xx HTTP status codes are returned.
- Verify that `error` SSE events are broadcast with the correct payload.

### Phase 1.3: SSE Event Stream Testing Strategy

#### 1.3.1 Automated SSE Client
- A dedicated, automated SSE test client will be implemented as a pytest fixture using `httpx`.
- This client will connect to the `/events/relay` endpoint at the start of a test.
- During the test, it will collect all received events into a list.

#### 1.3.2 Event Verification
- The `@then` steps for event validation (e.g., `Then a "contextInitialized" event should be broadcast`) will inspect the list of events collected by the SSE client.
- Assertions will be made on the event `type` and `payload` to ensure they match the Gherkin specification precisely.
- This approach validates the entire event stream for a given workflow, ensuring order and correctness.

### Phase 1.4: Acceptance Criteria

#### Phase 1 Success Metrics
- ✅ **100% of Gherkin scenarios in `gherkin.md` are automated and passing against the mock API.**
- ✅ The BDD test suite serves as the definitive validation of the API contract for the frontend developer.
- ✅ The automated SSE client correctly verifies all event-related scenarios.
- ✅ `Given` steps and fixtures provide reliable, scenario-driven test data setup.

---

## Phase 2: Core Functionality BDD Testing (1-2 weeks)

**Goal**: Ensure all BDD scenarios from Phase 1 continue to pass as mock logic is replaced with real backend integrations.

### Phase 2.1: Adapting BDD Tests for Real Services

#### 2.1.1 Database Integration
- The `conftest.py` fixtures will be updated to connect to a real test database (e.g., a separate MongoDB instance).
- `Given` steps that previously created in-memory objects will now insert documents into the test database.
- Teardown logic will be added to ensure tests are isolated.

#### 2.1.2 Embedding Service Integration
- The real embedding service client will be used.
- For tests, the embedding service API will be mocked at the network level (e.g., using `pytest-mock` or `httpx-mock`) to provide controlled, predictable embeddings and to avoid external dependencies during CI runs.

### Phase 2.2: Validating Real Business Logic
- No new tests need to be written. The existing BDD suite is re-run against the application which now uses real services.
- The goal is to make the existing scenarios pass with the new, real implementation. Any failures indicate a discrepancy between the real logic and the specified behavior.

### Phase 2.3: Acceptance Criteria

#### Phase 2 Success Metrics
- ✅ **100% of Gherkin scenarios continue to pass** with the real database and embedding service integrations.
- ✅ The BDD test suite successfully validates the correctness of the real business logic.
- ✅ Test fixtures for database and external services are reliable and provide proper isolation.

---

## Phase 3: Advanced Features BDD Testing (1-2 weeks)

### Phase 3.1: BDD-First for New Features
- For every new advanced feature, **new Gherkin scenarios will be written first**.
- These scenarios will initially fail.
- Development will consist of implementing the feature until the new scenarios pass.

### Phase 3.2: Acceptance Criteria

#### Phase 3 Success Metrics
- ✅ New Gherkin scenarios are written to define the behavior of all advanced features.
- ✅ All new and existing scenarios pass, demonstrating the new features work correctly without introducing regressions.

---

## Phase 4: Production Hardening Testing (1 week)

### Phase 4.1: BDD as Regression Suite
- The comprehensive BDD test suite is the primary tool for regression testing. It is run continuously in CI.
- **Load Testing**: Tools like `locust` will be used. Scenarios for load tests will be based on the high-traffic workflows identified in the Gherkin scenarios.
- **Security Testing**: While BDD tests validate functional authorization, dedicated security scans and penetration testing are separate activities.

### Phase 4.2: Acceptance Criteria

#### Phase 4 Success Metrics
- ✅ The BDD test suite runs in CI on every commit, providing a constant check for regressions.
- ✅ Performance and load tests are established for critical user journeys.
- ✅ The system is considered production-ready, with its behavior fully specified and verified by the BDD suite.

---

## Test Tools and Frameworks

### Core BDD Framework
- **pytest**: Primary testing framework.
- **pytest-bdd**: For parsing Gherkin files and linking them to Python test code.
- **httpx**: For both the API client and the automated SSE stream testing client.

### Test Data & Mocks
- **factory_boy** & **faker**: For generating realistic test data within `Given` step fixtures.
- **pytest-mock**: For mocking external services like the embedding API.

### Reporting
- **pytest-cov**: For tracking unit test coverage.
- **pytest-html**: For generating shareable reports of BDD test runs.

---

## Overall Success Criteria
- ✅ **All scenarios in `gherkin.md` are automated with `pytest-bdd` and pass in the CI/CD pipeline.**
- ✅ The test suite provides high confidence in the system's behavioral correctness.
- ✅ The BDD tests serve as living documentation of the system's features.
- ✅ Frontend and backend development is seamlessly integrated through a shared, executable specification.