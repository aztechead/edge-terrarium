#!/bin/bash

# =============================================================================
# CLEANUP OLD PODS SCRIPT
# =============================================================================
# This script ensures that only one pod of each type is running by cleaning up
# any old or duplicate pods that might be lingering from deployments or restarts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl >/dev/null 2>&1; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info >/dev/null 2>&1; then
    print_error "Not connected to a Kubernetes cluster"
    exit 1
fi

print_status "Cleaning up old pods in edge-terrarium namespace..."

# Function to cleanup old pods for a specific app
cleanup_app_pods() {
    local app_name=$1
    local namespace="edge-terrarium"
    
    print_status "Checking pods for app: $app_name"
    
    # Get all pods for this app
    local pods=$(kubectl get pods -n $namespace -l app=$app_name -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    
    if [ -z "$pods" ]; then
        print_warning "No pods found for app: $app_name"
        return 0
    fi
    
    # Count pods
    local pod_count=$(echo $pods | wc -w)
    print_status "Found $pod_count pod(s) for app: $app_name"
    
    if [ $pod_count -gt 1 ]; then
        print_warning "Multiple pods found for $app_name, keeping the newest one..."
        
        # Get the newest pod (by creation timestamp)
        local newest_pod=$(kubectl get pods -n $namespace -l app=$app_name -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | while read pod; do
            echo "$pod $(kubectl get pod -n $namespace $pod -o jsonpath='{.metadata.creationTimestamp}')"
        done | sort -k2 -r | head -1 | cut -d' ' -f1)
        
        print_status "Keeping newest pod: $newest_pod"
        
        # Delete all other pods
        for pod in $pods; do
            if [ "$pod" != "$newest_pod" ]; then
                print_status "Deleting old pod: $pod"
                kubectl delete pod -n $namespace $pod --grace-period=0 --force 2>/dev/null || true
            fi
        done
        
        print_success "Cleaned up old pods for $app_name"
    else
        print_success "Only one pod running for $app_name: $(echo $pods)"
    fi
}

# Cleanup pods for each app
cleanup_app_pods "custom-client"
cleanup_app_pods "service-sink"
cleanup_app_pods "vault"

# Wait for pods to be ready
print_status "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=custom-client -n edge-terrarium --timeout=60s 2>/dev/null || true
kubectl wait --for=condition=ready pod -l app=service-sink -n edge-terrarium --timeout=60s 2>/dev/null || true
kubectl wait --for=condition=ready pod -l app=vault -n edge-terrarium --timeout=60s 2>/dev/null || true

# Show final pod status
print_status "Final pod status:"
kubectl get pods -n edge-terrarium

print_success "Pod cleanup completed!"
