#!/bin/bash
echo "Starting Railway deployment..."
echo "PORT: $PORT"
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"

# Start uvicorn with Railway's PORT
exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --log-level info
