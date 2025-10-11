# Context Relay System - Integration Guide

## Overview

This guide provides comprehensive instructions for integrating with the Context Relay System API and Server-Sent Events (SSE) stream. This is a **Phase 1 Mock API** designed to enable parallel frontend development with realistic behavior and data contracts.

## Quick Start

### 1. Start the Mock API Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Server will be available at http://localhost:8000
```

### 2. Verify Server Status

```bash
curl http://localhost:8000/health/
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "0.1.0",
  "components": {
    "event_broadcaster": "healthy",
    "mock_data_service": "healthy",
    "storage": "in-memory",
    "sse_streaming": "active"
  }
}
```

### 3. Explore API Documentation

Open http://localhost:8000/docs in your browser to see the interactive OpenAPI documentation.

## API Endpoints

### Core Context Operations

#### Initialize Context
```http
POST /context/initialize
Content-Type: application/json

{
  "session_id": "demo-session-123",
  "initial_fragments": [
    {
      "id": "fragment-1",
      "type": "text",
      "content": "Initial context content",
      "source_agent": "human",
      "importance_score": 0.8,
      "metadata": {}
    }
  ],
  "metadata": {
    "user": "demo-user",
    "purpose": "testing"
  }
}
```

#### Relay Context
```http
POST /context/relay
Content-Type: application/json

{
  "context_id": "ctx-abc123",
  "from_agent": "ai_assistant",
  "to_agent": "human",
  "delta_fragments": [
    {
      "id": "fragment-2",
      "type": "text",
      "content": "Additional context from AI",
      "source_agent": "ai_assistant",
      "importance_score": 0.9
    }
  ],
  "conflict_resolution": "union"
}
```

#### Merge Contexts
```http
POST /context/merge
Content-Type: application/json

{
  "context_ids": ["ctx-abc123", "ctx-def456"],
  "target_context_id": "ctx-merged-789",
  "merge_strategy": "union"
}
```

#### Prune Context
```http
POST /context/prune
Content-Type: application/json

{
  "context_id": "ctx-abc123",
  "strategy": "recency",
  "max_fragments": 5
}
```

#### Create Version
```http
POST /context/{context_id}/version
Content-Type: application/json

{
  "version_metadata": {
    "label": "checkpoint-1",
    "reason": "milestone achieved"
  }
}
```

## Server-Sent Events (SSE)

### Connect to Event Stream

```javascript
const eventSource = new EventSource('http://localhost:8000/events/relay');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};

eventSource.addEventListener('contextInitialized', function(event) {
  const data = JSON.parse(event.data);
  console.log('Context initialized:', data);
});

eventSource.addEventListener('viz:contextInitialized', function(event) {
  const data = JSON.parse(event.data);
  // Use UI-specific data for visualization
  console.log('UI Event:', data.ui);
});
```

### Available Event Types

#### Business Events
- `contextInitialized` - New context created
- `relaySent` - Context relay initiated
- `relayReceived` - Context relay processed
- `contextMerged` - Contexts merged
- `contextPruned` - Context pruned
- `versionCreated` - Version created

#### Visualization Events (prefixed with `viz:`)
- `viz:contextInitialized` - UI event for node creation
- `viz:relaySent` - UI event for edge animation (outgoing)
- `viz:relayReceived` - UI event for edge animation (incoming)
- `viz:contextMerged` - UI event for node merge animation
- `viz:contextPruned` - UI event for node shrink animation
- `viz:versionCreated` - UI event for version indicator

### Event Payload Examples

#### Business Event: `relaySent`
```json
{
  "type": "relaySent",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "data": {
    "contextId": "ctx-abc123",
    "fromAgent": "ai_assistant",
    "toAgent": "human",
    "fragmentCount": 3
  }
}
```

#### Visualization Event: `viz:relaySent`
```json
{
  "type": "viz:relaySent",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "ui": {
    "sourceNode": "ai_assistant",
    "targetNode": "human",
    "color": "blue",
    "animate": true,
    "edgeId": "relay-ctx-abc123",
    "effect": "flow"
  },
  "data": {
    "contextId": "ctx-abc123",
    "fragmentCount": 3
  }
}
```

## Frontend Integration

### TypeScript Type Generation

1. **Generate OpenAPI Schema:**
   ```bash
   curl http://localhost:8000/openapi.json > openapi.json
   ```

2. **Use TypeScript Tools:**
   ```bash
   npm install -g openapi-typescript
   openapi-typescript openapi.json -o frontend-types.ts
   ```

### React Integration Example

```typescript
// types.ts - Generated from OpenAPI
import { ContextPacket, RelayRequest, RelayResponse } from './frontend-types';

// ContextRelayService.ts
class ContextRelayService {
  private baseUrl = 'http://localhost:8000';
  private eventSource: EventSource | null = null;

  async initializeContext(sessionId: string, fragments: any[]) {
    const response = await fetch(`${this.baseUrl}/context/initialize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        initial_fragments: fragments
      })
    });
    return response.json();
  }

  async relayContext(request: RelayRequest) {
    const response = await fetch(`${this.baseUrl}/context/relay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return response.json();
  }

  connectToEvents(onEvent: (event: any) => void) {
    this.eventSource = new EventSource(`${this.baseUrl}/events/relay`);

    this.eventSource.onmessage = (event) => {
      onEvent(JSON.parse(event.data));
    };

    // Listen for visualization events
    this.eventSource.addEventListener('viz:relaySent', (event) => {
      onEvent(JSON.parse(event.data));
    });

    return this.eventSource;
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

// React Component Example
import React, { useState, useEffect } from 'react';

const ContextVisualization: React.FC = () => {
  const [contexts, setContexts] = useState<Map<string, ContextPacket>>(new Map());
  const [events, setEvents] = useState<any[]>([]);
  const service = new ContextRelayService();

  useEffect(() => {
    const eventSource = service.connectToEvents((event) => {
      setEvents(prev => [...prev, event]);

      // Handle visualization events
      if (event.type.startsWith('viz:')) {
        // Update React Flow visualization
        handleVisualizationEvent(event);
      }
    });

    return () => {
      service.disconnect();
    };
  }, []);

  const handleVisualizationEvent = (event: any) => {
    // Implement React Flow updates based on event.ui data
    switch (event.type) {
      case 'viz:relaySent':
        // Animate edge from sourceNode to targetNode
        break;
      case 'viz:contextInitialized':
        // Add new node with event.ui.nodeId
        break;
      // ... handle other event types
    }
  };

  return (
    <div>
      <h1>Context Relay Visualization</h1>
      {/* React Flow visualization components */}
    </div>
  );
};
```

## CLI Integration

### Command-to-Endpoint Mapping

| CLI Command | API Endpoint | Method | Events Generated |
|-------------|--------------|--------|------------------|
| `context init --session "demo" --input "data.json"` | `/context/initialize` | POST | `contextInitialized` |
| `context relay --from AgentA --to AgentB --file "delta.json"` | `/context/relay` | POST | `relaySent`, `relayReceived` |
| `context merge --contexts ctx1,ctx2` | `/context/merge` | POST | `contextMerged` |
| `context prune --context ctx1 --strategy recency` | `/context/prune` | POST | `contextPruned` |
| `context watch` | `/events/relay` | GET (SSE) | All real-time events |

### Example CLI Workflow

```bash
# 1. Initialize a context
context init --session "demo-session" --input "initial_data.json"

# 2. Relay context between agents
context relay --from ai_assistant --to human --file "delta.json"

# 3. Watch real-time events
context watch --api-url "http://localhost:8000"
```

## Configuration

### Environment Variables

```bash
# API Configuration
CONTEXT_RELAY_API_URL=http://localhost:8000
CONTEXT_RELAY_EVENTS_URL=http://localhost:8000/events/relay

# Frontend Configuration
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_EVENTS_URL=http://localhost:8000/events/relay

# CLI Configuration
CONTEXT_RELAY_HOST=localhost
CONTEXT_RELAY_PORT=8000
```

### Configuration File (`.contextrelayrc`)

```json
{
  "api": {
    "base_url": "http://localhost:8000",
    "timeout": 30000,
    "retry_attempts": 3
  },
  "events": {
    "url": "http://localhost:8000/events/relay",
    "reconnect_interval": 5000,
    "max_reconnect_attempts": 10
  },
  "logging": {
    "level": "info",
    "include_events": true
  }
}
```

## Error Handling

### HTTP Error Responses

```json
{
  "detail": "Context ctx-abc123 not found",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### SSE Error Handling

```javascript
eventSource.addEventListener('error', function(event) {
  console.error('SSE connection error:', event);

  // Implement reconnection logic
  setTimeout(() => {
    connectToEvents();
  }, 5000);
});
```

### Client-Side Error Handling

```typescript
class ContextRelayError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public endpoint?: string
  ) {
    super(message);
    this.name = 'ContextRelayError';
  }
}

// Usage
try {
  const result = await service.initializeContext(sessionId, fragments);
} catch (error) {
  if (error instanceof ContextRelayError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

## Testing Integration

### Unit Testing API Calls

```typescript
// Using Jest and MSW
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.post('http://localhost:8000/context/initialize', (req, res, ctx) => {
    return res(ctx.json({
      context: {
        id: 'test-context-id',
        session_id: 'test-session',
        fragments: [],
        version: 1
      },
      success: true,
      message: 'Context initialized successfully'
    }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('initialize context', async () => {
  const service = new ContextRelayService();
  const result = await service.initializeContext('test-session', []);

  expect(result.success).toBe(true);
  expect(result.context.id).toBe('test-context-id');
});
```

### Integration Testing with SSE

```typescript
test('SSE event reception', (done) => {
  const service = new ContextRelayService();

  const eventSource = service.connectToEvents((event) => {
    if (event.type === 'contextInitialized') {
      expect(event.data.contextId).toBeDefined();
      done();
    }
  });

  // Trigger an event
  service.initializeContext('test-session', []);
});
```

## Performance Considerations

### Event Throttling
- Visualization events are throttled to prevent overwhelming the frontend
- Maximum 10 events per second per event type
- Events are batched during high-frequency operations

### Connection Management
- Implement exponential backoff for reconnections
- Monitor connection health with ping events
- Clean up connections on component unmount

### Memory Management
- Event history is limited to 1000 events
- Consider implementing local event filtering
- Monitor memory usage in long-running applications

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure frontend URL is in CORS origins list
   - Check that API URL is correct in configuration

2. **SSE Connection Drops**
   - Implement reconnection logic
   - Check network connectivity
   - Monitor server health endpoint

3. **Event Not Received**
   - Verify event type spelling
   - Check event listener registration
   - Ensure client is subscribed to event type

### Debug Tools

```bash
# Check API health
curl http://localhost:8000/health/

# View event statistics
curl http://localhost:8000/events/stats

# Get event history
curl "http://localhost:8000/events/history?limit=50"

# View available event types
curl http://localhost:8000/events/types
```

### Debug Logging

```typescript
// Enable debug logging
const DEBUG = true;

const debugLog = (message: string, data?: any) => {
  if (DEBUG) {
    console.log(`[ContextRelay] ${message}`, data);
  }
};

// Usage in event handlers
eventSource.addEventListener('relaySent', (event) => {
  const data = JSON.parse(event.data);
  debugLog('Relay sent event received', data);
});
```

## Next Steps

### For Frontend Developers
1. Set up React Flow visualization components
2. Implement event-driven UI updates
3. Add context management interface
4. Test with various scenarios

### For CLI Developers
1. Implement command-line interface
2. Add configuration file support
3. Implement event subscription and display
4. Add testing commands

### For Testing
1. Write comprehensive integration tests
2. Test error scenarios
3. Validate event handling
4. Performance testing

## Support

- **API Documentation**: http://localhost:8000/docs
- **Event Types**: http://localhost:8000/events/types
- **Health Check**: http://localhost:8000/health/
- **Architecture**: See `architecture.md`

## Mock API Limitations (Phase 1)

- Data is stored in memory only (lost on server restart)
- Embedding vectors are mocked
- No persistence or database integration
- Limited to basic conflict detection
- No authentication or rate limiting

These limitations will be addressed in Phase 2 when real backend services are integrated.