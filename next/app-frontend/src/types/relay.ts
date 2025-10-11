// Context Packet Structure (from CLAUDE.md)
export interface ContextPacket {
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

// Relay Event Types (from CLAUDE.md)
export type RelayEvent =
  | { type: 'contextInitialized'; contextId: string; packet: ContextPacket }
  | { type: 'relaySent'; from: string; to: string; contextId: string; delta?: any }
  | { type: 'relayReceived'; to: string; contextId: string; packet: ContextPacket; conflicts?: any[] }
  | { type: 'contextUpdated'; contextId: string; packet: ContextPacket; delta?: any }
  | { type: 'versionCreated'; versionId: string; contextId: string; summary?: string };

// Request/Response types for API
export interface InitializeRequest {
  sessionId: string;
  input: string;
}

export interface InitializeResponse {
  contextId: string;
  packet: ContextPacket;
}

export interface RelayRequest {
  from: string;
  to: string;
  contextId: string;
  delta?: any;
}

export interface RelayResponse {
  packet: ContextPacket;
  conflicts?: any[];
}

// Node data for React Flow
export interface AgentNodeData {
  label: string;
  subtitle: string;
  active: boolean;
  latestSnippet?: string;
  inputData?: any;
  outputData?: any;
}
