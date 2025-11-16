---
inclusion: always
---

# Product Overview

LLM File-Based Chatbot is a Python-based RAG (Retrieval-Augmented Generation) application that enables users to upload text documents and ask questions about their content.

## Core Features

- Document upload: Up to 5 .txt files per session (max 10MB each)
- Semantic search: Vector similarity search using pgvector
- Question answering: Context-aware responses using Google Gemini
- Preloaded knowledge base: System-wide reference documents
- Session isolation: User documents remain private to their session
- Mock LLM mode: Development without API credentials

## Key Characteristics

- No authentication or multi-user support
- No persistent conversation history (UI-only)
- Session-based document management
- Preloaded documents available to all sessions
