"""
File parser module for LLM File-Based Chatbot.

Handles file reading, validation, and content extraction for uploaded documents.
"""

import os
from typing import Any
from backend.config import MAX_FILE_SIZE_MB


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


def validate_file(file_obj: Any) -> None:
    """
    Validates file size and format.

    Args:
        file_obj: Gradio file object with 'name' and 'size' attributes

    Raises:
        FileValidationError: If file validation fails
    """
    # Check if file object is valid
    if file_obj is None:
        error_msg = "No file provided"
        raise FileValidationError(error_msg)

    # Get filename
    filename = getattr(file_obj, "name", None)
    if not filename:
        error_msg = "File has no name attribute"
        raise FileValidationError(error_msg)

    # Validate file extension
    if not filename.lower().endswith(".txt"):
        error_msg = (
            f"Invalid file format. Only .txt files are supported. "
            f"Got: {os.path.basename(filename)}"
        )
        raise FileValidationError(error_msg)

    # Validate file size
    # Gradio file objects may have different attributes depending on version
    # Try to get size from different possible attributes
    file_size = None

    try:
        # Try 'size' attribute first
        if hasattr(file_obj, "size") and file_obj.size is not None:
            file_size = file_obj.size
        # Try getting file size from the file path
        elif (
            hasattr(file_obj, "name")
            and file_obj.name
            and os.path.exists(file_obj.name)
        ):
            file_size = os.path.getsize(file_obj.name)
    except Exception as e:
        error_msg = (
            f"Error determining file size for {os.path.basename(filename)}: {str(e)}"
        )
        raise FileValidationError(error_msg) from e

    if file_size is None:
        error_msg = f"Unable to determine file size for {os.path.basename(filename)}"
        raise FileValidationError(error_msg)

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        error_msg = (
            f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB. "
            f"Got: {size_mb:.2f}MB for {os.path.basename(filename)}"
        )
        raise FileValidationError(error_msg)


def read_txt_file(file_obj: Any) -> str:
    """
    Reads and decodes text file content.

    Args:
        file_obj: Gradio file object with 'name' attribute pointing to file path

    Returns:
        str: File content as UTF-8 decoded string

    Raises:
        FileValidationError: If file cannot be read or is empty/whitespace-only
    """
    # Validate file first
    validate_file(file_obj)

    # Get file path
    file_path = file_obj.name

    try:
        # Read file with UTF-8 encoding and error handling
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except FileNotFoundError:
        raise FileValidationError(f"File not found: {os.path.basename(file_path)}")
    except PermissionError:
        raise FileValidationError(
            f"Permission denied reading file: {os.path.basename(file_path)}"
        )
    except Exception as e:
        raise FileValidationError(
            f"Error reading file {os.path.basename(file_path)}: {str(e)}"
        )

    # Validate content is not empty or whitespace-only
    if not content or not content.strip():
        raise FileValidationError(
            f"File is empty or contains only whitespace: {os.path.basename(file_path)}"
        )

    return content
