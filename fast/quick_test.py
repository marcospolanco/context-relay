"""Quick MongoDB cluster check."""
import pymongo
from pymongo import MongoClient
import sys

print("Quick MongoDB Cluster Check")
print("="*60)

uri = "mongodb+srv://context:relay@context-relay-dev.kc2veaj.mongodb.net/?retryWrites=true&w=majority&appName=context-relay-dev"

print("\n[1] Creating client with 5s timeout...")
try:
    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    print("  ✓ Client created")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

print("\n[2] Checking replica set status...")
try:
    # This will force server selection
    result = client.admin.command('replSetGetStatus')
    print("  ✓ Replica set status retrieved!")
    print(f"  Set name: {result.get('set')}")
    print(f"  Members: {len(result.get('members', []))}")

    for member in result.get('members', []):
        state_str = member.get('stateStr', 'UNKNOWN')
        name = member.get('name')
        print(f"    - {name}: {state_str}")

except pymongo.errors.OperationFailure as e:
    print(f"  ✗ Not authorized to check replica set: {e}")
    print("  (This is normal - user doesn't have admin rights)")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n[3] Testing basic operations...")
try:
    # Get database names (should work on secondary)
    print("  Trying to list databases...")
    dbs = client.list_database_names()
    print(f"  ✓ Found {len(dbs)} databases: {dbs}")
except Exception as e:
    print(f"  ✗ Failed: {e}")

print("\n[4] Testing write operation...")
db = client['context_relay']
collection = db['test']

try:
    print("  Attempting insert...")
    result = collection.insert_one({"test": "value"})
    print(f"  ✓ Insert successful! ID: {result.inserted_id}")

    # Clean up
    collection.delete_one({"_id": result.inserted_id})
    print("  ✓ Cleanup done")
    print("\n🎉 CLUSTER IS WORKING!")

except pymongo.errors.ServerSelectionTimeoutError as e:
    print(f"  ✗ Write failed - NO PRIMARY NODE")
    print(f"\n  Error details:")
    error_str = str(e)

    # Extract node status
    if "cluster0-shard-00-00" in error_str:
        print(f"\n  Node Status from Error:")
        if "RSSecondary" in error_str:
            print("    • Node 00: SECONDARY (working)")
        if "RSPrimary" in error_str:
            print("    • A node is PRIMARY")
        else:
            print("    • NO PRIMARY NODE FOUND")

        # Count Unknown nodes
        unknown_count = error_str.count("Unknown")
        if unknown_count > 0:
            print(f"    • {unknown_count} nodes are UNKNOWN/DOWN")

    print(f"\n❌ DIAGNOSIS: Hackathon MongoDB cluster is misconfigured")
    print(f"   Action: Contact organizers to restart/fix the cluster")

except Exception as e:
    print(f"  ✗ Unexpected error: {e}")
    print(f"   Error type: {type(e).__name__}")

client.close()
print("\n" + "="*60)
