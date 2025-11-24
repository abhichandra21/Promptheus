# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock README.md ./

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

COPY src/ ./src/

# Install dependencies with poetry (no dev dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/

# Set PYTHONPATH so Python can find the promptheus module
ENV PYTHONPATH=/app/src

# Create directory for history persistence
RUN mkdir -p /root/.promptheus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the web server
CMD ["uvicorn", "promptheus.web.server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]