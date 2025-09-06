#!/bin/bash

# Build script for Terrarium Docker images
# Auto-detects platform and builds for appropriate architecture

set -e

echo "Building Terrarium Docker images..."

# Detect host architecture
HOST_ARCH=$(uname -m)
case $HOST_ARCH in
    x86_64)
        PLATFORM="linux/amd64"
        echo "Detected AMD64 architecture, building for linux/amd64"
        ;;
    arm64|aarch64)
        PLATFORM="linux/arm64"
        echo "Detected ARM64 architecture, building for linux/arm64"
        ;;
    *)
        echo "Warning: Unknown architecture $HOST_ARCH, defaulting to linux/amd64"
        PLATFORM="linux/amd64"
        ;;
esac

# Build CDP Client
echo "Building CDP Client image for $PLATFORM..."
docker build \
  --no-cache \
  --platform $PLATFORM \
  -t edge-terrarium-cdp-client:latest \
  ./cdp-client

if [ $? -ne 0 ]; then
    echo "Error: Failed to build CDP Client image"
    exit 1
fi

# Build Service Sink
echo "Building Service Sink image for $PLATFORM..."
docker build \
  --no-cache \
  --platform $PLATFORM \
  -t edge-terrarium-service-sink:latest \
  ./service-sink

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Service Sink image"
    exit 1
fi

# Build Logthon
echo "Building Logthon image for $PLATFORM..."
docker build \
  --no-cache \
  --platform $PLATFORM \
  -t edge-terrarium-logthon:latest \
  ./logthon

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Logthon image"
    exit 1
fi

echo "All images built successfully!"
echo ""
echo "Available images:"
docker images | grep edge-terrarium

echo ""
echo "To deploy with Docker Compose:"
echo "   ./scripts/deploy.sh docker deploy"
echo ""
echo "To deploy to K3s:"
echo "   ./scripts/deploy.sh k3s deploy"
