#!/bin/bash

# =============================================================================
# K3S TLS SECRET CREATION SCRIPT
# =============================================================================
# This script generates TLS certificates and creates a Kubernetes secret
# for use in K3s deployments. It ensures the certificates are available
# for both Kong Gateway and Vault initialization.
#
# Usage:
#   ./scripts/create-k3s-tls-secret.sh
#
# Prerequisites:
#   - kubectl must be installed and configured
#   - K3s cluster must be running
#   - edge-terrarium namespace must exist
#
# Output:
#   - certs/edge-terrarium.crt (TLS certificate)
#   - certs/edge-terrarium.key (TLS private key)
#   - Kubernetes secret: edge-terrarium-tls in edge-terrarium namespace
# =============================================================================

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"
SECRET_NAME="edge-terrarium-tls"
NAMESPACE="edge-terrarium"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed"
        exit 1
    fi
    
    # Check if K3s cluster is accessible
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "K3s cluster is not accessible"
        log_info "Make sure K3s is running and kubectl is configured"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_warning "Namespace '$NAMESPACE' does not exist. Creating it..."
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace '$NAMESPACE' created"
    fi
    
    log_success "Prerequisites check passed"
}

# Function to generate TLS certificates
generate_tls_certificates() {
    log_info "Generating TLS certificates..."
    
    # Check if certificates already exist
    if [ -f "$CERTS_DIR/edge-terrarium.crt" ] && [ -f "$CERTS_DIR/edge-terrarium.key" ]; then
        log_info "TLS certificates already exist. Using existing certificates."
    else
        log_info "TLS certificates not found. Generating new certificates..."
        "$SCRIPT_DIR/generate-tls-certs.sh"
    fi
    
    log_success "TLS certificates are ready"
}

# Function to create Kubernetes secret
create_k8s_secret() {
    log_info "Creating Kubernetes TLS secret..."
    
    # Check if secret already exists
    if kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
        log_warning "Secret '$SECRET_NAME' already exists in namespace '$NAMESPACE'"
        log_info "Recreating secret automatically..."
        kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" >/dev/null 2>&1
    fi
    
    # Create the secret from certificate files
    log_info "Creating secret from certificate files..."
    kubectl create secret tls "$SECRET_NAME" \
        --cert="$CERTS_DIR/edge-terrarium.crt" \
        --key="$CERTS_DIR/edge-terrarium.key" \
        -n "$NAMESPACE"
    
    log_success "Kubernetes TLS secret created successfully"
}

# Function to verify the secret
verify_secret() {
    log_info "Verifying the created secret..."
    
    # Check if secret exists
    if ! kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Secret '$SECRET_NAME' was not created"
        return 1
    fi
    
    # Display secret information
    log_info "Secret details:"
    kubectl describe secret "$SECRET_NAME" -n "$NAMESPACE"
    
    # Verify certificate data
    log_info "Certificate data verification:"
    local cert_data
    cert_data=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.tls\.crt}' | base64 -d)
    echo "$cert_data" | openssl x509 -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)" || true
    
    log_success "Secret verification completed"
}

# Function to display next steps
display_next_steps() {
    echo ""
    echo "============================================================================="
    echo "K3S TLS SECRET CREATION COMPLETED"
    echo "============================================================================="
    echo "Secret Name: $SECRET_NAME"
    echo "Namespace: $NAMESPACE"
    echo "Certificate: $CERTS_DIR/edge-terrarium.crt"
    echo "Private Key: $CERTS_DIR/edge-terrarium.key"
    echo ""
    echo "Next Steps:"
    echo "  1. The secret is ready for use in K3s deployments"
    echo "  2. Vault initialization will load these certificates into Vault"
    echo "  3. Kong Gateway will use these certificates for HTTPS"
    echo "  4. Deploy the application with: ./scripts/deploy.sh k3s deploy"
    echo ""
    echo "To verify the secret:"
    echo "  kubectl get secret $SECRET_NAME -n $NAMESPACE"
    echo "  kubectl describe secret $SECRET_NAME -n $NAMESPACE"
    echo "============================================================================="
}

# Main execution
main() {
    echo "============================================================================="
    echo "K3S TLS SECRET CREATION"
    echo "============================================================================="
    echo "Project Root: $PROJECT_ROOT"
    echo "Certificates Directory: $CERTS_DIR"
    echo "Secret Name: $SECRET_NAME"
    echo "Namespace: $NAMESPACE"
    echo "============================================================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Generate TLS certificates
    generate_tls_certificates
    
    # Create Kubernetes secret
    create_k8s_secret
    
    # Verify the secret
    verify_secret
    
    # Display next steps
    display_next_steps
    
    log_success "K3s TLS secret creation completed successfully!"
}

# Run main function
main "$@"
