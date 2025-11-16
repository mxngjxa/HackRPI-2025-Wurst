import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.local_embeddings import get_embedding_model, embed_texts_local
from backend.config import EMBEDDING_DIMENSION, LOCAL_EMBEDDING_MODEL_NAME

# Mock the AutoModel and torch to prevent actual model loading during tests
@patch("backend.local_embeddings.AutoModel")
@patch("backend.local_embeddings.torch")
class TestLocalEmbeddings(unittest.TestCase):

    def setUp(self):
        # Reset the module-level cache before each test
        get_embedding_model.cache_clear()

    def test_model_loading_and_device(self, mock_torch, mock_AutoModel):
        """
        Test that the model is loaded correctly and sent to the correct device.
        """
        # Mock the model instance and its .to() method
        mock_model_instance = MagicMock()
        mock_AutoModel.from_pretrained.return_value = mock_model_instance
        
        # Mock the device detection
        mock_torch.cuda.is_available.return_value = True
        expected_device = "cuda"

        model = get_embedding_model()

        # Assertions
        mock_AutoModel.from_pretrained.assert_called_once_with(
            LOCAL_EMBEDDING_MODEL_NAME,
            trust_remote_code=True,
        )
        mock_model_instance.to.assert_called_once_with(expected_device)
        self.assertEqual(model, mock_model_instance)

    def test_model_caching(self, mock_torch, mock_AutoModel):
        """
        Test that repeated calls to get_embedding_model return the same instance.
        """
        # Mock the model instance
        mock_model_instance = MagicMock()
        mock_AutoModel.from_pretrained.return_value = mock_model_instance
        
        # First call
        model1 = get_embedding_model()
        # Second call
        model2 = get_embedding_model()

        # Assertions
        mock_AutoModel.from_pretrained.assert_called_once()
        self.assertEqual(model1, model2)
        self.assertEqual(model1, mock_model_instance)

    def test_embed_texts_local_shape(self, mock_torch, mock_AutoModel):
        """
        Test that embed_texts_local returns a numpy array with the correct shape.
        """
        texts = ["sentence one", "sentence two", "sentence three"]
        num_texts = len(texts)
        
        # Mock the model instance and its .encode() method
        mock_model_instance = MagicMock()
        mock_AutoModel.from_pretrained.return_value = mock_model_instance
        
        # Create mock embeddings with the expected shape
        expected_shape = (num_texts, EMBEDDING_DIMENSION)
        mock_embeddings = np.random.rand(*expected_shape).astype(np.float32)
        mock_model_instance.encode.return_value = mock_embeddings

        embeddings = embed_texts_local(texts)

        # Assertions
        mock_model_instance.encode.assert_called_once_with(texts)
        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(embeddings.shape, expected_shape)

    def test_embed_texts_local_empty_list(self, mock_torch, mock_AutoModel):
        """
        Test that embed_texts_local handles an empty list correctly.
        """
        embeddings = embed_texts_local([])
        
        # Assertions
        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(embeddings.size, 0)
        
        # Ensure model was not loaded
        mock_AutoModel.from_pretrained.assert_not_called()


if __name__ == "__main__":
    unittest.main()