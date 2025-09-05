#!/bin/bash

# Build script for Edge-Terrarium Docker images in K3s environment
# Single platform build for K3s compatibility

set -e

echo "Building Edge-Terrarium Docker images for K3s..."

# Check if we're in K3s environment
if ! docker info | grep -q "k3s"; then
    echo "Setting up K3s Docker environment..."
    # K3s uses containerd by default, but we can use docker if available
    echo "Note: K3s typically uses containerd, but docker images can be loaded manually"
fi

# Build CDP Client (single platform for K3s)
echo "Building CDP Client image..."
docker build \
  --platform linux/amd64 \
  -t edge-terrarium-cdp-client:latest \
  ./cdp-client

# Build Service Sink (single platform for K3s)
echo "Building Service Sink image..."
docker build \
  --platform linux/amd64 \
  -t edge-terrarium-service-sink:latest \
  ./service-sink

echo "All images built successfully in K3s environment!"
echo ""
echo "Available images:"
docker images | grep edge-terrarium

echo ""
echo "To deploy to K3s:"
echo "   kubectl apply -k configs/k3s/"
