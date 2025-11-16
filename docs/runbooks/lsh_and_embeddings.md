# LSH and Embeddings Runbook

This document provides instructions for managing the LSH index and toggling between local and remote embedding models.

## 1. Rebuild the LSH Index from PostgreSQL

The LSH index in Redis is an acceleration layer over the vectors stored in PostgreSQL. If the Redis data is lost or the index needs to be rebuilt (e.g., after a major configuration change), you can use the `scripts/build_lsh_index.py` script.

1.  **Ensure Redis is running** and accessible via the configuration in `.env`.
2.  **Run the build script**:
    ```bash
    python scripts/build_lsh_index.py
    ```
    This script will fetch all unindexed chunks from the `document_chunks` table, generate LSH signatures, and store them in Redis.

## 2. Verify Local Embedding Model

To confirm that the local Jina embedding model is correctly loaded and producing embeddings of the expected dimension (`EMBEDDING_DIMENSION`), you can run the dedicated test script.

1.  **Ensure Python dependencies are installed** (especially `torch` and `transformers`).
2.  **Run the test script**:
    ```bash
    python tests/test_local_embeddings.py
    ```
    The test will assert that the model is loaded once (caching works) and that the output shape is correct.

## 3. Toggle Embedding Modes

The system uses environment variables in the `.env` file to control which embedding model is used.

| Variable | Value | Description |
| :--- | :--- | :--- |
| `USE_LOCAL_EMBEDDINGS` | `true` | Use the local HuggingFace model (`LOCAL_EMBEDDING_MODEL_NAME`). |
| `USE_LOCAL_EMBEDDINGS` | `false` | Use the remote Gemini API (`GEMINI_EMBEDDING_MODEL`). |
| `ALLOW_EMBEDDING_FALLBACK` | `true` | If the local model fails to load, fall back to Gemini. |
| `ALLOW_EMBEDDING_FALLBACK` | `false` | If the local model fails to load, the application will fail fast. |

**To switch to local embeddings:**
Set `USE_LOCAL_EMBEDDINGS=true` in your `.env` file.

**To switch back to Gemini embeddings:**
Set `USE_LOCAL_EMBEDDINGS=false` in your `.env` file.

**Note**: After changing the embedding model, you should re-embed and re-index your documents to ensure consistency between the vectors in PostgreSQL and the LSH index. You can do this by re-running the preload script or re-uploading documents.