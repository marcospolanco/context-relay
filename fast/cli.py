import typer
import os
import json

app = typer.Typer()

generate_app = typer.Typer()
app.add_typer(generate_app, name="generate")


@generate_app.command("init-request")
def generate_init_request(output: str = typer.Option(..., "--output")):
    """Generates a template InitializeRequest JSON file."""
    data = {
        "session_id": "session-cli-123",
        "initial_input": "User wants to plan a trip to Japan",
        "metadata": {
            "user_type": "cli_tester",
            "priority": "normal"
        }
    }
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {output}")

@generate_app.command("relay-request")
def generate_relay_request(context_id: str = typer.Option(..., "--context-id"), output: str = typer.Option(..., "--output")):
    """Generates a template RelayRequest JSON file."""
    data = {
        "from_agent": "AgentA",
        "to_agent": "AgentB",
        "context_id": context_id,
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
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {output}")

@generate_app.command("merge-request")
def generate_merge_request(output: str = typer.Option(..., "--output")):
    """Generates a template MergeRequest JSON file."""
    data = {
        "context_ids": ["ctx-123", "ctx-456"],
        "session_id": "session-cli-merge-123"
    }
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {output}")

@generate_app.command("prune-request")
def generate_prune_request(context_id: str = typer.Option(..., "--context-id"), output: str = typer.Option(..., "--output")):
    """Generates a template PruneRequest JSON file."""
    data = {
        "context_id": context_id,
        "criteria": "remove fragments older than 24 hours"
    }
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {output}")

@generate_app.command("version-request")
def generate_version_request(context_id: str = typer.Option(..., "--context-id"), output: str = typer.Option(..., "--output")):
    """Generates a template VersionRequest JSON file."""
    data = {
        "context_id": context_id,
        "tag": "v1.0-cli"
    }
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {output}")

import requests

api_app = typer.Typer()
app.add_typer(api_app, name="api")

BASE_URL = os.environ.get("CONTEXT_RELAY_BASE_URL", "http://localhost:8000")

def handle_api_request(method: str, endpoint: str, json_data: dict = None, params: dict = None):
    """Helper function to make API requests."""
    try:
        response = requests.request(method, f"{BASE_URL}{endpoint}", json=json_data, params=params)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        raise typer.Exit(1)

@api_app.callback()
def api_callback(base_url: str = typer.Option(None, "--base-url", help="Base URL of the API server.")):
    """
    Interact with the API endpoints.
    """
    global BASE_URL
    if base_url:
        BASE_URL = base_url

@api_app.command("init")
def api_init(from_file: str = typer.Option(..., "--from-file")):
    """Initializes a new context."""
    with open(from_file, 'r') as f:
        data = json.load(f)
    handle_api_request("POST", "/context/initialize", json_data=data)

@api_app.command("relay")
def api_relay(from_file: str = typer.Option(..., "--from-file")):
    """Relays context between agents."""
    with open(from_file, 'r') as f:
        data = json.load(f)
    handle_api_request("POST", "/context/relay", json_data=data)

@api_app.command("merge")
def api_merge(from_file: str = typer.Option(..., "--from-file")):
    """Merges multiple contexts."""
    with open(from_file, 'r') as f:
        data = json.load(f)
    handle_api_request("POST", "/context/merge", json_data=data)

@api_app.command("prune")
def api_prune(from_file: str = typer.Option(..., "--from-file")):
    """Prunes a context."""
    with open(from_file, 'r') as f:
        data = json.load(f)
    handle_api_request("POST", "/context/prune", json_data=data)

@api_app.command("version")
def api_version(from_file: str = typer.Option(..., "--from-file")):
    """Creates a version snapshot of a context."""
    with open(from_file, 'r') as f:
        data = json.load(f)
    handle_api_request("POST", "/context/version", json_data=data)

@api_app.command("get")
def api_get(context_id: str):
    """Retrieves the full context packet for a given ID."""
    handle_api_request("GET", f"/context/{context_id}")

@api_app.command("list-versions")
def api_list_versions(context_id: str):
    """Lists all available versions for a given context ID."""
    handle_api_request("GET", f"/context/{context_id}/versions")

from sseclient import SSEClient

events_app = typer.Typer()
app.add_typer(events_app, name="events")

@events_app.command("listen")
def events_listen():
    """Connects to the SSE event stream and prints events as they are received."""
    sse_url = f"{BASE_URL}/events/relay"
    print(f"Connecting to SSE stream at {sse_url}...")
    try:
        client = SSEClient(sse_url)
        for event in client.events():
            print("---")
            print(f"EVENT: {event.event}")
            print("DATA:")
            print(json.dumps(json.loads(event.data), indent=2))
            print("---")
    except requests.exceptions.ConnectionError as e:
        print(f"Error connecting to SSE stream: {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        print("\nDisconnected from SSE stream.")

if __name__ == "__main__":
    app()
