# RAG System Architecture (Current State)

The system uses a Retrieval-Augmented Generation (RAG) pipeline with PostgreSQL/pgvector as the primary vector store and an optional Redis-backed LSH index for acceleration.

## Ingestion Flow (Document Upload)

1.  **Upload**: A file is uploaded via the UI and handled by [`backend.chat_service.handle_upload()`](backend/chat_service.py:36).
2.  **Chunking**: The file content is split into text chunks using [`backend.chunking.chunk_text()`](backend/chunking.py).
3.  **Embedding**: The text chunks are embedded using the Gemini API via [`backend.embeddings.embed_texts()`](backend/embeddings.py:28).
4.  **Storage**: The document metadata and the chunks, along with their Gemini embeddings, are stored in the `document_chunks` table in the PostgreSQL database.

## Query Flow (Question Answering - RAG Mode)

1.  **Query Handling**: A user question is processed by [`backend.chat_service.handle_question()`](backend/chat_service.py:138).
2.  **Retrieval**: The system calls [`backend.retrieval.get_context_chunks()`](backend/retrieval.py:66) to find relevant context.
3.  **Embedding**: The user's question is embedded using the Gemini API via [`backend.embeddings.embed_query()`](backend/embeddings.py:128).
4.  **Search**:
    *   **If LSH is disabled**: A direct pgvector search is performed via [`backend.db.search_similar_chunks()`](backend/db.py).
    *   **If LSH is enabled**: A hybrid search is performed via [`backend.retrieval.lsh_hybrid_search()`](backend/retrieval.py:17). This uses the LSH index (Redis) for candidate retrieval, and then fetches the full vectors from PostgreSQL for final cosine similarity reranking.
5.  **Generation**: The retrieved context is formatted by [`backend.retrieval.format_context()`](backend/retrieval.py:132) and passed to the LLM client via [`backend.llm_client.LLMClient.generate_answer()`](backend/llm_client.py) to generate the final answer.