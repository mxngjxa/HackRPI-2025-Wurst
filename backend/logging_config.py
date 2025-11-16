"""
Logging configuration module for LLM File-Based Chatbot.

Provides centralized logging setup with consistent formatting,
file handlers, and appropriate log levels for different modules.
"""

import logging
import logging.handlers
import os
from typing import Optional


class SessionContextFilter(logging.Filter):
    """
    Custom filter to add session_id to log records.

    Allows session_id to be included in log format even when
    not explicitly passed in every log call.
    """

    def filter(self, record):
        """Add session_id to record if not present."""
        if not hasattr(record, "session_id"):
            record.session_id = "N/A"
        return True


def setup_logging(
    log_level: str = "INFO", log_file: Optional[str] = None, log_dir: str = "logs"
) -> None:
    """
    Configures logging for the application.

    Sets up:
    - Console handler with colored output (if available)
    - File handler with rotation (if log_file specified)
    - Consistent format with timestamp, level, module, session_id
    - Appropriate log levels for different modules

    Args:
        log_level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (e.g., 'app.log')
        log_dir: Directory for log files (default: 'logs')
    """
    # Create log directory if it doesn't exist
    if log_file and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Define log format without session_id (to avoid issues with third-party libraries)
    log_format = "[%(asctime)s] [%(levelname)-8s] [%(name)-20s] %(message)s"

    # Date format
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (if log_file specified)
    if log_file:
        log_path = os.path.join(log_dir, log_file)

        # Use RotatingFileHandler to prevent log files from growing too large
        # Max size: 10MB, keep 5 backup files
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for different modules

    # Backend modules - INFO level
    logging.getLogger("backend").setLevel(logging.INFO)

    # Database module - INFO level (can be set to DEBUG for SQL debugging)
    logging.getLogger("backend.db").setLevel(logging.INFO)

    # Embeddings and LLM - INFO level
    logging.getLogger("backend.embeddings").setLevel(logging.INFO)
    logging.getLogger("backend.llm_client").setLevel(logging.INFO)

    # Chat service - INFO level
    logging.getLogger("backend.chat_service").setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("gradio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log initialization message
    root_logger.info(
        f"Logging configured: level={log_level}, file={log_file or 'None'}"
    )


def get_logger_with_session(
    name: str, session_id: Optional[str] = None
) -> logging.LoggerAdapter:
    """
    Returns a logger adapter that includes session_id in all log messages.

    This is a convenience function for modules that want to consistently
    include session_id in their logs.

    Args:
        name: Logger name (typically __name__)
        session_id: Session identifier to include in logs

    Returns:
        logging.LoggerAdapter: Logger adapter with session_id context

    Example:
        logger = get_logger_with_session(__name__, session_id)
        logger.info("Processing request")  # Will include session_id
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {"session_id": session_id or "N/A"})
