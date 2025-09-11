#!/bin/bash

# =============================================================================
# UNIFIED TEST SCRIPT FOR EDGE-TERRARIUM
# =============================================================================
# Tests both Docker Compose and K3s deployments with simplified, maintainable code

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
ENVIRONMENT=""
BASE_URL=""
VAULT_URL=""
VAULT_PORT_FORWARD_PID=""

# Cleanup function
cleanup() {
    if [ -n "$VAULT_PORT_FORWARD_PID" ]; then
        kill $VAULT_PORT_FORWARD_PID 2>/dev/null || true
        sleep 1
        kill -9 $VAULT_PORT_FORWARD_PID 2>/dev/null || true
    fi
    pkill -f "kubectl port-forward.*8200" 2>/dev/null || true
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Print functions
print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Test HTTP endpoint with simplified logic
test_endpoint() {
    local url="$1"
    local description="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    
    local curl_cmd="curl -k -s -w '%{http_code}' -o /tmp/response.json --connect-timeout 5 --max-time 10"
    
    if [ "$method" = "POST" ] || [ "$method" = "PUT" ]; then
        if [[ "$data" == *"{"* ]]; then
            curl_cmd="$curl_cmd -X $method -H 'Content-Type: application/json' -d '$data'"
        else
            curl_cmd="$curl_cmd -X $method -H 'Content-Type: application/x-www-form-urlencoded' -d '$data'"
        fi
    fi
    
    if [ "$ENVIRONMENT" = "k3s" ]; then
        curl_cmd="$curl_cmd -H 'Host: localhost'"
    fi
    
    local response=$(eval "$curl_cmd '$url'" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        print_success "$description"
        return 0
    else
        print_error "$description (HTTP $response)"
        return 1
    fi
}

# Test service health
test_service_health() {
    local service_name="$1"
    local health_url="$2"
    
    if test_endpoint "$health_url" "$service_name health check"; then
        return 0
    else
        print_info "Service may still be starting up..."
        return 1
    fi
}

# Test Vault connectivity
test_vault() {
    print_header "Testing Vault Integration"
    
    if [ "$ENVIRONMENT" = "docker" ]; then
        # Test Vault health
        if curl -s --connect-timeout 5 "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
            print_success "Vault is healthy"
        else
            print_error "Vault health check failed"
            return 1
        fi
        
        # Test secrets
        local secrets=("terrarium/tls" "custom-client/config" "custom-client/external-apis")
        for secret in "${secrets[@]}"; do
            if curl -s -H "X-Vault-Token: root" "http://localhost:8200/v1/secret/data/$secret" >/dev/null 2>&1; then
                print_success "Secret $secret found"
            else
                print_error "Secret $secret not found"
            fi
        done
        
    else # k3s
        # Set up port forwarding
        kubectl port-forward -n edge-terrarium service/vault 8200:8200 >/dev/null 2>&1 &
        VAULT_PORT_FORWARD_PID=$!
        sleep 3
        
        # Test Vault health
        if kubectl exec -n edge-terrarium deployment/vault -- vault status >/dev/null 2>&1; then
            print_success "Vault is healthy"
        else
            print_error "Vault health check failed"
            return 1
        fi
        
        # Test secrets
        local secrets=("secret/terrarium/tls" "secret/custom-client/config" "secret/custom-client/external-apis")
        for secret in "${secrets[@]}"; do
            if kubectl exec -n edge-terrarium deployment/vault -- vault kv get "$secret" >/dev/null 2>&1; then
                print_success "Secret $secret found"
            else
                print_error "Secret $secret not found"
            fi
        done
        
        # Test Custom client Vault integration
        local custom_pod=$(kubectl get pods -n edge-terrarium -l app=custom-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$custom_pod" ]; then
            if kubectl logs -n edge-terrarium "$custom_pod" --tail=100 | grep -q "mock-api-key-12345"; then
                print_success "Custom client retrieved Vault secrets"
                echo "Vault Secrets Retrieved:"
                echo "======================="
                kubectl logs -n edge-terrarium "$custom_pod" --tail=100 | \
                grep -A 20 "=== VAULT SECRETS RETRIEVED ===" | \
                grep -E "(API Key|Database URL|JWT Secret|Encryption Key|Log Level|Max Connections)" | \
                sed 's/.*{"status":"success","message":"Log entry added"}.*//g' | \
                sed 's/.*\[.*\] //g' | \
                sed 's/.*INFO.*//g' | \
                sed 's/.*DEBUG.*//g' | \
                sed 's/.*[0-9][0-9]:[0-9][0-9]:[0-9][0-9].*//g' | \
                grep -v "^$" | \
                head -10 || echo "No Vault secrets logs found"
            else
                print_error "Custom client failed to retrieve Vault secrets"
            fi
        fi
    fi
    echo ""
}

# Test application endpoints
test_applications() {
    print_header "Testing Application Endpoints"
    
    # Test Custom Client endpoints
    test_endpoint "$BASE_URL/fake-provider/test" "Custom Client - fake-provider route"
    test_endpoint "$BASE_URL/example-provider/test" "Custom Client - example-provider route"
    
    # Test Service Sink endpoints
    test_endpoint "$BASE_URL/api/test" "Service Sink - API route"
    test_endpoint "$BASE_URL/" "Service Sink - root route"
    
    # Test enhanced request logging
    print_info "Testing enhanced request logging..."
    test_endpoint "$BASE_URL/fake-provider/test?param1=value1&param2=value2" "Custom Client - GET with query params"
    test_endpoint "$BASE_URL/api/test?user=testuser&action=login" "Service Sink - GET with query params"
    test_endpoint "$BASE_URL/fake-provider/test" "Custom Client - POST with JSON" "POST" '{"username":"testuser","password":"testpass"}'
    test_endpoint "$BASE_URL/api/test" "Service Sink - POST with form data" "POST" "data=test&status=active"
    
    echo ""
}

# Test Logthon service
test_logthon() {
    print_header "Testing Logthon Service"
    
    test_service_health "Logthon" "$BASE_URL/logs/health"
    test_endpoint "$BASE_URL/logs/" "Logthon web UI"
    test_endpoint "$BASE_URL/logs/api/logs" "Logthon API endpoint"
    
    # Test log aggregation
    if [ "$ENVIRONMENT" = "k3s" ]; then
        local logthon_logs=$(kubectl logs -n edge-terrarium deployment/logthon --tail=50 2>/dev/null)
        if echo "$logthon_logs" | grep -q "custom-client.*Request:"; then
            print_success "Custom client logs are being sent to Logthon"
        else
            print_error "Custom client logs are NOT being sent to Logthon"
        fi
        
        if echo "$logthon_logs" | grep -q "service-sink.*Request:"; then
            print_success "Service-sink logs are being sent to Logthon"
        else
            print_error "Service-sink logs are NOT being sent to Logthon"
        fi
    fi
    
    echo ""
}

# Test File Storage service
test_file_storage() {
    print_header "Testing File Storage Service"
    
    test_service_health "File Storage" "$BASE_URL/storage/health"
    if [ "$ENVIRONMENT" = "docker" ]; then
        test_endpoint "$BASE_URL/storage/storage/info" "File Storage info endpoint"
    else
        test_endpoint "$BASE_URL/storage/info" "File Storage info endpoint"
    fi
    test_endpoint "$BASE_URL/storage/files" "File Storage list endpoint"
    test_endpoint "$BASE_URL/storage/files" "File Storage create endpoint" "PUT" '{"content":"Test file","filename_prefix":"test","extension":".txt"}'
    test_endpoint "$BASE_URL/logs/api/files" "Logthon file storage integration"
    
    echo ""
}

# Test request logging
test_request_logging() {
    print_header "Testing Request Logging"
    
    if [ "$ENVIRONMENT" = "docker" ]; then
        local file_count=$(docker exec edge-terrarium-custom-client ls -1 /tmp/requests/ 2>/dev/null | wc -l)
        if [ "$file_count" -gt 0 ]; then
            print_success "$file_count request files present"
        else
            print_error "No request files found"
        fi
    else # k3s
        local custom_pod=$(kubectl get pods -n edge-terrarium -l app=custom-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$custom_pod" ]; then
            local request_count=$(kubectl exec -n edge-terrarium "$custom_pod" -- ls /tmp/requests/ 2>/dev/null | wc -l)
            if [ "$request_count" -gt 0 ]; then
                print_success "$request_count request files present"
            else
                print_error "No request files found"
            fi
        else
            print_error "No Custom client pod available"
        fi
    fi
    
    echo ""
}

# Detect environment and set up
detect_environment() {
    if docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps | grep -q "Up"; then
        ENVIRONMENT="docker"
        BASE_URL="https://localhost:8443"
        print_info "Detected Docker Compose environment"
        
        # Initialize Vault if needed
        if docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps | grep -q "vault.*Up"; then
            print_info "Initializing Vault with secrets..."
            ./scripts/init-vault-enhanced.sh http://localhost:8200 both >/dev/null 2>&1
        fi
        
    elif kubectl get namespace edge-terrarium >/dev/null 2>&1; then
        ENVIRONMENT="k3s"
        BASE_URL="https://localhost:443"
        print_info "Detected K3s environment"
        
        # Check if K3s is running
        if ! kubectl cluster-info >/dev/null 2>&1; then
            print_error "K3s is not running. Please start K3s first."
            exit 1
        fi
        
        # Check if kubectl is configured for K3s
        if ! kubectl config current-context | grep -q "k3d-edge-terrarium"; then
            print_error "kubectl is not configured for K3s context"
            exit 1
        fi
        
        # Wait for pods to be ready
        print_info "Waiting for pods to be ready..."
        kubectl wait --for=condition=ready pod -l app=custom-client -n edge-terrarium --timeout=60s >/dev/null 2>&1
        kubectl wait --for=condition=ready pod -l app=service-sink -n edge-terrarium --timeout=60s >/dev/null 2>&1
        
    else
        print_error "No running environment detected. Please start Docker Compose or K3s deployment first."
        exit 1
    fi
    
    echo ""
}

# Main test execution
main() {
    print_header "Edge-Terrarium Test Suite"
    
    detect_environment
    
    test_applications
    test_logthon
    test_file_storage
    test_vault
    test_request_logging
    
    print_header "Test Summary"
    print_success "All tests completed for $ENVIRONMENT environment"
    print_info "Check individual test results above for any failures"
    echo ""
}

# Run main function
main "$@"
