import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import redis

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.lsh_indexer import LSHIndexer, EMBEDDING_DIMENSION
from backend.config import REDIS_HOST, REDIS_PORT, LSH_REDIS_PREFIX

# Mock the database engine and connection for isolation
@patch("backend.lsh_indexer.get_engine")
# Mock the LSHRS library to prevent actual Redis connection during init
@patch("backend.lsh_indexer.LSHRS")
class TestLSHDBIntegration(unittest.TestCase):

    def setUp(self):
        # Mock Redis connection for cleanup (if LSHRS is not fully mocked)
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        # Clear the test prefix before each test
        for key in self.redis_client.keys(f"{LSH_REDIS_PREFIX}:*"):
            self.redis_client.delete(key)

    def tearDown(self):
        # Clean up after each test
        for key in self.redis_client.keys(f"{LSH_REDIS_PREFIX}:*"):
            self.redis_client.delete(key)

    def mock_db_fetch(self, mock_get_engine, mock_LSHRS, mock_data):
        """Helper to mock the DB connection and fetch results."""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        # Mock the fetchall result for the internal _fetch_vectors_for_lshrs
        mock_conn.execute.return_value.fetchall.return_value = mock_data

        # Mock the LSHRS instance
        mock_lshrs_instance = MagicMock()
        mock_LSHRS.return_value = mock_lshrs_instance
        
        return LSHIndexer(), mock_lshrs_instance, mock_conn

    def test_fetch_vectors_from_postgres(self, mock_LSHRS, mock_get_engine):
        """
        Test the internal DB fetch function used by LSHRS.
        """
        # Arrange: Mock DB data (id, embedding_str)
        # Create a full-dimension mock embedding string
        mock_embedding_str = "[" + ", ".join([str(i / EMBEDDING_DIMENSION) for i in range(EMBEDDING_DIMENSION)]) + "]"
        mock_db_data = [
            (101, mock_embedding_str),
            (102, mock_embedding_str),
        ]

        indexer, _, mock_conn = self.mock_db_fetch(mock_get_engine, mock_LSHRS, mock_db_data)
        
        # Act
        chunk_ids = ["101", "102"]
        results = indexer._fetch_vectors_for_lshrs(chunk_ids)

        # Assert
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "101")
        self.assertIsInstance(results[0][1], np.ndarray)
        self.assertEqual(results[0][1].shape, (EMBEDDING_DIMENSION,))
        
        # Verify SQL execution
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        self.assertIn("SELECT id, embedding FROM document_chunks WHERE id = ANY(:chunk_ids)", str(mock_conn.execute.call_args))
        self.assertEqual(call_args[1]["chunk_ids"], [101, 102])

    @patch("backend.lsh_indexer.mark_document_as_indexed")
    @patch("backend.lsh_indexer.get_unindexed_chunks")
    def test_index_documents_calls_lshrs(self, mock_get_unindexed_chunks, mock_mark_document_as_indexed, mock_LSHRS, mock_get_engine):
        """
        Test that index_documents correctly fetches chunks and calls lsh.add_vectors.
        """
        # Arrange
        indexer, mock_lshrs_instance, _ = self.mock_db_fetch(mock_get_engine, mock_LSHRS, [])
        
        # Mock unindexed chunks: (chunk_id, document_id, embedding_list)
        mock_embedding = [0.1] * EMBEDDING_DIMENSION
        mock_get_unindexed_chunks.return_value = [
            (1, 10, mock_embedding),
            (2, 10, mock_embedding),
            (3, 20, mock_embedding),
        ]
        
        # Act
        indexed_count = indexer.index_documents()
        
        # Assert
        self.assertEqual(indexed_count, 3)
        self.assertEqual(mock_lshrs_instance.add_vectors.call_count, 2) # One call per document
        mock_mark_document_as_indexed.assert_any_call(10)
        mock_mark_document_as_indexed.assert_any_call(20)

    def test_index_new_chunks_calls_lshrs(self, mock_LSHRS, mock_get_engine):
        """
        Test that index_new_chunks correctly formats data and calls lsh.add_vectors.
        """
        # Arrange
        indexer, mock_lshrs_instance, _ = self.mock_db_fetch(mock_get_engine, mock_LSHRS, [])
        
        chunk_ids = [1, 2, 3]
        embeddings = np.random.rand(3, EMBEDDING_DIMENSION).astype(np.float32)
        
        # Act
        indexer.index_new_chunks(chunk_ids, embeddings)
        
        # Assert
        mock_lshrs_instance.add_vectors.assert_called_once()
        call_args = mock_lshrs_instance.add_vectors.call_args[0]
        
        # Check IDs are converted to strings
        self.assertEqual(list(call_args[0]), ["1", "2", "3"])
        # Check embeddings are passed as numpy array
        self.assertTrue(np.array_equal(call_args[1], embeddings))

    def test_query_similar_chunks_calls_lshrs(self, mock_LSHRS, mock_get_engine):
        """
        Test that query_similar_chunks calls the correct LSHRS methods.
        """
        # Arrange
        indexer, mock_lshrs_instance, _ = self.mock_db_fetch(mock_get_engine, mock_LSHRS, [])
        
        query_embedding = np.random.rand(EMBEDDING_DIMENSION).astype(np.float32)
        top_k = 5
        
        # Mock LSHRS results: (chunk_id_str, similarity_score)
        mock_lshrs_results = [("103", 0.95), ("101", 0.85), ("102", 0.90)]
        mock_lshrs_instance.get_top_k.return_value = mock_lshrs_results
        mock_lshrs_instance.get_above_p.return_value = mock_lshrs_results # Mock reranking result

        # Act
        results = indexer.query_similar_chunks(query_embedding, top_k)

        # Assert
        mock_lshrs_instance.get_top_k.assert_called_once_with(query_embedding, topk=50)
        mock_lshrs_instance.get_above_p.assert_called_once()
        
        # Check final result is sorted and converted to int IDs
        # The expected order is 103 (0.95), 102 (0.90), 101 (0.85)
        self.assertEqual(results, [103, 102, 101])

    def test_fetch_vectors_returns_numpy_array(self, mock_LSHRS, mock_get_engine):
        """
        Test the public fetch_vectors function returns a single numpy array.
        """
        # Arrange
        indexer, _, _ = self.mock_db_fetch(mock_get_engine, mock_LSHRS, [])
        
        # Mock the internal fetcher to return the expected LSHRS format
        mock_vector1 = np.random.rand(EMBEDDING_DIMENSION).astype(np.float32)
        mock_vector2 = np.random.rand(EMBEDDING_DIMENSION).astype(np.float32)
        indexer._fetch_vectors_for_lshrs = MagicMock(return_value=[
            ("1", mock_vector1),
            ("2", mock_vector2),
        ])
        
        # Act
        indices = [1, 2]
        vectors = indexer.fetch_vectors(indices)
        
        # Assert
        self.assertIsInstance(vectors, np.ndarray)
        self.assertEqual(vectors.shape, (2, EMBEDDING_DIMENSION))
        self.assertTrue(np.array_equal(vectors[0], mock_vector1))
        self.assertTrue(np.array_equal(vectors[1], mock_vector2))
        indexer._fetch_vectors_for_lshrs.assert_called_once_with(["1", "2"])


if __name__ == "__main__":
    unittest.main()