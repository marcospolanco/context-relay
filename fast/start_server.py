#!/usr/bin/env python3
"""
Context Relay API Server Startup Script

This script starts the FastAPI server with proper configuration
for Phase 1 mock API development.
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("🚀 Starting Context Relay API Server (Phase 1 Mock)")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔗 Event Stream: http://localhost:8000/events/relay")
    print("💚 Health Check: http://localhost:8000/health/")
    print()

    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )