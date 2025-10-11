# Context Relay System - Implementation Plan

## Executive Summary

This document outlines a phased, Behavior-Driven Development (BDD) plan for the Context Relay System. The `gherkin.md` specification is the single source of truth for the system's behavior. All development and testing will be driven by implementing the Gherkin scenarios.

**Priority #1: Deliver a complete, mocked, and BDD-tested API for the frontend developer as quickly as possible.**

## Phase Structure

- **Phase 1**: BDD-Driven Mock API Implementation (2-3 days) - **HIGHEST PRIORITY**
- **Phase 2**: Core Functionality (1-2 weeks)
- **Phase 3**: Advanced Features (1-2 weeks)
- **Phase 4**: Production Hardening (1 week)

---

## Phase 1: BDD-Driven Mock API Implementation (2-3 days)

**Goal**: Provide the frontend developer with a fully functional FastAPI server that passes all BDD scenarios from `gherkin.md` using mock data. This enables parallel frontend development against a reliable, behaviorally-correct API contract.

### Phase 1.1: Project & BDD Framework Setup (Day 1)

#### 1.1.1 FastAPI Project Structure
```
context-relay/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── context.py          # ContextPacket, ContextFragment models
│   │   ├── events.py           # Event models for SSE
│   │   └── responses.py        # Response schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── context.py      # Context operations endpoints
│   │   │   ├── events.py       # SSE streaming endpoint
│   │   │   └── health.py       # Health check endpoint
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── services/
│   │   ├── __init__.py
│   │   ├── mock_data.py        # MockDataService for realistic test data
│   │   └── event_broadcaster.py # SSE event broadcasting
│   └── core/
│       ├── __init__.py
│       ├── config.py           # Application configuration
│       └── events.py           # Event handling infrastructure
├── tests/
│   ├── features/
│   │   ├── context_initialization.feature
│   │   ├── context_relay.feature
│   │   ├── context_merging.feature
│   │   ├── context_pruning.feature
│   │   └── versioning.feature
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── test_context_steps.py
│   │   └── test_event_steps.py
│   └── conftest.py             # Test configuration and fixtures
├── requirements.txt
├── README.md
├── .env.example
├── architecture.md             # NEW: System architecture diagram
└── openapi.json                # Generated API specification
```

#### 1.1.2 Dependencies
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
pytest==7.4.3
pytest-bdd==6.1.1
httpx==0.25.1
pydantic-settings==2.1.0
```

#### 1.1.3 Configure BDD Test Framework
- Configure `pytest` and `pytest-bdd` to recognize `.feature` files.
- Set up linters and formatters to ensure code quality.
- Establish CI pipeline to run BDD tests on every commit.

### Phase 1.2: Foundational Models & Services (Day 1)

#### 1.2.1 Complete Pydantic Models
Implement all models from `logic.md` specification to define the data contracts.

**Critical Models to Implement:**
- `ContextPacket` - Core context container with fragments
- `ContextFragment` - Individual context pieces with metadata
- `RelayRequest` - Request payload for context relay operations
- `MergeRequest` - Request payload for context merging operations
- `PruneRequest` - Request payload for context pruning operations
- `VisualizationEvent` - **NEW**: UI-friendly event payloads for frontend visualization
- `SSEEvent` - Base event model for Server-Sent Events

#### 1.2.2 Mock Data Service
Implement a basic `MockDataService` to generate realistic data for passing BDD scenarios.

**Mock Service Requirements:**
- Generate realistic context fragments with semantic metadata
- Simulate conflict scenarios with overlapping content
- Provide mock embedding vectors for similarity calculations
- Create realistic decision traces for debugging
- Support deterministic data generation for test reproducibility

#### 1.2.3 **NEW**: Shared Schema Definition
Create a unified schema module accessible across all components:
- **File**: `app/models/shared.py`
- **Purpose**: Single source of truth for data structures
- **Export**: JSON Schema for frontend integration
- **Validation**: Automatic model validation and serialization

### Phase 1.3: BDD-Driven Mock API Implementation (Day 1-2)

**Goal**: Implement mock API endpoints and logic by making Gherkin scenarios pass one by one. Development for a feature is complete only when its scenarios pass.

#### **NEW**: Phase 1.3.0 API Contract Definition
Before implementing endpoints, define the complete API contract:

**Core Endpoints to Implement:**
- `POST /context/initialize` - Initialize new context packet
- `POST /context/relay` - Relay context between agents
- `POST /context/merge` - Merge multiple contexts
- `POST /context/prune` - Prune context fragments
- `POST /context/{context_id}/version` - Create new context version
- `GET /context/{context_id}/versions` - List context versions
- `GET /context/{context_id}` - Retrieve specific context
- `GET /events/relay` - **SSE endpoint for real-time events**
- `GET /health` - Health check endpoint

**Request/Response Schema Requirements:**
- All endpoints must accept and return structured JSON
- Include detailed validation with Pydantic models
- Provide clear error responses with appropriate HTTP status codes
- Support request ID tracking for debugging

#### 1.3.1 Implement Gherkin Scenarios: Context Initialization
- Develop the `POST /context/initialize` endpoint.
- Write mock logic to satisfy all scenarios in the "Context Initialization" feature.
- Ensure the implementation passes all `pytest-bdd` tests for this feature.
- **Validation**: Initialize context with proper fragment structure and metadata

#### 1.3.2 Implement Gherkin Scenarios: Context Relay
- Develop the `POST /context/relay` endpoint.
- Write mock logic to handle relays, conflicts, and removals as described in the scenarios.
- Ensure all "Context Relay" scenarios pass.
- **Key Features**: Conflict detection, semantic similarity mocking, decision traces

#### 1.3.3 Implement Gherkin Scenarios: Context Merging & Pruning
- Develop `POST /context/merge` and `POST /context/prune` endpoints.
- Implement mock logic for different strategies (union, semantic similarity, importance-based).
- Ensure all "Context Merging" and "Context Pruning" scenarios pass.
- **Mock Logic**: Simulate embedding vectors and similarity calculations

#### 1.3.4 Implement Gherkin Scenarios: Versioning
- Develop `POST /context/{context_id}/version` and `GET /context/{context_id}/versions`.
- Ensure all "Versioning Operations" scenarios pass.
- **Implementation**: In-memory version tracking with metadata

#### 1.3.5 Implement Gherkin Scenarios: SSE Event Streaming
- Develop the `GET /events/relay` endpoint for Server-Sent Events.
- Implement the event broadcasting system using `EventBroadcaster` service.
- Write tests to verify that all operations trigger the correct SSE events as specified in the Gherkin scenarios.
- **Critical Events**: `contextInitialized`, `relaySent`, `relayReceived`, `contextMerged`, `contextPruned`, `versionCreated`

#### **NEW**: 1.3.6 Visualization Event Contract
Implement UI-friendly event payloads alongside business events:

**VisualizationEvent Structure:**
```python
{
    "type": "relaySent",
    "timestamp": "2024-01-01T12:00:00Z",
    "ui": {
        "sourceNode": "AgentA",
        "targetNode": "AgentB",
        "color": "blue",
        "animate": true,
        "edgeId": "relay-123"
    },
    "data": {
        "contextId": "ctx-456",
        "fragmentCount": 3
    }
}
```

**Implementation Requirements:**
- Each business event generates a corresponding visualization event
- UI events contain only frontend-relevant data (node positions, colors, animations)
- Events are throttled to prevent overwhelming the frontend
- Support for event batching during high-frequency operations

### Phase 1.4: Documentation & Frontend Handoff (Day 3)

#### 1.4.1 API Documentation
- Auto-generate OpenAPI docs from the FastAPI implementation.
- Add examples directly from the Gherkin scenarios to the documentation.
- **Generate**: `openapi.json` for frontend TypeScript integration
- **Include**: Request/response examples, error codes, and event schemas

#### 1.4.2 Frontend Integration Guide & Quick Start
- Provide a comprehensive guide for the frontend developer on how to connect to the mock API and SSE stream.
- Include a `docker-compose` or simple script to run the BDD-tested mock server.

**Integration Guide Contents:**
- Server startup instructions and configuration
- API endpoint URL mapping and authentication
- SSE event subscription and handling patterns
- TypeScript type generation from OpenAPI spec
- Error handling and reconnection strategies
- Sample frontend code snippets

#### **NEW**: 1.4.3 CLI Integration Documentation
- Create command-to-endpoint mapping table for CLI developer
- Document configuration file format (`.contextrelayrc`)
- Provide example CLI workflows and expected responses

**CLI Command Mapping:**
| CLI Command | FastAPI Endpoint | Events Generated |
|-------------|------------------|------------------|
| `context init --session "demo" --input "data.json"` | `POST /context/initialize` | `contextInitialized` |
| `context relay --from AgentA --to AgentB --file "delta.json"` | `POST /context/relay` | `relaySent`, `relayReceived` |
| `context merge --contexts ctx1,ctx2` | `POST /context/merge` | `contextMerged` |
| `context prune --context ctx1 --strategy recency` | `POST /context/prune` | `contextPruned` |
| `context watch` | `GET /events/relay` (SSE) | All real-time events |

#### **NEW**: 1.4.4 Architecture Documentation
- Create `architecture.md` with system component diagram
- Document data flow between CLI, FastAPI, and future frontend
- Define ownership boundaries and integration points

**Architecture Diagram Elements:**
- Component ownership mapping (Backend vs Logic vs Frontend vs CLI)
- Data flow visualization with event streams
- API contract boundaries and responsibility areas
- Integration testing strategy and validation points

### Phase 1.5: Frontend Collaboration (Daily)

#### 1.5.1 Formal Frontend Developer Sync
- Schedule a brief daily sync with the frontend developer.
- **Goal**: Validate that the mock API's behavior and data structures are meeting frontend needs, preventing rework.
- Adjust mock data generation based on feedback.

#### **NEW**: 1.5.2 Validation Checklist for Frontend Handoff
Before declaring Phase 1 complete, validate:

**API Readiness:**
- [ ] All BDD scenarios pass consistently
- [ ] OpenAPI documentation is comprehensive and accurate
- [ ] SSE events are properly formatted and throttled
- [ ] Error responses include appropriate debugging information

**Frontend Integration:**
- [ ] Frontend developer can successfully connect to mock API
- [ ] TypeScript types can be generated from OpenAPI spec
- [ ] SSE event stream works with frontend client
- [ ] Visualization events match frontend UI requirements

**Documentation:**
- [ ] Integration guide is complete and tested
- [ ] CLI command mapping is documented
- [ ] Architecture diagram clearly shows system boundaries
- [ ] Quick start script runs without issues

#### **NEW**: 1.5.3 Phase 1 Acceptance Criteria
Phase 1 is complete when:

1. **Functional Requirements:**
   - All Gherkin scenarios pass via `pytest-bdd`
   - Mock API handles all documented endpoints correctly
   - SSE streaming works for real-time event visualization
   - Error handling covers all edge cases

2. **Integration Requirements:**
   - Frontend developer can integrate with mock API independently
   - CLI developer has complete command-to-endpoint mapping
   - Shared schemas work across all components
   - Visualization events support frontend animation needs

3. **Documentation Requirements:**
   - Complete OpenAPI specification with examples
   - Comprehensive integration guide
   - System architecture documentation
   - Working quick-start setup

---

## Phase 2: Core Functionality (1-2 weeks)

**Goal**: Replace mock implementations with real business logic and backend integrations, ensuring all BDD scenarios continue to pass.

### Phase 2.1: Database Integration (3-4 days)

#### 2.1.1 MongoDB Setup & Persistence
- Integrate MongoDB and implement data persistence for all context operations.
- Refactor BDD test step definitions to use a real test database instead of in-memory objects.

### Phase 2.2: Embedding Service Integration (3-4 days)

#### 2.2.1 Embedding Client & Vector Operations
- Integrate the real embedding service client.
- Update BDD tests to mock the embedding service API, ensuring the application handles it correctly.

### Phase 2.3: BDD-Driven Business Logic Implementation (4-5 days)

**Goal**: Re-implement the business logic for each feature, driven by the Gherkin scenarios.

#### 2.3.1 Implement Relay Scenarios with Real Logic
- Replace mock conflict detection with real semantic similarity checks.
- Ensure all "Context Relay" scenarios pass with the new logic.

#### 2.3.2 Implement Merge Scenarios with Real Logic
- Implement union, semantic similarity, and overwrite strategies using real data and embeddings.
- Ensure all "Context Merging" scenarios pass.

#### 2.3.3 Implement Pruning Scenarios with Real Logic
- Implement recency, semantic diversity, and importance-based pruning.
- Ensure all "Context Pruning" scenarios pass.

---

## Phase 3: Advanced Features (1-2 weeks)

**Goal**: Implement advanced features, adding new Gherkin scenarios as needed to define their behavior.

### Phase 3.1: Advanced Conflict Detection (3-4 days)
- **BDD First**: Write new scenarios for advanced conflict cases.
- Implement sophisticated similarity algorithms and decision trace analysis to make these new scenarios pass.

### Phase 3.2: Performance Optimizations (3-4 days)
- Implement caching and batch processing.
- BDD tests are used to verify functional correctness after optimization.

### Phase 3.3: Advanced Features (4-5 days)
- **BDD First**: Write new scenarios for multi-agent coordination, advanced versioning, etc.
- Implement the features to make the scenarios pass.

---

## Phase 4: Production Hardening (1 week)

**Goal**: Prepare system for production deployment, with BDD tests forming the core of regression testing.

### Phase 4.1: Testing & Quality (2-3 days)
- **BDD Suite**: The full suite of Gherkin scenarios serves as the primary regression test suite.
- Augment with integration, load, and error scenario testing.

### Phase 4.2: Monitoring & Observability (2 days)
- Implement logging, metrics, and health checks.

### Phase 4.3: Security & Deployment (2 days)
- Implement authentication, rate limiting, and production deployment configurations.

---

## Deliverables Summary

### Phase 1 Deliverables (Priority #1)
- ✅ Complete FastAPI server that passes all `gherkin.md` scenarios with mock data.
- ✅ Fully functional SSE event streaming with visualization contracts, tested via BDD scenarios.
- ✅ BDD test framework and initial step definitions with automated endpoint testing.
- ✅ **NEW**: Shared schema module for unified data structures across all components.
- ✅ **NEW**: CLI-to-endpoint mapping documentation for CLI developer integration.
- ✅ **NEW**: System architecture diagram showing component ownership and data flow.
- ✅ **NEW**: Comprehensive frontend integration guide with working examples.
- ✅ **NEW**: OpenAPI specification with TypeScript type generation support.

### Phase 2 Deliverables
- ✅ Real MongoDB and Embedding service integration.
- ✅ All `gherkin.md` scenarios passing with real business logic.

### Phase 3 Deliverables
- ✅ New Gherkin scenarios for advanced features.
- ✅ Implementation of advanced features, passing all related scenarios.

### Phase 4 Deliverables
- ✅ Production-ready system with a comprehensive BDD regression suite.
- ✅ Monitoring, security, and deployment configurations.

---

## Success Criteria

### Phase 1 Success (Frontend Developer Ready)
- Frontend developer can start immediately against a stable, behaviorally-correct API with full visualization support.
- All API endpoints and SSE events are implemented and pass their corresponding Gherkin scenarios.
- **NEW**: CLI developer has complete integration path with command-to-endpoint mapping.
- **NEW**: All components share unified schemas via exported JSON specifications.
- **NEW**: Complete documentation exists, including architecture diagrams and integration guides.
- **NEW**: TypeScript types can be generated automatically from OpenAPI specification.
- **NEW**: Visualization events provide UI-ready payloads for frontend animation.

### Final Success
- **All `gherkin.md` scenarios are automated and pass continuously.**
- Complete implementation of `logic.md` specification, verified by the BDD suite.
- Production-ready system with high confidence due to comprehensive behavioral testing.

---

## Risk Mitigation

### Phase 1 Risks
- **Risk**: Mock data not realistic enough.
- **Mitigation**: Use real examples from Gherkin scenarios. **Formal daily sync with frontend developer to validate data and behavior.**
- **NEW - Risk**: Component integration gaps between CLI, FastAPI, and frontend.
- **Mitigation**: Create shared schemas and clear API contracts. Document all data flows and component boundaries.
- **NEW - Risk**: Frontend visualization requirements not aligned with event structure.
- **Mitigation**: Implement dedicated VisualizationEvent model with UI-friendly payloads. Validate with frontend developer early.
- **NEW - Risk**: Architecture complexity leads to integration confusion.
- **Mitigation**: Create comprehensive architecture diagram with ownership mapping. Establish clear component boundaries.

### Phase 2 Risks
- **Risk**: Backend service integration delays.
- **Mitigation**: The BDD-tested mock API from Phase 1 provides a stable fallback for frontend development.

### Overall Risks
- **Risk**: Scope creep.
- **Mitigation**: All new functionality must be defined in a Gherkin scenario first, making scope changes explicit and deliberate.

---

## Timeline Summary

| Phase | Duration | Start | End | Priority |
|-------|----------|-------|-----|----------|
| Phase 1: BDD Mock API | 2-3 days | Day 1 | Day 3 | **CRITICAL** |
| Phase 2: Core Logic | 1-2 weeks | Day 4 | Day 14 | High |
| Phase 3: Advanced | 1-2 weeks | Day 15 | Day 28 | Medium |
| Phase 4: Production | 1 week | Day 29 | Day 35 | Medium |

**Total Timeline: 5 weeks**
**Frontend Developer Ready: Day 3** 🎯