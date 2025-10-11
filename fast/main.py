from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.database import connect_to_mongodb, close_mongodb_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting Context Relay API...")
    await connect_to_mongodb()
    yield
    # Shutdown
    print("🛑 Shutting down Context Relay API...")
    await close_mongodb_connection()


app = FastAPI(
    title="Context Relay API",
    description="A FastAPI application for context relay functionality",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Context Relay API"}

@app.get("/health")
async def health_check():
    """Health check endpoint that verifies MongoDB connection."""
    from app.config.database import mongodb_client

    mongodb_status = "connected" if mongodb_client else "disconnected"

    # Try to ping MongoDB
    try:
        if mongodb_client:
            await mongodb_client.admin.command('ping')
            mongodb_ping = "ok"
        else:
            mongodb_ping = "no client"
    except Exception as e:
        mongodb_ping = f"error: {str(e)}"

    return {
        "status": "healthy",
        "mongodb": {
            "status": mongodb_status,
            "ping": mongodb_ping
        }
    }

# Import routers
from app.api.contexts import router as contexts_router

# Register routers
app.include_router(contexts_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)