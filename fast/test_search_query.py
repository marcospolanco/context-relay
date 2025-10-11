#!/usr/bin/env python3
"""Quick test to search for similar content."""
import requests
import json

# First, initialize a context to get an embedding
init_response = requests.post(
    "http://localhost:8000/context/initialize",
    json={
        "session_id": "search_test",
        "initial_input": "Artificial intelligence and data science applications",
        "metadata": {}
    }
)

if init_response.status_code == 200:
    data = init_response.json()
    embedding = data["context_packet"]["fragments"][0]["embedding"]
    print(f"✅ Generated embedding with {len(embedding)} dimensions")

    # Now search for similar fragments
    search_response = requests.post(
        "http://localhost:8000/search/fragments/similar",
        json={
            "query_embedding": embedding,
            "limit": 5,
            "min_score": 0.5  # Lower threshold
        }
    )

    print(f"\n🔍 Search Results (status: {search_response.status_code}):")
    if search_response.status_code == 200:
        results = search_response.json()
        print(json.dumps(results, indent=2))

        if results["count"] > 0:
            print(f"\n✅ Found {results['count']} similar fragments!")
            for i, result in enumerate(results["results"][:3], 1):
                print(f"\n{i}. Score: {result['score']:.3f}")
                print(f"   Content: {result['content'][:100]}...")
        else:
            print("\n⚠️  No results found. Index might still be building (wait ~5 min)")
    else:
        print(f"Error: {search_response.text}")
else:
    print(f"Failed to initialize context: {init_response.text}")
