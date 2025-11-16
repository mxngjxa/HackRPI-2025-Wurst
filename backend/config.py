"""
Configuration module for LLM File-Based Chatbot.

Loads and validates environment variables for database connection,
API credentials, and application parameters.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


# Required Environment Variables
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Optional Environment Variables with Defaults
GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "embedding-001")

# Local Embedding Configuration
LOCAL_EMBEDDING_MODEL_NAME: str = os.getenv("LOCAL_EMBEDDING_MODEL_NAME", "jinaai/jina-embeddings-v2-base-en")
USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() in ("true", "yes", "1")
ALLOW_EMBEDDING_FALLBACK: bool = os.getenv("ALLOW_EMBEDDING_FALLBACK", "false").lower() in ("true", "yes", "1")

EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))

# Parse USE_MOCK_LLM flag (accepts: true/false, yes/no, 1/0)
_mock_llm_value = os.getenv("USE_MOCK_LLM", "true").lower()
USE_MOCK_LLM: bool = _mock_llm_value in ("true", "yes", "1")

# Chunking parameters
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval parameters
TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))

# LSH Configuration
USE_LSH_SEARCH: bool = os.getenv("USE_LSH_SEARCH", "false").lower() in (
    "true",
    "yes",
    "1",
)
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
LSH_NUM_PERM: int = int(os.getenv("LSH_NUM_PERM", "256"))
LSH_SIMILARITY_THRESHOLD: float = float(os.getenv("LSH_SIMILARITY_THRESHOLD", "0.7"))
LSH_REDIS_PREFIX: str = os.getenv("LSH_REDIS_PREFIX", "lsh:demo")

# File upload limits
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILES_PER_SESSION: int = int(os.getenv("MAX_FILES_PER_SESSION", "5"))

# Function Calling Configuration
USE_FUNCTION_CALLING: bool = os.getenv("USE_FUNCTION_CALLING", "false").lower() in (
    "true",
    "yes",
    "1",
)

# Tool toggles
ENABLE_SEMANTIC_SEARCH_TOOL: bool = os.getenv(
    "ENABLE_SEMANTIC_SEARCH_TOOL", "true"
).lower() in ("true", "yes", "1")
ENABLE_KEYWORD_SEARCH_TOOL: bool = os.getenv(
    "ENABLE_KEYWORD_SEARCH_TOOL", "true"
).lower() in ("true", "yes", "1")
ENABLE_DOCUMENT_QUERY_TOOL: bool = os.getenv(
    "ENABLE_DOCUMENT_QUERY_TOOL", "true"
).lower() in ("true", "yes", "1")

# Function Calling parameters
MAX_FUNCTION_CALLS: int = int(os.getenv("MAX_FUNCTION_CALLS", "5"))


def validate_config() -> None:
    """
    Validates that all required environment variables are present.

    Raises:
        ConfigurationError: If required configuration is missing or invalid.
    """
    errors = []

    # Check required variables
    if not DATABASE_URL:
        errors.append(
            "DATABASE_URL is required. Please set it in your .env file or environment.\n"
            "Example: DATABASE_URL=postgresql://user:password@localhost:5432/llm_chatbot"
        )

    if not GEMINI_API_KEY:
        errors.append(
            "GEMINI_API_KEY is required. Please set it in your .env file or environment.\n"
            "Get your API key from: https://makersuite.google.com/app/apikey"
        )

    # Validate numeric parameters
    if CHUNK_SIZE <= 0:
        errors.append(f"CHUNK_SIZE must be positive, got: {CHUNK_SIZE}")

    if CHUNK_OVERLAP < 0:
        errors.append(f"CHUNK_OVERLAP must be non-negative, got: {CHUNK_OVERLAP}")

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(
            f"CHUNK_OVERLAP ({CHUNK_OVERLAP}) must be less than CHUNK_SIZE ({CHUNK_SIZE})"
        )

    if TOP_K_RETRIEVAL <= 0:
        errors.append(f"TOP_K_RETRIEVAL must be positive, got: {TOP_K_RETRIEVAL}")

    if MAX_FILE_SIZE_MB <= 0:
        errors.append(f"MAX_FILE_SIZE_MB must be positive, got: {MAX_FILE_SIZE_MB}")

    if MAX_FILES_PER_SESSION <= 0:
        errors.append(
            f"MAX_FILES_PER_SESSION must be positive, got: {MAX_FILES_PER_SESSION}"
        )

    if EMBEDDING_DIMENSION <= 0:
        errors.append(
            f"EMBEDDING_DIMENSION must be positive, got: {EMBEDDING_DIMENSION}"
        )

    # Validate LSH parameters
    if LSH_NUM_PERM <= 0:
        errors.append(f"LSH_NUM_PERM must be positive, got: {LSH_NUM_PERM}")
    
    if not 0.0 <= LSH_SIMILARITY_THRESHOLD <= 1.0:
        errors.append(
            f"LSH_SIMILARITY_THRESHOLD must be between 0.0 and 1.0, got: {LSH_SIMILARITY_THRESHOLD}"
        )

    # Validate Function Calling parameters
    if MAX_FUNCTION_CALLS <= 0:
        errors.append(f"MAX_FUNCTION_CALLS must be positive, got: {MAX_FUNCTION_CALLS}")

    # If there are any errors, raise exception with all messages
    if errors:
        error_message = "Configuration validation failed:\n\n" + "\n\n".join(errors)
        raise ConfigurationError(error_message)


# Validate configuration on module import
validate_config()
