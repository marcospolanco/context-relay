# Context Relay CLI - Specification (`clispec.md`)

## 1. Executive Summary

This document specifies the design for `context-relay-cli`, a command-line interface designed to exercise the Context Relay System's API. The CLI allows developers and testers to manually trigger each operation defined in `gherkin.md`, using mock data from local JSON files.

The primary goals of this CLI are:
- To provide a simple, scriptable way to interact with the API.
- To facilitate manual testing and validation of the Gherkin scenarios.
- To unblock developers by allowing them to generate mock request bodies and simulate a full workflow without a UI.

## 2. Installation & Configuration

The CLI will be a Python application, installable via pip.

```bash
pip install .
```

It will require configuration to know the base URL of the running API server. This can be set via an environment variable or a command-line option.

- **Environment Variable**: `CONTEXT_RELAY_BASE_URL`
- **CLI Option**: `--base-url http://localhost:8000`

```bash
export CONTEXT_RELAY_BASE_URL="http://localhost:8000"
```

## 3. High-Level Command Structure

The CLI will be structured with clear, nested commands.

```
context-relay-cli [OPTIONS] COMMAND [SUBCOMMAND] [ARGS]...
```

- **`generate`**: A top-level command for creating mock data files.
- **`api`**: A top-level command for interacting with the API endpoints.
- **`events`**: A top-level command for listening to the SSE event stream.

## 4. Data Generation Commands (`generate`)

This command group is responsible for scaffolding the JSON files required to make API calls. This prevents users from having to write the JSON from scratch.

### `context-relay-cli generate init-request`

Generates a template `InitializeRequest` JSON file.

- **Usage**: `context-relay-cli generate init-request --output <filename>`
- **Example**: `context-relay-cli generate init-request --output init_payload.json`
- **Output (`init_payload.json`)**:
  ```json
  {
    "session_id": "session-cli-123",
    "initial_input": "User wants to plan a trip to Japan",
    "metadata": {
      "user_type": "cli_tester",
      "priority": "normal"
    }
  }
  ```

### `context-relay-cli generate relay-request`

Generates a template `RelayRequest` JSON file.

- **Usage**: `context-relay-cli generate relay-request --context-id <id> --output <filename>`
- **Example**: `context-relay-cli generate relay-request --context-id ctx-123 --output relay_payload.json`
- **Output (`relay_payload.json`)**:
  ```json
  {
    "from_agent": "AgentA",
    "to_agent": "AgentB",
    "context_id": "ctx-123",
    "delta": {
      "new_fragments": [
        {
          "fragment_id": "frag-cli-456",
          "content": "User prefers budget accommodation under $100/night",
          "metadata": { "source": "cli_input" }
        }
      ],
      "removed_fragment_ids": [],
      "decision_updates": [
        {
          "agent": "AgentA",
          "decision": "added_cli_constraint",
          "timestamp": "2025-10-11T10:00:00Z",
          "reasoning": "manual input from cli"
        }
      ]
    }
  }
  ```

### Other `generate` commands

Similar commands will exist for all other POST/PUT request bodies:
- `context-relay-cli generate merge-request --output merge_payload.json`
- `context-relay-cli generate prune-request --context-id <id> --output prune_payload.json`
- `context-relay-cli generate version-request --context-id <id> --output version_payload.json`

## 5. API Interaction Commands (`api`)

This command group interacts directly with the running API server.

### `context-relay-cli api init`

Initializes a new context.

- **Usage**: `context-relay-cli api init --from-file <filename>`
- **Example**: `context-relay-cli api init --from-file init_payload.json`
- **Action**: Reads the specified JSON file and makes a `POST` request to `/context/initialize`. Prints the formatted JSON response to stdout.

### `context-relay-cli api relay`

Relays context between agents.

- **Usage**: `context-relay-cli api relay --from-file <filename>`
- **Example**: `context-relay-cli api relay --from-file relay_payload.json`
- **Action**: Reads the file and makes a `POST` request to `/context/relay`. Prints the response.

### `context-relay-cli api merge`

Merges multiple contexts.

- **Usage**: `context-relay-cli api merge --from-file <filename>`
- **Example**: `context-relay-cli api merge --from-file merge_payload.json`
- **Action**: Reads the file and makes a `POST` request to `/context/merge`. Prints the response.

### `context-relay-cli api prune`

Prunes a context.

- **Usage**: `context-relay-cli api prune --from-file <filename>`
- **Example**: `context-relay-cli api prune --from-file prune_payload.json`
- **Action**: Reads the file and makes a `POST` request to `/context/prune`. Prints the response.

### `context-relay-cli api version`

Creates a version snapshot of a context.

- **Usage**: `context-relay-cli api version --from-file <filename>`
- **Example**: `context-relay-cli api version --from-file version_payload.json`
- **Action**: Reads the file and makes a `POST` request to `/context/version`. Prints the response.

### `context-relay-cli api get`

Retrieves the full context packet for a given ID.

- **Usage**: `context-relay-cli api get <context_id>`
- **Example**: `context-relay-cli api get ctx-12345`
- **Action**: Makes a `GET` request to `/context/{context_id}`. Prints the response.

### `context-relay-cli api list-versions`

Lists all available versions for a given context ID.

- **Usage**: `context-relay-cli api list-versions <context_id>`
- **Example**: `context-relay-cli api list-versions ctx-12345`
- **Action**: Makes a `GET` request to `/context/versions/{context_id}`. Prints the response.

## 6. SSE Event Listener (`events`)

### `context-relay-cli events listen`

Connects to the SSE event stream and prints events as they are received.

- **Usage**: `context-relay-cli events listen`
- **Action**: Establishes a connection to the `/events/relay` endpoint and prints each event to stdout in a readable format. The command will run indefinitely until interrupted (Ctrl+C).
- **Example Output**:
  ```
  Connecting to SSE stream at http://localhost:8000/events/relay...
  ---
  EVENT: contextInitialized
  DATA:
  {
    "context_id": "ctx-abcde",
    "context_packet": { ... }
  }
  ---
  EVENT: relaySent
  DATA:
  {
    "from_agent": "AgentA",
    "to_agent": "AgentB",
    ...
  }
  ---
  ```

## 7. Example Workflow

This workflow demonstrates how a user would manually step through the "Successful context relay" scenario from `gherkin.md`.

**Terminal 1: Listen for events**
```bash
# Start the event listener in one terminal to see all events in real-time
context-relay-cli events listen
```

**Terminal 2: Execute the workflow**
```bash
# 1. Generate a mock request file for initialization
context-relay-cli generate init-request --output init.json

# (User can optionally edit init.json here)

# 2. Initialize the context and capture the new context_id from the response
# Let's assume the response contains "context_id": "ctx-xyz-789"
context-relay-cli api init --from-file init.json > init_response.json
cat init_response.json

# 3. Generate a mock request file for the relay operation, using the new ID
context-relay-cli generate relay-request --context-id "ctx-xyz-789" --output relay.json

# (User can optionally edit relay.json to add more specific fragments)

# 4. Execute the relay
context-relay-cli api relay --from-file relay.json > relay_response.json
cat relay_response.json

# 5. Check the final state of the context
context-relay-cli api get "ctx-xyz-789"
```

Throughout this process, the user would observe `contextInitialized`, `relaySent`, and `relayReceived` events appearing in Terminal 1, confirming the behavior specified in the Gherkin scenario.