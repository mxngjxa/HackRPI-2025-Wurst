---
inclusion: always
---

# Technology Stack

## Core Technologies

- **Python 3.8+**: Primary language
- **Gradio 4.0+**: Web interface framework
- **PostgreSQL 12+**: Database with pgvector extension
- **Google Gemini API**: Embeddings (embedding-001) and chat (gemini-1.5-flash)

## Key Libraries

- `gradio`: Web UI and session management
- `psycopg2-binary`: PostgreSQL driver
- `SQLAlchemy`: Database ORM and connection pooling
- `pgvector`: Vector similarity search
- `python-dotenv`: Environment configuration
- `google-generativeai`: Gemini API client

## Database

- PostgreSQL with pgvector extension for vector operations
- IVFFlat index for efficient similarity search
- Cascade delete for automatic chunk cleanup
- Connection pooling (pool_size=10, max_overflow=20)

## Common Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create database
createdb llm_chatbot

# Initialize database schema
python -c "from backend.db import init_db; init_db()"
```

### Development
```bash
# Run application (starts Gradio server on http://127.0.0.1:7860)
python app.py

# Preload knowledge base documents
python scripts/preload_data.py

# Use mock LLM mode (set in .env)
USE_MOCK_LLM=true
```

### Database Operations
```bash
# Check PostgreSQL status
pg_isready

# List databases
psql -l

# Connect to database
psql llm_chatbot
```

## Configuration

All configuration via environment variables in `.env` file:
- Required: `DATABASE_URL`, `GEMINI_API_KEY`
- Optional: Model names, chunking parameters, file limits
- See `.env.example` for complete reference
