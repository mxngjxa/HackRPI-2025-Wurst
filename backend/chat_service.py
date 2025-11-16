"""
Chat service orchestration module for LLM File-Based Chatbot.

Provides high-level orchestration for document upload, question answering,
and session management operations.
"""

import logging
import uuid
from typing import List, Tuple, Any

from backend.config import MAX_FILES_PER_SESSION, CHUNK_SIZE, CHUNK_OVERLAP
from backend.file_parser import read_txt_file, FileValidationError
from backend.chunking import chunk_text
from backend.embeddings import embed_texts
from backend.db import insert_document, insert_chunks, clear_session_documents
from backend.retrieval import get_context_chunks, format_context
from backend.llm_client import get_llm_client

# Configure logging
logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """
    Generates a unique session identifier using UUID4.

    Returns:
        str: Unique session identifier
    """
    session_id = str(uuid.uuid4())
    logger.info(f"Generated new session ID: {session_id}")
    return session_id


def handle_upload(files: List[Any], session_id: str) -> Tuple[int, List[str]]:
    """
    Processes file uploads for a session.

    Handles up to MAX_FILES_PER_SESSION files, processing each through
    the complete pipeline: validation, reading, chunking, embedding,
    and database storage. Collects errors for failed files and continues
    processing remaining files.

    Args:
        files: List of Gradio file objects to process
        session_id: Current session identifier

    Returns:
        Tuple[int, List[str]]: (success_count, error_messages)
            - success_count: Number of files successfully processed
            - error_messages: List of error messages for failed files
    """
    if not files:
        logger.warning("handle_upload called with empty file list")
        return (0, ["No files provided"])

    logger.info(f"Processing {len(files)} file(s) for session: {session_id}")

    # Limit to MAX_FILES_PER_SESSION
    files_to_process = files[:MAX_FILES_PER_SESSION]
    if len(files) > MAX_FILES_PER_SESSION:
        logger.warning(
            f"User attempted to upload {len(files)} files. "
            f"Processing only first {MAX_FILES_PER_SESSION} files."
        )

    success_count = 0
    errors = []

    # Process each file
    for file_obj in files_to_process:
        try:
            # Get filename for logging
            filename = getattr(file_obj, "name", "unknown")
            logger.info(f"Processing file: {filename}")

            # Step 1: Read and validate file
            content = read_txt_file(file_obj)
            logger.debug(f"Read {len(content)} characters from {filename}")

            # Step 2: Chunk the text
            chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
            logger.debug(f"Created {len(chunks)} chunks from {filename}")

            if not chunks:
                raise ValueError(f"No chunks generated from file: {filename}")

            # Step 3: Generate embeddings
            embeddings = embed_texts(chunks)
            logger.debug(f"Generated {len(embeddings)} embeddings for {filename}")

            if len(chunks) != len(embeddings):
                raise ValueError(
                    f"Chunk/embedding count mismatch for {filename}: "
                    f"{len(chunks)} chunks vs {len(embeddings)} embeddings"
                )

            # Step 4: Store in database
            # Insert document record
            document_id = insert_document(
                filename=filename,
                mime_type="text/plain",
                is_preloaded=False,
                session_id=session_id,
            )

            # Insert chunks with embeddings
            insert_chunks(document_id, chunks, embeddings)

            logger.info(
                f"Successfully processed file: {filename} (document_id: {document_id})"
            )
            success_count += 1

        except FileValidationError as e:
            # File validation errors (user-friendly messages)
            error_msg = str(e)
            logger.warning(f"File validation error: {error_msg}")
            errors.append(error_msg)

        except Exception as e:
            # Other processing errors
            error_msg = (
                f"Error processing {getattr(file_obj, 'name', 'unknown')}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(
        f"Upload complete: {success_count} successful, {len(errors)} failed "
        f"(session: {session_id})"
    )

    return (success_count, errors)


def handle_question(question: str, session_id: str) -> str:
    """
    Processes a user question and generates an answer.

    Orchestrates the complete question-answering pipeline:
    1. Retrieves relevant context chunks using semantic search
    2. Formats context for LLM consumption
    3. Generates answer using LLM client

    Args:
        question: User's question text
        session_id: Current session identifier

    Returns:
        str: Generated answer from the LLM

    Raises:
        ValueError: If question is empty or whitespace-only
    """
    if not question or not question.strip():
        logger.warning("handle_question called with empty question")
        raise ValueError("Question cannot be empty")

    logger.info(f"Handling question for session {session_id}: {question[:50]}...")

    try:
        # Get LLM client
        llm_client = get_llm_client()

        # Check if using Function Calling mode
        from backend.config import USE_FUNCTION_CALLING

        if USE_FUNCTION_CALLING:
            # Function Calling mode: AI fetches its own data through tools
            logger.info(
                "Using Function Calling mode - AI will call tools to fetch data"
            )
            answer = llm_client.generate_answer("", question, session_id)
        else:
            # RAG mode: We provide context
            logger.info("Using RAG mode - fetching context for AI")

            # Step 1: Retrieve relevant context chunks
            chunks = get_context_chunks(question, session_id)

            # Check if any documents are available
            if not chunks:
                logger.info("No documents available for context")
                return (
                    "I don't have any documents to reference. "
                    "Please upload some documents first so I can answer your questions."
                )

            # Step 2: Format context for LLM
            context = format_context(chunks)
            logger.debug(f"Formatted context length: {len(context)} characters")

            # Step 3: Generate answer with context
            answer = llm_client.generate_answer(context, question, session_id)

        logger.info(f"Successfully generated answer (length: {len(answer)})")
        return answer

    except ValueError:
        # Re-raise validation errors
        raise

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Error generating answer: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return (
            "I apologize, but I encountered an error while processing your question. "
            "Please try again or rephrase your question."
        )


def handle_clear_session(session_id: str) -> int:
    """
    Clears all documents associated with a session.

    Deletes all session-specific documents from the database.
    Preloaded documents are not affected. Chunks are automatically
    deleted via CASCADE DELETE constraint.

    Args:
        session_id: Session identifier to clear

    Returns:
        int: Number of documents deleted
    """
    logger.info(f"Clearing session: {session_id}")

    try:
        deleted_count = clear_session_documents(session_id)
        logger.info(
            f"Successfully cleared {deleted_count} document(s) from session: {session_id}"
        )
        return deleted_count

    except Exception as e:
        error_msg = f"Error clearing session {session_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
