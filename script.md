# Context Relay CLI Demo Script

## Introduction
"Today I'll demonstrate the Context Relay system - a powerful framework for managing context flow between AI agents. Let me show you how it works using only our command-line interface."

## Setup
"First, let's start our context relay server in the background..."

*(Demo note: Server should be running on localhost:8000)*

## Scene 1: Creating Context Templates

"Let me show you how easy it is to create different types of context requests. I'll generate templates for our workflow."

```bash
# Create an initial context request
python fast/cli.py generate init-request --output fast/test-init.json
```

*(Show the generated file)*

"Perfect! This creates a basic initialization request with a session ID and user input. Now let's create a relay request that shows how context flows between agents."

```bash
# Create a relay request
python fast/cli.py generate relay-request --context-id ctx-trip-2024 --output fast/test-relay.json
```

"Notice how this includes context fragments and decision updates - this is the core of how agents share and build upon each other's work."

## Scene 2: Initializing the Context

"Now let's initialize our context with the server. This is like starting a conversation between agents."

```bash
# Initialize the context
python fast/cli.py api init --from-file fast/test-init.json
```

*(Show the JSON response)*

"Great! The server has created our context and assigned it a unique ID. This ID will be used to track the context as it moves through our system."

## Scene 3: The Relay Mechanism

"Here's where the magic happens. Let's relay some context between agents using the template we created."

```bash
# Relay context between agents
python fast/cli.py api relay --from-file fast/test-relay.json
```

"What just happened? Agent A sent context information to Agent B, including new fragments and decision updates. The system maintains a complete audit trail of all interactions."

## Scene 4: Managing Context

"Let me show you how to retrieve and manage contexts in the system."

```bash
# Get the full context
python fast/cli.py api get ctx-trip-2024

# Create a version snapshot
python fast/cli.py generate version-request --context-id ctx-trip-2024 --output fast/create-version.json
python fast/cli.py api version --from-file fast/create-version.json

# List all versions
python fast/cli.py api list-versions ctx-trip-2024
```

"This gives us full visibility into how our context evolves over time. Each version represents a snapshot we can return to if needed."

## Scene 5: Real-time Event Streaming

"One of the most powerful features is real-time event streaming. Let's listen in on context events as they happen."

*(In a separate terminal)*
```bash
python fast/cli.py events listen
```

*(While this is running, perform another relay operation in the first terminal to show live events)*

"Watch as events flow through the system in real-time! This is perfect for monitoring multi-agent workflows and debugging complex interactions."

## Scene 6: Advanced Context Operations

"Let me demonstrate some advanced operations like merging contexts and pruning old information."

```bash
# Create a merge request
python fast/cli.py generate merge-request --output fast/test-merge.json

# Merge multiple contexts
python fast/cli.py api merge --from-file fast/test-merge.json

# Create a prune request
python fast/cli.py generate prune-request --context-id ctx-trip-2024 --output fast/test-prune.json

# Prune old context fragments
python fast/cli.py api prune --from-file fast/test-prune.json
```

"These operations show how the system can combine different context streams and maintain clean, relevant information."

## Conclusion

"What you've seen today is a complete context management system that enables:

✅ **Context Initialization** - Starting conversations with structured data
✅ **Agent-to-Agent Relaying** - Seamless information flow between AI agents
✅ **Version Control** - Tracking context evolution over time
✅ **Real-time Monitoring** - Live event streaming for transparency
✅ **Context Management** - Merging, pruning, and organizing information

The CLI provides direct access to all these capabilities, making it perfect for testing, debugging, and scripting complex multi-agent workflows. And this is just the foundation - on top of this, we can build sophisticated applications like the Multi-Agent Interview Assistant that would use these same primitives to orchestrate complex AI workflows."

## Technical Notes

- Server runs on `localhost:8000` (configurable via `CONTEXT_RELAY_BASE_URL`)
- All commands support `--help` for detailed usage information
- JSON files are human-readable and can be modified manually
- Events use Server-Sent Events (SSE) for real-time updates
- Full audit trail maintained for all context operations