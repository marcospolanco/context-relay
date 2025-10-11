#!/bin/bash

# Context Relay System - FastAPI Server Startup Script
# This script follows the instructions in fast/README.md to start the server

set -e  # Exit on any error

echo "🚀 Starting Context Relay System FastAPI Server..."

# Check if we're in the correct directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the 'fast' directory"
    echo "   Usage: cd fast && ./start.sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "🌐 Starting FastAPI server..."
echo "   Server will be available at:"
echo "   - API: http://localhost:8000"
echo "   - Documentation: http://localhost:8000/docs"
echo "   - Events: http://localhost:8000/events/relay"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Use uvicorn with the same configuration as in README
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000