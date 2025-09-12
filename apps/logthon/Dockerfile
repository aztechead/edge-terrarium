# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system fastapi uvicorn[standard] pydantic python-multipart websockets jinja2 python-dateutil httpx

# Copy application code
COPY main.py ./
COPY logthon/ ./logthon/

# Verify the logthon package is properly copied
RUN ls -la logthon/ && \
    test -f logthon/__init__.py && \
    test -f logthon/api.py && \
    test -f logthon/storage.py && \
    echo "✓ Logthon package structure verified"

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start the application
CMD ["python", "main.py"]
