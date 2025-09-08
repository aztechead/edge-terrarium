#!/bin/bash

# Build script for Edge-Terrarium Docker images in K3s environment
# Auto-detects platform and builds for appropriate architecture

set -e

echo "Building Edge-Terrarium Docker images for K3s..."

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

# Check if we're in K3s environment
if ! docker info | grep -q "k3s"; then
    echo "Setting up K3s Docker environment..."
    # K3s uses containerd by default, but we can use docker if available
    echo "Note: K3s typically uses containerd, but docker images can be loaded manually"
fi

# Build Custom Client (platform-specific for K3s)
echo "Building Custom Client image for $PLATFORM..."
docker build \
  --no-cache \
  --platform $PLATFORM \
  -t edge-terrarium-custom-client:latest \
  ./custom-client

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Custom Client image"
    exit 1
fi

# Build Service Sink (platform-specific for K3s)
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

# Build Logthon (platform-specific for K3s)
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

# Build File Storage (platform-specific for K3s)
echo "Building File Storage image for $PLATFORM..."
docker build \
  --no-cache \
  --platform $PLATFORM \
  -t edge-terrarium-file-storage:latest \
  ./file-storage

if [ $? -ne 0 ]; then
    echo "Error: Failed to build File Storage image"
    exit 1
fi

# Verify Logthon image has the required package structure and dependencies
echo "Verifying Logthon image structure and dependencies..."
docker run --rm edge-terrarium-logthon:latest sh -c "
    if [ -d 'logthon' ] && [ -f 'logthon/__init__.py' ] && [ -f 'logthon/api.py' ] && [ -f 'logthon/storage.py' ]; then
        echo '✓ Logthon package structure verified in image'
    else
        echo '✗ Logthon package structure missing in image'
        exit 1
    fi
    
    if python -c 'import httpx' 2>/dev/null; then
        echo '✓ httpx dependency verified in image'
    else
        echo '✗ httpx dependency missing in image'
        exit 1
    fi
"

if [ $? -ne 0 ]; then
    echo "Error: Logthon image verification failed"
    exit 1
fi

echo "All images built successfully in K3s environment!"
echo ""
echo "Available images:"
docker images | grep edge-terrarium

echo ""
echo "To deploy to K3s:"
echo "   kubectl apply -k configs/k3s/"
