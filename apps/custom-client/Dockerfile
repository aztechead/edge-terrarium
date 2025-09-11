# Multi-stage build for Custom Client
FROM alpine:3.18 AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev curl-dev json-c-dev

# Set working directory
WORKDIR /app

# Copy source code
COPY src/ ./src/

# Compile the application with curl, json-c, and pthread libraries
RUN gcc -o custom-client src/*.c -lcurl -ljson-c -lpthread

# Final stage
FROM alpine:3.18

# Install runtime dependencies
RUN apk add --no-cache ca-certificates curl json-c

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/custom-client .

# Create requests directory with proper permissions
RUN mkdir -p /tmp/requests && \
    chown -R appuser:appgroup /tmp/requests && \
    chmod 755 /tmp/requests

# Create wait script
RUN echo '#!/bin/sh' > /app/wait-for-vault.sh && \
    echo 'echo "Waiting for Vault to be ready..."' >> /app/wait-for-vault.sh && \
    echo 'until curl -s http://vault:8200/v1/sys/health > /dev/null; do' >> /app/wait-for-vault.sh && \
    echo '  echo "Vault is not ready yet. Waiting..."' >> /app/wait-for-vault.sh && \
    echo '  sleep 2' >> /app/wait-for-vault.sh && \
    echo 'done' >> /app/wait-for-vault.sh && \
    echo 'echo "Vault is ready! Waiting for initialization..."' >> /app/wait-for-vault.sh && \
    echo 'until curl -s -H "X-Vault-Token: root" http://vault:8200/v1/secret/data/custom-client/config > /dev/null; do' >> /app/wait-for-vault.sh && \
    echo '  echo "Vault initialization not complete yet. Waiting..."' >> /app/wait-for-vault.sh && \
    echo '  sleep 2' >> /app/wait-for-vault.sh && \
    echo 'done' >> /app/wait-for-vault.sh && \
    echo 'echo "Vault initialization complete! Waiting a moment for secrets to be fully available..."' >> /app/wait-for-vault.sh && \
    echo 'sleep 5' >> /app/wait-for-vault.sh && \
    echo 'echo "Starting Custom client..."' >> /app/wait-for-vault.sh && \
    echo 'exec ./custom-client' >> /app/wait-for-vault.sh && \
    chmod +x /app/wait-for-vault.sh && \
    chown appuser:appgroup /app/wait-for-vault.sh

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 443 1337

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD nc -z localhost 1337 || exit 1

# Run the wait script which will start the application
CMD ["/app/wait-for-vault.sh"]
