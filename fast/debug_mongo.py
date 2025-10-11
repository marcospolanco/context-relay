"""Comprehensive MongoDB connection debugging."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReadPreference
import sys

async def detailed_debug():
    print("="*60)
    print("MongoDB Connection Debugging")
    print("="*60)

    uri = "mongodb+srv://context:relay@cluster0.hu7qay.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

    print("\n1. Testing connection with various configurations...")
    print("-"*60)

    # Test 1: Basic connection info
    print(f"\n[Test 1] Connection URI (sanitized): {uri.replace('relay', '***')[:80]}...")

    # Test 2: Try with longer timeout and direct primary read
    print("\n[Test 2] Attempting connection with 30s timeout...")
    try:
        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
        )

        print("  ✓ Client created")

        # Get server info
        print("\n[Test 3] Getting server information...")
        server_info = await client.server_info()
        print(f"  ✓ MongoDB Version: {server_info.get('version')}")
        print(f"  ✓ Connection successful!")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        print(f"  Error type: {type(e).__name__}")

    # Test 4: Try reading from secondary
    print("\n[Test 4] Attempting to read from secondary nodes...")
    try:
        client_secondary = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=30000,
            readPreference=ReadPreference.SECONDARY_PREFERRED
        )

        db = client_secondary['context_relay']

        # Try a simple read operation
        print("  Attempting to list collections...")
        collections = await db.list_collection_names()
        print(f"  ✓ Collections found: {collections if collections else '(none - empty database)'}")

        # Try to get stats (read operation)
        print("\n  Attempting to read database stats...")
        stats = await db.command('dbStats')
        print(f"  ✓ Database stats retrieved!")
        print(f"    - Database: {stats.get('db')}")
        print(f"    - Collections: {stats.get('collections')}")
        print(f"    - Data Size: {stats.get('dataSize')} bytes")

    except Exception as e:
        print(f"  ✗ Secondary read failed: {e}")

    # Test 5: Try a write operation to confirm primary issue
    print("\n[Test 5] Attempting a write operation (will likely fail)...")
    try:
        test_db = client['test_db']
        test_collection = test_db['test_collection']

        result = await test_collection.insert_one({"test": "data", "timestamp": "now"})
        print(f"  ✓ Write successful! ID: {result.inserted_id}")

        # Clean up
        await test_collection.delete_one({"_id": result.inserted_id})
        print("  ✓ Cleanup successful")

    except Exception as e:
        print(f"  ✗ Write failed: {e}")
        print(f"  ✗ This confirms: NO PRIMARY NODE AVAILABLE")

    # Test 6: Get detailed topology description
    print("\n[Test 6] Detailed Topology Information...")
    try:
        # Force a server check
        await client.admin.command('ping')
    except Exception as e:
        # Parse the error for topology info
        error_str = str(e)
        if "Topology Description" in error_str:
            print("  Topology Details:")
            # Extract topology description
            import re
            topology_match = re.search(r'<TopologyDescription.*?>', error_str)
            if topology_match:
                topo = topology_match.group()
                print(f"    {topo}")

                # Parse server descriptions
                servers = re.findall(r"<ServerDescription \('([^']+)', (\d+)\) server_type: (\w+), rtt: ([^>]+)>", error_str)
                print("\n  Individual Nodes:")
                for host, port, server_type, rtt in servers:
                    status = "✓" if server_type not in ["Unknown"] else "✗"
                    print(f"    {status} {host}:{port}")
                    print(f"      Type: {server_type}")
                    print(f"      RTT: {rtt}")

    # Test 7: Try directly connecting to the specific hosts
    print("\n[Test 7] Testing direct connection to individual nodes...")
    hosts = [
        "cluster0-shard-00-00.hu7qay.mongodb.net",
        "cluster0-shard-00-01.hu7qay.mongodb.net",
        "cluster0-shard-00-02.hu7qay.mongodb.net"
    ]

    for host in hosts:
        try:
            print(f"\n  Testing {host}...")
            direct_uri = f"mongodb://{host}:27017/?serverSelectionTimeoutMS=5000"
            direct_client = AsyncIOMotorClient(direct_uri)
            await direct_client.admin.command('ping')
            print(f"    ✓ {host} is reachable")
            direct_client.close()
        except Exception as e:
            print(f"    ✗ {host} not reachable: {e}")

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSIS:")
    print("="*60)
    print("""
If you see:
  ✓ Collections found / Database stats retrieved
  ✗ Write failed with 'No replica set members match selector "Primary()"'

Then: THE CLUSTER CONFIGURATION IS BROKEN (not your code!)

If you see:
  ✗ All operations failed with timeout/network errors

Then: Check your internet connection or firewall

If you see:
  ✓ All tests passed

Then: The cluster is working! Retest your app.
    """)

if __name__ == "__main__":
    asyncio.run(detailed_debug())
