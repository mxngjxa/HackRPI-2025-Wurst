"""
LLM File-Based Chatbot - Gradio Frontend

Main application entry point providing a web interface for document upload
and question answering using RAG (Retrieval-Augmented Generation).
"""

import logging
import os
import gradio as gr
from typing import List, Tuple, Optional, Any

from backend.logging_config import setup_logging
from backend.chat_service import (
    generate_session_id,
    handle_upload,
    handle_question,
    handle_clear_session,
)
from backend.config import MAX_FILES_PER_SESSION

# Configure logging with centralized setup
# Use environment variable for log level, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv(
    "LOG_FILE", "app.log"
)  # Set to empty string to disable file logging
setup_logging(
    log_level=log_level, log_file=log_file if log_file else None, log_dir="logs"
)

logger = logging.getLogger(__name__)


def on_upload(
    files: Optional[List[Any]], session_id: str, history: List[List[Optional[str]]]
) -> Tuple[List[List[Optional[str]]], Optional[List]]:
    """
    Handles file upload event.

    Processes uploaded files and updates chat history with status message.
    Clears file input after successful upload.

    Args:
        files: List of uploaded file objects from Gradio
        session_id: Current session identifier
        history: Current chat history

    Returns:
        Tuple containing:
            - Updated chat history with upload status
            - None (to clear file input)
    """
    if not files:
        # No files selected
        error_msg = "Please select at least one file to upload."
        logger.warning(f"Upload attempted with no files (session: {session_id})")
        history.append([None, error_msg])
        return (history, None)

    try:
        logger.info(f"Upload initiated: {len(files)} file(s) (session: {session_id})")

        # Process files
        success_count, errors = handle_upload(files, session_id)

        # Build status message
        if success_count > 0 and not errors:
            # All files successful
            msg = f"✓ Successfully uploaded {success_count} file(s)."
            logger.info(
                f"Upload successful: {success_count} files (session: {session_id})"
            )
        elif success_count > 0 and errors:
            # Partial success
            msg = f"✓ Successfully uploaded {success_count} file(s).\n\n"
            msg += "⚠ Errors:\n" + "\n".join(f"  • {err}" for err in errors)
            logger.warning(
                f"Upload partially successful: {success_count} succeeded, "
                f"{len(errors)} failed (session: {session_id})"
            )
        else:
            # All files failed
            msg = "✗ Upload failed:\n" + "\n".join(f"  • {err}" for err in errors)
            logger.error(f"Upload failed for all files (session: {session_id})")

        # Add limit warning if applicable
        if len(files) > MAX_FILES_PER_SESSION:
            msg += f"\n\nNote: Only the first {MAX_FILES_PER_SESSION} files were processed."

        # Add system message to history (None as user message indicates system message)
        history.append([None, msg])

        # Return updated history and None to clear file input
        return (history, None)

    except Exception as e:
        # Unexpected error
        error_msg = f"✗ An unexpected error occurred during upload: {str(e)}"
        logger.error(
            f"Unexpected upload error (session: {session_id}): {str(e)}", exc_info=True
        )
        history.append([None, error_msg])
        return (history, None)


def on_send(
    message: str, session_id: str, history: List[List[Optional[str]]]
) -> Tuple[str, List[List[Optional[str]]]]:
    """
    Handles question submission event.

    Processes user question and generates answer using RAG pipeline.
    Clears text input after sending message.

    Args:
        message: User's question text
        session_id: Current session identifier
        history: Current chat history

    Returns:
        Tuple containing:
            - Empty string (to clear text input)
            - Updated chat history with question and answer
    """
    if not message or not message.strip():
        # Empty message
        logger.warning(f"Send attempted with empty message (session: {session_id})")
        return ("", history)

    try:
        logger.info(f"Question submitted (session: {session_id}): {message[:50]}...")

        # Add user message to history
        history.append([message, None])

        # Generate answer
        answer = handle_question(message, session_id)

        # Update last message with answer
        history[-1][1] = answer

        logger.info(f"Answer generated (session: {session_id})")

        # Return empty string to clear input, and updated history
        return ("", history)

    except ValueError as e:
        # Validation error (e.g., empty question)
        error_msg = f"✗ {str(e)}"
        logger.warning(f"Validation error (session: {session_id}): {str(e)}")
        history.append([message, error_msg])
        return ("", history)

    except Exception as e:
        # Unexpected error
        error_msg = (
            "✗ I apologize, but I encountered an error while processing your question. "
            "Please try again."
        )
        logger.error(
            f"Unexpected error processing question (session: {session_id}): {str(e)}",
            exc_info=True,
        )
        history.append([message, error_msg])
        return ("", history)


def on_clear(session_id: str, history: List[List[Optional[str]]]) -> Tuple[str, List]:
    """
    Handles session clear event.

    Deletes all session documents and generates new session ID.
    Resets chat history.

    Args:
        session_id: Current session identifier to clear
        history: Current chat history (will be cleared)

    Returns:
        Tuple containing:
            - New session ID
            - Empty chat history
    """
    try:
        logger.info(f"Clear session initiated (session: {session_id})")

        # Clear session documents
        deleted_count = handle_clear_session(session_id)

        # Generate new session ID
        new_session_id = generate_session_id()

        logger.info(
            f"Session cleared: {deleted_count} document(s) deleted. "
            f"New session: {new_session_id}"
        )

        # Return new session ID and empty history
        return (new_session_id, [])

    except Exception as e:
        # Error during clear - still generate new session
        logger.error(f"Error clearing session {session_id}: {str(e)}", exc_info=True)
        new_session_id = generate_session_id()

        # Return new session with error message in history
        error_msg = f"⚠ Warning: Error clearing session documents: {str(e)}"
        return (new_session_id, [[None, error_msg]])


# Build Gradio interface
with gr.Blocks(title="LLM File-Based Chatbot") as app:
    # Header
    gr.Markdown("# 📚 LLM File-Based Chatbot")
    gr.Markdown(
        "Upload text documents and ask questions about their content. "
        f"You can upload up to {MAX_FILES_PER_SESSION} files per session."
    )

    # Session state - initialize with a session ID
    session_id_state = gr.State(value=generate_session_id())

    # Main layout
    with gr.Row():
        with gr.Column(scale=2):
            # Chatbot display
            chatbot = gr.Chatbot(label="Conversation", height=500, show_label=True)

            # Question input and send button
            with gr.Row():
                question_input = gr.Textbox(
                    label="Ask a question",
                    placeholder="Type your question here...",
                    lines=2,
                    scale=4,
                    show_label=False,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

        with gr.Column(scale=1):
            # File upload
            file_upload = gr.File(
                label=f"Upload Documents (max {MAX_FILES_PER_SESSION} files)",
                file_count="multiple",
                file_types=[".txt"],
                type="filepath",
            )
            upload_btn = gr.Button("Upload Files", variant="secondary")

            # Clear session button
            gr.Markdown("---")
            clear_btn = gr.Button("Clear Session", variant="stop")
            gr.Markdown(
                "*Clearing session will delete your uploaded documents "
                "and reset the conversation.*"
            )

    # Event handlers

    # Handle file upload
    upload_btn.click(
        fn=on_upload,
        inputs=[file_upload, session_id_state, chatbot],
        outputs=[chatbot, file_upload],
    )

    # Handle question submission (button click)
    send_btn.click(
        fn=on_send,
        inputs=[question_input, session_id_state, chatbot],
        outputs=[question_input, chatbot],
    )

    # Handle question submission (Enter key)
    question_input.submit(
        fn=on_send,
        inputs=[question_input, session_id_state, chatbot],
        outputs=[question_input, chatbot],
    )

    # Handle session clear
    clear_btn.click(
        fn=on_clear,
        inputs=[session_id_state, chatbot],
        outputs=[session_id_state, chatbot],
    )


if __name__ == "__main__":
    logger.info("Starting LLM File-Based Chatbot application")
    # Let Gradio find an available port automatically
    app.launch(server_name="127.0.0.1", share=False)
