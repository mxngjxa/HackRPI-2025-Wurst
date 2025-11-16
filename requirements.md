# RAG System Refactoring Requirements
## LSH + Redis Integration for Semantic Search

### Project Context
Refactoring existing RAG system to use Locality Sensitive Hashing (LSH) with Redis for efficient semantic search, replacing direct pgvector cosine similarity search.

### Current State
- **Database**: PostgreSQL with pgvector extension (768-dimensional embeddings)
- **Embedding Model**: Google Gemini (text-embedding-004, 768 dimensions)
- **Search**: Direct cosine similarity using pgvector
- **Chunking**: Character-based (1000 chars, 200 overlap)
- **Storage**: Documents and chunks in PostgreSQL

### Target Architecture

#### Core Components
1. **LSH Index**: Redis-backed LSH for candidate retrieval
2. **Vector Storage**: PostgreSQL for full vectors and metadata
3. **Hybrid Search**: LSH for fast candidates → cosine reranking

### Database Schema Requirements

#### PostgreSQL Tables
```sql
-- Keep existing schema, add LSH metadata
ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    lsh_indexed BOOLEAN DEFAULT FALSE;

ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS
    lsh_signature TEXT; -- Store signature for debugging/analysis
```

#### Redis Structure
- **Namespace**: `lsh:demo:*` for development
- **Buckets**: Sets containing chunk IDs per LSH band
- **Metadata**: Hash storing LSH configuration

### Integration Requirements

#### 1. LSH Configuration
```python
# Optimal parameters for 768-dim Gemini embeddings
LSH_CONFIG = {
    "dim": 768,
    "num_perm": 256,  # Number of hash functions
    "num_bands": 32,   # Bands for LSH
    "num_rows": 8,     # Rows per band (256/32)
    "redis_prefix": "lsh:demo",
    "similarity_threshold": 0.7  # Target similarity
}
```

#### 2. Ingestion Pipeline
- **Input**: Gemini embeddings from existing pipeline
- **Process**: 
  1. Generate LSH signatures for chunks
  2. Store signatures in Redis buckets
  3. Mark documents as `lsh_indexed=TRUE`
- **Batch Size**: 1000 chunks per Redis pipeline

#### 3. Query Pipeline
```python
def hybrid_search(query_embedding, session_id, top_k=5):
    # Phase 1: LSH candidate retrieval (top 50)
    candidates = lsh.get_top_k(query_embedding, topk=50)

    # Phase 2: Fetch full vectors from PostgreSQL
    vectors = fetch_chunk_embeddings(candidates)

    # Phase 3: Rerank with cosine similarity
    reranked = lsh.get_above_p(query_embedding, p=0.7)

    # Phase 4: Return top_k results
    return reranked[:top_k]
```

#### 4. Backend Modifications

##### New Module: backend/lsh_indexer.py
```python
from lshrs import LSHRS
import numpy as np
from typing import List, Tuple

class LSHIndexer:
    def __init__(self, redis_host="localhost", postgres_dsn=DATABASE_URL):
        self.lsh = LSHRS(
            dim=768,
            num_perm=256,
            redis_host=redis_host,
            redis_prefix="lsh:demo",
            vector_fetch_fn=self.fetch_vectors_from_postgres
        )

    def index_documents(self, session_id=None):
        # Index all documents or session-specific ones
        pass

    def fetch_vectors_from_postgres(self, chunk_ids):
        # Bridge function for LSHRS vector_fetch_fn
        pass
```

##### Modified: backend/retrieval.py
```python
def get_context_chunks(question: str, session_id: str, top_k: int = 5):
    # Old: Direct pgvector search
    # New: Use LSH hybrid search

    if USE_LSH_SEARCH:
        return lsh_hybrid_search(question, session_id, top_k)
    else:
        return pgvector_search(question, session_id, top_k)
```

### Migration Strategy

#### Phase 1: Setup (Non-Breaking)
1. Add LSH columns to existing schema
2. Deploy Redis container
3. Add `lsh_indexer.py` module
4. Add feature flag `USE_LSH_SEARCH=False`

#### Phase 2: Index Building
1. Run initial indexing for preloaded documents
2. Build LSH index from existing embeddings
3. Verify index integrity

#### Phase 3: Testing
1. A/B test with feature flag
2. Compare search quality metrics
3. Measure latency improvements

#### Phase 4: Cutover
1. Enable `USE_LSH_SEARCH=True`
2. Update ingestion pipeline to index new documents
3. Monitor performance

### Docker Compose Configuration
```yaml
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  db:
    image: postgres
    environment:
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: rag_demo
    ports:
      - "5432:5432"

  adminer:
    image: adminer
    ports:
      - "8080:8080"

volumes:
  redis_data:
```

### Environment Variables
```bash
# Existing
DATABASE_URL=postgresql://postgres:changeme@localhost/rag_demo
GEMINI_API_KEY=your-key-here
USE_MOCK_LLM=False

# New LSH configuration
USE_LSH_SEARCH=False  # Feature flag
REDIS_HOST=localhost
REDIS_PORT=6379
LSH_NUM_PERM=256
LSH_SIMILARITY_THRESHOLD=0.7
```

### Performance Targets
- **Indexing**: <1ms per vector
- **Search Latency**: <50ms for top-5 retrieval
- **Recall@10**: >0.85 compared to exact search
- **Redis Memory**: <500MB for 100K chunks

### Testing Requirements

#### Unit Tests
- LSH signature generation correctness
- Redis bucket operations
- PostgreSQL ↔ Redis ID mapping

#### Integration Tests
- End-to-end indexing pipeline
- Query with both preloaded and session documents
- Fallback to pgvector if Redis unavailable

#### Performance Tests
- Benchmark against current pgvector implementation
- Load test with 100K+ documents
- Memory usage profiling

### Monitoring & Observability
- Redis memory usage and key distribution
- LSH bucket size distribution (identify hotspots)
- Query latency P50/P95/P99
- Cache hit rates for reranking

### Success Criteria
1. **Latency**: 5x faster than pgvector for top-k retrieval
2. **Accuracy**: Recall@10 > 0.85
3. **Scalability**: Support 1M+ chunks
4. **Reliability**: Graceful fallback to pgvector

### Demo Script
```python
# 1. Load sample documents
python scripts/preload_data.py

# 2. Build LSH index
python scripts/build_lsh_index.py

# 3. Compare search methods
python scripts/benchmark_search.py

# 4. Launch UI with LSH enabled
USE_LSH_SEARCH=True python app.py
```

### Dependencies
```toml
[project.dependencies]
lshrs = "^0.1.0"
redis = "^5.0.0"
psycopg = {extras = ["binary"], version = "^3.1"}
numpy = "^2.0.0"
gradio = "^4.0.0"
google-generativeai = "^0.3.0"
sqlalchemy = "^2.0.0"
pgvector = "^0.2.0"
```
