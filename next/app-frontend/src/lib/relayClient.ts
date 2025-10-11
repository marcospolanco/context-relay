import type {
  InitializeResponse,
  RelayRequest,
  RelayResponse,
  RelayEvent,
  ContextPacket,
} from '../types/relay';

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK === 'true' || true; // Default to mock for demo

// Event callback type
type EventCallback = (event: RelayEvent) => void;

let eventCallbacks: EventCallback[] = [];
let mockEventSource: EventSource | null = null;

/**
 * Initialize a new context with input data
 */
export async function sendInitialize(input: string): Promise<InitializeResponse> {
  if (USE_MOCK_DATA) {
    return mockInitialize(input);
  }

  const response = await fetch(`${API_BASE_URL}/api/context/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId: crypto.randomUUID(), input }),
  });

  if (!response.ok) {
    throw new Error(`Initialize failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send a relay from one agent to another
 */
export async function sendRelay(body: RelayRequest): Promise<RelayResponse> {
  if (USE_MOCK_DATA) {
    return mockRelay(body);
  }

  const response = await fetch(`${API_BASE_URL}/api/context/relay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Relay failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Subscribe to relay events (SSE or WebSocket)
 */
export function onEvent(callback: EventCallback): () => void {
  eventCallbacks.push(callback);

  // Start mock event stream if not already started
  if (USE_MOCK_DATA && !mockEventSource) {
    // Mock events will be triggered by sendInitialize and sendRelay
  } else if (!USE_MOCK_DATA && !mockEventSource) {
    startEventStream();
  }

  // Return unsubscribe function
  return () => {
    eventCallbacks = eventCallbacks.filter((cb) => cb !== callback);
  };
}

/**
 * Emit an event to all subscribers
 */
function emitEvent(event: RelayEvent): void {
  eventCallbacks.forEach((cb) => cb(event));
}

/**
 * Start SSE connection to backend
 */
function startEventStream(): void {
  mockEventSource = new EventSource(`${API_BASE_URL}/events`);

  mockEventSource.onmessage = (event) => {
    try {
      const relayEvent: RelayEvent = JSON.parse(event.data);
      emitEvent(relayEvent);
    } catch (err) {
      console.error('Failed to parse event:', err);
    }
  };

  mockEventSource.onerror = (err) => {
    console.error('EventSource error:', err);
    mockEventSource?.close();
    mockEventSource = null;
    // Attempt reconnect after 3s
    setTimeout(startEventStream, 3000);
  };
}

// ========================================
// MOCK DATA FUNCTIONS
// These will be replaced by real backend data
// ========================================

let mockContextId = 'mock-context-1';
let mockPacket: ContextPacket = {};

function mockInitialize(input: string): Promise<InitializeResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      mockContextId = `context-${Date.now()}`;
      mockPacket = {
        input,
        history: [{ step: 'initialized', ts: Date.now() }],
      };

      const response: InitializeResponse = {
        contextId: mockContextId,
        packet: mockPacket,
      };

      // Emit event
      emitEvent({
        type: 'contextInitialized',
        contextId: mockContextId,
        packet: mockPacket,
      });

      resolve(response);
    }, 300);
  });
}

function mockRelay(body: RelayRequest): Promise<RelayResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Emit relaySent event
      emitEvent({
        type: 'relaySent',
        from: body.from,
        to: body.to,
        contextId: body.contextId,
        delta: body.delta,
      });

      // Simulate agent processing
      setTimeout(() => {
        // Update packet based on the agent receiving the relay
        updateMockPacket(body.to);

        // Emit relayReceived event
        emitEvent({
          type: 'relayReceived',
          to: body.to,
          contextId: body.contextId,
          packet: mockPacket,
        });

        resolve({
          packet: mockPacket,
        });
      }, 800);
    }, 200);
  });
}

function updateMockPacket(agent: string): void {
  mockPacket.history = mockPacket.history || [];
  mockPacket.history.push({ step: `relay-to-${agent}`, ts: Date.now() });

  switch (agent) {
    case 'analyzer':
      mockPacket.analyzerOutput = {
        summary: 'Analyzed the input and identified key areas',
        strengths: ['Strong technical background', 'Leadership experience'],
        gaps: ['Limited cloud experience', 'No ML projects'],
      };
      break;

    case 'designer':
      mockPacket.designerOutput = {
        interviewQuestions: [
          'Can you describe your experience with distributed systems?',
          'Tell me about a time you led a technical project',
          'How would you approach learning cloud technologies?',
        ],
        rationale: 'Questions designed to probe strengths and address gaps',
      };
      break;

    case 'evaluator':
      mockPacket.evaluatorOutput = {
        score: 8.5,
        notes: 'Strong questions that target both strengths and development areas',
      };
      break;
  }
}

/**
 * Export mock data generator for testing
 * Your logic teammate can replace this with their mock data
 */
export function setMockDataGenerator(generator: {
  initialize?: (input: string) => Promise<InitializeResponse>;
  relay?: (body: RelayRequest) => Promise<RelayResponse>;
}): void {
  if (generator.initialize) {
    // Override mock functions
    console.log('Mock data generator set for initialize');
  }
  if (generator.relay) {
    console.log('Mock data generator set for relay');
  }
}
