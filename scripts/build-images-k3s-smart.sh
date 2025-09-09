#!/bin/bash

# Smart build script for Edge-Terrarium Docker images in K3s environment
# Only rebuilds images if source files have changed since last build

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "Building Edge-Terrarium Docker images for K3s with smart caching..."

# Detect host architecture
HOST_ARCH=$(uname -m)
case $HOST_ARCH in
    x86_64)
        PLATFORM="linux/amd64"
        print_status "Detected AMD64 architecture, building for linux/amd64"
        ;;
    arm64|aarch64)
        PLATFORM="linux/arm64"
        print_status "Detected ARM64 architecture, building for linux/arm64"
        ;;
    *)
        print_warning "Unknown architecture $HOST_ARCH, defaulting to linux/amd64"
        PLATFORM="linux/amd64"
        ;;
esac

# Check if we're in K3s environment
if ! docker info | grep -q "k3s"; then
    print_status "Setting up K3s Docker environment..."
    print_status "Note: K3s typically uses containerd, but docker images can be loaded manually"
fi

# Function to check if image needs rebuilding
needs_rebuild() {
    local image_name=$1
    local build_context=$2
    
    # Check if image exists
    if ! docker image inspect "$image_name" >/dev/null 2>&1; then
        print_status "Image $image_name does not exist, will build"
        return 0
    fi
    
    # Get image creation time
    local image_time=$(docker image inspect "$image_name" --format='{{.Created}}' 2>/dev/null || echo "1970-01-01T00:00:00Z")
    local image_timestamp=$(date -d "$image_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${image_time%.*}" +%s 2>/dev/null || echo 0)
    
    # Find the most recent file in build context
    local latest_file_time=0
    if [ -d "$build_context" ]; then
        # Use find to get the most recent modification time
        if command -v gfind >/dev/null 2>&1; then
            # GNU find (Linux)
            latest_file_time=$(gfind "$build_context" -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1)
        else
            # BSD find (macOS) - use stat
            latest_file_time=$(find "$build_context" -type f -exec stat -f %m {} \; 2>/dev/null | sort -n | tail -1)
        fi
    fi
    
    # Compare timestamps
    if [ "$latest_file_time" -gt "$image_timestamp" ]; then
        print_status "Source files in $build_context have changed since last build, will rebuild $image_name"
        return 0
    else
        print_success "No changes detected in $build_context, using cached image $image_name"
        return 1
    fi
}

# Function to build image with smart caching
build_image() {
    local image_name=$1
    local build_context=$2
    local dockerfile_path=${3:-"$build_context/Dockerfile"}
    
    if needs_rebuild "$image_name" "$build_context"; then
        print_status "Building $image_name..."
        docker build \
            --platform $PLATFORM \
            -t "$image_name" \
            -f "$dockerfile_path" \
            "$build_context"
        
        if [ $? -ne 0 ]; then
            print_error "Failed to build $image_name"
            exit 1
        fi
        print_success "Successfully built $image_name"
    fi
}

# Build Custom Client (platform-specific for K3s)
build_image "edge-terrarium-custom-client:latest" "./custom-client"

# Build Service Sink (platform-specific for K3s)
build_image "edge-terrarium-service-sink:latest" "./service-sink"

# Build Logthon (platform-specific for K3s)
build_image "edge-terrarium-logthon:latest" "./logthon"

# Build File Storage (platform-specific for K3s)
build_image "edge-terrarium-file-storage:latest" "./file-storage"

# Build Kong Gateway (platform-specific for K3s)
build_image "edge-terrarium-kong:latest" "." "./kong/Dockerfile"
# Also tag with version for K3s compatibility
docker tag edge-terrarium-kong:latest edge-terrarium-kong:0.0.1

# Verify Logthon image has the required package structure and dependencies
print_status "Verifying Logthon image structure and dependencies..."
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
    print_error "Logthon image verification failed"
    exit 1
fi

print_success "All images built successfully in K3s environment!"
echo ""
echo "Available images:"
docker images | grep edge-terrarium

echo ""
echo "To deploy to K3s:"
echo "   kubectl apply -k configs/k3s/"
