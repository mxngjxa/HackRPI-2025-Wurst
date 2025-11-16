# RAG System Architecture (Refactored)

The system uses a single, consistent Retrieval-Augmented Generation (RAG) pipeline with PostgreSQL/pgvector as the **source of truth** for all vectors and metadata. The Redis-backed LSH index acts strictly as an **acceleration/indexing layer**.

## Embedding Strategy

-   **Local vs. Remote**: The system supports toggling between a local HuggingFace model (Jina-Embeddings-v2-Base-en) and the remote Gemini API via the `USE_LOCAL_EMBEDDINGS` and `ALLOW_EMBEDDING_FALLBACK` configuration flags.
-   **Consistency**: All embedding calls (for ingestion and query) are routed through the unified abstraction in [`backend.embeddings.py`](backend/embeddings.py:1).

## Ingestion Flow (Document Upload)

1.  **Upload & Chunking**: A file is processed into text chunks.
2.  **Embedding**: Chunks are embedded using the configured embedding model (local Jina if enabled).
3.  **Storage**: The document metadata and chunks with their embeddings are stored in the `document_chunks` table in PostgreSQL.
4.  **LSH Indexing**: **If LSH is enabled**, the new chunk IDs and embeddings are immediately indexed into the Redis-backed LSHRS index via [`backend.lsh_indexer.index_new_chunks()`](backend/lsh_indexer.py).

## Query Flow (Question Answering - RAG Mode & MCP Tools)

1.  **Query Handling**: A user question (from the UI or an MCP tool call) is processed.
2.  **Embedding**: The question is embedded using the configured embedding model (local Jina if enabled).
3.  **Search**: The system calls [`backend.retrieval.get_context_chunks()`](backend/retrieval.py:66).
    *   **If LSH is enabled**: A hybrid search is performed via [`backend.retrieval.lsh_hybrid_search()`](backend/retrieval.py:17).
        *   It uses the query embedding to get candidate chunk IDs from the LSH index (Redis) via [`backend.lsh_indexer.query_similar_chunks()`](backend/lsh_indexer.py).
        *   The LSH indexer fetches the full vectors for reranking directly from PostgreSQL via its `vector_fetch_fn` (which calls [`backend.lsh_indexer._fetch_vectors_for_lshrs()`](backend/lsh_indexer.py)).
        *   **Fallback**: If the LSH search fails, the system automatically falls back to a direct pgvector search.
    *   **If LSH is disabled (or fallback is triggered)**: A direct pgvector search is performed via [`backend.db.search_similar_chunks()`](backend/db.py).
4.  **Generation**: The retrieved context is formatted and passed to the LLM client to generate the final answer.

## MCP Integration

-   The MCP `semantic_search` tool calls the same [`backend.retrieval.get_context_chunks()`](backend/retrieval.py:66) function as the main UI flow, ensuring a single, authoritative RAG path.
-   A dedicated helper, [`backend.mcp_query.embed_mcp_query()`](backend/mcp_query.py), wraps the core embedding logic for clarity in the MCP context.