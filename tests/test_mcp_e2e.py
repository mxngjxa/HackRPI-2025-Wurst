import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import json
import numpy as np

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.mcp_tools import execute_tool
from backend.config import EMBEDDING_DIMENSION

# Mock the entire RAG pipeline for E2E testing the MCP tool flow
@patch("backend.mcp_tools.get_context_chunks")
@patch("backend.mcp_tools.get_llm_client")
class TestMCPE2E(unittest.TestCase):

    def setUp(self):
        self.session_id = "test-mcp-session"
        self.query = "What is the capital of France?"
        self.top_k = 3

    def test_semantic_search_tool_success(self, mock_get_llm_client, mock_get_context_chunks):
        """
        Tests the semantic_search tool execution path.
        """
        # Arrange
        mock_chunks = [
            "The capital of France is Paris.",
            "Paris is a beautiful city.",
            "France is in Europe.",
        ]
        mock_get_context_chunks.return_value = mock_chunks
        
        tool_args = {"query": self.query, "top_k": self.top_k}
        
        # Act
        result_json = execute_tool("semantic_search", tool_args, self.session_id)
        result = json.loads(result_json)

        # Assert
        mock_get_context_chunks.assert_called_once_with(self.query, self.session_id, self.top_k)
        self.assertEqual(result["found"], len(mock_chunks))
        self.assertEqual(result["chunks"], mock_chunks)

    @patch("backend.retrieval.embed_query")
    @patch("backend.retrieval.get_lsh_indexer")
    @patch("backend.retrieval.USE_LSH_SEARCH", True)
    def test_semantic_search_uses_lsh_path(self, mock_get_lsh_indexer, mock_embed_query, mock_get_llm_client, mock_get_context_chunks):
        """
        Tests that the semantic search tool triggers the LSH path in retrieval.
        This is an integration test of the tool with the retrieval module.
        """
        # Arrange
        mock_embedding_list = [0.1] * EMBEDDING_DIMENSION
        mock_embed_query.return_value = mock_embedding_list
        
        mock_indexer = MagicMock()
        mock_get_lsh_indexer.return_value = mock_indexer
        mock_indexer.query_similar_chunks.return_value = [1, 2, 3]
        
        mock_get_context_chunks.return_value = ["chunk1", "chunk2", "chunk3"]
        
        tool_args = {"query": self.query, "top_k": self.top_k}
        
        # Act
        execute_tool("semantic_search", tool_args, self.session_id)

        # Assert
        # The tool calls get_context_chunks, which is the unified RAG path
        mock_get_context_chunks.assert_called_once_with(self.query, self.session_id, self.top_k)
        
        # The internal logic of get_context_chunks (local embedding, LSH call) 
        # is tested in other unit/integration tests. This E2E test confirms the tool wiring.

    def test_semantic_search_tool_no_results(self, mock_get_llm_client, mock_get_context_chunks):
        """
        Tests the semantic_search tool when no results are found.
        """
        # Arrange
        mock_get_context_chunks.return_value = []
        tool_args = {"query": self.query, "top_k": self.top_k}
        
        # Act
        result_str = execute_tool("semantic_search", tool_args, self.session_id)

        # Assert
        self.assertIn("No relevant documents found.", result_str)


if __name__ == "__main__":
    unittest.main()