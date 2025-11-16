"""
Embeddings module for LLM File-Based Chatbot.

Generates embeddings using Google Gemini API with batch processing
and error handling, or a local HuggingFace model.
"""

import logging
import time
from typing import List, Union
import numpy as np
import google.generativeai as genai
from backend.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    USE_LOCAL_EMBEDDINGS,
    ALLOW_EMBEDDING_FALLBACK,
)

# Configure logging
logger = logging.getLogger(__name__)

# Import local embeddings only if needed to avoid unnecessary dependency load
if USE_LOCAL_EMBEDDINGS:
    try:
        from backend.local_embeddings import embed_texts_local
    except ImportError as e:
        logger.error(f"Failed to import local_embeddings: {e}")
        # If import fails, we must fall back or fail fast
        if not ALLOW_EMBEDDING_FALLBACK:
            raise RuntimeError("Local embeddings enabled but failed to import.") from e
        # If fallback is allowed, we proceed with remote only
        USE_LOCAL_EMBEDDINGS = False
        logger.warning("Falling back to remote Gemini embeddings.")

# Configure Gemini API
if not USE_LOCAL_EMBEDDINGS or ALLOW_EMBEDDING_FALLBACK:
    genai.configure(api_key=GEMINI_API_KEY)

# Batch size for embedding generation
BATCH_SIZE = 100

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for multiple texts using batch processing.

    Uses local model if USE_LOCAL_EMBEDDINGS is true, otherwise falls back to Gemini.

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

    if USE_LOCAL_EMBEDDINGS:
        try:
            logger.info(f"Generating local embeddings for {len(texts)} texts")
            # Local model returns np.ndarray
            embeddings_np = embed_texts_local(texts)
            # Convert numpy array to list of lists for compatibility
            return embeddings_np.tolist()
        except Exception as e:
            if ALLOW_EMBEDDING_FALLBACK:
                logger.warning(
                    f"Local embedding failed: {str(e)}. Falling back to Gemini."
                )
            else:
                logger.error(
                    f"Local embedding failed and fallback is disabled: {str(e)}",
                    exc_info=True,
                )
                raise RuntimeError("Local embedding failed and fallback is disabled.") from e

    # Fallback / Default: Gemini API
    logger.info(f"Generating Gemini embeddings for {len(texts)} texts")

    all_embeddings = []

    # Process texts in batches
    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(texts))
        batch = texts[batch_start:batch_end]

        logger.debug(
            f"Processing batch {batch_start // BATCH_SIZE + 1}: "
            f"texts {batch_start} to {batch_end - 1}"
        )

        # Retry logic with exponential backoff
        for attempt in range(MAX_RETRIES):
            try:
                # Generate embeddings for the batch
                result = genai.embed_content(
                    model=f"models/{GEMINI_EMBEDDING_MODEL}",
                    content=batch,
                    task_type="retrieval_document",
                )

                # Extract embeddings from result
                if isinstance(result, dict) and "embedding" in result:
                    # Single text response
                    batch_embeddings = [result["embedding"]]
                else:
                    # Multiple texts response
                    batch_embeddings = result["embedding"]

                # Flatten if embeddings are nested (e.g., from Mock)
                flattened_embeddings = []
                for emb in batch_embeddings:
                    if (
                        isinstance(emb, list)
                        and len(emb) > 0
                        and isinstance(emb[0], list)
                    ):
                        # Nested list - take the first element
                        flattened_embeddings.append(emb[0])
                    else:
                        flattened_embeddings.append(emb)

                all_embeddings.extend(flattened_embeddings)
                logger.debug(
                    f"Successfully generated {len(batch_embeddings)} embeddings"
                )
                break  # Success, exit retry loop

            except Exception as e:
                error_type = type(e).__name__
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"{error_type}: {str(e)}"
                )

                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = RETRY_DELAY * (2**attempt)
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

    Uses local model if USE_LOCAL_EMBEDDINGS is true, otherwise falls back to Gemini.

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

    if USE_LOCAL_EMBEDDINGS:
        try:
            logger.info(f"Generating local embedding for query: {text[:50]}...")
            # Local model returns np.ndarray of shape (1, dim)
            embedding_np = embed_texts_local([text])
            # Convert numpy array to list of floats for compatibility
            return embedding_np[0].tolist()
        except Exception as e:
            if ALLOW_EMBEDDING_FALLBACK:
                logger.warning(
                    f"Local query embedding failed: {str(e)}. Falling back to Gemini."
                )
            else:
                logger.error(
                    f"Local query embedding failed and fallback is disabled: {str(e)}",
                    exc_info=True,
                )
                raise RuntimeError("Local query embedding failed and fallback is disabled.") from e

    # Fallback / Default: Gemini API
    logger.info(f"Generating Gemini embedding for query: {text[:50]}...")

    # Retry logic with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{GEMINI_EMBEDDING_MODEL}",
                content=text,
                task_type="retrieval_query",
            )

            # Extract embedding from result
            embedding = result["embedding"]

            logger.info(
                f"Successfully generated query embedding (dimension: {len(embedding)})"
            )
            return embedding

        except Exception as e:
            error_type = type(e).__name__
            logger.warning(
                f"Query embedding generation failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"{error_type}: {str(e)}"
            )

            if attempt < MAX_RETRIES - 1:
                # Exponential backoff
                delay = RETRY_DELAY * (2**attempt)
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
