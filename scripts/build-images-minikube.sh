#!/bin/bash

# Build script for Terrarium Docker images in Minikube environment
# Single platform build for Minikube compatibility

set -e

echo "Building Terrarium Docker images for Minikube..."

# Check if we're in Minikube environment
if ! docker info | grep -q "minikube"; then
    echo "Setting up Minikube Docker environment..."
    eval $(minikube docker-env)
fi

# Build CDP Client (single platform for Minikube)
echo "Building CDP Client image..."
docker build \
  --platform linux/amd64 \
  -t terrarium-cdp-client:latest \
  ./cdp-client

# Build Service Sink (single platform for Minikube)
echo "Building Service Sink image..."
docker build \
  --platform linux/amd64 \
  -t terrarium-service-sink:latest \
  ./service-sink

echo "All images built successfully in Minikube environment!"
echo ""
echo "Available images:"
docker images | grep terrarium

echo ""
echo "To deploy to Minikube:"
echo "   kubectl apply -k k8s/"
