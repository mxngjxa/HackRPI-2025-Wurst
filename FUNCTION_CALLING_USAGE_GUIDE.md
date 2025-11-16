# Function Calling Usage Guide

This guide explains how to enable and use Function Calling mode, where the Language Model actively calls functions to access the database and retrieve data when users ask questions.

## What is Function Calling?

Function Calling allows the AI model to **actively decide** what information it needs and **call functions** to retrieve that data from the database, rather than receiving all context upfront.

### Traditional RAG vs Function Calling

**Traditional RAG Mode (Default):**
```
User Question → System retrieves documents → Provides context to AI → AI generates answer
```
- System decides what to retrieve
- All context provided upfront
- Single retrieval step

**Function Calling Mode:**
```
User Question → AI decides what it needs → AI calls tools → Tools query database → AI gets results → AI generates answer
```
- AI decides what to retrieve
- Multiple tool calls possible
- Dynamic information gathering

## Architecture Overview

```
┌─────────────┐
│    User     │
│  Question   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  GeminiFunctionCallingClient    │
│  (backend/llm_client.py)        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│    FunctionHandler              │
│  (backend/function_handler.py)  │
│  - Manages AI conversation      │
│  - Detects function calls       │
│  - Executes tools               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│    Tool Execution               │
│  (backend/mcp_tools.py)         │
│  - semantic_search()            │
│  - list_documents()             │
│  - keyword_search()             │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│    PostgreSQL Database          │
│  - documents table              │
│  - document_chunks table        │
│  - Vector similarity search     │
└─────────────────────────────────┘
```

## Step 1: Enable Function Calling

### Configure .env File

Edit your `.env` file:

```bash
# ============================================
# Function Calling Configuration
# ============================================

# Enable Function Calling mode
USE_FUNCTION_CALLING=true

# Disable Mock LLM (Function Calling requires real API)
USE_MOCK_LLM=false

# Required: Your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here

# Required: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/llm_chatbot

# Optional: Model configuration
GEMINI_CHAT_MODEL=gemini-1.5-flash

# Optional: Maximum function calls per question (prevents infinite loops)
MAX_FUNCTION_CALLS=5

# Optional: Enable/disable specific tools
ENABLE_SEMANTIC_SEARCH_TOOL=true
ENABLE_KEYWORD_SEARCH_TOOL=true
ENABLE_DOCUMENT_QUERY_TOOL=true
```

### Restart Application

```bash
python app.py
```

You should see in the logs:
```
[INFO] Creating GeminiFunctionCallingClient (USE_FUNCTION_CALLING=true)
[INFO] Initialized FunctionHandler with 3 tools
```

## Step 2: Understanding Available Tools

The AI has access to three tools to query the database:

### 1. semantic_search

**Purpose:** Find relevant information using vector similarity (meaning-based search)

**When AI uses it:** When it needs to find content related to a concept or question

**Parameters:**
- `query` (required): The search query
- `top_k` (optional): Number of results to return (default: 5)

**Database Query:**
```sql
SELECT dc.content, d.filename, 
       (dc.embedding <=> :query_embedding) AS distance
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
ORDER BY dc.embedding <=> :query_embedding
LIMIT :top_k
```

**Example AI Call:**
```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "machine learning algorithms",
    "top_k": 5
  }
}
```

**Returns:**
```json
{
  "found": 5,
  "chunks": [
    {
      "content": "Machine learning algorithms include...",
      "filename": "ml_guide.txt",
      "distance": 0.23
    },
    ...
  ]
}
```

### 2. list_documents

**Purpose:** See what documents are available in the current session

**When AI uses it:** When it needs to know what documents exist before searching

**Parameters:**
- `include_preloaded` (optional): Include system-wide documents (default: true)

**Database Query:**
```sql
SELECT id, filename, mime_type, is_preloaded, uploaded_at
FROM documents
WHERE is_preloaded = TRUE OR session_id = :session_id
ORDER BY is_preloaded DESC, uploaded_at DESC
```

**Example AI Call:**
```json
{
  "name": "list_documents",
  "arguments": {
    "include_preloaded": true
  }
}
```

**Returns:**
```json
{
  "total": 3,
  "documents": [
    {
      "id": 1,
      "filename": "user_guide.txt",
      "mime_type": "text/plain",
      "is_preloaded": true,
      "uploaded_at": "2024-01-15 10:30:00"
    },
    ...
  ]
}
```

### 3. keyword_search

**Purpose:** Find exact text matches using traditional keyword search

**When AI uses it:** When looking for specific terms, names, or exact phrases

**Parameters:**
- `keywords` (required): Keywords to search for
- `limit` (optional): Maximum results (default: 10)

**Database Query:**
```sql
SELECT dc.content, d.filename
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
AND dc.content ILIKE :search_pattern
LIMIT :limit
```

**Example AI Call:**
```json
{
  "name": "keyword_search",
  "arguments": {
    "keywords": "API endpoint",
    "limit": 10
  }
}
```

**Returns:**
```json
{
  "found": 3,
  "results": [
    {
      "content": "The API endpoint is located at...",
      "filename": "api_docs.txt"
    },
    ...
  ]
}
```

## Step 3: How Function Calling Works

### Complete Workflow Example

**User asks:** "What are the main topics covered in the documents?"

#### Iteration 1: AI calls list_documents

```
AI → list_documents(include_preloaded=true)
```

**Database executes:**
```sql
SELECT id, filename, mime_type, is_preloaded, uploaded_at
FROM documents
WHERE is_preloaded = TRUE OR session_id = 'abc-123'
```

**Returns to AI:**
```json
{
  "total": 2,
  "documents": [
    {"filename": "python_basics.txt", ...},
    {"filename": "web_development.txt", ...}
  ]
}
```

#### Iteration 2: AI calls semantic_search

```
AI → semantic_search(query="main topics overview", top_k=5)
```

**Database executes:**
```sql
-- First, generate embedding for "main topics overview"
-- Then search for similar vectors
SELECT dc.content, d.filename
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (d.is_preloaded = TRUE OR d.session_id = 'abc-123')
ORDER BY dc.embedding <=> '[0.123, 0.456, ...]'::vector
LIMIT 5
```

**Returns to AI:**
```json
{
  "found": 5,
  "chunks": [
    {"content": "Python basics include variables, functions...", ...},
    {"content": "Web development covers HTML, CSS, JavaScript...", ...},
    ...
  ]
}
```

#### Iteration 3: AI generates final answer

```
AI: Based on the documents, the main topics covered are:

1. Python Basics - covering variables, functions, and data structures
2. Web Development - including HTML, CSS, and JavaScript fundamentals

The documents provide comprehensive coverage of both programming fundamentals and web technologies.
```

### Code Flow

```python
# backend/function_handler.py

def generate_answer(self, question: str, session_id: str) -> str:
    # Start chat with AI
    chat = self.model.start_chat(history=[])
    
    # Send question
    response = chat.send_message(question)
    
    # Loop until AI provides final answer
    while has_function_calls(response):
        # Extract function calls from AI response
        function_calls = extract_function_calls(response)
        
        # Execute each function
        for func_call in function_calls:
            tool_name = func_call.name
            tool_args = func_call.args
            
            # Execute tool (queries database)
            result = execute_tool(tool_name, tool_args, session_id)
            
            # Send result back to AI
            response = chat.send_message(result)
    
    # Extract final answer
    return response.text
```

## Step 4: Testing Function Calling

### Test Script

Create `test_function_calling.py`:

```python
import logging
from backend.llm_client import get_llm_client
from backend.chat_service import generate_session_id, handle_upload

logging.basicConfig(level=logging.INFO)

# Generate session
session_id = generate_session_id()
print(f"Session ID: {session_id}")

# Upload test document
test_files = ["test_documents/sample1.txt"]
success, errors = handle_upload(test_files, session_id)
print(f"Uploaded: {success} files")

# Get Function Calling client
client = get_llm_client()
print(f"Client type: {type(client).__name__}")

# Test questions
questions = [
    "What documents are available?",
    "Summarize the main content",
    "Search for specific keywords about 'machine learning'"
]

for question in questions:
    print(f"\n{'='*60}")
    print(f"Q: {question}")
    print(f"{'='*60}")
    
    answer = client.generate_answer("", question, session_id)
    print(f"A: {answer}")
```

Run the test:
```bash
python test_function_calling.py
```

### Expected Output

```
Session ID: abc-123-def-456
Uploaded: 1 files
Client type: GeminiFunctionCallingClient

============================================================
Q: What documents are available?
============================================================
[INFO] Generating answer with function calling: What documents are available?...
[INFO] Iteration 1: Processing 1 function call(s)
[INFO] Executing tool: list_documents
[INFO] Generated final answer (length: 156)
A: You have 1 document available: "sample1.txt" which was uploaded recently. This is a text/plain document.

============================================================
Q: Summarize the main content
============================================================
[INFO] Generating answer with function calling: Summarize the main content...
[INFO] Iteration 1: Processing 1 function call(s)
[INFO] Executing tool: semantic_search
[INFO] Generated final answer (length: 342)
A: The document discusses machine learning fundamentals, including supervised and unsupervised learning algorithms...
```

## Step 5: Monitoring and Debugging

### Enable Detailed Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

### View Function Calls in Real-Time

```bash
# Watch logs
tail -f logs/app.log | grep -E "(Executing tool|function call|Iteration)"
```

### Log Output Example

```
[INFO] Generating answer with function calling: What are the main topics?...
[INFO] Iteration 1: Processing 1 function call(s)
[INFO] Executing tool: list_documents
[DEBUG] Tool result: {"total": 2, "documents": [...]}
[INFO] Iteration 2: Processing 1 function call(s)
[INFO] Executing tool: semantic_search
[DEBUG] Tool result: {"found": 5, "chunks": [...]}
[INFO] Generated final answer (length: 245)
```

### Common Patterns

**Pattern 1: List then Search**
```
User: "What's in the documents?"
AI calls: list_documents() → semantic_search()
```

**Pattern 2: Direct Search**
```
User: "Find information about X"
AI calls: semantic_search(query="X")
```

**Pattern 3: Keyword then Semantic**
```
User: "Find exact mentions of 'API' and related concepts"
AI calls: keyword_search(keywords="API") → semantic_search(query="API concepts")
```

## Step 6: Advanced Configuration

### Limit Function Calls

Prevent excessive API usage:

```bash
# .env
MAX_FUNCTION_CALLS=3  # AI can call max 3 functions per question
```

### Disable Specific Tools

```bash
# Only allow semantic search
ENABLE_SEMANTIC_SEARCH_TOOL=true
ENABLE_KEYWORD_SEARCH_TOOL=false
ENABLE_DOCUMENT_QUERY_TOOL=false
```

### Custom System Instructions

Edit `backend/function_handler.py`:

```python
def _build_system_instruction(self, session_id: str) -> str:
    return f"""You are a helpful AI assistant with access to a document database.

Current session ID: {session_id}

Guidelines:
1. Always use semantic_search for conceptual questions
2. Use keyword_search for exact terms
3. Call list_documents first if you're unsure what's available
4. Provide concise, accurate answers
5. Cite the source document when possible

Remember: You can call multiple tools to gather complete information."""
```

## Step 7: Performance Optimization

### Database Indexes

Ensure these indexes exist for fast queries:

```sql
-- Vector similarity search (most important)
CREATE INDEX idx_chunks_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Session filtering
CREATE INDEX idx_documents_session ON documents(session_id);

-- Preloaded documents
CREATE INDEX idx_documents_preloaded ON documents(is_preloaded);

-- Keyword search
CREATE INDEX idx_chunks_content_gin ON document_chunks 
USING gin(to_tsvector('english', content));
```

### Connection Pooling

Adjust pool size for Function Calling workload:

```python
# backend/db.py
engine = create_engine(
    DATABASE_URL,
    pool_size=15,        # Higher for multiple tool calls
    max_overflow=30,
    pool_timeout=30
)
```

### Caching (Optional)

For frequently asked questions, consider caching:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_semantic_search(query: str, session_id: str, top_k: int):
    return _semantic_search({"query": query, "top_k": top_k}, session_id)
```

## Troubleshooting

### Issue: "session_id is required for function calling mode"

**Cause:** Function Calling requires session_id to filter documents

**Solution:** Ensure session_id is passed:
```python
answer = client.generate_answer("", question, session_id)  # session_id required
```

### Issue: AI doesn't call any functions

**Cause:** Question might be too general or AI doesn't think it needs data

**Solution:** 
- Ask more specific questions
- Check system instructions in `function_handler.py`
- Verify tools are enabled in `.env`

### Issue: "Max iterations reached"

**Cause:** AI is calling too many functions

**Solution:**
- Increase `MAX_FUNCTION_CALLS` in `.env`
- Simplify the question
- Check if AI is stuck in a loop (review logs)

### Issue: Slow responses

**Cause:** Multiple function calls + database queries

**Solution:**
- Optimize database indexes
- Increase connection pool size
- Consider caching frequent queries
- Reduce `TOP_K_RETRIEVAL` value

### Issue: Empty results from tools

**Cause:** No documents in session or poor query

**Solution:**
```bash
# Check documents exist
psql llm_chatbot -c "SELECT COUNT(*) FROM documents WHERE session_id = 'your-session-id';"

# Check chunks exist
psql llm_chatbot -c "SELECT COUNT(*) FROM document_chunks;"
```

## Best Practices

### 1. Session Management

Always use consistent session IDs:
```python
# Generate once per user session
session_id = generate_session_id()

# Use same session_id for all operations
handle_upload(files, session_id)
client.generate_answer("", question, session_id)
```

### 2. Error Handling

Tools return error messages as strings:
```python
def execute_tool(tool_name, tool_args, session_id):
    try:
        # Execute tool
        return result
    except Exception as e:
        return f"Error: {str(e)}"  # AI will see this error
```

### 3. Cost Management

Function Calling uses more API calls:
- Each function call = 1 API request
- Final answer generation = 1 API request
- Total = (number of function calls + 1) × API cost

Monitor usage:
```bash
# Count function calls in logs
grep "Executing tool" logs/app.log | wc -l
```

### 4. Security

Tools automatically filter by session_id:
```sql
-- Users can only access their own documents
WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
```

## Comparison: RAG vs Function Calling

| Aspect | Traditional RAG | Function Calling |
|--------|----------------|------------------|
| **Control** | System decides | AI decides |
| **Flexibility** | Single retrieval | Multiple calls |
| **API Calls** | 1 per question | 2-6 per question |
| **Cost** | Lower | Higher |
| **Accuracy** | Good | Better |
| **Latency** | Faster | Slower |
| **Use Case** | Simple Q&A | Complex queries |

## Next Steps

1. ✓ Enable Function Calling in `.env`
2. ✓ Upload test documents
3. ✓ Ask questions and observe tool calls in logs
4. ✓ Experiment with different question types
5. ✓ Monitor performance and costs
6. ✓ Optimize based on your use case

For database connection issues, see `DATABASE_CONNECTION_GUIDE.md`.
