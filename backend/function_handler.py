"""
Function Handler module for LLM File-Based Chatbot.

Handles the interaction between Gemini function calling and tool execution.
"""

import logging
from typing import List

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from backend.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL, MAX_FUNCTION_CALLS
from backend.mcp_tools import get_available_tools, execute_tool

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


class FunctionHandler:
    """
    Handles function calling through Gemini API.
    """

    def __init__(self):
        """Initialize function handler with Gemini model and tools."""
        self.model_name = GEMINI_CHAT_MODEL
        self.tools = self._prepare_tools()
        self.model = genai.GenerativeModel(model_name=self.model_name, tools=self.tools)
        logger.info(f"Initialized FunctionHandler with {len(self.tools)} tools")

    def _prepare_tools(self) -> List[Tool]:
        """
        Prepares tools in Gemini format.

        Returns:
            List of Gemini Tool objects
        """
        tool_definitions = get_available_tools()

        # Convert to Gemini FunctionDeclaration format
        function_declarations = []
        for tool_def in tool_definitions:
            func_decl = FunctionDeclaration(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"],
            )
            function_declarations.append(func_decl)

        # Wrap in Tool object
        if function_declarations:
            return [Tool(function_declarations=function_declarations)]
        return []

    def generate_answer(
        self, question: str, session_id: str, max_iterations: int = None
    ) -> str:
        """
        Generates answer using Gemini with function calling.

        Args:
            question: User's question
            session_id: Current session ID
            max_iterations: Maximum number of function call iterations

        Returns:
            str: Generated answer
        """
        if max_iterations is None:
            max_iterations = MAX_FUNCTION_CALLS

        logger.info(
            f"Generating answer with function calling for question: {question[:50]}..."
        )

        # Build system instruction
        system_instruction = self._build_system_instruction(session_id)

        # Start chat session
        chat = self.model.start_chat(history=[])

        # Send initial message
        try:
            response = chat.send_message(
                f"{system_instruction}\n\nUser question: {question}"
            )
        except Exception as e:
            logger.error(f"Error sending initial message: {str(e)}", exc_info=True)
            return f"Error: Failed to communicate with AI model. {str(e)}"

        # Handle function calling loop
        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Check if response contains function calls
            if not response.candidates:
                logger.warning("No candidates in response")
                break

            candidate = response.candidates[0]

            # Check for function calls
            if not candidate.content.parts:
                logger.warning("No parts in candidate content")
                break

            # Look for function calls
            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if hasattr(part, "function_call") and part.function_call
            ]

            if not function_calls:
                # No more function calls, extract final answer
                final_text = "".join(
                    [
                        part.text
                        for part in candidate.content.parts
                        if hasattr(part, "text")
                    ]
                )

                if final_text:
                    logger.info(f"Generated final answer (length: {len(final_text)})")
                    return final_text
                else:
                    logger.warning("No text in final response")
                    break

            # Execute function calls
            logger.info(
                f"Iteration {iteration}: Processing {len(function_calls)} function call(s)"
            )

            function_responses = []
            for func_call in function_calls:
                tool_name = func_call.name
                tool_args = dict(func_call.args)

                logger.info(f"Executing tool: {tool_name}")

                # Execute tool
                try:
                    result = execute_tool(tool_name, tool_args, session_id)
                    function_responses.append({"name": tool_name, "response": result})
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    function_responses.append(
                        {"name": tool_name, "response": f"Error: {str(e)}"}
                    )

            # Send function responses back to model
            try:
                # Build function response parts
                from google.generativeai.types import content_types

                response_parts = []
                for func_resp in function_responses:
                    response_parts.append(
                        content_types.FunctionResponse(
                            name=func_resp["name"],
                            response={"result": func_resp["response"]},
                        )
                    )

                response = chat.send_message(response_parts)

            except Exception as e:
                logger.error(
                    f"Error sending function responses: {str(e)}", exc_info=True
                )
                return f"Error: Failed to process tool results. {str(e)}"

        # Max iterations reached
        if iteration >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached")
            return "I apologize, but I need more steps to answer your question. Please try rephrasing it."

        # Fallback
        return "I apologize, but I couldn't generate a proper answer. Please try again."

    def _build_system_instruction(self, session_id: str) -> str:
        """
        Builds system instruction for the AI.

        Args:
            session_id: Current session ID

        Returns:
            str: System instruction
        """
        return f"""You are a helpful AI assistant with access to a document database.

Current session ID: {session_id}

You have access to the following tools:
- semantic_search: Find relevant information using semantic (meaning-based) search
- list_documents: See what documents are available
- keyword_search: Search for specific keywords in documents

Guidelines:
1. Use semantic_search when you need to find information related to the user's question
2. Use list_documents to see what documents are available
3. Use keyword_search when looking for specific terms or exact matches
4. Always filter by the current session_id (this is handled automatically)
5. Provide clear, helpful answers based on the information you find
6. If you can't find relevant information, say so clearly

Remember: You can call multiple tools if needed to gather complete information."""
