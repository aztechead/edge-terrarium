# Multi-stage build for Service Sink
FROM --platform=$BUILDPLATFORM alpine:3.18 AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev curl-dev json-c-dev

# Set working directory
WORKDIR /app

# Copy source code
COPY main.c .

# Compile the application
RUN gcc -o service-sink main.c -lcurl -ljson-c

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
COPY --from=builder /app/service-sink .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD nc -z localhost 8080 || exit 1

# Run the application
CMD ["./service-sink"]
