#!/usr/bin/env python3
"""
Preload script for LLM File-Based Chatbot.

Loads .txt files from the preload_docs/ directory into the database
as system-wide reference documents. These documents are available to
all sessions and persist after session clears.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.logging_config import setup_logging
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP
from backend.file_parser import FileValidationError
from backend.chunking import chunk_text
from backend.embeddings import embed_texts
from backend.db import init_db, insert_document, insert_chunks, document_exists

# Configure logging with centralized setup
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(
    log_level=log_level,
    log_file="preload.log",
    log_dir="logs"
)

logger = logging.getLogger(__name__)


class PreloadFileObject:
    """
    Simple file object wrapper to make local files compatible
    with the file_parser module's interface.
    """
    def __init__(self, file_path: str):
        self.name = file_path
        self.size = os.path.getsize(file_path)


def preload_documents(directory: str = "preload_docs") -> Tuple[int, int, List[str]]:
    """
    Loads all .txt files from the specified directory into the database.
    
    Processes files using the same pipeline as user uploads:
    1. Read and validate file
    2. Chunk the text
    3. Generate embeddings
    4. Store in database with is_preloaded=True and session_id=NULL
    
    Checks for existing documents to avoid duplicates. If a document
    with the same filename already exists as preloaded, it is skipped.
    
    Args:
        directory: Path to directory containing .txt files to preload
    
    Returns:
        Tuple[int, int, List[str]]: (success_count, skipped_count, errors)
            - success_count: Number of files successfully processed
            - skipped_count: Number of files skipped (already exist)
            - errors: List of error messages for failed files
    """
    logger.info(f"Starting preload from directory: {directory}")
    
    # Check if directory exists
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return (0, 0, [f"Directory not found: {directory}"])
    
    if not os.path.isdir(directory):
        logger.error(f"Path is not a directory: {directory}")
        return (0, 0, [f"Path is not a directory: {directory}"])
    
    # Find all .txt files in directory
    txt_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith('.txt') and os.path.isfile(os.path.join(directory, f))
    ]
    
    if not txt_files:
        logger.warning(f"No .txt files found in directory: {directory}")
        return (0, 0, [f"No .txt files found in {directory}"])
    
    logger.info(f"Found {len(txt_files)} .txt file(s) to process")
    
    success_count = 0
    skipped_count = 0
    errors = []
    
    # Process each file
    for file_path in txt_files:
        filename = os.path.basename(file_path)
        
        try:
            # Check if document already exists
            if document_exists(filename, is_preloaded=True):
                logger.info(f"Skipping {filename} (already exists as preloaded document)")
                skipped_count += 1
                continue
            
            logger.info(f"Processing file: {filename}")
            
            # Step 1: Read file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Validate content is not empty
            if not content or not content.strip():
                raise ValueError(f"File is empty or contains only whitespace")
            
            logger.debug(f"Read {len(content)} characters from {filename}")
            
            # Step 2: Chunk the text
            chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
            logger.debug(f"Created {len(chunks)} chunks from {filename}")
            
            if not chunks:
                raise ValueError(f"No chunks generated from file")
            
            # Step 3: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embeddings = embed_texts(chunks)
            logger.debug(f"Generated {len(embeddings)} embeddings for {filename}")
            
            if len(chunks) != len(embeddings):
                raise ValueError(
                    f"Chunk/embedding count mismatch: "
                    f"{len(chunks)} chunks vs {len(embeddings)} embeddings"
                )
            
            # Step 4: Store in database as preloaded document
            document_id = insert_document(
                filename=filename,
                mime_type="text/plain",
                is_preloaded=True,
                session_id=None  # NULL for preloaded documents
            )
            
            # Insert chunks with embeddings
            insert_chunks(document_id, chunks, embeddings)
            
            logger.info(
                f"✓ Successfully preloaded: {filename} "
                f"(document_id: {document_id}, {len(chunks)} chunks)"
            )
            success_count += 1
            
        except FileValidationError as e:
            error_msg = f"Validation error for {filename}: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            
        except Exception as e:
            error_msg = f"Error processing {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Preload Summary:")
    logger.info(f"  Total files found: {len(txt_files)}")
    logger.info(f"  Successfully preloaded: {success_count}")
    logger.info(f"  Skipped (already exist): {skipped_count}")
    logger.info(f"  Failed: {len(errors)}")
    logger.info("=" * 60)
    
    if errors:
        logger.warning("Errors encountered:")
        for error in errors:
            logger.warning(f"  - {error}")
    
    return (success_count, skipped_count, errors)


def main():
    """
    Main entry point for the preload script.
    """
    logger.info("LLM File-Based Chatbot - Preload Script")
    logger.info("=" * 60)
    
    try:
        # Initialize database schema if needed
        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database schema ready")
        
        # Preload documents
        success_count, skipped_count, errors = preload_documents()
        
        # Exit with appropriate code
        if errors and success_count == 0:
            logger.error("Preload failed - no documents were loaded")
            sys.exit(1)
        elif errors:
            logger.warning("Preload completed with some errors")
            sys.exit(0)
        else:
            logger.info("Preload completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error during preload: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
