# Base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LLM_PROVIDER="openai" # Example: Gemini API or OpenAI

# Install system dependencies for ReportLab (or other libs)
# RUN apt-get update && apt-get install -y \
#     libfreetype6-dev \
#     libpng-dev \
#     # Clean up
#     && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application (using Uvicorn for production-ready ASGI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]