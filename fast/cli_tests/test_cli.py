import sys
import os

# Add the project root to the python path to allow importing `cli`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typer.testing import CliRunner
from cli import app
import json

runner = CliRunner()

def test_generate_init_request():
    output_file = "init_payload.json"
    result = runner.invoke(app, ["generate", "init-request", "--output", output_file])
    assert result.exit_code == 0
    assert f"Generated {output_file}" in result.stdout
    with open(output_file, 'r') as f:
        data = json.load(f)
    assert data["session_id"] == "session-cli-123"
    os.remove(output_file)

def test_generate_relay_request():
    output_file = "relay_payload.json"
    context_id = "ctx-test-123"
    result = runner.invoke(app, ["generate", "relay-request", "--context-id", context_id, "--output", output_file])
    assert result.exit_code == 0
    assert f"Generated {output_file}" in result.stdout
    with open(output_file, 'r') as f:
        data = json.load(f)
    assert data["context_id"] == context_id
    os.remove(output_file)
