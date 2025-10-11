import uvicorn

# Uvicorn configuration
config = {
    "app": "main:app",
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "log_level": "info",
    "access_log": True,
}

def run_server():
    """Run the FastAPI server with Uvicorn"""
    uvicorn.run(**config)

if __name__ == "__main__":
    run_server()