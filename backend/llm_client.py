"""
LLM client abstraction for LLM File-Based Chatbot.

Provides abstract base class and implementations for Mock and Real LLM clients.
Supports factory pattern for client instantiation based on configuration.
"""

import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
from backend.config import (
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
    USE_MOCK_LLM,
    USE_FUNCTION_CALLING,
)

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


class LLMClient(ABC):
    """
    Abstract base class for LLM client implementations.

    Defines the interface that all LLM clients must implement.
    """

    @abstractmethod
    def generate_answer(
        self, context: str, question: str, session_id: str = None
    ) -> str:
        """
        Generates an answer to the question based on the provided context.

        Args:
            context: Retrieved document chunks formatted as context
            question: User's question
            session_id: Current session ID (optional, used in Function Calling mode)

        Returns:
            str: Generated answer
        """
        pass


class MockLLMClient(LLMClient):
    """
    Mock LLM client for development and testing.

    Returns simulated responses without making real API calls.
    Useful for development without API credentials or costs.
    """

    def generate_answer(
        self, context: str, question: str, session_id: str = None
    ) -> str:
        """
        Generates a mock response with question and context preview.

        Args:
            context: Retrieved document chunks formatted as context
            question: User's question
            session_id: Current session ID (optional, not used in mock mode)

        Returns:
            str: Mock response showing question and context preview
        """
        logger.info(f"MockLLMClient generating answer for question: {question[:50]}...")

        # Create context preview (first 200 characters)
        context_preview = context[:200] + "..." if len(context) > 200 else context

        # Format mock response
        mock_response = f"""[MOCK LLM RESPONSE]

Question: {question}

Context Preview: {context_preview}

This is a simulated response. In production mode, the real Gemini LLM would analyze the full context and provide an actual answer.

To enable real LLM responses, set USE_MOCK_LLM=false in your .env file."""

        logger.debug(f"Mock response generated (length: {len(mock_response)})")
        return mock_response


class GeminiLLMClient(LLMClient):
    """
    Real LLM client using Google Gemini API.

    Makes actual API calls to Gemini for generating answers based on
    retrieved context using the RAG (Retrieval-Augmented Generation) pattern.
    """

    def __init__(self):
        """Initialize Gemini model."""
        self.model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
        logger.info(f"Initialized GeminiLLMClient with model: {GEMINI_CHAT_MODEL}")

    def generate_answer(
        self, context: str, question: str, session_id: str = None
    ) -> str:
        """
        Generates an answer using Gemini API based on context and question.

        Uses a RAG prompt template to instruct the model to answer based
        on the provided context.

        Args:
            context: Retrieved document chunks formatted as context
            question: User's question
            session_id: Current session ID (optional, not used in RAG mode)

        Returns:
            str: Generated answer from Gemini
        """
        logger.info(
            f"GeminiLLMClient generating answer for question: {question[:50]}..."
        )

        # Create RAG prompt template
        prompt = f"""You are a helpful assistant. Answer the user's question based on the provided context.
If the context doesn't contain relevant information, say so clearly.

Context:
{context}

Question: {question}

Answer:"""

        try:
            # Call Gemini API
            logger.debug(f"Calling Gemini API with prompt length: {len(prompt)}")
            response = self.model.generate_content(prompt)

            # Extract text from response
            answer = response.text

            logger.info(f"Successfully generated answer (length: {len(answer)})")
            return answer

        except AttributeError as e:
            # Response object doesn't have expected structure
            logger.error(f"Gemini API response format error: {str(e)}", exc_info=True)
            fallback_message = (
                "I received an unexpected response format from the AI service. "
                "Please try again."
            )
            return fallback_message

        except Exception as e:
            # Log error with details and return fallback message
            error_type = type(e).__name__
            logger.error(
                f"Gemini API call failed: {error_type}: {str(e)}", exc_info=True
            )

            fallback_message = (
                "I apologize, but I encountered an error while generating a response. "
                "Please try again later or contact support if the issue persists."
            )

            return fallback_message


class GeminiFunctionCallingClient(LLMClient):
    """
    Gemini client with function calling support.

    AI can actively call tools to get information instead of
    receiving pre-retrieved context.
    """

    def __init__(self):
        """Initialize with function handler."""
        from backend.function_handler import FunctionHandler

        self.function_handler = FunctionHandler()
        logger.info("Initialized GeminiFunctionCallingClient")

    def generate_answer(
        self, context: str, question: str, session_id: str = None
    ) -> str:
        """
        Generates answer using function calling.

        Args:
            context: Ignored in function calling mode
            question: User's question
            session_id: Required for function calling

        Returns:
            str: Generated answer
        """
        if not session_id:
            logger.error("session_id is required for function calling mode")
            return "Error: Session ID is required for function calling mode."

        logger.info(f"Generating answer with function calling: {question[:50]}...")

        try:
            answer = self.function_handler.generate_answer(question, session_id)
            logger.info(f"Successfully generated answer (length: {len(answer)})")
            return answer
        except Exception as e:
            logger.error(f"Function calling failed: {str(e)}", exc_info=True)
            return (
                "I apologize, but I encountered an error while processing your question. "
                "Please try again."
            )


def get_llm_client() -> LLMClient:
    """
    Factory function to return appropriate LLM client based on configuration.

    Returns:
        LLMClient: Appropriate LLM client instance based on configuration
    """
    if USE_MOCK_LLM:
        logger.info("Creating MockLLMClient (USE_MOCK_LLM=true)")
        return MockLLMClient()
    elif USE_FUNCTION_CALLING:
        logger.info("Creating GeminiFunctionCallingClient (USE_FUNCTION_CALLING=true)")
        return GeminiFunctionCallingClient()
    else:
        logger.info("Creating GeminiLLMClient (RAG mode)")
        return GeminiLLMClient()
