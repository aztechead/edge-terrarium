#!/bin/bash

# =============================================================================
# ENHANCED VAULT INITIALIZATION SCRIPT
# =============================================================================
# This script initializes HashiCorp Vault with support for both static token
# and role-based authentication. It automatically generates UI access tokens
# and provides comprehensive setup for both Docker and K3s environments.
#
# Usage:
#   ./scripts/init-vault-enhanced.sh [vault_url] [mode]
#
# Parameters:
#   vault_url - Optional Vault URL (default: http://localhost:8200)
#   mode      - Authentication mode: "static", "rbac", or "both" (default: both)
#
# Prerequisites:
#   - Vault must be running and accessible
#   - curl must be installed
#   - For RBAC mode: kubectl must be configured and able to access the cluster
#   - TLS certificates must exist in certs/ directory
# =============================================================================

set -e  # Exit on any error

# Configuration
VAULT_URL="${1:-http://localhost:8200}"
AUTH_MODE="${2:-both}"
VAULT_TOKEN="root"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"
NAMESPACE="edge-terrarium"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_highlight() {
    echo -e "${PURPLE}[HIGHLIGHT]${NC} $1"
}

# Function to check if Vault is accessible
check_vault_health() {
    log_info "Checking Vault health at $VAULT_URL..."
    
    local health_response
    health_response=$(curl -s -w "%{http_code}" "$VAULT_URL/v1/sys/health" || echo "000")
    local http_code="${health_response: -3}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "503" ]; then
        log_success "Vault is accessible (HTTP $http_code)"
        return 0
    else
        log_error "Vault is not accessible (HTTP $http_code)"
        return 1
    fi
}

# Function to check if kubectl is available and cluster is accessible
check_kubectl() {
    log_info "Checking kubectl and cluster access..."
    
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl is not available - RBAC mode will be skipped"
        return 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_warning "Cannot access Kubernetes cluster - RBAC mode will be skipped"
        return 1
    fi
    
    log_success "kubectl is available and cluster is accessible"
    return 0
}

# Function to enable KV secrets engine
enable_kv_engine() {
    log_info "Enabling KV secrets engine..."
    
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/mounts/secret" \
        -d '{"type":"kv-v2","description":"KV secrets engine for Terrarium"}' || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "204" ] || [ "$http_code" = "400" ]; then
        log_success "KV secrets engine is enabled"
        return 0
    else
        log_error "Failed to enable KV secrets engine (HTTP $http_code)"
        return 1
    fi
}

# Function to check if TLS certificates exist
check_tls_certificates() {
    log_info "Checking for TLS certificates..."
    log_info "PROJECT_ROOT: $PROJECT_ROOT"
    log_info "CERTS_DIR: $CERTS_DIR"
    
    # Check multiple possible locations for certificates
    local cert_locations=(
        "/tmp/certs/tls.crt"
        "/tmp/certs/edge-terrarium.crt"
        "$CERTS_DIR/edge-terrarium.crt"
    )
    
    local key_locations=(
        "/tmp/certs/tls.key"
        "/tmp/certs/edge-terrarium.key"
        "$CERTS_DIR/edge-terrarium.key"
    )
    
    local cert_file=""
    local key_file=""
    
    # Debug: List what's actually in /tmp/certs/
    log_info "Contents of /tmp/certs/:"
    if [ -d "/tmp/certs" ]; then
        ls -la /tmp/certs/ || log_warning "Could not list /tmp/certs/"
    else
        log_warning "/tmp/certs/ directory does not exist"
    fi
    
    # Debug: List what's actually in the CERTS_DIR
    log_info "Contents of $CERTS_DIR:"
    if [ -d "$CERTS_DIR" ]; then
        ls -la "$CERTS_DIR/" || log_warning "Could not list $CERTS_DIR/"
    else
        log_warning "$CERTS_DIR directory does not exist"
    fi
    
    # Debug: List what's actually in the root directory
    log_info "Contents of root directory:"
    ls -la / || log_warning "Could not list root directory"
    
    # Find certificate file
    for location in "${cert_locations[@]}"; do
        log_info "Checking certificate location: $location"
        if [ -f "$location" ]; then
            cert_file="$location"
            log_success "Found certificate at: $location"
            break
        else
            log_info "Certificate not found at: $location"
        fi
    done
    
    # Find key file
    for location in "${key_locations[@]}"; do
        log_info "Checking key location: $location"
        if [ -f "$location" ]; then
            key_file="$location"
            log_success "Found key at: $location"
            break
        else
            log_info "Key not found at: $location"
        fi
    done
    
    if [ -z "$cert_file" ]; then
        log_warning "TLS certificate not found in any expected location"
        log_info "Checked locations: ${cert_locations[*]}"
        log_info "Run './scripts/generate-tls-certs.sh' to generate certificates"
        return 1
    fi
    
    if [ -z "$key_file" ]; then
        log_warning "TLS private key not found in any expected location"
        log_info "Checked locations: ${key_locations[*]}"
        log_info "Run './scripts/generate-tls-certs.sh' to generate certificates"
        return 1
    fi
    
    log_success "TLS certificates found at $cert_file and $key_file"
    
    # Set global variables for use in store_tls_certificates
    export FOUND_CERT_FILE="$cert_file"
    export FOUND_KEY_FILE="$key_file"
    
    return 0
}

# Function to store TLS certificates in Vault
store_tls_certificates() {
    log_info "Storing TLS certificates in Vault..."
    
    # Use the certificate files found by check_tls_certificates
    local cert_file="$FOUND_CERT_FILE"
    local key_file="$FOUND_KEY_FILE"
    
    if [ -z "$cert_file" ] || [ -z "$key_file" ]; then
        log_error "Certificate files not found. Run check_tls_certificates first."
        return 1
    fi
    
    log_info "Using certificate file: $cert_file"
    log_info "Using key file: $key_file"
    
    # Read and base64 encode the certificate
    local cert_b64
    cert_b64=$(base64 -w 0 < "$cert_file")
    
    # Read and base64 encode the private key
    local key_b64
    key_b64=$(base64 -w 0 < "$key_file")
    
    # Store the TLS secret
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/secret/data/terrarium/tls" \
        -d "{
            \"data\": {
                \"cert\": \"$cert_b64\",
                \"key\": \"$key_b64\",
                \"ca\": \"$cert_b64\"
            }
        }" || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        log_success "TLS certificates stored in Vault"
        return 0
    else
        log_error "Failed to store TLS certificates (HTTP $http_code)"
        log_error "Response: ${response%???}"
        return 1
    fi
}

# Function to store Custom client configuration secrets
store_custom_client_config() {
    log_info "Storing Custom client configuration secrets..."
    
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/secret/data/custom-client/config" \
        -d '{
            "data": {
                "api_key": "mock-api-key-12345",
                "database_url": "postgresql://mock-user:mock-pass@mock-db:5432/mock-db",
                "jwt_secret": "mock-jwt-secret-67890",
                "encryption_key": "mock-encryption-key-abcdef",
                "log_level": "INFO",
                "max_connections": "100"
            }
        }' || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        log_success "Custom client configuration secrets stored"
        return 0
    else
        log_error "Failed to store Custom client configuration secrets (HTTP $http_code)"
        log_error "Response: ${response%???}"
        return 1
    fi
}

# Function to store Custom client external API secrets
store_custom_client_external_apis() {
    log_info "Storing Custom client external API secrets..."
    
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/secret/data/custom-client/external-apis" \
        -d '{
            "data": {
                "provider_auth_token": "mock-provider-token-xyz",
                "webhook_secret": "mock-webhook-secret-123",
                "rate_limit": "1000",
                "timeout_seconds": "30"
            }
        }' || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        log_success "Custom client external API secrets stored"
        return 0
    else
        log_error "Failed to store Custom client external API secrets (HTTP $http_code)"
        log_error "Response: ${response%???}"
        return 1
    fi
}

# Function to create Vault policies for RBAC
create_policies() {
    log_info "Creating Vault policies for RBAC..."
    
    # Custom Client Policy
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/custom-client-policy" \
        -d '{
            "policy": "path \"secret/data/custom-client/*\" { capabilities = [\"read\"] }\npath \"secret/data/terrarium/tls\" { capabilities = [\"read\"] }\npath \"secret/metadata/custom-client/*\" { capabilities = [\"list\"] }"
        }' > /dev/null
    
    # Service Sink Policy
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/service-sink-policy" \
        -d '{
            "policy": "path \"secret/data/service-sink/*\" { capabilities = [\"read\"] }"
        }' > /dev/null
    
    # Logthon Policy
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/logthon-policy" \
        -d '{
            "policy": "path \"secret/data/logthon/*\" { capabilities = [\"read\"] }\npath \"secret/data/shared/logging/*\" { capabilities = [\"read\"] }\npath \"secret/metadata/logthon/*\" { capabilities = [\"list\"] }"
        }' > /dev/null
    
    # File Storage Policy
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/file-storage-policy" \
        -d '{
            "policy": "path \"secret/data/file-storage/*\" { capabilities = [\"read\"] }\npath \"secret/data/shared/storage/*\" { capabilities = [\"read\"] }\npath \"secret/metadata/file-storage/*\" { capabilities = [\"list\"] }"
        }' > /dev/null
    
    # Admin Policy
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/admin-policy" \
        -d '{
            "policy": "path \"secret/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"] }\npath \"auth/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\", \"sudo\"] }\npath \"sys/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\", \"sudo\"] }"
        }' > /dev/null
    
    log_success "Vault policies created successfully"
}

# Function to enable Kubernetes auth method
enable_kubernetes_auth() {
    log_info "Enabling Kubernetes auth method..."
    
    # Get the Kubernetes service account token for Vault
    local vault_token
    vault_token=$(kubectl get secret -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.annotations.kubernetes\.io/service-account\.name=="vault-admin-sa")].data.token}' | base64 -d 2>/dev/null || echo "")
    
    if [ -z "$vault_token" ]; then
        log_warning "Could not retrieve Vault service account token - using default token"
        vault_token=$(kubectl get secret -n $NAMESPACE -o jsonpath='{.items[0].data.token}' | base64 -d 2>/dev/null || echo "")
    fi
    
    if [ -z "$vault_token" ]; then
        log_error "Could not retrieve any Kubernetes service account token"
        return 1
    fi
    
    # Get the Kubernetes API server address
    local k8s_host
    k8s_host=$(kubectl config view --raw -o jsonpath='{.clusters[0].cluster.server}')
    
    # Enable Kubernetes auth method
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/auth/kubernetes" \
        -d "{
            \"type\": \"kubernetes\",
            \"description\": \"Kubernetes auth method for Terrarium\"
        }" || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "204" ]; then
        log_success "Kubernetes auth method enabled"
    else
        log_error "Failed to enable Kubernetes auth method (HTTP $http_code)"
        return 1
    fi
    
    # Configure Kubernetes auth method
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/config" \
        -d "{
            \"token_reviewer_jwt\": \"$vault_token\",
            \"kubernetes_host\": \"$k8s_host\",
            \"kubernetes_ca_cert\": \"\"
        }" || echo "000")
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "204" ]; then
        log_success "Kubernetes auth method configured"
        return 0
    else
        log_error "Failed to configure Kubernetes auth method (HTTP $http_code)"
        return 1
    fi
}

# Function to create Vault roles
create_roles() {
    log_info "Creating Vault roles..."
    
    # Custom Client Role
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/role/custom-client-role" \
        -d "{
            \"bound_service_account_names\": [\"custom-client-sa\"],
            \"bound_service_account_namespaces\": [\"$NAMESPACE\"],
            \"policies\": [\"custom-client-policy\"],
            \"ttl\": \"24h\"
        }" > /dev/null
    
    # Service Sink Role
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/role/service-sink-role" \
        -d "{
            \"bound_service_account_names\": [\"service-sink-sa\"],
            \"bound_service_account_namespaces\": [\"$NAMESPACE\"],
            \"policies\": [\"service-sink-policy\"],
            \"ttl\": \"24h\"
        }" > /dev/null
    
    # Logthon Role
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/role/logthon-role" \
        -d "{
            \"bound_service_account_names\": [\"logthon-sa\"],
            \"bound_service_account_namespaces\": [\"$NAMESPACE\"],
            \"policies\": [\"logthon-policy\"],
            \"ttl\": \"24h\"
        }" > /dev/null
    
    # File Storage Role
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/role/file-storage-role" \
        -d "{
            \"bound_service_account_names\": [\"file-storage-sa\"],
            \"bound_service_account_namespaces\": [\"$NAMESPACE\"],
            \"policies\": [\"file-storage-policy\"],
            \"ttl\": \"24h\"
        }" > /dev/null
    
    # Admin Role
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/kubernetes/role/admin-role" \
        -d "{
            \"bound_service_account_names\": [\"vault-admin-sa\"],
            \"bound_service_account_namespaces\": [\"$NAMESPACE\"],
            \"policies\": [\"admin-policy\"],
            \"ttl\": \"1h\"
        }" > /dev/null
    
    log_success "Vault roles created successfully"
}

# Function to create UI access token
create_ui_token() {
    log_info "Creating UI access token..."
    
    # First, ensure the admin policy exists (create it if it doesn't)
    curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/sys/policies/acl/admin-policy" \
        -d '{
            "policy": "path \"*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\", \"sudo\"] }"
        }' > /dev/null
    
    local response
    response=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/auth/token/create" \
        -d '{
            "policies": ["admin-policy"],
            "ttl": "24h",
            "display_name": "UI Access Token",
            "meta": {
                "purpose": "Vault UI access",
                "created_by": "init-vault-enhanced.sh"
            }
        }')
    
    if echo "$response" | grep -q "client_token"; then
        local ui_token
        ui_token=$(echo "$response" | grep -o '"client_token":"[^"]*"' | cut -d'"' -f4)
        log_success "UI access token created successfully"
        echo "$ui_token"
        return 0
    else
        log_error "Failed to create UI access token"
        log_error "Response: $response"
        return 1
    fi
}

# Function to test role-based authentication
test_rbac() {
    log_info "Testing role-based authentication..."
    
    # Get a token for custom-client-sa
    local custom_client_token
    custom_client_token=$(kubectl get secret -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.annotations.kubernetes\.io/service-account\.name=="custom-client-sa")].data.token}' | base64 -d 2>/dev/null || echo "")
    
    if [ -z "$custom_client_token" ]; then
        log_warning "Could not retrieve custom-client service account token for testing"
        return 0
    fi
    
    # Test authentication with Kubernetes auth
    local auth_response
    auth_response=$(curl -s -X POST \
        "$VAULT_URL/v1/auth/kubernetes/login" \
        -d "{
            \"role\": \"custom-client-role\",
            \"jwt\": \"$custom_client_token\"
        }")
    
    if echo "$auth_response" | grep -q "auth"; then
        log_success "Role-based authentication test passed"
        
        # Extract the client token
        local client_token
        client_token=$(echo "$auth_response" | grep -o '"client_token":"[^"]*"' | cut -d'"' -f4)
        
        # Test secret access
        local secret_response
        secret_response=$(curl -s -H "X-Vault-Token: $client_token" \
            "$VAULT_URL/v1/secret/data/custom-client/config")
        
        if echo "$secret_response" | grep -q "api_key"; then
            log_success "Secret access test passed"
        else
            log_warning "Secret access test failed"
        fi
    else
        log_warning "Role-based authentication test failed"
    fi
}

# Function to display access information
display_access_info() {
    local ui_token="$1"
    
    echo ""
    echo "============================================================================="
    echo "VAULT ACCESS INFORMATION"
    echo "============================================================================="
    echo "Vault URL: $VAULT_URL"
    echo "Root Token: $VAULT_TOKEN"
    echo ""
    
    if [ -n "$ui_token" ]; then
        echo "UI Access Token: $ui_token"
        echo ""
        echo "Vault UI Access:"
        echo "  URL: $VAULT_URL/ui"
        echo "  Token: $ui_token"
        echo ""
    fi
    
    echo "API Access:"
    echo "  URL: $VAULT_URL/v1/"
    echo "  Token: $VAULT_TOKEN"
    echo ""
    
    if [ "$AUTH_MODE" = "rbac" ] || [ "$AUTH_MODE" = "both" ]; then
        echo "RBAC Authentication:"
        echo "  - Applications use Service Account tokens"
        echo "  - No static tokens in environment variables"
        echo "  - Automatic token rotation"
        echo ""
    fi
    
    echo "Available Secrets:"
    echo "  - custom-client/config"
    echo "  - custom-client/external-apis"
    echo "  - terrarium/tls"
    echo ""
    echo "============================================================================="
}

# Main execution
main() {
    echo "============================================================================="
    echo "ENHANCED VAULT INITIALIZATION SCRIPT"
    echo "============================================================================="
    echo "Vault URL: $VAULT_URL"
    echo "Auth Mode: $AUTH_MODE"
    echo "Vault Token: $VAULT_TOKEN"
    echo "Project Root: $PROJECT_ROOT"
    echo "============================================================================="
    echo ""
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v base64 &> /dev/null; then
        log_error "base64 is required but not installed"
        exit 1
    fi
    
    # Check Vault health
    if ! check_vault_health; then
        log_error "Cannot proceed without a healthy Vault instance"
        log_info "Make sure Vault is running and accessible at $VAULT_URL"
        exit 1
    fi
    
    # Enable KV secrets engine
    if ! enable_kv_engine; then
        log_error "Failed to enable KV secrets engine"
        exit 1
    fi
    
    # Check and store TLS certificates
    if check_tls_certificates; then
        if ! store_tls_certificates; then
            log_error "Failed to store TLS certificates"
            exit 1
        fi
    else
        log_warning "Skipping TLS certificate storage"
    fi
    
    # Store Custom client secrets
    if ! store_custom_client_config; then
        log_error "Failed to store Custom client configuration secrets"
        exit 1
    fi
    
    if ! store_custom_client_external_apis; then
        log_error "Failed to store Custom client external API secrets"
        exit 1
    fi
    
    # Handle RBAC setup if requested
    local ui_token=""
    if [ "$AUTH_MODE" = "rbac" ] || [ "$AUTH_MODE" = "both" ]; then
        if check_kubectl; then
            log_info "Setting up RBAC authentication..."
            
            if ! create_policies; then
                log_error "Failed to create Vault policies"
                exit 1
            fi
            
            if ! enable_kubernetes_auth; then
                log_error "Failed to enable Kubernetes auth method"
                exit 1
            fi
            
            if ! create_roles; then
                log_error "Failed to create Vault roles"
                exit 1
            fi
            
            # Test the setup
            test_rbac
            
            log_success "RBAC authentication setup completed"
        else
            log_warning "Skipping RBAC setup - kubectl not available"
        fi
    fi
    
    # Create UI access token (always create for UI access)
    ui_token=$(create_ui_token)
    
    # Display access information
    display_access_info "$ui_token"
    
    log_success "Vault initialization completed successfully!"
    echo ""
    echo "Your applications can now retrieve secrets from Vault."
    echo "To test the setup, run:"
    echo "  ./scripts/test.sh"
    echo ""
}

# Run main function
main "$@"
