# LLM File-Based Chatbot

This project is a file-based chatbot that uses a Large Language Model (LLM) to answer questions about uploaded documents. It is built with a Python FastAPI backend and a separate ultra-retro HTML/CSS/JS frontend, using a PostgreSQL database with pgvector for vector storage.

![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/mxngjxa/HackRPI-2025-Wurst?utm_source=oss&utm_medium=github&utm_campaign=mxngjxa%2FHackRPI-2025-Wurst&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
[![FastAPI](https://img.shields.io/badge/FastAPI-009485.svg?logo=fastapi&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)


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
    docker run -p 8000:8000 -v ./.env:/app/.env llm-chatbot
    ```
3.  **Access the Application**: The FastAPI server will be running at `http://localhost:8000`, which also serves the frontend.

## Local Development

For local development, you will need to have a PostgreSQL database running on your machine. You can then install the dependencies with `uv` and run the backend API with `python main.py`. The frontend is a set of static files in the `frontend/` directory.

```bash
uv sync
```

### Running the Backend API

```bash
uv run main.py
```

The API will run on `http://127.0.0.1:8000`.

