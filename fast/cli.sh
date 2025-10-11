#!/bin/bash

# Source environment variables from .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the CLI
python cli.py "$@"