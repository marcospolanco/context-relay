# MongoDB Atlas Vector Search Setup Guide

## ✅ What Was Added

1. **Vector Search Service** (`app/services/vector_search_service.py`)
   - Find similar fragments
   - Find similar contexts
   - Detect conflicts using embeddings

2. **Search API Endpoints** (`app/api/search.py`)
   - `POST /search/fragments/similar` - Find similar fragments
   - `POST /search/contexts/similar` - Find similar contexts
   - `POST /search/conflicts/detect` - Detect conflicts

3. **Integration** - Wired into `main.py` startup

## 🔧 Setup Steps

### Step 1: Create Vector Search Index in MongoDB Atlas

1. Go to your MongoDB Atlas cluster
2. Click **Search** tab → **Create Search Index**
3. Choose **JSON Editor**
4. Select collection: `context_packets`
5. Paste this index definition:

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "fragments": {
        "type": "document",
        "dynamic": true,
        "fields": {
          "embedding": {
            "type": "knnVector",
            "dimensions": 384,
            "similarity": "cosine"
          }
        }
      }
    }
  }
}
```

6. Name it: **`vector_search_index`**
7. Click **Create Search Index**

⏱️ Index creation takes ~5 minutes

### Step 2: Verify Your Embedding Dimensions

Check `app/services/voyage_embedding_service.py` to confirm embedding dimensions:

```python
# Should be 384 for voyage-lite-02-instruct
# Or 1024 for voyage-2
```

If using `voyage-2` (1024 dimensions), update the index:
```json
"dimensions": 1024
```

### Step 3: Set Environment Variables

Ensure `.env` has:
```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB_NAME=context_relay
VOYAGE_API_KEY=your-key-here
```

### Step 4: Start the Server

```bash
cd fast
source venv/bin/activate
python main.py
```

Check logs for:
```
✅ Connected to MongoDB: context_relay
✅ Vector search service initialized
```

## 📡 API Usage Examples

### 1. Find Similar Fragments

```bash
curl -X POST http://localhost:8000/search/fragments/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_embedding": [0.123, 0.456, ...],  # 384 floats
    "limit": 5,
    "min_score": 0.7
  }'
```

**Response:**
```json
{
  "results": [
    {
      "context_id": "ctx_123",
      "fragment_id": "frag_456",
      "content": {...},
      "score": 0.92
    }
  ],
  "count": 1
}
```

### 2. Find Similar Contexts

```bash
curl -X POST http://localhost:8000/search/contexts/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_embedding": [0.123, ...],
    "session_id": "sess_123",
    "limit": 3,
    "min_score": 0.8
  }'
```

### 3. Detect Conflicts

```bash
curl -X POST http://localhost:8000/search/conflicts/detect \
  -H "Content-Type: application/json" \
  -d '{
    "new_fragments": [
      {
        "fragment_id": "new_1",
        "content": "...",
        "embedding": [0.1, 0.2, ...]
      }
    ],
    "context_id": "ctx_123",
    "similarity_threshold": 0.9
  }'
```

**Response:**
```json
{
  "results": [
    {
      "new_fragment_id": "new_1",
      "conflicting_fragments": [
        {
          "fragment_id": "existing_456",
          "score": 0.95
        }
      ]
    }
  ],
  "count": 1
}
```

## 🔗 Integration into Relay Logic

### Option 1: Use in `relay_context` endpoint

Modify `app/main.py` or `app/api/contexts.py`:

```python
from app.services.vector_search_service import get_vector_search_service

@router.post("/context/relay")
async def relay_context(request: RelayRequest):
    # ... existing code ...

    # BEFORE applying delta, check for conflicts
    vector_search = get_vector_search_service()

    if request.delta.new_fragments:
        conflicts = await vector_search.detect_conflicts(
            new_fragments=[f.dict() for f in request.delta.new_fragments],
            context_id=request.context_id,
            similarity_threshold=0.9
        )

        if conflicts:
            # Return conflicts to caller
            return RelayResponse(
                context_packet=context,
                conflicts=[c["new_fragment_id"] for c in conflicts]
            )

    # ... apply delta normally ...
```

### Option 2: Semantic Context Retrieval for Agents

When running an agent, retrieve similar past contexts:

```python
from app.services.vector_search_service import get_vector_search_service
from app.services.voyage_embedding_service import get_voyage_embedding_service

async def run_agent_with_context(context_id: str):
    # Get current context
    context = await mongodb_service.get_context(context_id)

    # Generate embedding for current summary
    embedding_service = get_voyage_embedding_service()
    summary_embedding = await embedding_service.generate_embedding(
        context.fragments[0].content  # or summary field
    )

    # Find similar past contexts
    vector_search = get_vector_search_service()
    similar_contexts = await vector_search.find_similar_contexts(
        query_embedding=summary_embedding,
        limit=3,
        min_score=0.7
    )

    # Include in agent prompt
    prompt = f"""
    Current context: {context}

    Similar past contexts:
    {similar_contexts}

    Task: ...
    """
```

## 🧪 Testing Vector Search

### 1. Initialize a context with embeddings

```bash
curl -X POST http://localhost:8000/context/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session",
    "initial_input": "Test data for vector search",
    "metadata": {}
  }'
```

(Embeddings will be auto-generated via Voyage AI)

### 2. Search for similar content

Get the embedding from the created context, then search:

```bash
# First, get the context
curl http://localhost:8000/context/<context_id>

# Extract embedding from response, then search
curl -X POST http://localhost:8000/search/fragments/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_embedding": [... extracted embedding ...],
    "limit": 5
  }'
```

## 🐛 Troubleshooting

### "Index not found" error

- Wait 5 minutes after creating index
- Verify index name is exactly `vector_search_index`
- Check collection name is `context_packets`

### "Vector dimensions mismatch"

- Check your Voyage AI model (voyage-lite = 384, voyage-2 = 1024)
- Update index definition to match

### No results returned

- Lower `min_score` threshold (try 0.5)
- Verify embeddings are actually stored in fragments
- Check MongoDB Atlas search index status

## 📊 Performance Notes

- **Index build time**: ~5 minutes
- **Query latency**: 50-200ms typical
- **Free tier**: Atlas M0 does NOT support Vector Search (need M10+)
- **Batch queries**: More efficient than individual searches

## 🔗 References

- [MongoDB Atlas Vector Search Docs](https://www.mongodb.com/docs/atlas/atlas-vector-search/)
- [Voyage AI Embeddings](https://docs.voyageai.com/)
- [kNN Search Examples](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-tutorial/)
