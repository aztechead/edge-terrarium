#!/bin/bash

# =============================================================================
# DYNAMIC TLS CERTIFICATE GENERATION SCRIPT
# =============================================================================
# This script dynamically generates TLS certificates for the Edge Terrarium project.
# It creates self-signed certificates that are suitable for development and testing.
#
# Usage:
#   ./scripts/generate-tls-certs.sh
#
# Output:
#   - certs/edge-terrarium.crt (TLS certificate)
#   - certs/edge-terrarium.key (TLS private key)
#
# Prerequisites:
#   - openssl must be installed
#   - certs/ directory must exist
# =============================================================================

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

# Certificate configuration
CERT_NAME="edge-terrarium"
CERT_FILE="$CERTS_DIR/$CERT_NAME.crt"
KEY_FILE="$CERTS_DIR/$CERT_NAME.key"
DAYS_VALID=365

# Subject information for the certificate
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORGANIZATION="Edge Terrarium"
ORGANIZATIONAL_UNIT="Development"
COMMON_NAME="edge-terrarium.local"
EMAIL="admin@edge-terrarium.local"

# Subject Alternative Names (SANs) for the certificate
SAN_DNS="DNS:edge-terrarium.local,DNS:localhost,DNS:*.edge-terrarium.local"
SAN_IP="IP:127.0.0.1,IP:0.0.0.0"

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
    
    # Check if openssl is installed
    if ! command -v openssl &> /dev/null; then
        log_error "openssl is required but not installed"
        log_info "Please install openssl:"
        log_info "  - macOS: brew install openssl"
        log_info "  - Ubuntu/Debian: sudo apt-get install openssl"
        log_info "  - CentOS/RHEL: sudo yum install openssl"
        exit 1
    fi
    
    # Check if certs directory exists
    if [ ! -d "$CERTS_DIR" ]; then
        log_info "Creating certs directory: $CERTS_DIR"
        mkdir -p "$CERTS_DIR"
    fi
    
    log_success "Prerequisites check passed"
}

# Function to check if certificates already exist
check_existing_certificates() {
    log_info "Checking for existing certificates..."
    
    if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
        log_warning "TLS certificates already exist:"
        log_warning "  Certificate: $CERT_FILE"
        log_warning "  Private Key: $KEY_FILE"
        
        # Check certificate expiration
        if command -v openssl &> /dev/null; then
            local expiry_date
            expiry_date=$(openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2)
            if [ -n "$expiry_date" ]; then
                log_info "Certificate expires: $expiry_date"
            fi
        fi
        
        echo ""
        read -p "Do you want to regenerate the certificates? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Using existing certificates"
            return 1
        fi
    fi
    
    return 0
}

# Function to generate TLS certificate
generate_tls_certificate() {
    log_info "Generating TLS certificate and private key..."
    
    # Create a temporary configuration file for openssl
    local config_file
    config_file=$(mktemp)
    
    cat > "$config_file" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=$ORGANIZATIONAL_UNIT
CN=$COMMON_NAME
emailAddress=$EMAIL

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = edge-terrarium.local
DNS.2 = localhost
DNS.3 = *.edge-terrarium.local
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF
    
    # Generate private key
    log_info "Generating private key..."
    openssl genrsa -out "$KEY_FILE" 2048
    
    # Generate certificate signing request
    log_info "Generating certificate signing request..."
    local csr_file
    csr_file=$(mktemp)
    openssl req -new -key "$KEY_FILE" -out "$csr_file" -config "$config_file"
    
    # Generate self-signed certificate
    log_info "Generating self-signed certificate..."
    openssl x509 -req -in "$csr_file" -signkey "$KEY_FILE" -out "$CERT_FILE" -days "$DAYS_VALID" -extensions v3_req -extfile "$config_file"
    
    # Clean up temporary files
    rm -f "$config_file" "$csr_file"
    
    log_success "TLS certificate and private key generated successfully"
}

# Function to verify generated certificates
verify_certificates() {
    log_info "Verifying generated certificates..."
    
    # Check if files exist
    if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
        log_error "Certificate files were not created"
        return 1
    fi
    
    # Verify certificate
    log_info "Certificate details:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)"
    
    # Verify private key
    log_info "Private key details:"
    openssl rsa -in "$KEY_FILE" -check -noout
    
    # Verify certificate and key match
    local cert_md5
    local key_md5
    cert_md5=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
    key_md5=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
    
    if [ "$cert_md5" = "$key_md5" ]; then
        log_success "Certificate and private key match"
    else
        log_error "Certificate and private key do not match"
        return 1
    fi
    
    log_success "Certificate verification completed"
}

# Function to set proper file permissions
set_file_permissions() {
    log_info "Setting file permissions..."
    
    # Set restrictive permissions on private key
    chmod 600 "$KEY_FILE"
    
    # Set readable permissions on certificate
    chmod 644 "$CERT_FILE"
    
    log_success "File permissions set"
}

# Function to display certificate information
display_certificate_info() {
    echo ""
    echo "============================================================================="
    echo "TLS CERTIFICATE GENERATION COMPLETED"
    echo "============================================================================="
    echo "Certificate: $CERT_FILE"
    echo "Private Key: $KEY_FILE"
    echo "Valid for: $DAYS_VALID days"
    echo ""
    echo "Certificate Details:"
    echo "  Common Name: $COMMON_NAME"
    echo "  Organization: $ORGANIZATION"
    echo "  Subject Alternative Names:"
    echo "    - edge-terrarium.local"
    echo "    - localhost"
    echo "    - *.edge-terrarium.local"
    echo "    - 127.0.0.1"
    echo "    - 0.0.0.0"
    echo ""
    echo "Next Steps:"
    echo "  1. The certificates will be automatically loaded into Vault"
    echo "  2. Kong Gateway will use these certificates for HTTPS"
    echo "  3. You can access the application at https://localhost:8443"
    echo "  4. You may need to accept the self-signed certificate in your browser"
    echo "============================================================================="
}

# Main execution
main() {
    echo "============================================================================="
    echo "DYNAMIC TLS CERTIFICATE GENERATION"
    echo "============================================================================="
    echo "Project Root: $PROJECT_ROOT"
    echo "Certificates Directory: $CERTS_DIR"
    echo "Certificate Name: $CERT_NAME"
    echo "Days Valid: $DAYS_VALID"
    echo "============================================================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Check for existing certificates
    if ! check_existing_certificates; then
        log_info "Using existing certificates"
        display_certificate_info
        exit 0
    fi
    
    # Generate new certificates
    generate_tls_certificate
    
    # Verify certificates
    verify_certificates
    
    # Set file permissions
    set_file_permissions
    
    # Display information
    display_certificate_info
    
    log_success "TLS certificate generation completed successfully!"
}

# Run main function
main "$@"
