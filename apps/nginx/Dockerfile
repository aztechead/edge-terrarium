# NGINX Gateway Dockerfile
FROM nginx:1.25-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Create nginx user and group (already exists in nginx image)
# nginx user is UID 101, GID 101

# Configuration files will be mounted as volumes from the generated configs
# No need to copy them here

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/nginx-health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
