"""MongoDB database configuration using Beanie ODM."""
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB client instance
mongodb_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongodb():
    """Connect to MongoDB and initialize Beanie."""
    global mongodb_client

    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI not found in environment variables")

    db_name = os.getenv("MONGODB_DB_NAME", "context_relay")

    # Create MongoDB client
    mongodb_client = AsyncIOMotorClient(mongodb_uri)

    # Get database
    database = mongodb_client[db_name]

    # Import models here to avoid circular imports
    from app.models.context import ContextPacket, VersionInfo

    # Initialize Beanie with document models (only Document classes, not BaseModel)
    await init_beanie(
        database=database,
        document_models=[
            ContextPacket,
            VersionInfo,
        ]
    )

    print(f"✅ Connected to MongoDB: {db_name}")


async def close_mongodb_connection():
    """Close MongoDB connection."""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("❌ Disconnected from MongoDB")


def get_database():
    """Get the database instance."""
    if not mongodb_client:
        raise RuntimeError("MongoDB not connected. Call connect_to_mongodb() first.")
    db_name = os.getenv("MONGODB_DB_NAME", "context_relay")
    return mongodb_client[db_name]


def get_database_client():
    """Get the MongoDB client instance."""
    return mongodb_client


# Settings class for configuration
class Settings:
    """Database settings."""
    MONGO_DB = os.getenv("MONGODB_DB_NAME", "context_relay")


settings = Settings()
