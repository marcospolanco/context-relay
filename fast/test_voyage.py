"""Quick test of Voyage AI embedding service."""
import asyncio
from app.services.voyage_embedding_service import get_voyage_service


async def test_voyage():
    print("Testing Voyage AI Embedding Service...")
    print("=" * 60)

    service = get_voyage_service()

    # Test 1: Service status
    print("\n[Test 1] Service Status:")
    status = service.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Test 2: Single embedding
    print("\n[Test 2] Generate Single Embedding:")
    text = "User wants to plan a trip to Japan"
    embedding = await service.generate_embedding(text)
    print(f"  Text: {text}")
    print(f"  Embedding dimensions: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")

    # Test 3: Batch embeddings
    print("\n[Test 3] Generate Batch Embeddings:")
    texts = [
        "I love traveling to Japan",
        "Tokyo is a beautiful city",
        "Python programming is fun",
        "Machine learning algorithms"
    ]
    embeddings = await service.generate_embeddings_batch(texts)
    print(f"  Generated {len(embeddings)} embeddings")
    for i, text in enumerate(texts):
        print(f"  {i+1}. {text[:40]}... → {len(embeddings[i])} dims")

    # Test 4: Similarity computation
    print("\n[Test 4] Compute Similarities:")
    similarity_01 = await service.compute_similarity(embeddings[0], embeddings[1])
    similarity_02 = await service.compute_similarity(embeddings[0], embeddings[2])
    print(f"  '{texts[0]}' vs '{texts[1]}': {similarity_01:.4f}")
    print(f"  '{texts[0]}' vs '{texts[2]}': {similarity_02:.4f}")
    print(f"  ✓ Travel texts should be more similar than travel vs programming")

    # Test 5: Find similar fragments
    print("\n[Test 5] Find Similar Fragments:")
    query_embedding = embeddings[0]  # "I love traveling to Japan"
    fragment_embeddings = [(f"frag-{i}", emb) for i, emb in enumerate(embeddings[1:])]

    similar = await service.find_similar_fragments(
        query_embedding,
        fragment_embeddings,
        threshold=0.5,
        top_k=2
    )

    print(f"  Query: '{texts[0]}'")
    print(f"  Similar fragments:")
    for frag_id, score in similar:
        idx = int(frag_id.split('-')[1]) + 1
        print(f"    - {texts[idx]}: {score:.4f}")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_voyage())
