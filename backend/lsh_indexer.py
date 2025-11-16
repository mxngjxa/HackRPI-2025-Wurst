import logging
import numpy as np
from typing import List, Tuple, Optional

from lshrs import LSHRS
from sqlalchemy import text
from backend.config import (
    DATABASE_URL,
    REDIS_HOST,
    REDIS_PORT,
    LSH_NUM_PERM,
    LSH_SIMILARITY_THRESHOLD,
    LSH_REDIS_PREFIX,
    EMBEDDING_DIMENSION,
)
from backend.db import get_engine, get_unindexed_chunks, mark_document_as_indexed

logger = logging.getLogger(__name__)

class LSHIndexer:
    """
    Handles the creation, maintenance, and querying of the LSH index 
    backed by Redis, with full vectors stored in PostgreSQL.
    """
    def __init__(self, redis_host: str = REDIS_HOST, redis_port: int = REDIS_PORT):
        """
        Initializes the LSHRS instance.
        """
        # LSHRS requires a function to fetch the full vectors for reranking
        self.lsh = LSHRS(
            dim=EMBEDDING_DIMENSION,
            num_perm=LSH_NUM_PERM,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_prefix=LSH_REDIS_PREFIX,
            vector_fetch_fn=self.fetch_vectors_from_postgres
        )
        self.engine = get_engine()
        self.similarity_threshold = LSH_SIMILARITY_THRESHOLD

    def fetch_vectors_from_postgres(self, chunk_ids: List[str]) -> List[Tuple[str, np.ndarray]]:
        """
        Bridge function for LSHRS vector_fetch_fn.
        Fetches full embedding vectors from PostgreSQL for a list of chunk IDs.
        
        Args:
            chunk_ids: List of chunk IDs (as strings) to fetch.
            
        Returns:
            List[Tuple[str, np.ndarray]]: List of (chunk_id, vector) tuples.
        """
        if not chunk_ids:
            return []
            
        # Convert chunk_ids to integers for the SQL query
        chunk_id_ints = [int(cid) for cid in chunk_ids]
        
        logger.debug(f"Fetching vectors for {len(chunk_id_ints)} chunks from PostgreSQL.")

        try:
            with self.engine.connect() as conn:
                # Use ANY to query for multiple IDs
                query = """
                    SELECT id, embedding
                    FROM document_chunks
                    WHERE id = ANY(:chunk_ids)
                """
                
                result = conn.execute(
                    text(query),
                    {"chunk_ids": chunk_id_ints}
                )
                
                vectors = []
                for chunk_id, embedding_str in result.fetchall():
                    # Convert the PostgreSQL vector string representation to a numpy array
                    # e.g., "[1.23, 4.56, ...]" -> np.array([1.23, 4.56, ...])
                    embedding = np.array([float(x) for x in embedding_str.strip("[]").split(",")])
                    vectors.append((str(chunk_id), embedding))

            logger.debug(f"Successfully fetched {len(vectors)} vectors.")
            return vectors

        except Exception as e:
            logger.error(
                f"Database error fetching vectors for LSH reranking: {str(e)}", exc_info=True
            )
            # Return empty list to allow LSHRS to continue without these vectors
            return []

    def index_documents(self, session_id: Optional[str] = None) -> int:
        """
        Indexes all unindexed document chunks into the LSH index.
        
        Args:
            session_id: If provided, only indexes documents for that session.
            
        Returns:
            int: The total number of chunks indexed.
        """
        logger.info(f"Starting LSH indexing for session_id: {session_id}")
        
        # 1. Fetch unindexed chunks from DB (chunk_id, document_id, embedding)
        unindexed_chunks = get_unindexed_chunks(session_id=session_id)
        total_chunks = len(unindexed_chunks)
        logger.info(f"Found {total_chunks} unindexed chunks to process.")
        
        if total_chunks == 0:
            return 0

        # Group chunks by document_id to mark them as indexed later
        chunks_by_document = {}
        for chunk_id, document_id, embedding in unindexed_chunks:
            if document_id not in chunks_by_document:
                chunks_by_document[document_id] = []
            chunks_by_document[document_id].append((chunk_id, embedding))

        # 2. Batch process: generate signature, add to LSH index
        indexed_count = 0
        BATCH_SIZE = 1000 # As per requirements.md
        
        for document_id, chunks in chunks_by_document.items():
            chunk_ids = [str(c[0]) for c in chunks]
            embeddings = [np.array(c[1]) for c in chunks]
            
            # Process in batches
            for i in range(0, len(chunk_ids), BATCH_SIZE):
                batch_ids = chunk_ids[i:i + BATCH_SIZE]
                batch_embeddings = embeddings[i:i + BATCH_SIZE]
                
                # Add to LSH index (this handles signature generation and Redis storage)
                self.lsh.add_vectors(batch_ids, batch_embeddings)
                indexed_count += len(batch_ids)
                
                logger.debug(f"Indexed batch of {len(batch_ids)} chunks for document {document_id}. Total indexed: {indexed_count}")

            # 3. Mark document as lsh_indexed=TRUE
            mark_document_as_indexed(document_id)
            logger.info(f"Document {document_id} marked as LSH indexed.")

        logger.info(f"LSH indexing complete. Total chunks indexed: {indexed_count}")
        return indexed_count

    def hybrid_search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[int]:
        """
        Performs a hybrid search: LSH candidate retrieval followed by cosine reranking.
        
        Args:
            query_embedding: The embedding vector of the query.
            top_k: The number of final results to return.
            
        Returns:
            List[int]: List of top_k chunk IDs (integers) ordered by similarity.
        """
        # Phase 1: LSH candidate retrieval (top 50)
        # The LSHRS get_top_k returns a list of (chunk_id, similarity) tuples
        # where chunk_id is a string.
        candidates_with_sim = self.lsh.get_top_k(query_embedding, topk=50)
        
        if not candidates_with_sim:
            logger.info("LSH candidate retrieval returned no results.")
            return []
            
        # Phase 2 & 3: Fetch full vectors from PostgreSQL and Rerank with cosine similarity
        # LSHRS handles this internally via vector_fetch_fn and reranking logic.
        # We use get_above_p to get all candidates above the similarity threshold,
        # which is a more robust approach than a fixed top-k for reranking.
        
        # get_above_p returns a list of (chunk_id, similarity) tuples
        reranked_results = self.lsh.get_above_p(
            query_embedding, 
            p=self.similarity_threshold, 
            candidates=candidates_with_sim
        )
        
        # Sort by similarity (descending) and take top_k
        reranked_results.sort(key=lambda x: x[1], reverse=True)
        
        # Phase 4: Return top_k results
        top_k_chunk_ids = [int(chunk_id) for chunk_id, _ in reranked_results[:top_k]]
        
        logger.info(f"Hybrid search returned {len(top_k_chunk_ids)} chunks.")
        return top_k_chunk_ids

# Global instance for easy access
lsh_indexer: Optional[LSHIndexer] = None

def get_lsh_indexer() -> LSHIndexer:
    """
    Returns the global LSHIndexer instance, creating it if it doesn't exist.
    """
    global lsh_indexer
    if lsh_indexer is None:
        lsh_indexer = LSHIndexer()
    return lsh_indexer