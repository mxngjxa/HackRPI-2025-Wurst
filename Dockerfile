# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv for dependency management
RUN pip install uv

# Copy dependency files and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uv", "run", "main.py"]