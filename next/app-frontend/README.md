# Interview Assistant - Context Relay Frontend

React + Vite frontend for visualizing context handoffs between agents (Analyzer → Question Designer → Evaluator).

## Features

- Interactive React Flow visualization
- Real-time context packet display
- Animated relay transitions
- Mock data mode for standalone demo
- Ready for FastAPI backend integration

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The app will be available at `http://localhost:5173`

## Project Structure

```
app-frontend/
├── src/
│   ├── components/
│   │   ├── AgentNode.tsx          # Custom node component
│   │   ├── AnimatedEdge.tsx       # Animated edge component
│   │   ├── DemoControls.tsx       # Control panel for demo
│   │   └── InterviewRelayFlow.tsx # Main React Flow component
│   ├── lib/
│   │   └── relayClient.ts         # API client (mock + real)
│   ├── types/
│   │   └── relay.ts               # TypeScript types matching CLAUDE.md
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env                           # Environment configuration
└── package.json
```

## Configuration

Edit `.env` to configure the frontend:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Use mock data for demo (set to 'false' when backend is ready)
VITE_USE_MOCK=true
```

## Using Mock Data (Current Setup)

The app currently runs in **mock mode** - perfect for demos without a backend!

### Demo Controls

1. **Start Analysis** - Initialize context with resume input
2. **Run Full Flow** - Automatically run all steps
3. **Step-by-step** - Manually trigger each relay

### What Happens

1. User inputs resume text
2. Analyzer node activates → extracts insights
3. Context relays to Designer → generates questions
4. Context relays to Evaluator → scores output
5. JSON panel shows evolving context packet

## Integrating with Backend

When your logic teammate provides mock data or the backend is ready:

### Option 1: Custom Mock Data

```typescript
// In your code
import { setMockDataGenerator } from './lib/relayClient';

setMockDataGenerator({
  initialize: async (input) => {
    // Your custom mock logic
    return { contextId: '...', packet: {...} };
  },
  relay: async (body) => {
    // Your custom relay logic
    return { packet: {...} };
  }
});
```

### Option 2: Connect to Real Backend

1. Update `.env`:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_USE_MOCK=false
   ```

2. Ensure your FastAPI backend implements:
   - `POST /api/context/initialize`
   - `POST /api/context/relay`
   - `GET /events` (SSE stream)

See `CLAUDE.md` for API contracts.

## API Contracts (from CLAUDE.md)

### REST Endpoints

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/context/initialize` | POST | `{ sessionId, input }` | `{ contextId, packet }` |
| `/api/context/relay` | POST | `{ from, to, contextId, delta }` | `{ packet, conflicts? }` |

### Event Stream (SSE)

Events emitted:
- `contextInitialized`
- `relaySent`
- `relayReceived`
- `contextUpdated`
- `versionCreated`

## Technology Stack

- **React 18** - UI framework
- **Vite** - Build tool & dev server
- **React Flow** - Node graph visualization
- **TailwindCSS** - Styling
- **TypeScript** - Type safety

## Development Tips

- HMR (Hot Module Replacement) is enabled - changes appear instantly
- React Flow node IDs are stable: `analyzer`, `designer`, `evaluator`
- Edge IDs are stable: `a-b`, `b-c`
- Context packet updates trigger UI animations automatically

## Architecture Notes

- **Single Source of Truth**: Backend owns state, frontend reflects it
- **Event-Driven**: UI responds to relay events, not polling
- **Stateless Components**: All data flows through React Flow state
- **Type-Safe**: Full TypeScript coverage matching API contracts

## Next Steps

1. Test the demo with mock data
2. Coordinate with logic teammate for real mock data
3. Integrate with FastAPI backend when ready
4. Add more agents or features as needed

## Troubleshooting

**Issue**: Animations not working
- Check browser console for event logs
- Verify mock mode is enabled in `.env`

**Issue**: Build fails
- Run `npm install` to ensure dependencies are installed
- Check Node.js version (20.19+ or 22.12+ recommended)

**Issue**: Can't connect to backend
- Verify `VITE_API_URL` in `.env`
- Check CORS configuration on FastAPI
- Ensure backend is running

## Demo Sequence

1. Enter resume text in Demo Controls
2. Click "Run Full Flow" or step through manually
3. Watch nodes activate and edges animate
4. See context packet evolve in side panel
5. Observe final evaluation score

Ready to demo!
