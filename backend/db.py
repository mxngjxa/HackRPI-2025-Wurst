"""
Database module for LLM File-Based Chatbot.

Handles database connection management, schema initialization,
and CRUD operations for documents and chunks.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.pool import QueuePool
from backend.config import DATABASE_URL, EMBEDDING_DIMENSION

# Configure logging
logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Returns SQLAlchemy engine with connection pooling.
    
    Creates engine on first call and reuses it for subsequent calls.
    
    Returns:
        Engine: SQLAlchemy engine instance with connection pooling configured.
    
    Raises:
        Exception: If engine creation fails
    """
    global _engine
    
    if _engine is None:
        logger.info("Creating database engine with connection pooling")
        
        try:
            _engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=False  # Set to True for SQL query logging
            )
            logger.info("Database engine created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {str(e)}", exc_info=True)
            raise Exception(
                f"Failed to connect to database. Please check your DATABASE_URL: {str(e)}"
            ) from e
    
    return _engine


def init_db() -> None:
    """
    Initializes database schema and extensions.
    
    Creates:
    - pgvector extension
    - documents table with constraints
    - document_chunks table with CASCADE DELETE
    - Indexes for performance optimization
    
    This function is idempotent and can be called multiple times safely.
    
    Raises:
        Exception: If database initialization fails
    """
    logger.info("Initializing database schema")
    
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            # Enable pgvector extension
            logger.info("Creating pgvector extension")
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                logger.error(f"Failed to create pgvector extension: {str(e)}")
                raise Exception(
                    "Failed to enable pgvector extension. "
                    "Please ensure pgvector is installed on your PostgreSQL server."
                ) from e
            
            # Create documents table
            logger.info("Creating documents table")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    is_preloaded BOOLEAN DEFAULT FALSE,
                    session_id VARCHAR(64),
                    uploaded_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT unique_preloaded_filename UNIQUE (filename, is_preloaded)
                )
            """))
            
            # Create document_chunks table with CASCADE DELETE
            logger.info("Creating document_chunks table")
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIMENSION}) NOT NULL,
                    CONSTRAINT unique_chunk_per_document UNIQUE (document_id, chunk_index)
                )
            """))
            
            # Create index on session_id for efficient session-based queries
            logger.info("Creating index on session_id column")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_session 
                ON documents(session_id) 
                WHERE session_id IS NOT NULL
            """))
            
            # Create IVFFlat index on embedding column for vector search
            logger.info("Creating IVFFlat index on embedding column")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
                ON document_chunks 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            
            conn.commit()
        
        logger.info("Database schema initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        raise Exception(f"Failed to initialize database: {str(e)}") from e


def insert_document(
    filename: str,
    mime_type: str,
    is_preloaded: bool,
    session_id: Optional[str]
) -> int:
    """
    Inserts a document record into the database.
    
    Args:
        filename: Name of the document file
        mime_type: MIME type of the document
        is_preloaded: Whether this is a preloaded document
        session_id: Session identifier (None for preloaded documents)
    
    Returns:
        int: The document_id of the inserted document
    
    Raises:
        Exception: If database operation fails
    """
    engine = get_engine()
    
    logger.info(f"Inserting document: {filename} (preloaded={is_preloaded}, session={session_id})")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO documents (filename, mime_type, is_preloaded, session_id)
                    VALUES (:filename, :mime_type, :is_preloaded, :session_id)
                    RETURNING id
                """),
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "is_preloaded": is_preloaded,
                    "session_id": session_id
                }
            )
            document_id = result.fetchone()[0]
            conn.commit()
        
        logger.info(f"Document inserted with id: {document_id}")
        return document_id
        
    except Exception as e:
        logger.error(
            f"Database error inserting document {filename}: {str(e)}",
            exc_info=True
        )
        raise Exception(f"Failed to insert document into database: {str(e)}") from e


def insert_chunks(
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]]
) -> None:
    """
    Batch inserts chunks with their embeddings into the database.
    
    Args:
        document_id: ID of the parent document
        chunks: List of text chunks
        embeddings: List of embedding vectors (same length as chunks)
    
    Raises:
        ValueError: If chunks and embeddings lists have different lengths
        Exception: If database operation fails
    """
    if len(chunks) != len(embeddings):
        error_msg = (
            f"Chunks and embeddings must have same length. "
            f"Got {len(chunks)} chunks and {len(embeddings)} embeddings"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    engine = get_engine()
    
    logger.info(f"Inserting {len(chunks)} chunks for document_id: {document_id}")
    
    try:
        with engine.connect() as conn:
            # Batch insert all chunks in a single transaction
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Convert embedding to PostgreSQL array format
                embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                
                # Use string formatting for vector cast (safe because embedding_str is generated by us)
                query = f"""
                    INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
                    VALUES (:document_id, :chunk_index, :content, '{embedding_str}'::vector)
                """
                
                conn.execute(
                    text(query),
                    {
                        "document_id": document_id,
                        "chunk_index": idx,
                        "content": chunk
                    }
                )
            
            conn.commit()
        
        logger.info(f"Successfully inserted {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(
            f"Database error inserting chunks for document_id {document_id}: {str(e)}",
            exc_info=True
        )
        raise Exception(f"Failed to insert chunks into database: {str(e)}") from e


def search_similar_chunks(
    query_embedding: List[float],
    session_id: str,
    top_k: int
) -> List[str]:
    """
    Searches for similar chunks using pgvector cosine distance.
    
    Retrieves chunks from both preloaded documents and session-specific documents.
    
    Args:
        query_embedding: Embedding vector of the query
        session_id: Current session identifier
        top_k: Number of top results to return
    
    Returns:
        List[str]: List of chunk content strings, ordered by similarity
    
    Raises:
        Exception: If database search fails
    """
    engine = get_engine()
    
    logger.info(f"Searching for top {top_k} similar chunks for session: {session_id}")
    
    try:
        with engine.connect() as conn:
            # Convert embedding list to PostgreSQL array format string
            embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
            
            # Use string formatting for the vector cast (safe because embedding_str is generated by us)
            query = f"""
                SELECT dc.content
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.is_preloaded = TRUE OR d.session_id = :session_id
                ORDER BY dc.embedding <-> '{embedding_str}'::vector
                LIMIT :top_k
            """
            
            result = conn.execute(
                text(query),
                {
                    "session_id": session_id,
                    "top_k": top_k
                }
            )
            
            chunks = [row[0] for row in result.fetchall()]
        
        logger.info(f"Found {len(chunks)} similar chunks")
        return chunks
        
    except Exception as e:
        logger.error(
            f"Database error searching similar chunks for session {session_id}: {str(e)}",
            exc_info=True
        )
        raise Exception(f"Failed to search for similar chunks: {str(e)}") from e


def clear_session_documents(session_id: str) -> int:
    """
    Deletes all documents associated with a session.
    
    Chunks are automatically deleted via CASCADE DELETE constraint.
    
    Args:
        session_id: Session identifier
    
    Returns:
        int: Number of documents deleted
    
    Raises:
        Exception: If database operation fails
    """
    engine = get_engine()
    
    logger.info(f"Clearing documents for session: {session_id}")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM documents
                    WHERE session_id = :session_id
                    RETURNING id
                """),
                {"session_id": session_id}
            )
            
            deleted_count = len(result.fetchall())
            conn.commit()
        
        logger.info(f"Deleted {deleted_count} documents for session: {session_id}")
        return deleted_count
        
    except Exception as e:
        logger.error(
            f"Database error clearing session {session_id}: {str(e)}",
            exc_info=True
        )
        raise Exception(f"Failed to clear session documents: {str(e)}") from e


def document_exists(filename: str, is_preloaded: bool) -> bool:
    """
    Checks if a document already exists in the database.
    
    For preloaded documents, checks by filename and preloaded status.
    
    Args:
        filename: Name of the document file
        is_preloaded: Whether checking for preloaded document
    
    Returns:
        bool: True if document exists, False otherwise
    
    Raises:
        Exception: If database query fails
    """
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM documents
                    WHERE filename = :filename AND is_preloaded = :is_preloaded
                """),
                {
                    "filename": filename,
                    "is_preloaded": is_preloaded
                }
            )
            
            count = result.fetchone()[0]
        
        exists = count > 0
        logger.debug(f"Document exists check: {filename} (preloaded={is_preloaded}) = {exists}")
        return exists
        
    except Exception as e:
        logger.error(
            f"Database error checking if document exists {filename}: {str(e)}",
            exc_info=True
        )
        raise Exception(f"Failed to check if document exists: {str(e)}") from e
