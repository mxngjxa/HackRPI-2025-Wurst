"""
Local Embeddings module for LLM File-Based Chatbot.

Encapsulates the loading and usage of a local HuggingFace embedding model
(e.g., Jina-Embeddings) for fast, local embedding generation.
"""

import logging
from typing import List, Optional
import numpy as np
import torch
from transformers import AutoModel

from backend.config import LOCAL_EMBEDDING_MODEL_NAME

# Configure logging
logger = logging.getLogger(__name__)

# Determine device for model loading
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Module-level cache for the model instance
_model: Optional[AutoModel] = None


def get_embedding_model() -> AutoModel:
    """
    Lazily loads the local embedding model and sends it to the appropriate device.

    The model is cached in the module-level variable `_model`.

    Returns:
        AutoModel: The loaded HuggingFace model instance.
    """
    global _model
    if _model is None:
        logger.info(
            f"Loading local embedding model: {LOCAL_EMBEDDING_MODEL_NAME} on device: {DEVICE}"
        )
        try:
            _model = AutoModel.from_pretrained(
                LOCAL_EMBEDDING_MODEL_NAME,
                trust_remote_code=True,
            ).to(DEVICE)
            logger.info("Local embedding model loaded successfully.")
        except Exception as e:
            logger.error(
                f"Failed to load local embedding model {LOCAL_EMBEDDING_MODEL_NAME}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to load local embedding model: {LOCAL_EMBEDDING_MODEL_NAME}"
            ) from e
    return _model


def embed_texts_local(texts: List[str]) -> np.ndarray:
    """
    Generates embeddings for a list of texts using the local model.

    Args:
        texts: List of text strings to embed.

    Returns:
        np.ndarray: A numpy array of embeddings with shape (n, EMBEDDING_DIMENSION).
    """
    if not texts:
        logger.warning("embed_texts_local called with empty list")
        return np.array([])

    model = get_embedding_model()
    logger.debug(f"Generating local embeddings for batch size: {len(texts)}")

    # model.encode is provided by trust_remote_code
    with torch.no_grad():
        # The model's encode method handles tokenization and forward pass
        embeddings = model.encode(texts)

    logger.debug(f"Generated embeddings with shape: {embeddings.shape}")
    return embeddings


def test_embedding() -> None:
    """
    Simple test function to verify model loading and embedding generation.
    """
    texts = ["Hello world", "This is a test sentence for the local model."]
    embeddings = embed_texts_local(texts)
    print(f"Test successful. Generated {len(embeddings)} embeddings.")
    print(f"First embedding shape: {embeddings.shape}")


if __name__ == "__main__":
    # Simple setup for local testing
    logging.basicConfig(level=logging.INFO)
    test_embedding()