#!/usr/bin/env python3
"""
Test script for MongoDB Atlas Vector Search integration.

Usage:
    python test_vector_search.py

Prerequisites:
    1. FastAPI server running (python main.py)
    2. MongoDB Atlas Vector Search index created
    3. Environment variables set (.env)
"""

import requests
import json
import time
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"


def test_health():
    """Test server health."""
    print("\n🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print(f"✅ Server is healthy")
        print(f"   Embedding service: {data['services']['embedding_service']}")
        print(f"   MongoDB: {data['services']['mongodb_service']}")
        return True
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False


def test_initialize_context():
    """Initialize a context and get embeddings."""
    print("\n🔍 Testing context initialization...")
    try:
        payload = {
            "session_id": "test_session_vector_search",
            "initial_input": "Machine learning is transforming how we process data",
            "metadata": {
                "test": "vector_search",
                "timestamp": time.time()
            }
        }

        response = requests.post(
            f"{BASE_URL}/context/initialize",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        context_id = data["context_id"]
        fragments = data["context_packet"]["fragments"]

        print(f"✅ Context initialized: {context_id}")
        print(f"   Fragments: {len(fragments)}")

        if fragments and fragments[0].get("embedding"):
            embedding_dim = len(fragments[0]["embedding"])
            print(f"   Embedding dimensions: {embedding_dim}")
            print(f"   Embedding sample: {fragments[0]['embedding'][:3]}...")
            return {
                "context_id": context_id,
                "embedding": fragments[0]["embedding"]
            }
        else:
            print("⚠️  No embedding generated")
            return {"context_id": context_id, "embedding": None}

    except Exception as e:
        print(f"❌ Context initialization failed: {e}")
        return None


def test_search_similar_fragments(embedding: List[float]):
    """Test fragment similarity search."""
    print("\n🔍 Testing fragment similarity search...")
    try:
        payload = {
            "query_embedding": embedding,
            "limit": 5,
            "min_score": 0.5  # Lower threshold for testing
        }

        response = requests.post(
            f"{BASE_URL}/search/fragments/similar",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Search completed")
        print(f"   Results found: {data['count']}")

        if data['results']:
            for i, result in enumerate(data['results'][:3], 1):
                print(f"   {i}. Fragment {result['fragment_id'][:8]}... (score: {result['score']:.3f})")
                print(f"      Context: {result['context_id'][:8]}...")

        return data['results']

    except requests.exceptions.HTTPError as e:
        print(f"❌ Search failed with HTTP error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return None


def test_search_similar_contexts(embedding: List[float]):
    """Test context similarity search."""
    print("\n🔍 Testing context similarity search...")
    try:
        payload = {
            "query_embedding": embedding,
            "session_id": "test_session_vector_search",
            "limit": 3,
            "min_score": 0.5
        }

        response = requests.post(
            f"{BASE_URL}/search/contexts/similar",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Search completed")
        print(f"   Contexts found: {data['count']}")

        if data['results']:
            for i, result in enumerate(data['results'], 1):
                print(f"   {i}. Context {result['context_id'][:8]}... (score: {result['search_score']:.3f})")
                print(f"      Fragments: {len(result.get('fragments', []))}")

        return data['results']

    except requests.exceptions.HTTPError as e:
        print(f"❌ Search failed with HTTP error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return None


def test_conflict_detection(context_id: str, embedding: List[float]):
    """Test conflict detection."""
    print("\n🔍 Testing conflict detection...")
    try:
        # Create a fragment with the same embedding (high similarity)
        payload = {
            "new_fragments": [
                {
                    "fragment_id": "test_conflict_fragment",
                    "content": "Similar content about machine learning and data",
                    "embedding": embedding,
                    "metadata": {}
                }
            ],
            "context_id": context_id,
            "similarity_threshold": 0.95  # High threshold for conflicts
        }

        response = requests.post(
            f"{BASE_URL}/search/conflicts/detect",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Conflict detection completed")
        print(f"   Conflicts found: {data['count']}")

        if data['results']:
            for conflict in data['results']:
                print(f"   Fragment {conflict['new_fragment_id']} conflicts with:")
                for conf_frag in conflict['conflicting_fragments']:
                    print(f"      - {conf_frag['fragment_id']} (score: {conf_frag['score']:.3f})")

        return data['results']

    except requests.exceptions.HTTPError as e:
        print(f"❌ Conflict detection failed: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Conflict detection failed: {e}")
        return None


def test_check_vector_index():
    """Check if vector search endpoints are available."""
    print("\n🔍 Checking vector search endpoints...")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()

        paths = openapi_spec.get('paths', {})
        search_endpoints = [
            path for path in paths.keys()
            if path.startswith('/search/')
        ]

        if search_endpoints:
            print(f"✅ Found {len(search_endpoints)} search endpoints:")
            for endpoint in search_endpoints:
                print(f"   - {endpoint}")
            return True
        else:
            print("❌ No search endpoints found")
            return False

    except Exception as e:
        print(f"❌ Failed to check endpoints: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("MongoDB Atlas Vector Search Test Suite")
    print("="*60)

    # Step 1: Health check
    if not test_health():
        print("\n❌ Server is not running. Start it with: python main.py")
        return

    # Step 2: Check endpoints
    if not test_check_vector_index():
        print("\n⚠️  Vector search endpoints not found")

    # Step 3: Initialize context with embeddings
    context_data = test_initialize_context()
    if not context_data or not context_data.get("embedding"):
        print("\n❌ Cannot proceed without embeddings")
        return

    context_id = context_data["context_id"]
    embedding = context_data["embedding"]

    # Wait a moment for MongoDB to index
    print("\n⏳ Waiting 2 seconds for indexing...")
    time.sleep(2)

    # Step 4: Test fragment search
    test_search_similar_fragments(embedding)

    # Step 5: Test context search
    test_search_similar_contexts(embedding)

    # Step 6: Test conflict detection
    test_conflict_detection(context_id, embedding)

    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)

    print("\n📝 Next steps:")
    print("   1. Check MongoDB Atlas for the vector search index")
    print("   2. Verify index name is 'vector_search_index'")
    print("   3. If searches return 0 results, check:")
    print("      - Index is built (takes ~5 minutes)")
    print("      - Embedding dimensions match (384 or 1024)")
    print("      - Collection name is 'context_packets'")


if __name__ == "__main__":
    main()
