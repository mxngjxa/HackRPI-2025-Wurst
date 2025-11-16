"""
MCP Query module for LLM File-Based Chatbot.

Provides a dedicated helper for generating query embeddings for the MCP server,
ensuring the correct embedding model (local Jina if enabled) is used.
"""

import logging
from typing import List
import numpy as np

from backend.embeddings import embed_query

# Configure logging
logger = logging.getLogger(__name__)


def embed_mcp_query(text: str) -> np.ndarray:
    """
    Generates an embedding for an MCP query text.

    Wraps the core embed_query function and converts the result to a numpy array.

    Args:
        text: Query text to embed

    Returns:
        np.ndarray: Embedding vector for the query (numpy array).

    Raises:
        Exception: If embedding generation fails.
    """
    logger.info(f"Generating MCP query embedding for: {text[:50]}...")
    
    # embed_query returns List[float]
    embedding_list = embed_query(text)
    
    # Convert to numpy array as required by LSHRS/retrieval pipeline
    embedding_np = np.array(embedding_list)
    
    logger.debug(f"MCP query embedding generated with shape: {embedding_np.shape}")
    return embedding_np