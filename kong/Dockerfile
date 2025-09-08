# =============================================================================
# KONG GATEWAY WITH TLS CERTIFICATES
# =============================================================================
# Simple Dockerfile that extends the official Kong image and includes
# the TLS certificates directly in the image to avoid volume mount issues.
# =============================================================================

FROM kong:latest

# Switch to root to set permissions
USER root

# Copy TLS certificates to a location Kong can access
COPY ../certs/edge-terrarium.crt /tmp/edge-terrarium.crt
COPY ../certs/edge-terrarium.key /tmp/edge-terrarium.key

# Set proper permissions
RUN chmod 644 /tmp/edge-terrarium.crt && \
    chmod 600 /tmp/edge-terrarium.key && \
    chown kong:kong /tmp/edge-terrarium.crt && \
    chown kong:kong /tmp/edge-terrarium.key

# Switch back to kong user
USER kong
