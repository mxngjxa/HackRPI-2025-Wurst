import logging
import time
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.lsh_indexer import get_lsh_indexer
from backend.db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_lsh_index():
    """
    Initializes the database and runs the LSH indexing process for all unindexed documents.
    """
    logger.info("--- Starting LSH Index Build Script ---")
    
    # 1. Initialize DB (ensures schema is up-to-date with LSH columns)
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # 2. Get LSH Indexer instance
    try:
        indexer = get_lsh_indexer()
    except Exception as e:
        logger.error(f"Failed to initialize LSHIndexer: {e}")
        return

    # 3. Run indexing
    start_time = time.time()
    try:
        indexed_count = indexer.index_documents(session_id=None)
        end_time = time.time()
        
        logger.info("--- LSH Index Build Complete ---")
        logger.info(f"Total chunks indexed: {indexed_count}")
        logger.info(f"Time taken: {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"An error occurred during indexing: {e}", exc_info=True)


if __name__ == "__main__":
    build_lsh_index()