"""
Function Tools module for LLM File-Based Chatbot.

Defines and implements tools that AI can call through Gemini function calling
to access database and perform searches.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import text

from backend.db import get_engine
from backend.retrieval import get_context_chunks
from backend.config import (
    ENABLE_SEMANTIC_SEARCH_TOOL,
    ENABLE_KEYWORD_SEARCH_TOOL,
    ENABLE_DOCUMENT_QUERY_TOOL,
)

logger = logging.getLogger(__name__)


def get_available_tools() -> List[Dict[str, Any]]:
    """
    Returns list of available tools for Gemini function calling.

    Returns:
        List of tool definitions in Gemini function calling format
    """
    tools = []

    if ENABLE_SEMANTIC_SEARCH_TOOL:
        tools.append(
            {
                "name": "semantic_search",
                "description": (
                    "Performs semantic (vector) search to find relevant document chunks "
                    "based on meaning, not just keywords. Use this when you need to find "
                    "information related to the user's question."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query or question",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)",
                        },
                    },
                    "required": ["query"],
                },
            }
        )

    if ENABLE_DOCUMENT_QUERY_TOOL:
        tools.append(
            {
                "name": "list_documents",
                "description": (
                    "Lists all documents available in the current session, including "
                    "preloaded documents. Use this to see what documents are available."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_preloaded": {
                            "type": "boolean",
                            "description": "Include preloaded system documents (default: true)",
                        }
                    },
                    "required": [],
                },
            }
        )

    if ENABLE_KEYWORD_SEARCH_TOOL:
        tools.append(
            {
                "name": "keyword_search",
                "description": (
                    "Performs traditional keyword search in document content. "
                    "Use this when you need exact text matches or specific terms."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Keywords to search for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                        },
                    },
                    "required": ["keywords"],
                },
            }
        )

    logger.info(f"Loaded {len(tools)} function calling tools")
    return tools


def execute_tool(tool_name: str, tool_args: Dict[str, Any], session_id: str) -> str:
    """
    Executes a tool call and returns the result.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        session_id: Current session ID for data isolation

    Returns:
        str: Tool execution result as string

    Raises:
        ValueError: If tool name is unknown or execution fails
    """
    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

    try:
        if tool_name == "semantic_search":
            return _semantic_search(tool_args, session_id)
        elif tool_name == "list_documents":
            return _list_documents(tool_args, session_id)
        elif tool_name == "keyword_search":
            return _keyword_search(tool_args, session_id)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    except Exception as e:
        error_msg = f"Error executing tool {tool_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {str(e)}"


def _semantic_search(args: Dict[str, Any], session_id: str) -> str:
    """
    Performs semantic vector search.

    Args:
        args: {"query": str, "top_k": int}
        session_id: Current session ID

    Returns:
        str: JSON-formatted search results
    """
    query = args.get("query", "")
    top_k = args.get("top_k", 5)

    if not query:
        return "Error: query parameter is required"

    logger.info(f"Semantic search: '{query}' (top_k={top_k}, session={session_id})")

    # Use existing retrieval function
    chunks = get_context_chunks(query, session_id, top_k)

    if not chunks:
        return "No relevant documents found."

    # Format results
    result = {"found": len(chunks), "chunks": chunks}

    import json

    return json.dumps(result, ensure_ascii=False, indent=2)


def _list_documents(args: Dict[str, Any], session_id: str) -> str:
    """
    Lists available documents.

    Args:
        args: {"include_preloaded": bool}
        session_id: Current session ID

    Returns:
        str: JSON-formatted document list
    """
    include_preloaded = args.get("include_preloaded", True)

    logger.info(
        f"Listing documents (include_preloaded={include_preloaded}, session={session_id})"
    )

    engine = get_engine()

    try:
        with engine.connect() as conn:
            if include_preloaded:
                query = text("""
                    SELECT id, filename, mime_type, is_preloaded, uploaded_at
                    FROM documents
                    WHERE is_preloaded = TRUE OR session_id = :session_id
                    ORDER BY is_preloaded DESC, uploaded_at DESC
                """)
            else:
                query = text("""
                    SELECT id, filename, mime_type, is_preloaded, uploaded_at
                    FROM documents
                    WHERE session_id = :session_id
                    ORDER BY uploaded_at DESC
                """)

            result = conn.execute(query, {"session_id": session_id})
            rows = result.fetchall()

            documents = []
            for row in rows:
                documents.append(
                    {
                        "id": row[0],
                        "filename": row[1],
                        "mime_type": row[2],
                        "is_preloaded": row[3],
                        "uploaded_at": str(row[4]),
                    }
                )

            result_data = {"total": len(documents), "documents": documents}

            import json

            return json.dumps(result_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


def _keyword_search(args: Dict[str, Any], session_id: str) -> str:
    """
    Performs keyword-based text search.

    Args:
        args: {"keywords": str, "limit": int}
        session_id: Current session ID

    Returns:
        str: JSON-formatted search results
    """
    keywords = args.get("keywords", "")
    limit = args.get("limit", 10)

    if not keywords:
        return "Error: keywords parameter is required"

    logger.info(f"Keyword search: '{keywords}' (limit={limit}, session={session_id})")

    engine = get_engine()

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT dc.content, d.filename
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
                AND dc.content ILIKE :search_pattern
                LIMIT :limit
            """)

            search_pattern = f"%{keywords}%"
            result = conn.execute(
                query,
                {
                    "session_id": session_id,
                    "search_pattern": search_pattern,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

            results = []
            for row in rows:
                results.append({"content": row[0], "filename": row[1]})

            result_data = {"found": len(results), "results": results}

            import json

            return json.dumps(result_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error in keyword search: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"
