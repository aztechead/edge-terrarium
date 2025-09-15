# Vault Dockerfile
# Uses the official HashiCorp Vault image
FROM hashicorp/vault:latest

# The official Vault image already has a vault user, so we don't need to create one
# Just expose the port and set up health check

# Expose port
EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD vault status || exit 1

# Default command (can be overridden)
CMD ["vault", "server", "-dev", "-dev-root-token-id=root", "-dev-listen-address=0.0.0.0:8200"]
