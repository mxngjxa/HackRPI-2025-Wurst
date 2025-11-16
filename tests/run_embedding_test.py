import torch
from transformers import AutoModel

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")


def test_embedding():
    try:
        # trust_remote_code is needed to use the encode method
        model = AutoModel.from_pretrained('jinaai/jina-embeddings-v2-base-en', trust_remote_code=True).to(DEVICE)
        
        sentences = ['How is the weather today?', 'What is the current weather like today?']
        print(f"Encoding sentences: {sentences}")
        
        embeddings = model.encode(sentences)
        
        print(f"Successfully generated embeddings.")
        print(f"Number of embeddings: {len(embeddings)}")
        print(f"Embedding dimension: {embeddings.shape[1]}")
        
        # Print a small part of the embeddings for verification
        print(f"First embedding (first 5 elements): {embeddings[0][:5].tolist()}")
        
    except Exception as e:
        print(f"An error occurred during embedding generation: {e}")