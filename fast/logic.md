Below is a logic.md specification for your logic layer in FastAPI. It defines:
	•	data models / schema
	•	REST / SSE endpoints & contracts (with request/response)
	•	internal event types
	•	how the logic layer integrates with backend storage (MongoDB, embeddings)
	•	how the events map to the React frontend
	•	sequence flows

Treat this as a blueprint your team can implement against.

⸻

Logic Layer Spec (FastAPI) — context relay

Purpose & responsibilities

The logic layer:
	•	Implements context relay operations (initialize, relay, merge, prune, versioning)
	•	Emits event streams (via SSE) to the frontend UI for visualization
	•	Interfaces with backend services (embedding service, MongoDB storage)
	•	Validates contracts with React frontend (event schema, REST API)

It does not render UI; it is purely server-side logic + event streaming.

⸻

Terminology & core data concepts

Here are the key models and types used in the logic layer.

# Pydantic / Python models (pseudo code)

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

class ContextFragment(BaseModel):
    fragment_id: str  # unique id for fragment
    content: Any       # e.g. JSON representing fact / summary / outline piece
    embedding: Optional[List[float]]  # vector embedding
    metadata: Dict[str, Any]

class ContextPacket(BaseModel):
    context_id: str
    fragments: List[ContextFragment]
    decision_trace: List[Dict[str, Any]]  # e.g. sequence of {agent, decision, timestamp}
    metadata: Dict[str, Any]
    version: int  # incremental version

class ContextDelta(BaseModel):
    new_fragments: List[ContextFragment]
    removed_fragment_ids: List[str] = []
    decision_updates: List[Dict[str, Any]] = []

class RelayRequest(BaseModel):
    from_agent: str
    to_agent: str
    context_id: str
    delta: ContextDelta

class RelayResponse(BaseModel):
    context_packet: ContextPacket
    conflicts: Optional[List[str]] = None  # list of fragment_ids conflicting

class MergeRequest(BaseModel):
    context_ids: List[str]
    merge_strategy: str  # e.g. "union", "overwrite", "semantic_similarity"

class MergeResponse(BaseModel):
    merged_context: ContextPacket
    conflict_report: Optional[List[str]]

class PruneRequest(BaseModel):
    context_id: str
    pruning_strategy: str
    budget: int

class PruneResponse(BaseModel):
    pruned_context: ContextPacket

class VersionRequest(BaseModel):
    context_id: str
    version_label: str  # optional human label

class VersionInfo(BaseModel):
    version_id: str
    context_id: str
    timestamp: str
    summary: Optional[str]

class InitializeRequest(BaseModel):
    session_id: str
    initial_input: Any
    metadata: Dict[str, Any]

class InitializeResponse(BaseModel):
    context_id: str
    context_packet: ContextPacket

You may extend or adjust fields, but these give you a basic contract for context relay.

⸻

Internal event types (for SSE)

The logic layer emits a stream of events to the frontend. Each event has:
	•	type — string event name
	•	payload — JSON object (per schema)

Event types:

Event Type	Payload Schema	Meaning / usage
contextInitialized	{ context_id: str, context_packet: ContextPacket }	After initialization
relaySent	{ from_agent: str, to_agent: str, context_id: str, delta: ContextDelta }	just before a relay operation
relayReceived	{ to_agent: str, context_id: str, new_packet: ContextPacket, conflicts?: List[str] }	after relay/merge in target agent
contextMerged	{ input_context_ids: [str], merged_context: ContextPacket, conflict_report?: List[str] }	after merge of multiple contexts
contextPruned	{ context_id: str, pruned_context: ContextPacket }	after pruning operation
contextUpdated	{ context_id: str, new_packet: ContextPacket, delta: ContextDelta }	any update not captured by above
versionCreated	{ version_info: VersionInfo }	a version snapshot is stored
error	{ context_id?: str, error_code: str, message: str }	any error in logic layer

These are the events the React frontend subscribes to via SSE.

⸻

REST / HTTP API — request / response contracts

These endpoints allow the React app (or orchestration logic) to invoke actions in the logic layer.

Path	Method	Request Body	Response Body	Description
/context/initialize	POST	InitializeRequest	InitializeResponse	Start a new context with initial input
/context/relay	POST	RelayRequest	RelayResponse	Relay context from one agent to another (applies merging / conflict logic)
/context/merge	POST	MergeRequest	MergeResponse	Merge multiple contexts into one
/context/prune	POST	PruneRequest	PruneResponse	Prune less relevant fragments to fit budget
/context/version	POST	VersionRequest	VersionInfo	Create snapshot / version
/context/versions/{context_id}	GET	—	List[VersionInfo]	List all versions of a context
/context/{context_id}	GET	—	ContextPacket	Fetch full context packet
/events/relay	GET	— (SSE)	Stream of events (see event types)	SSE event stream for UI updates

All JSON responses must follow the Pydantic / schema models above.

⸻

Backend & embedding integration (calls you’ll make internally)

Within the logic layer, you will call into backend services for:
	1.	Embedding service
	•	Whenever you create new fragments (in delta.new_fragments), call embedding API to compute embeddings (unless already provided).
	•	You may batch embeddings for efficiency.
	2.	MongoDB / persistent store
	•	Store each ContextPacket document in a collection with an indexed context_id
	•	Also store fragments within the packet (or separate “fragment” collection)
	•	Store versions / snapshots in a separate collection
	3.	Vector / semantic lookup
	•	When merging or pruning, use vector search (via MongoDB Atlas vector search) to detect near-duplicate fragments or semantically close ones
	•	E.g. db.fragments.aggregate([{ $vectorSearch: { queryVector: ..., vectorField: "embedding", k: ... } }, ... ])
	•	Use that to decide which fragments to drop / merge
	4.	Conflict detection logic
	•	Use embedding similarity, content rules, decision trace consistency to detect conflicting fragments
	•	For any conflict, include fragment IDs in conflicts arrays

Make sure embedding and MongoDB clients are injected dependencies (e.g. via FastAPI dependencies).

⸻

SSE implementation and subscription model

You need an SSE endpoint /events/relay that streams event messages to any connected React clients. The logic layer publishes events when state changes occur.

SSE mechanics (in FastAPI)
	•	Use StreamingResponse or a helper library like fastapi_sse to send SSE events.  ￼
	•	Maintain a list of subscriber queues (asyncio.Queue) for each client connection
	•	On each logic event (e.g. in your relay or merge handler), push that event into all client queues
	•	The SSE generator continuously yields events to connected clients, checking for disconnection

Pseudocode:

# global or module variable
subscriber_queues: List[asyncio.Queue] = []

@app.get("/events/relay")
async def sse_events(request: Request):
    q = asyncio.Queue()
    subscriber_queues.append(q)
    async def event_gen():
        while True:
            if await request.is_disconnected():
                break
            evt = await q.get()
            # Format SSE:
            yield f"event: {evt['type']}\n"
            yield f"data: {json.dumps(evt['payload'])}\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")

def broadcast_event(evt: dict):
    for q in subscriber_queues:
        q.put_nowait(evt)

You may also use fastapi_sse.sse_response to simplify typed event emission.  ￼

Handle reconnection / last-event-id optionally for robustness.  ￼

⸻

Sequence example: initialization + relay handoff

Here’s a simplified flow between React frontend ↔ logic layer during demo.
	1.	Frontend starts
	•	React sends POST /context/initialize with { session_id, initial_input, metadata }
	•	Logic layer:
	•	creates a new ContextPacket with fragments (e.g. a fragment wrapping initial_input)
	•	assigns context_id, version = 0
	•	stores it in MongoDB
	•	broadcasts event { type: "contextInitialized", payload: { context_id, context_packet } }
	•	React receives the HTTP response, gets context_id & initial packet; also receives SSE event and renders initial node.
	2.	Agent A → Agent B relay
	•	React triggers POST /context/relay with a RelayRequest: { from_agent: "A", to_agent: "B", context_id, delta }
	•	Logic layer:
	•	fetches existing context packet (from DB)
	•	merges delta (e.g. add new fragments)
	•	computes embedding for new fragments
	•	runs conflict detection
	•	updates decision trace
	•	stores updated packet back to DB
	•	before returning response, broadcast relaySent event
	•	after processing, broadcast relayReceived event with new packet + conflicts
	•	React frontend:
	•	sees relaySent event → animates a packet moving from node A → node B
	•	sees relayReceived → updates node B’s state (fragments, decision trace, conflict markers)
	3.	Merge or Prune (optionally)
	•	React calls /context/merge or /context/prune
	•	Logic applies merging / pruning logic, stores result, emits contextMerged or contextPruned events
	•	React updates UI accordingly
	4.	Version snapshot
	•	React calls /context/version
	•	Logic stores a snapshot, generates VersionInfo, emits versionCreated event
	•	React adds timeline marker
	5.	Frontend reconnection
	•	If React’s SSE connection drops, it reconnects to /events/relay
	•	Optionally, pass Last-Event-ID so server can replay missed events

⸻

Error handling & edge cases
	•	On invalid requests (missing fields, unknown context_id), respond with 4xx errors (HTTP) and also broadcast an error event with a payload.
	•	In SSE: wrap your event generator in try/except to catch unhandled exceptions and emit error events before closing connection.
	•	If subscriber disconnects, clean up its queue.
	•	If logic emits many events fast, you may want to buffer or throttle broadcasts.
	•	Use versioning / optimistic locking when updating context documents so concurrent writes don’t conflict.
	•	If embedding or DB calls fail, rollback or mark fragment creation as error.

⸻

Summary & deliverables for your team
	•	Pydantic models: ContextPacket, ContextDelta, RelayRequest/Response, MergeRequest/Response, etc.
	•	FastAPI endpoints implementing the REST contract above
	•	SSE endpoint /events/relay that streams the internal event types
	•	broadcast_event(...) helper to send events to SSE clients
	•	Internal logic for merging, pruning, conflict detection, embedding calls, storage
	•	Integration with MongoDB + embedding service
	•	Tests / validation to ensure responses conform to schema
	•	Clear mapping from events → React UI animations

With this logic.md spec, your frontend and backend engineers and agent logic engineer can all code against the same contracts and integrate seamlessly.

If you like, I can also generate a stub FastAPI project skeleton (folder structure + stub files) matching this spec so your team can start coding directly. Do you want me to produce that?