"""Simple script to test MongoDB connection."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    print("Testing MongoDB connection...")

    uri = "mongodb+srv://context:relay@cluster0.hu7qay.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&readPreference=secondaryPreferred"

    try:
        print(f"Connecting to: {uri[:50]}...")
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)

        # Test the connection
        print("Pinging MongoDB...")
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")

        # List databases
        print("\nAvailable databases:")
        db_list = await client.list_database_names()
        for db in db_list:
            print(f"  - {db}")

        # Test our database
        db = client["context_relay"]
        print(f"\n✅ Connected to database: context_relay")

        # List collections
        collections = await db.list_collection_names()
        print(f"Existing collections: {collections if collections else 'None (database is empty)'}")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
