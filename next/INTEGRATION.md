# Frontend Integration Guide

Quick reference for integrating the frontend with backend mock data or real APIs.

## Current State

The frontend is **fully functional** with built-in mock data and ready to demo.

- Location: `/app-frontend/`
- Status: Built and tested
- Mode: Mock data (standalone)

## For Your Logic Teammate

Your logic teammate can provide mock data in two ways:

### Method 1: Replace Mock Functions in relayClient.ts

Edit `app-frontend/src/lib/relayClient.ts` and update these functions:

```typescript
// Around line 120
function mockInitialize(input: string): Promise<InitializeResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      // YOUR MOCK DATA HERE
      const mockData = {
        contextId: `context-${Date.now()}`,
        packet: {
          input,
          // Add your analyzer output, designer output, etc.
        }
      };

      emitEvent({
        type: 'contextInitialized',
        contextId: mockData.contextId,
        packet: mockData.packet,
      });

      resolve(mockData);
    }, 300);
  });
}

function mockRelay(body: RelayRequest): Promise<RelayResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      emitEvent({
        type: 'relaySent',
        from: body.from,
        to: body.to,
        contextId: body.contextId,
      });

      setTimeout(() => {
        // YOUR RELAY LOGIC HERE
        updateMockPacket(body.to); // Or replace this entirely

        emitEvent({
          type: 'relayReceived',
          to: body.to,
          contextId: body.contextId,
          packet: mockPacket,
        });

        resolve({ packet: mockPacket });
      }, 800);
    }, 200);
  });
}

function updateMockPacket(agent: string): void {
  // YOUR AGENT OUTPUT HERE
  switch (agent) {
    case 'analyzer':
      mockPacket.analyzerOutput = {
        // Your analyzer output
      };
      break;
    case 'designer':
      mockPacket.designerOutput = {
        // Your designer output
      };
      break;
    case 'evaluator':
      mockPacket.evaluatorOutput = {
        // Your evaluator output
      };
      break;
  }
}
```

### Method 2: Use setMockDataGenerator

Create a separate file with your mock logic and inject it:

```typescript
// mockDataProvider.ts (your logic teammate creates this)
import { setMockDataGenerator } from './lib/relayClient';

export function setupCustomMockData() {
  setMockDataGenerator({
    initialize: async (input) => {
      // Your logic here
      const result = await yourCustomAnalyzer(input);
      return {
        contextId: generateId(),
        packet: result
      };
    },
    relay: async (body) => {
      // Your logic here
      const result = await yourCustomRelay(body);
      return {
        packet: result
      };
    }
  });
}

// Then in App.tsx or main.tsx:
import { setupCustomMockData } from './mockDataProvider';
setupCustomMockData();
```

## TypeScript Types (Already Defined)

Your mock data must match these types (see `src/types/relay.ts`):

```typescript
interface ContextPacket {
  input?: string;
  analyzerOutput?: {
    summary?: string;
    strengths?: string[];
    gaps?: string[];
  };
  designerOutput?: {
    interviewQuestions?: string[];
    rationale?: string;
  };
  evaluatorOutput?: {
    score?: number;
    notes?: string;
  };
  history?: { step: string; ts: number }[];
}
```

## Event Flow

The frontend listens for these events:

1. **contextInitialized** - When analysis starts
2. **relaySent** - Triggers edge animation
3. **relayReceived** - Updates node and stops animation
4. **contextUpdated** - Updates JSON panel

Make sure to call `emitEvent()` in your mock functions to trigger UI updates.

## For Your Backend Teammate

When the FastAPI backend is ready:

1. Update `app-frontend/.env`:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_USE_MOCK=false
   ```

2. Implement these endpoints:
   - `POST /api/context/initialize` → Returns `{ contextId, packet }`
   - `POST /api/context/relay` → Returns `{ packet, conflicts? }`
   - `GET /events` → SSE stream for real-time updates

3. Add CORS middleware (see CLAUDE.md)

## Testing Checklist

- [ ] Nodes activate when receiving context
- [ ] Edges animate during relay
- [ ] JSON panel updates with new data
- [ ] Snippets appear in node cards
- [ ] Demo controls work step-by-step
- [ ] "Run Full Flow" completes successfully

## Files to Share with Teammates

- `CLAUDE.md` - Full architecture spec
- `INTEGRATION.md` - This file
- `app-frontend/src/types/relay.ts` - Type definitions
- `app-frontend/README.md` - Frontend setup guide

## Quick Demo Test

```bash
cd app-frontend
npm install
npm run dev
```

Then:
1. Click "Run Full Flow"
2. Watch the visualization
3. Check JSON panel on right
4. Verify all three agents activate in sequence

Done!
