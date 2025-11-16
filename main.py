"""
LLM File-Based Chatbot - FastAPI Backend API
"""

import logging
import os
import uvicorn
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.logging_config import setup_logging
from backend.chat_service import (
    generate_session_id,
    handle_upload,
    handle_question,
    handle_clear_session,
)
from backend.config import validate_config, ConfigurationError
from backend.db import init_db

# --- Logging Configuration ---

# Generate a per-run timestamp
run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Base log filename from env, or default
base_log_file = os.getenv("LOG_FILE", "app.log")

if base_log_file:
    # Insert timestamp before extension, e.g. app_2025-11-16_13-40-57.log
    root, ext = os.path.splitext(base_log_file)
    log_file = f"{root}_{run_ts}{ext or '.log'}"
else:
    log_file = None  # disables file logging

# Use environment variable for log level, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")

# Call centralized setup
setup_logging(
    log_level=log_level,
    log_file=log_file,
    log_dir="logs",
)

logger = logging.getLogger(__name__)

# --- Application Startup ---

try:
    # 1. Validate configuration
    validate_config()
    logger.info("Configuration validated successfully.")

    # 2. Initialize database schema (create tables, extensions)
    init_db()
    logger.info("Database schema initialized successfully on startup.")

except ConfigurationError as e:
    logger.error(f"FATAL: Configuration Error: {str(e)}")
    # Exit if configuration fails
    exit(1)
except Exception as e:
    logger.error(f"FATAL: Failed to initialize database schema: {str(e)}")
    # Exit if database initialization fails
    exit(1)

# --- FastAPI App Setup ---

app = FastAPI(
    title="LLM File-Based Chatbot API",
    description="HTTP API for the RAG Chatbot, replacing the Gradio frontend.",
    version="1.0.0",
)

# Serve static files from the 'frontend' directory
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Configure CORS to allow frontend to connect
# In a real-world scenario, this should be restricted to the frontend's origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---

class SessionResponse(BaseModel):
    session_id: str

class UploadResponse(BaseModel):
    success_count: int
    errors: List[str]

class QuestionRequest(BaseModel):
    question: str
    session_id: str

class QuestionResponse(BaseModel):
    answer: str
    # Note: Sources are not explicitly returned by handle_question, 
    # but the prompt implies they might be. For now, stick to the current 
    # handle_question signature which returns only the answer string.

class ClearRequest(BaseModel):
    session_id: str

class ClearResponse(BaseModel):
    deleted_count: int

# --- API Endpoints ---

@app.post("/session", response_model=SessionResponse)
async def create_session():
    """
    Generates a new unique session ID.
    """
    session_id = generate_session_id()
    logger.info(f"API: New session created: {session_id}")
    return {"session_id": session_id}

@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Accepts one or more .txt files and a session_id.
    Wraps handle_upload(files, session_id).
    """
    logger.info(f"API: Upload request received for session {session_id} with {len(files)} file(s)")
    
    # FastAPI's UploadFile is a SpooledTemporaryFile, which handle_upload expects.
    # We need to pass the actual file-like object to handle_upload.
    # The handle_upload function expects a list of file-like objects.
    
    # We need to read the content of the UploadFile into a temporary file 
    # or a structure that handle_upload can process, as handle_upload 
    # expects a list of Gradio file objects which have a 'name' attribute 
    # and are file-like. FastAPI's UploadFile is a file-like object 
    # but its 'name' is the client-side filename.
    
    # The existing handle_upload expects a list of Gradio file objects.
    # Gradio file objects are typically temporary files with a 'name' attribute 
    # pointing to the original filename.
    
    # To maintain the backend/chat_service.py signature, we will create a list 
    # of objects that mimic the required attributes of the Gradio file object:
    # 1. A file-like object (UploadFile itself is one)
    # 2. A 'name' attribute (UploadFile.filename)
    
    # We will create a list of temporary file objects that mimic the Gradio file structure.
    # Since handle_upload expects a list of objects that can be passed to 
    # backend.file_parser.read_txt_file, and read_txt_file expects a file-like object 
    # with a 'name' attribute, we can use a simple wrapper class or modify 
    # the UploadFile objects slightly.
    
    # For simplicity and to avoid complex temporary file management, we will 
    # rely on the fact that UploadFile is a file-like object and has a .filename attribute.
    # We will temporarily monkey-patch the UploadFile objects to have a 'name' attribute 
    # for compatibility with the existing backend.
    
    files_for_backend = []
    for file in files:
        # Create a temporary object that mimics the Gradio file structure
        # by having a 'name' attribute for the original filename.
        # We use the UploadFile object itself as the file-like object.
        class MockGradioFile:
            def __init__(self, upload_file: UploadFile):
                self.name = upload_file.filename
                self.file = upload_file.file
            
            def read(self, size=-1):
                return self.file.read(size)
            
            def seek(self, offset):
                return self.file.seek(offset)
            
            def close(self):
                # Do not close the underlying SpooledTemporaryFile here, 
                # let FastAPI handle its cleanup.
                pass

        files_for_backend.append(MockGradioFile(file))

    try:
        success_count, errors = handle_upload(files_for_backend, session_id)
        return {"success_count": success_count, "errors": errors}
    except Exception as e:
        logger.error(f"API: Unexpected error during upload for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error during upload: {str(e)}")

@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Accepts a question and session_id.
    Wraps handle_question(question, session_id).
    """
    logger.info(f"API: Question request received for session {request.session_id}: {request.question[:50]}...")
    try:
        answer = handle_question(request.question, request.session_id)
        return {"answer": answer}
    except ValueError as e:
        # Handle validation errors from chat_service (e.g., empty question)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API: Unexpected error during question for session {request.session_id}: {str(e)}", exc_info=True)
        # Return the error message from handle_question if it's a user-facing one, 
        # otherwise a generic error. handle_question already returns a user-friendly 
        # error message on failure, so we can return that.
        # However, if it's an unexpected exception, we should return a 500.
        # Since handle_question catches and returns a user-friendly string on most 
        # exceptions, we'll rely on that for the answer, but for a true 
        # unexpected exception, we'll raise a 500.
        if "I apologize, but I encountered an error" in str(e):
             # This is a user-friendly error from handle_question's internal catch
             # We can return it as a 200 OK with the error message in the answer field
             return {"answer": str(e)}
        else:
             # True unexpected error
             raise HTTPException(status_code=500, detail="Internal Server Error during question processing.")


@app.post("/clear", response_model=ClearResponse)
async def clear_session(request: ClearRequest):
    """
    Accepts a session_id and clears all associated documents.
    Wraps handle_clear_session(session_id).
    """
    logger.info(f"API: Clear session request received for session {request.session_id}")
    try:
        deleted_count = handle_clear_session(request.session_id)
        return {"deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"API: Error clearing session {request.session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error during session clear: {str(e)}")

# Catch-all route to serve index.html for the root path
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """
    Serves the main index.html file for the frontend.
    """
    with open("frontend/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# --- Main Execution Block ---

if __name__ == "__main__":
    logger.info("Starting LLM File-Based Chatbot FastAPI application")
    
    # The host and port can be configured via environment variables or hardcoded.
    # Using 0.0.0.0 to be accessible from inside a container/docker-compose.
    uvicorn.run(app, host="0.0.0.0", port=8000)