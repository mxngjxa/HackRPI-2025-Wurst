# Database Connection Guide

This guide explains how to properly connect a PostgreSQL database to the LLM File-Based Chatbot application.

## Prerequisites

- PostgreSQL 12+ installed
- Python 3.8+ with virtual environment
- Database with pgvector extension support

## Step 1: Install PostgreSQL with pgvector

### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Install pgvector extension
brew install pgvector
```

### Ubuntu/Debian
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector
sudo apt install postgresql-14-pgvector
```

### Verify Installation
```bash
# Check PostgreSQL is running
pg_isready

# Expected output: /tmp:5432 - accepting connections
```

## Step 2: Create Database

### Option A: Local Database (Recommended for Development)

```bash
# Create database
createdb llm_chatbot

# Or using psql
psql postgres
CREATE DATABASE llm_chatbot;
\q
```

### Option B: Remote Database (Production)

If using a cloud provider (AWS RDS, Google Cloud SQL, etc.):

1. Create a PostgreSQL instance through your cloud provider
2. Note down the connection details:
   - Host
   - Port (usually 5432)
   - Database name
   - Username
   - Password

## Step 3: Enable pgvector Extension

```bash
# Connect to your database
psql llm_chatbot

# Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify extension is installed
\dx

# Expected output should include:
# vector | 0.x.x | public | vector data type and ivfflat access method

# Exit psql
\q
```

## Step 4: Configure Database Connection

### Create .env File

Create a `.env` file in the project root directory:

```bash
# Copy from example
cp .env.example .env

# Edit the file
nano .env  # or use your preferred editor
```

### Configure DATABASE_URL

The `DATABASE_URL` follows this format:
```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

#### Local Database Examples:

**Without password (default local setup):**
```bash
DATABASE_URL=postgresql://yourusername@localhost:5432/llm_chatbot
```

**With password:**
```bash
DATABASE_URL=postgresql://yourusername:yourpassword@localhost:5432/llm_chatbot
```

**Using default postgres user:**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/llm_chatbot
```

#### Remote Database Examples:

**AWS RDS:**
```bash
DATABASE_URL=postgresql://admin:mypassword@mydb.abc123.us-east-1.rds.amazonaws.com:5432/llm_chatbot
```

**Google Cloud SQL:**
```bash
DATABASE_URL=postgresql://postgres:mypassword@34.123.45.67:5432/llm_chatbot
```

**Heroku Postgres:**
```bash
DATABASE_URL=postgresql://user:pass@ec2-xx-xxx-xxx-xxx.compute-1.amazonaws.com:5432/dbname
```

### Complete .env Configuration

```bash
# Required: Database connection
DATABASE_URL=postgresql://yourusername@localhost:5432/llm_chatbot

# Required: Gemini API key
GEMINI_API_KEY=your_actual_api_key_here

# Optional: Model configuration
GEMINI_CHAT_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=embedding-001
EMBEDDING_DIMENSION=768

# Optional: Application settings
USE_MOCK_LLM=false
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_SESSION=5
```

## Step 5: Initialize Database Schema

The application will automatically create the required tables on first run, but you can also initialize manually:

### Automatic Initialization (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the application
python app.py
```

The application will automatically:
1. Connect to the database
2. Create the `documents` table
3. Create the `document_chunks` table with vector column
4. Create necessary indexes

### Manual Initialization (Optional)

If you prefer to create tables manually:

```bash
# Connect to database
psql llm_chatbot

# Create tables
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    is_preloaded BOOLEAN DEFAULT FALSE,
    session_id VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768),
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX idx_documents_session ON documents(session_id);
CREATE INDEX idx_documents_preloaded ON documents(is_preloaded);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);

\q
```

## Step 6: Verify Connection

### Test Database Connection

Create a test script `test_db_connection.py`:

```python
from backend.db import get_engine, init_db
import logging

logging.basicConfig(level=logging.INFO)

try:
    # Test connection
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"✓ Connected to PostgreSQL: {version}")
    
    # Test pgvector extension
    with engine.connect() as conn:
        result = conn.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        if result.fetchone():
            print("✓ pgvector extension is installed")
        else:
            print("✗ pgvector extension is NOT installed")
    
    # Initialize schema
    init_db()
    print("✓ Database schema initialized")
    
    print("\n✓ Database connection successful!")
    
except Exception as e:
    print(f"✗ Database connection failed: {str(e)}")
```

Run the test:
```bash
python test_db_connection.py
```

Expected output:
```
✓ Connected to PostgreSQL: PostgreSQL 14.x on ...
✓ pgvector extension is installed
✓ Database schema initialized
✓ Database connection successful!
```

## Step 7: Connection Pooling

The application uses SQLAlchemy connection pooling for efficient database access:

```python
# backend/db.py configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Number of connections to maintain
    max_overflow=20,       # Additional connections when pool is full
    pool_timeout=30,       # Seconds to wait for available connection
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

## Troubleshooting

### Issue: "could not connect to server"

**Solution:**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
# macOS:
brew services start postgresql@14

# Linux:
sudo systemctl start postgresql
```

### Issue: "database does not exist"

**Solution:**
```bash
# Create the database
createdb llm_chatbot
```

### Issue: "extension 'vector' does not exist"

**Solution:**
```bash
# Install pgvector
# macOS:
brew install pgvector

# Linux:
sudo apt install postgresql-14-pgvector

# Then enable in database:
psql llm_chatbot -c "CREATE EXTENSION vector;"
```

### Issue: "password authentication failed"

**Solution:**
1. Check your username and password in DATABASE_URL
2. For local development, you may need to configure `pg_hba.conf`:

```bash
# Find pg_hba.conf location
psql -c "SHOW hba_file;"

# Edit the file (requires sudo)
sudo nano /path/to/pg_hba.conf

# Change authentication method to 'trust' for local development:
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust

# Restart PostgreSQL
brew services restart postgresql@14  # macOS
sudo systemctl restart postgresql    # Linux
```

### Issue: "SSL connection required"

For remote databases that require SSL:

```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### Issue: Connection pool exhausted

If you see "QueuePool limit exceeded":

1. Increase pool size in `backend/db.py`:
```python
pool_size=20,
max_overflow=40
```

2. Or check for connection leaks in your code

## Security Best Practices

### 1. Never Commit .env File

Add to `.gitignore`:
```
.env
*.env
```

### 2. Use Environment Variables in Production

Instead of `.env` file, set environment variables directly:

```bash
# Linux/macOS
export DATABASE_URL="postgresql://..."
export GEMINI_API_KEY="..."

# Or use your platform's secret management
# AWS: AWS Secrets Manager
# Google Cloud: Secret Manager
# Heroku: Config Vars
```

### 3. Use Read-Only Credentials When Possible

For production, create a dedicated database user with minimal permissions:

```sql
-- Create read-only user for queries
CREATE USER chatbot_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE llm_chatbot TO chatbot_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO chatbot_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chatbot_app;
```

### 4. Enable SSL for Remote Connections

```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## Performance Optimization

### 1. Create Appropriate Indexes

```sql
-- Already created by init_db(), but verify:
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_documents_session 
ON documents(session_id);
```

### 2. Adjust Connection Pool

For high-traffic applications:
```python
pool_size=20,
max_overflow=40
```

For low-traffic applications:
```python
pool_size=5,
max_overflow=10
```

### 3. Monitor Connection Usage

```python
# Check pool status
engine = get_engine()
print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
```

## Next Steps

Once your database is connected:

1. ✓ Test the connection with `test_db_connection.py`
2. ✓ Run the application: `python app.py`
3. ✓ Upload test documents through the web interface
4. ✓ Verify data is stored in the database:
   ```bash
   psql llm_chatbot -c "SELECT COUNT(*) FROM documents;"
   psql llm_chatbot -c "SELECT COUNT(*) FROM document_chunks;"
   ```

For using Function Calling with the database, see `FUNCTION_CALLING_USAGE_GUIDE.md`.
