FROM python:3.13-slim

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml .
RUN uv pip install --system fastapi uvicorn[standard] pydantic requests

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage && chown -R appuser:appgroup /app

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run the application
CMD ["python", "main.py"]
