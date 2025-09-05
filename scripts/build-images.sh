#!/bin/bash

# Build script for Terrarium Docker images
# Supports both AMD64 and ARM64 architectures

set -e

echo "Building Terrarium Docker images..."

# Build CDP Client
echo "Building CDP Client image..."
docker build \
  --platform linux/amd64,linux/arm64 \
  -t terrarium-cdp-client:latest \
  ./cdp-client

# Build Service Sink
echo "Building Service Sink image..."
docker build \
  --platform linux/amd64,linux/arm64 \
  -t terrarium-service-sink:latest \
  ./service-sink

echo "All images built successfully!"
echo ""
echo "Available images:"
docker images | grep terrarium

echo ""
echo "To deploy with Docker Compose:"
echo "   ./scripts/deploy.sh docker deploy"
echo ""
echo "To deploy to Minikube:"
echo "   ./scripts/deploy.sh minikube deploy"
