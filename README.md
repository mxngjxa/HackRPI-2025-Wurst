# LLM File-Based Chatbot

This project is a file-based chatbot that uses a Large Language Model (LLM) to answer questions about uploaded documents. It is built with Python, Gradio, and a PostgreSQL database with pgvector for vector storage.

## Features

-   **File Upload**: Upload text files to the chatbot.
-   **RAG Pipeline**: Uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions.
-   **Vector Search**: Uses pgvector for efficient similarity search.
-   **Containerized**: Comes with a `Dockerfile` for easy deployment.

## Prerequisites

-   **Docker**: The application is containerized and requires Docker to run.
-   **PostgreSQL**: A PostgreSQL database with the pgvector extension is required.
-   **Gemini API Key**: A Google Gemini API key is required for the LLM.

## Configuration

1.  **Create a `.env` file**: Copy the `.env.example` file to `.env`.
2.  **Set `DATABASE_URL`**: Set the `DATABASE_URL` to your PostgreSQL database.
3.  **Set `GEMINI_API_KEY`**: Set the `GEMINI_API_KEY` to your Gemini API key.

## Deployment

1.  **Build the Docker image**:
    ```bash
    docker build -t llm-chatbot .
    ```2.  **Run the Docker container**:
    ```bash
    docker run -p 7860:7860 -v ./.env:/app/.env llm-chatbot
    ```
3.  **Access the application**: Open your browser and go to `http://localhost:7860`.

## Local Development

For local development, you will need to have a PostgreSQL database running on your machine. You can then install the dependencies with `uv` and run the application with `python app.py`.

```bash
uv pip install
