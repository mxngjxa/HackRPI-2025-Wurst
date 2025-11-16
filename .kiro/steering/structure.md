---
inclusion: always
---

# Project Structure

## Directory Layout

```
llm-file-chatbot/
├── backend/              # Core application logic
│   ├── config.py        # Environment variables and validation
│   ├── db.py            # Database operations (SQLAlchemy)
│   ├── file_parser.py   # File validation and reading
│   ├── chunking.py      # Text segmentation with overlap
│   ├── embeddings.py    # Gemini embedding generation
│   ├── retrieval.py     # Semantic search and context assembly
│   ├── llm_client.py    # LLM abstraction (Mock + Real)
│   └── chat_service.py  # Service orchestration
├── scripts/             # Utility scripts
│   └── preload_data.py  # Preload knowledge base documents
├── preload_docs/        # System-wide reference documents (.txt)
├── app.py               # Gradio web interface (main entry point)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md           # Setup and usage documentation
```

## Module Organization

### Backend Modules

- **config.py**: Centralized configuration with validation on import
- **db.py**: Database layer with connection pooling and CRUD operations
- **file_parser.py**: File validation (size, format) and UTF-8 reading
- **chunking.py**: Text splitting with configurable size and overlap
- **embeddings.py**: Batch embedding generation with retry logic
- **retrieval.py**: Vector search and context formatting
- **llm_client.py**: Abstract LLM interface (MockLLMClient for dev, GeminiLLMClient for prod)
- **chat_service.py**: High-level orchestration (upload, question, clear session)

### Database Schema

**documents table**:
- Stores both preloaded and session-specific documents
- `is_preloaded=TRUE` + `session_id=NULL` for system documents
- `is_preloaded=FALSE` + `session_id=<uuid>` for user uploads

**document_chunks table**:
- One row per chunk with embedding vector
- CASCADE DELETE on document removal
- IVFFlat index on embedding column for fast similarity search

## Architecture Patterns

- **Separation of concerns**: Each module has single responsibility
- **Configuration validation**: Fails fast on startup if config invalid
- **Connection pooling**: Reusable database connections
- **Batch processing**: Embeddings generated in batches (100 texts)
- **Retry logic**: Exponential backoff for API failures
- **Session isolation**: Documents scoped to Gradio session ID
- **Mock mode**: Development without external API dependencies
