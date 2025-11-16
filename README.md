# LLM File-Based Chatbot

A Python-based web application that enables users to upload text documents and ask questions about their content using Retrieval-Augmented Generation (RAG). The system uses Gradio for the web interface, PostgreSQL with pgvector for vector storage and similarity search, and Google Gemini for both embeddings and chat completion.

## Features

- **Document Upload**: Upload up to 5 text files per session (.txt format, max 10MB each)
- **Semantic Search**: Find relevant information using vector similarity search
- **Question Answering**: Get answers to questions based on uploaded documents
- **Preloaded Knowledge Base**: System administrators can preload common reference documents
- **Session Isolation**: Your documents remain private to your session
- **Mock LLM Mode**: Develop and test without requiring API credentials
- **Dual Architecture Modes**: Choose between RAG mode and Function Calling mode

## Architecture Modes

This application supports two operational modes:

### RAG Mode (Default) - Recommended

Traditional Retrieval-Augmented Generation approach:
1. System retrieves relevant document chunks using vector search
2. Chunks are formatted as context
3. AI generates answer based on provided context

**Advantages**:
- ✅ Faster response time (2-5 seconds)
- ✅ Lower API costs (fewer API calls)
- ✅ More predictable behavior
- ✅ Suitable for most use cases

**Configuration**: Set `USE_FUNCTION_CALLING=false` in `.env` (default)

### Function Calling Mode - Experimental

AI-driven data access using Gemini function calling:
1. AI receives user question
2. AI decides what information it needs
3. AI calls tools (semantic_search, list_documents, keyword_search)
4. AI analyzes results and generates answer

**Advantages**:
- ✅ More flexible (AI chooses search strategy)
- ✅ Can perform multi-step reasoning
- ✅ Better for complex queries

**Trade-offs**:
- ⚠️ Slower response time (5-15 seconds)
- ⚠️ Higher API costs (multiple API calls)
- ⚠️ Less predictable

**Configuration**: Set `USE_FUNCTION_CALLING=true` in `.env`

**Note**: Function Calling mode uses Gemini's native function calling feature, not MCP (Model Context Protocol). The database connection remains direct (Python → PostgreSQL) in both modes.

## Prerequisites

Before setting up the application, ensure you have the following installed:

1. **Python 3.8+**
2. **PostgreSQL 12+** with **pgvector extension**
3. **Google Gemini API Key** (for production mode)

### Installing PostgreSQL with pgvector

#### macOS (using Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15
```

Then install pgvector:
```bash
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

Then install pgvector following the instructions at: https://github.com/pgvector/pgvector

## Setup Instructions

### 1. Clone or Download the Project

```bash
cd llm-file-chatbot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

Create a new database for the application:

```bash
createdb llm_chatbot
```

Or using psql:
```sql
CREATE DATABASE llm_chatbot;
```

### 5. Configure Environment Variables

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
```

Edit `.env` and set the required variables:

```bash
# Required
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/llm_chatbot
GEMINI_API_KEY=your_actual_api_key_here

# Optional - adjust as needed
USE_MOCK_LLM=false  # Set to true for development without API
```

**Getting a Gemini API Key:**
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

### 6. Initialize the Database

The database schema will be automatically created when you first run the application. Alternatively, you can initialize it manually:

```bash
python -c "from backend.db import init_db; init_db()"
```

### 7. (Optional) Preload Knowledge Base Documents

Place any `.txt` files you want to preload into the `preload_docs/` directory, then run:

```bash
python scripts/preload_data.py
```

These documents will be available to all users across all sessions.

### 8. Run the Application

```bash
python app.py
```

The application will start and display a local URL (typically http://127.0.0.1:7860). Open this URL in your web browser.

## Usage

### Uploading Documents

1. Click the **file upload area** and select up to 5 `.txt` files
2. Click the **Upload files** button
3. Wait for the confirmation message

### Asking Questions

1. Type your question in the text input field
2. Click the **Send** button
3. The system will retrieve relevant context and generate an answer

### Clearing Your Session

1. Click the **Clear session** button
2. This will delete all your uploaded documents (but not preloaded ones)
3. A new session will be created automatically

## Development Mode

For development and testing without requiring a Gemini API key, set `USE_MOCK_LLM=true` in your `.env` file. The mock LLM will return formatted responses showing the question and context preview instead of making real API calls.

## Switching Between Modes

### To Use RAG Mode (Default)

Edit `.env` file:
```bash
USE_FUNCTION_CALLING=false
```

Restart the application. The system will use traditional retrieval-then-generate approach.

### To Use Function Calling Mode

Edit `.env` file:
```bash
USE_FUNCTION_CALLING=true
```

Restart the application. The AI will actively call tools to fetch information.

**Verification**: Check the logs after asking a question:
- RAG mode: `INFO - Using RAG mode - fetching context for AI`
- Function Calling mode: `INFO - Using Function Calling mode - AI will call tools to fetch data`

For more details, see `HOW_TO_SWITCH_MODES.md`.

## Project Structure

```
llm-file-chatbot/
├── backend/              # Backend modules
│   ├── config.py        # Configuration management
│   ├── db.py            # Database operations
│   ├── file_parser.py   # File reading and validation
│   ├── chunking.py      # Text segmentation
│   ├── embeddings.py    # Gemini embedding generation
│   ├── retrieval.py     # Semantic search
│   ├── llm_client.py    # LLM abstraction
│   └── chat_service.py  # Service orchestration
├── scripts/             # Utility scripts
│   └── preload_data.py  # Preload knowledge base
├── preload_docs/        # Documents to preload
├── app.py               # Gradio web interface
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
└── README.md           # This file
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `GEMINI_API_KEY` | Yes* | - | Google Gemini API key (*not required if USE_MOCK_LLM=true) |
| `GEMINI_CHAT_MODEL` | No | `gemini-1.5-flash` | Model for chat completion |
| `GEMINI_EMBEDDING_MODEL` | No | `embedding-001` | Model for embeddings |
| `EMBEDDING_DIMENSION` | No | `768` | Embedding vector dimension |
| `USE_MOCK_LLM` | No | `true` | Use mock LLM for development |
| `USE_FUNCTION_CALLING` | No | `false` | Enable Function Calling mode |
| `MAX_FUNCTION_CALLS` | No | `5` | Max function calls per question |
| `ENABLE_SEMANTIC_SEARCH_TOOL` | No | `true` | Enable semantic search tool |
| `ENABLE_KEYWORD_SEARCH_TOOL` | No | `true` | Enable keyword search tool |
| `ENABLE_DOCUMENT_QUERY_TOOL` | No | `true` | Enable document query tool |
| `CHUNK_SIZE` | No | `1000` | Maximum characters per chunk |
| `CHUNK_OVERLAP` | No | `200` | Overlap between chunks |
| `TOP_K_RETRIEVAL` | No | `5` | Number of chunks to retrieve |
| `MAX_FILE_SIZE_MB` | No | `10` | Maximum file size in MB |
| `MAX_FILES_PER_SESSION` | No | `5` | Maximum files per upload |

## Troubleshooting

### Database Connection Errors

- Verify PostgreSQL is running: `pg_isready`
- Check your `DATABASE_URL` in `.env`
- Ensure the database exists: `psql -l`

### pgvector Extension Not Found

- Install pgvector following the instructions above
- Restart PostgreSQL after installation
- Verify installation: `psql -c "CREATE EXTENSION vector;"`

### Gemini API Errors

- Verify your API key is correct
- Check your API quota at https://makersuite.google.com
- Use `USE_MOCK_LLM=true` for development

### File Upload Issues

- Ensure files are `.txt` format
- Check file size is under 10MB
- Verify files contain valid UTF-8 text

## License

This project is provided as-is for educational and demonstration purposes.

## Support

For issues and questions, please refer to the project documentation or contact the development team.
