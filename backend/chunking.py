"""
Chunking module for LLM File-Based Chatbot.

Handles text segmentation with configurable size and overlap.
"""

from typing import List


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Splits text into overlapping chunks.
    
    Args:
        text: The text to split into chunks
        chunk_size: Maximum number of characters per chunk
        overlap: Number of characters to overlap between consecutive chunks
        
    Returns:
        List[str]: List of text chunks
        
    Examples:
        >>> chunk_text("Hello World", 5, 2)
        ['Hello', 'lo Wo', 'World']
        
        >>> chunk_text("", 100, 20)
        []
        
        >>> chunk_text("Short", 100, 20)
        ['Short']
    """
    # Handle empty text
    if not text or not text.strip():
        return []
    
    # Handle text smaller than chunk size
    if len(text) <= chunk_size:
        return [text]
    
    # Validate parameters
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got: {chunk_size}")
    
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got: {overlap}")
    
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # Calculate end position for this chunk
        end = start + chunk_size
        
        # Extract chunk
        chunk = text[start:end]
        chunks.append(chunk)
        
        # Move start position forward by (chunk_size - overlap)
        # This creates the overlap between consecutive chunks
        start += chunk_size - overlap
        
        # If we've reached the end, break
        if end >= text_length:
            break
    
    return chunks
