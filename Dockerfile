FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
COPY backend/requirements.txt backend/
COPY backend/pyproject.toml backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Health check - disable built-in healthcheck, Railway handles this
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD python -c "import requests; requests.get('http://localhost:${PORT:-8000}/healthz', timeout=5)" || exit 1

# Start the application - Railway will set PORT environment variable
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
