"""
Embeddings module for LLM File-Based Chatbot.

Generates embeddings using Google Gemini API with batch processing
and error handling.
"""

import logging
import time
from typing import List
import google.generativeai as genai
from backend.config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Batch size for embedding generation
BATCH_SIZE = 100

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for multiple texts using batch processing.
    
    Processes texts in batches to optimize API usage and handles
    API failures with retry logic and exponential backoff.
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        List[List[float]]: List of embedding vectors, one per input text
    
    Raises:
        Exception: If embedding generation fails after all retries
    """
    if not texts:
        logger.warning("embed_texts called with empty list")
        return []
    
    logger.info(f"Generating embeddings for {len(texts)} texts")
    
    all_embeddings = []
    
    # Process texts in batches
    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(texts))
        batch = texts[batch_start:batch_end]
        
        logger.debug(f"Processing batch {batch_start//BATCH_SIZE + 1}: "
                    f"texts {batch_start} to {batch_end-1}")
        
        # Retry logic with exponential backoff
        for attempt in range(MAX_RETRIES):
            try:
                # Generate embeddings for the batch
                result = genai.embed_content(
                    model=f"models/{GEMINI_EMBEDDING_MODEL}",
                    content=batch,
                    task_type="retrieval_document"
                )
                
                # Extract embeddings from result
                if isinstance(result, dict) and 'embedding' in result:
                    # Single text response
                    batch_embeddings = [result['embedding']]
                else:
                    # Multiple texts response
                    batch_embeddings = result['embedding']
                
                # Flatten if embeddings are nested (e.g., from Mock)
                flattened_embeddings = []
                for emb in batch_embeddings:
                    if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
                        # Nested list - take the first element
                        flattened_embeddings.append(emb[0])
                    else:
                        flattened_embeddings.append(emb)
                
                all_embeddings.extend(flattened_embeddings)
                logger.debug(f"Successfully generated {len(batch_embeddings)} embeddings")
                break  # Success, exit retry loop
                
            except Exception as e:
                error_type = type(e).__name__
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"{error_type}: {str(e)}"
                )
                
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(
                        f"Failed to generate embeddings after {MAX_RETRIES} attempts. "
                        f"Last error: {error_type}: {str(e)}"
                    )
                    # Provide user-friendly error message
                    user_msg = (
                        "Failed to generate embeddings. This may be due to API issues. "
                        "Please check your API key and try again."
                    )
                    raise Exception(user_msg) from e
    
    logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
    return all_embeddings


def embed_query(text: str) -> List[float]:
    """
    Generates embedding for a single query text.
    
    Uses retrieval_query task type for optimal query embedding.
    
    Args:
        text: Query text to embed
    
    Returns:
        List[float]: Embedding vector for the query
    
    Raises:
        Exception: If embedding generation fails after all retries
    """
    if not text or not text.strip():
        logger.warning("embed_query called with empty text")
        raise ValueError("Query text cannot be empty")
    
    logger.info(f"Generating embedding for query: {text[:50]}...")
    
    # Retry logic with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{GEMINI_EMBEDDING_MODEL}",
                content=text,
                task_type="retrieval_query"
            )
            
            # Extract embedding from result
            embedding = result['embedding']
            
            logger.info(f"Successfully generated query embedding (dimension: {len(embedding)})")
            return embedding
            
        except Exception as e:
            error_type = type(e).__name__
            logger.warning(
                f"Query embedding generation failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"{error_type}: {str(e)}"
            )
            
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff
                delay = RETRY_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                # Final attempt failed
                logger.error(
                    f"Failed to generate query embedding after {MAX_RETRIES} attempts. "
                    f"Last error: {error_type}: {str(e)}"
                )
                # Provide user-friendly error message
                user_msg = (
                    "Failed to process your question. This may be due to API issues. "
                    "Please check your connection and try again."
                )
                raise Exception(user_msg) from e
