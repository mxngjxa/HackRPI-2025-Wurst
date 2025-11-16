"""
Retrieval module for LLM File-Based Chatbot.

Handles semantic search and context assembly for question answering.
"""

import logging
from typing import List
import numpy as np
from backend.embeddings import embed_query
from backend.db import search_similar_chunks
from backend.config import TOP_K_RETRIEVAL, USE_LSH_SEARCH
from backend.lsh_indexer import get_lsh_indexer
from backend.db import get_chunk_content_by_ids

# Configure logging
logger = logging.getLogger(__name__)

def lsh_hybrid_search(
    question: str, session_id: str, top_k: int
) -> List[str]:
    """
    Performs a hybrid search using LSH for candidate retrieval and PostgreSQL 
    for cosine similarity reranking.

    Args:
        question: User's question text
        session_id: Current session identifier (not used in LSH search but kept for signature consistency)
        top_k: Number of top results to retrieve

    Returns:
        List[str]: List of relevant chunk content strings, ordered by similarity.
    """
    logger.info(
        f"LSH Hybrid Search for question: {question[:50]}... (top_k: {top_k})"
    )
    
    try:
        # 1. Generate embedding for the question
        # embed_query now returns List[float], convert to np.ndarray for LSHRS
        query_embedding_list = embed_query(question)
        query_embedding = np.array(query_embedding_list)
        
        # 2. Perform hybrid search
        indexer = get_lsh_indexer()
        # The query_similar_chunks method returns a list of chunk IDs (integers)
        chunk_ids = indexer.query_similar_chunks(query_embedding, top_k=top_k)
        
        if not chunk_ids:
            logger.info("LSH hybrid search returned no chunk IDs.")
            return []
            
        # 3. Fetch chunk content from PostgreSQL
        chunks = get_chunk_content_by_ids(chunk_ids)
        
        logger.info(f"LSH hybrid search retrieved {len(chunks)} chunks.")
        return chunks
        
    except Exception as e:
        logger.error(
            f"LSH Hybrid Search failed for session {session_id}: {str(e)}",
            exc_info=True,
        )
        # Fallback to pgvector search is handled in get_context_chunks
        raise


def get_context_chunks(
    question: str, session_id: str, top_k: int = TOP_K_RETRIEVAL
) -> List[str]:
    """
    Retrieves relevant chunks for a question using semantic search.

    Generates an embedding for the question and searches for the most
    similar chunks from both preloaded documents and session-specific
    documents.

    Args:
        question: User's question text
        session_id: Current session identifier
        top_k: Number of top results to retrieve (default from config)

    Returns:
        List[str]: List of relevant chunk content strings, ordered by similarity.
                   Returns empty list if no documents are available.

    Raises:
        ValueError: If question is empty or whitespace-only
        Exception: If embedding generation or database search fails
    """
    if not question or not question.strip():
        logger.warning("get_context_chunks called with empty question")
        raise ValueError("Question cannot be empty")

    logger.info(
        f"Retrieving context chunks for question: {question[:50]}... (session: {session_id})"
    )

    try:
        chunks = []
        if USE_LSH_SEARCH:
            logger.info("Attempting LSH hybrid search.")
            try:
                # The LSH search handles embedding generation internally
                chunks = lsh_hybrid_search(question, session_id, top_k)
            except Exception as e:
                # If LSH fails, log and fall back to pgvector search
                logger.error(
                    f"LSH search failed, falling back to pgvector search: {str(e)}",
                    exc_info=True,
                )
                logger.info("Using pgvector direct search as fallback.")
                # Fallback: Generate embedding for the question
                query_embedding = embed_query(question)
                logger.debug(
                    f"Generated query embedding with dimension: {len(query_embedding)}"
                )

                # Search for similar chunks
                chunks = search_similar_chunks(query_embedding, session_id, top_k)
        else:
            logger.info("Using pgvector direct search.")
            # Generate embedding for the question
            query_embedding = embed_query(question)
            logger.debug(
                f"Generated query embedding with dimension: {len(query_embedding)}"
            )

            # Search for similar chunks
            chunks = search_similar_chunks(query_embedding, session_id, top_k)

        if not chunks:
            logger.info("No relevant chunks found - no documents available")
            return []

        logger.info(f"Retrieved {len(chunks)} relevant chunks")
        return chunks

    except ValueError:
        # Re-raise validation errors
        raise

    except Exception as e:
        logger.error(
            f"Failed to retrieve context chunks for session {session_id}: {str(e)}",
            exc_info=True,
        )
        raise Exception(f"Failed to retrieve relevant context: {str(e)}") from e


def format_context(chunks: List[str]) -> str:
    """
    Formats chunks into a context string for LLM consumption.

    Concatenates chunks with clear delimiters to help the LLM
    distinguish between different pieces of context.

    Args:
        chunks: List of chunk content strings

    Returns:
        str: Formatted context string with delimiters.
             Returns empty string if chunks list is empty.
    """
    if not chunks:
        logger.debug("format_context called with empty chunks list")
        return ""

    logger.debug(f"Formatting {len(chunks)} chunks into context string")

    # Format with numbered delimiters for clarity
    formatted_chunks = []
    for idx, chunk in enumerate(chunks, 1):
        formatted_chunks.append(f"[Context {idx}]\n{chunk}")

    context = "\n\n---\n\n".join(formatted_chunks)

    logger.debug(f"Formatted context length: {len(context)} characters")
    return context
