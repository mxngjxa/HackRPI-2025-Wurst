# Design Document

## Overview

The LLM File-Based Chatbot is a Python-based web application that enables users to upload text documents and ask questions about their content using Retrieval-Augmented Generation (RAG). The system uses Gradio for the web interface, PostgreSQL with pgvector for vector storage and similarity search, and Google Gemini for both embeddings and chat completion.

The architecture follows a modular design with clear separation between the presentation layer (Gradio UI), business logic layer (service modules), and data layer (PostgreSQL). The system supports both a Mock LLM mode for development and testing, and a Real LLM mode for production use with Gemini.

### Key Design Principles

1. **Modularity**: Each component has a single responsibility and can be tested independently
2. **Configurability**: All parameters are externalized through environment variables
3. **Incremental Development**: Mock LLM allows development without API dependencies
4. **Session Isolation**: User documents are scoped to sessions for privacy
5. **Performance**: Database indexing and batch processing optimize response times
6. **Error Resilience**: Comprehensive error handling at all layers

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    User[User Browser]
    Gradio[Gradio Frontend<br/>app.py]
    ChatService[Chat Service<br/>chat_service.py]
    FileParser[File Parser<br/>file_parser.py]
    Chunking[Chunking<br/>chunking.py]
    Embeddings[Embeddings<br/>embeddings.py]
    Retrieval[Retrieval<br/>retrieval.py]
    LLMClient[LLM Client<br/>llm_client.py]
    DB[Database Layer<br/>db.py]
    Postgres[(PostgreSQL<br/>+ pgvector)]
    Gemini[Gemini API]
    Config[Configuration<br/>config.py]
    
    User -->|HTTP| Gradio
    Gradio -->|upload_files| ChatService
    Gradio -->|ask_question| ChatService
    Gradio -->|clear_session| ChatService
    
    ChatService --> FileParser
    ChatService --> Chunking
    ChatService --> Embeddings
    ChatService --> Retrieval
    ChatService --> LLMClient
    ChatService --> DB
    
    FileParser --> DB
    Chunking --> Embeddings
    Embeddings -->|embed_texts| Gemini
    Embeddings --> DB
    Retrieval -->|embed_query| Gemini
    Retrieval --> DB
    
    LLMClient -->|Real Mode| Gemini
    
    DB --> Postgres
    
    Config -.->|env vars| ChatService
    Config -.->|env vars| Embeddings
    Config -.->|env vars| LLMClient
    Config -.->|env vars| DB
```

### Layer Architecture

**Presentation Layer**
- `app.py`: Gradio UI components, event handlers, session state management

**Service Layer**
- `chat_service.py`: Orchestrates document upload, question answering, and session management
- `retrieval.py`: Handles semantic search and context retrieval

**Processing Layer**
- `file_parser.py`: File reading and validation
- `chunking.py`: Text segmentation
- `embeddings.py`: Gemini embedding generation
- `llm_client.py`: LLM abstraction with Mock and Real implementations

**Data Layer**
- `db.py`: Database operations and connection management
- PostgreSQL + pgvector: Persistent storage

**Configuration Layer**
- `config.py`: Environment variable loading and validation

## Components and Interfaces

### 1. Configuration Module (`backend/config.py`)

**Purpose**: Centralized configuration management with validation

**Interface**:
```python
# Constants
DATABASE_URL: str
GEMINI_API_KEY: str
GEMINI_CHAT_MODEL: str
GEMINI_EMBEDDING_MODEL: str
EMBEDDING_DIMENSION: int
USE_MOCK_LLM: bool
CHUNK_SIZE: int
CHUNK_OVERLAP: int
TOP_K_RETRIEVAL: int
MAX_FILE_SIZE_MB: int
MAX_FILES_PER_SESSION: int

# Functions
def validate_config() -> None:
    """Validates required environment variables are present"""
```

**Design Decisions**:
- Use `python-dotenv` for .env file support
- Provide sensible defaults for optional parameters
- Validate required variables at startup
- Raise clear exceptions for missing configuration

### 2. Database Module (`backend/db.py`)

**Purpose**: Database connection management and CRUD operations

**Interface**:
```python
def get_engine() -> Engine:
    """Returns SQLAlchemy engine with connection pooling"""

def init_db() -> None:
    """Initializes database schema and extensions"""

def insert_document(
    filename: str,
    mime_type: str,
    is_preloaded: bool,
    session_id: Optional[str]
) -> int:
    """Inserts document record, returns document_id"""

def insert_chunks(
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]]
) -> None:
    """Batch inserts chunks with embeddings"""

def search_similar_chunks(
    query_embedding: List[float],
    session_id: str,
    top_k: int
) -> List[str]:
    """Returns top-k similar chunks using cosine distance"""

def clear_session_documents(session_id: str) -> int:
    """Deletes session documents, returns count deleted"""

def document_exists(filename: str, is_preloaded: bool) -> bool:
    """Checks if preloaded document already exists"""
```

**Design Decisions**:
- Use SQLAlchemy for database abstraction
- Enable connection pooling (pool_size=10, max_overflow=20)
- Use parameterized queries to prevent SQL injection
- Implement batch insert for chunks to reduce round trips
- Use pgvector's `<->` operator for cosine distance
- Create indexes on `embedding` (ivfflat) and `session_id` (btree)

### 3. File Parser Module (`backend/file_parser.py`)

**Purpose**: File reading, validation, and content extraction

**Interface**:
```python
class FileValidationError(Exception):
    """Raised when file validation fails"""

def validate_file(file_obj: Any) -> None:
    """Validates file size and format"""

def read_txt_file(file_obj: Any) -> str:
    """Reads and decodes text file content"""
```

**Design Decisions**:
- Support Gradio's file object interface
- Validate file size before reading (10MB limit)
- Use UTF-8 decoding with error handling
- Reject empty or whitespace-only files
- Raise custom exceptions for validation errors

### 4. Chunking Module (`backend/chunking.py`)

**Purpose**: Text segmentation with overlap

**Interface**:
```python
def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int
) -> List[str]:
    """Splits text into overlapping chunks"""
```

**Design Decisions**:
- Use character-based chunking (simple and predictable)
- Support configurable chunk size and overlap
- Ensure last chunk is included even if smaller
- Preserve word boundaries where possible (future enhancement)

### 5. Embeddings Module (`backend/embeddings.py`)

**Purpose**: Generate embeddings using Gemini API

**Interface**:
```python
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for multiple texts in batches"""

def embed_query(text: str) -> List[float]:
    """Generates embedding for a single query"""
```

**Design Decisions**:
- Use `google-generativeai` SDK
- Batch process embeddings (batch_size=100) to optimize API calls
- Implement retry logic with exponential backoff
- Cache API client instance
- Handle API errors gracefully with logging

### 6. Retrieval Module (`backend/retrieval.py`)

**Purpose**: Semantic search and context assembly

**Interface**:
```python
def get_context_chunks(
    question: str,
    session_id: str,
    top_k: int
) -> List[str]:
    """Retrieves relevant chunks for a question"""

def format_context(chunks: List[str]) -> str:
    """Formats chunks into context string"""
```

**Design Decisions**:
- Use cosine similarity for vector search
- Include both preloaded and session documents
- Format context with clear delimiters
- Return empty list if no documents available

### 7. LLM Client Module (`backend/llm_client.py`)

**Purpose**: Abstract LLM interface with Mock and Real implementations

**Interface**:
```python
class LLMClient(ABC):
    @abstractmethod
    def generate_answer(self, context: str, question: str) -> str:
        """Generates answer given context and question"""

class MockLLMClient(LLMClient):
    def generate_answer(self, context: str, question: str) -> str:
        """Returns mock response with context preview"""

class GeminiLLMClient(LLMClient):
    def generate_answer(self, context: str, question: str) -> str:
        """Calls Gemini API for real response"""

def get_llm_client() -> LLMClient:
    """Factory function returning appropriate client"""
```

**Design Decisions**:
- Use Abstract Base Class for interface definition
- Factory pattern for client instantiation
- Mock client returns formatted debug information
- Real client uses Gemini's `generate_content` API
- Implement prompt template for RAG pattern
- Handle API errors with fallback messages

**Gemini API Integration**:
```python
# Prompt template
system_prompt = """You are a helpful assistant. Answer the user's question based on the provided context.
If the context doesn't contain relevant information, say so clearly.

Context:
{context}

Question: {question}

Answer:"""

# API call
model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
response = model.generate_content(system_prompt)
return response.text
```

### 8. Chat Service Module (`backend/chat_service.py`)

**Purpose**: High-level orchestration of chat operations

**Interface**:
```python
def generate_session_id() -> str:
    """Generates unique session identifier"""

def handle_upload(
    files: List[Any],
    session_id: str
) -> Tuple[int, List[str]]:
    """Processes file uploads, returns (count, errors)"""

def handle_question(
    question: str,
    session_id: str
) -> str:
    """Processes question and returns answer"""

def handle_clear_session(session_id: str) -> int:
    """Clears session documents, returns count deleted"""
```

**Design Decisions**:
- Use UUID4 for session identifiers
- Process files sequentially with error collection
- Validate inputs before processing
- Return structured results with success/error information
- Log all operations for debugging

### 9. Gradio Frontend (`app.py`)

**Purpose**: Web UI and user interaction handling

**Components**:
- File upload component (multiple files, .txt only)
- Chatbot display component
- Text input for questions
- Three action buttons (Upload, Send, Clear)
- Session state management

**Event Handlers**:
```python
def on_load() -> Tuple[str, List]:
    """Initializes session on app load"""

def on_upload(files, session_id, history) -> Tuple[List, List]:
    """Handles file upload, returns (history, files)"""

def on_send(message, session_id, history) -> Tuple[str, List]:
    """Handles question submission, returns (cleared_input, history)"""

def on_clear(session_id, history) -> Tuple[str, List]:
    """Handles session clear, returns (new_session_id, empty_history)"""
```

**Design Decisions**:
- Use Gradio Blocks for custom layout
- Store session_id and history in gr.State
- Clear file input after successful upload
- Show loading indicators during processing
- Display system messages distinctly (using None as user)
- Handle errors gracefully with user-friendly messages

### 10. Preload Script (`scripts/preload_data.py`)

**Purpose**: Load initial knowledge base documents

**Interface**:
```python
def preload_documents(directory: str) -> None:
    """Loads all .txt files from directory into database"""
```

**Design Decisions**:
- Check for existing documents to avoid duplicates
- Process files sequentially with progress logging
- Skip invalid files with warnings
- Use same processing pipeline as user uploads
- Support re-running without side effects

## Data Models

### Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    is_preloaded BOOLEAN DEFAULT FALSE,
    session_id VARCHAR(64),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_preloaded_filename UNIQUE (filename, is_preloaded)
        WHERE is_preloaded = TRUE
);

-- Index for session-based queries
CREATE INDEX IF NOT EXISTS idx_documents_session 
    ON documents(session_id) 
    WHERE session_id IS NOT NULL;

-- Document chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    CONSTRAINT unique_chunk_per_document UNIQUE (document_id, chunk_index)
);

-- Index for vector similarity search (IVFFlat)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
    ON document_chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Design Rationale**:
- `documents.is_preloaded`: Distinguishes permanent vs session documents
- `documents.session_id`: NULL for preloaded, UUID for session documents
- Unique constraint on preloaded filenames prevents duplicates
- CASCADE DELETE ensures chunks are removed with documents
- IVFFlat index optimizes vector search (lists=100 for ~10k documents)
- Partial index on session_id saves space

### Python Data Classes

```python
@dataclass
class Document:
    id: int
    filename: str
    mime_type: str
    is_preloaded: bool
    session_id: Optional[str]
    uploaded_at: datetime

@dataclass
class Chunk:
    id: int
    document_id: int
    chunk_index: int
    content: str
    embedding: List[float]

@dataclass
class UploadResult:
    success_count: int
    errors: List[str]

@dataclass
class ChatResponse:
    answer: str
    sources: List[str]  # Future enhancement
```

## Error Handling

### Error Categories and Strategies

**1. File Upload Errors**
- Invalid file format → Reject with clear message
- File too large → Reject with size limit message
- Empty file → Reject with validation message
- Encoding errors → Try fallback encodings, then reject

**2. Database Errors**
- Connection failure → Display error, prevent operations
- Query timeout → Retry once, then fail gracefully
- Constraint violation → Log and return user-friendly message

**3. API Errors**
- Gemini API failure → Retry with exponential backoff (3 attempts)
- Rate limiting → Wait and retry with backoff
- Invalid API key → Log error, display generic message
- Network timeout → Retry once, then fail

**4. Processing Errors**
- Chunking failure → Log error, skip document
- Embedding generation failure → Retry batch, then fail
- Empty context → Return "no relevant information" message

### Error Response Format

```python
@dataclass
class ErrorResponse:
    error_type: str  # "validation", "database", "api", "processing"
    user_message: str  # User-friendly message
    technical_details: str  # For logging
    recoverable: bool  # Can user retry?
```

### Logging Strategy

- Use Python `logging` module with structured logging
- Log levels:
  - DEBUG: Function entry/exit, variable values
  - INFO: Successful operations, user actions
  - WARNING: Recoverable errors, fallback usage
  - ERROR: Failed operations, API errors
  - CRITICAL: System failures, configuration errors
- Log format: `[timestamp] [level] [module] [session_id] message`
- Rotate logs daily, keep 30 days

## Testing Strategy

### Unit Tests

**Modules to Test**:
1. `config.py`: Environment variable validation
2. `file_parser.py`: File reading, validation, error cases
3. `chunking.py`: Chunk generation, edge cases (empty, small, large)
4. `db.py`: CRUD operations with test database
5. `llm_client.py`: Mock client behavior, factory function
6. `chat_service.py`: Orchestration logic with mocked dependencies

**Testing Approach**:
- Use `pytest` as test framework
- Use `pytest-mock` for mocking external dependencies
- Use test fixtures for database setup/teardown
- Mock Gemini API calls in unit tests
- Aim for >80% code coverage

### Integration Tests

**Test Scenarios**:
1. End-to-end upload flow: file → chunks → embeddings → database
2. End-to-end query flow: question → embedding → retrieval → LLM → response
3. Session isolation: verify documents don't leak between sessions
4. Preloaded documents: verify accessible across all sessions
5. Clear session: verify complete cleanup

**Testing Approach**:
- Use test PostgreSQL database
- Use Mock LLM for predictable responses
- Test with real Gemini API in separate suite (optional)
- Verify database state after operations

### Manual Testing Checklist

- [ ] Upload single file and ask questions
- [ ] Upload multiple files (up to 5)
- [ ] Attempt to upload >5 files (verify limit)
- [ ] Upload file >10MB (verify rejection)
- [ ] Upload empty file (verify rejection)
- [ ] Upload non-.txt file (verify rejection)
- [ ] Ask question with no documents (verify graceful handling)
- [ ] Clear session and verify documents removed
- [ ] Verify preloaded documents persist after clear
- [ ] Test with Mock LLM mode
- [ ] Test with Real LLM mode (when available)
- [ ] Test error scenarios (database down, API failure)

## Performance Considerations

### Optimization Strategies

**1. Database Performance**
- Connection pooling (10 connections, 20 max overflow)
- Batch insert for chunks (single transaction)
- IVFFlat index for vector search
- Partial indexes on filtered columns
- Query result caching (future enhancement)

**2. Embedding Generation**
- Batch processing (100 texts per API call)
- Async processing (future enhancement)
- Progress indicators for long operations

**3. Vector Search**
- Limit top-k to reasonable number (default 5)
- Use approximate nearest neighbor (IVFFlat)
- Consider HNSW index for larger datasets

**4. Memory Management**
- Stream large files instead of loading entirely
- Limit chunk size to prevent memory issues
- Clear session data promptly

### Expected Performance

- File upload (1MB): ~2-5 seconds
- Embedding generation: ~1-2 seconds per 100 chunks
- Vector search: <100ms for 10k documents
- LLM response: ~2-5 seconds (Gemini API dependent)
- Total question answering: ~3-8 seconds

## Security Considerations

### Input Validation
- File size limits (10MB)
- File type validation (.txt only)
- Content sanitization (strip control characters)
- SQL injection prevention (parameterized queries)

### Data Privacy
- Session isolation (documents not shared)
- No persistent conversation history
- Session cleanup on clear
- No user authentication (single-user demo)

### API Security
- API keys in environment variables (not in code)
- HTTPS for Gemini API calls
- Rate limiting (handled by Gemini)
- Error messages don't expose sensitive details

### Future Security Enhancements
- Add user authentication
- Implement rate limiting per session
- Add CSRF protection
- Sanitize LLM outputs
- Add content filtering

## Deployment Considerations

### Local Development Setup

1. Install PostgreSQL with pgvector extension
2. Create database and run schema
3. Set up Python virtual environment
4. Install dependencies from requirements.txt
5. Configure .env file
6. Run preload script for knowledge base
7. Launch Gradio app

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/llm_demo
GEMINI_API_KEY=your_api_key_here

# Optional (with defaults)
GEMINI_CHAT_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=embedding-001
EMBEDDING_DIMENSION=768
USE_MOCK_LLM=true
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_SESSION=5
```

### Dependencies

```
gradio>=4.0.0
psycopg2-binary>=2.9.0
SQLAlchemy>=2.0.0
pgvector>=0.2.0
python-dotenv>=1.0.0
google-generativeai>=0.3.0
```

## Future Enhancements

### Phase 2 Features
- Support for PDF, DOCX, and other file formats
- Conversation history persistence
- Multi-user support with authentication
- Document management UI (list, delete individual files)
- Source attribution in responses
- Streaming LLM responses

### Phase 3 Features
- Advanced chunking strategies (semantic, recursive)
- Hybrid search (keyword + vector)
- Query rewriting and expansion
- Multi-modal support (images, tables)
- Analytics dashboard
- Export conversation history

### Technical Improvements
- Async processing with Celery
- Redis caching layer
- Horizontal scaling support
- Monitoring and observability
- Automated testing pipeline
- Docker containerization
