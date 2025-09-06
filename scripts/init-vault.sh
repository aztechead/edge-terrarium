#!/bin/bash

# =============================================================================
# VAULT INITIALIZATION SCRIPT
# =============================================================================
# This script initializes HashiCorp Vault with the necessary secrets and
# configuration for the Terrarium application. It sets up TLS certificates
# and mock secrets for the CDP client.
#
# Usage:
#   ./scripts/init-vault.sh [vault_url]
#
# Parameters:
#   vault_url - Optional Vault URL (default: http://localhost:8200)
#
# Prerequisites:
#   - Vault must be running and accessible
#   - curl must be installed
#   - TLS certificates must exist in certs/ directory
# =============================================================================

set -e  # Exit on any error

# Configuration
VAULT_URL="${1:-http://localhost:8200}"
VAULT_TOKEN="root"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

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
    
    local cert_file="$CERTS_DIR/edge-terrarium.crt"
    local key_file="$CERTS_DIR/edge-terrarium.key"
    
    if [ ! -f "$cert_file" ]; then
        log_warning "TLS certificate not found at $cert_file"
        log_info "Run './scripts/generate-tls-certs.sh' to generate certificates"
        return 1
    fi
    
    if [ ! -f "$key_file" ]; then
        log_warning "TLS private key not found at $key_file"
        log_info "Run './scripts/generate-tls-certs.sh' to generate certificates"
        return 1
    fi
    
    log_success "TLS certificates found"
    return 0
}

# Function to store TLS certificates in Vault
store_tls_certificates() {
    log_info "Storing TLS certificates in Vault..."
    
    local cert_file="$CERTS_DIR/edge-terrarium.crt"
    local key_file="$CERTS_DIR/edge-terrarium.key"
    
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

# Function to store CDP client configuration secrets
store_cdp_client_config() {
    log_info "Storing CDP client configuration secrets..."
    
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/secret/data/cdp-client/config" \
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
        log_success "CDP client configuration secrets stored"
        return 0
    else
        log_error "Failed to store CDP client configuration secrets (HTTP $http_code)"
        log_error "Response: ${response%???}"
        return 1
    fi
}

# Function to store CDP client external API secrets
store_cdp_client_external_apis() {
    log_info "Storing CDP client external API secrets..."
    
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -X POST \
        "$VAULT_URL/v1/secret/data/cdp-client/external-apis" \
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
        log_success "CDP client external API secrets stored"
        return 0
    else
        log_error "Failed to store CDP client external API secrets (HTTP $http_code)"
        log_error "Response: ${response%???}"
        return 1
    fi
}

# Function to list all secrets for verification
list_secrets() {
    log_info "Listing all secrets in Vault..."
    
    # List all secret paths (simplified without jq dependency)
    local response
    response=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_URL/v1/secret/metadata?list=true" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        log_success "Vault secrets are accessible"
    else
        log_warning "Could not list Vault secrets (jq not available)"
    fi
}

# Main execution
main() {
    echo "============================================================================="
    echo "VAULT INITIALIZATION SCRIPT"
    echo "============================================================================="
    echo "Vault URL: $VAULT_URL"
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
    
    # Store CDP client secrets
    if ! store_cdp_client_config; then
        log_error "Failed to store CDP client configuration secrets"
        exit 1
    fi
    
    if ! store_cdp_client_external_apis; then
        log_error "Failed to store CDP client external API secrets"
        exit 1
    fi
    
    # List all secrets for verification
    list_secrets
    
    log_success "Vault initialization completed successfully!"
    echo ""
    echo "You can now start the CDP client and it will retrieve secrets from Vault."
    echo "To test the setup, run:"
    echo "  docker-compose up cdp-client"
    echo ""
}

# Run main function
main "$@"
