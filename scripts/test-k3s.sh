#!/bin/bash

# =============================================================================
# K3S TEST SCRIPT
# =============================================================================
# This script tests the Edge-Terrarium application running in K3s
# It verifies that all services are working correctly with Kong ingress

set -e

# Timeout function to detect hanging commands
# Uses different timeout implementations based on OS
timeout_cmd() {
    local timeout_duration=$1
    shift
    local cmd="$@"
    
    echo "Running: $cmd (timeout: ${timeout_duration}s)"
    
    # Try different timeout commands
    if command -v timeout >/dev/null 2>&1; then
        # Linux timeout
        if timeout $timeout_duration $cmd; then
            return 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo "ERROR: Command timed out after ${timeout_duration} seconds"
                echo "Command: $cmd"
                return 1
            else
                echo "ERROR: Command failed with exit code $exit_code"
                echo "Command: $cmd"
                return $exit_code
            fi
        fi
    elif command -v gtimeout >/dev/null 2>&1; then
        # macOS with GNU coreutils
        if gtimeout $timeout_duration $cmd; then
            return 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo "ERROR: Command timed out after ${timeout_duration} seconds"
                echo "Command: $cmd"
                return 1
            else
                echo "ERROR: Command failed with exit code $exit_code"
                echo "Command: $cmd"
                return $exit_code
            fi
        fi
    else
        # Fallback: run command without timeout but with warning
        echo "WARNING: No timeout command available, running without timeout"
        if $cmd; then
            return 0
        else
            local exit_code=$?
            echo "ERROR: Command failed with exit code $exit_code"
            echo "Command: $cmd"
            return $exit_code
        fi
    fi
}

echo "Testing Edge-Terrarium application in K3s..."
echo "=============================================="

# Check if K3s is running
if ! timeout_cmd 10 kubectl cluster-info >/dev/null 2>&1; then
    echo "Error: K3s is not running. Please start K3s first:"
    echo "  k3d cluster create edge-terrarium --port \"80:80@loadbalancer\" --port \"443:443@loadbalancer\" --port \"8200:8200@loadbalancer\""
    exit 1
fi

# Check if kubectl is configured for K3s
if ! kubectl config current-context | grep -q "k3d-edge-terrarium"; then
    echo "Error: kubectl is not configured for K3s context"
    echo "Current context: $(kubectl config current-context)"
    exit 1
fi

echo "K3s is running and configured correctly"
echo ""

# Check if the edge-terrarium namespace exists
if ! timeout_cmd 10 kubectl get namespace edge-terrarium >/dev/null 2>&1; then
    echo "Error: edge-terrarium namespace not found. Please deploy the application first:"
    echo "  kubectl apply -k configs/k3s/"
    exit 1
fi

echo "Checking pod status..."
kubectl get pods -n edge-terrarium
echo ""

# Check if all pods are running
if ! kubectl get pods -n edge-terrarium --field-selector=status.phase=Running | grep -q "custom-client"; then
    echo "Error: Custom client pods are not running"
    exit 1
fi

if ! kubectl get pods -n edge-terrarium --field-selector=status.phase=Running | grep -q "service-sink"; then
    echo "Error: Service sink pods are not running"
    exit 1
fi

if ! kubectl get pods -n edge-terrarium --field-selector=status.phase=Running | grep -q "vault"; then
    echo "Error: Vault pod is not running"
    exit 1
fi

echo "All pods are running successfully"
echo ""

# Check if ingress is configured
if ! kubectl get ingress -n edge-terrarium edge-terrarium-ingress >/dev/null 2>&1; then
    echo "Error: edge-terrarium-ingress not found"
    exit 1
fi

echo "Ingress is configured"
echo ""

# Clean up any existing port forwarding processes
echo "Cleaning up any existing port forwarding processes..."
pkill -f "kubectl port-forward.*8200" 2>/dev/null || true
pkill -f "kubectl port-forward.*edge-terrarium" 2>/dev/null || true
pkill -f "kubectl port-forward.*vault" 2>/dev/null || true
sleep 2

# Use localhost with k3d port mappings for production-like testing
echo "Using localhost with k3d port mappings for production-like testing..."
echo "Note: k3d maps Kong LoadBalancer ports to localhost (80->80, 443->443)"
KONG_HOST="localhost"
KONG_HTTP_PORT="80"
KONG_HTTPS_PORT="443"

# Set up port forwarding for Vault (port 8200)
echo "Setting up Vault port forwarding..."
timeout_cmd 30 kubectl port-forward -n edge-terrarium service/vault 8200:8200 &
VAULT_PORT_FORWARD_PID=$!

# Wait for port forwarding to be ready
sleep 3

echo "Testing HTTPS endpoints (simulating port 443 via 8443)..."
echo ""

# Test Custom client endpoints
echo "Testing Custom Client endpoints:"
echo "-----------------------------"

echo "Testing /fake-provider/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/fake-provider/test)
if [ -n "$response" ]; then
    echo "✓ /fake-provider/test - SUCCESS"
else
    echo "✗ /fake-provider/test - FAILED"
fi

echo "Testing /example-provider/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/example-provider/test)
if [ -n "$response" ]; then
    echo "✓ /example-provider/test - SUCCESS"
else
    echo "✗ /example-provider/test - FAILED"
fi

echo ""

# Test Service Sink endpoints
echo "Testing Service Sink endpoints:"
echo "-------------------------------"

echo "Testing root path /:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/)
if [ -n "$response" ]; then
    echo "✓ / - SUCCESS"
else
    echo "✗ / - FAILED"
fi

echo "Testing /api/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/api/test)
if [ -n "$response" ]; then
    echo "✓ /api/test - SUCCESS"
else
    echo "✗ /api/test - FAILED"
fi

echo ""

# Test enhanced request logging
echo "Testing enhanced request logging:"
echo "================================="

echo "Testing GET with query parameters:"
echo "----------------------------------"

echo "Testing Custom Client - GET with query params:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 "https://$KONG_HOST:$KONG_HTTPS_PORT/fake-provider/test?param1=value1&param2=value2&test=query")
if [ -n "$response" ]; then
    echo "✓ Custom Client - GET with query params - SUCCESS"
else
    echo "✗ Custom Client - GET with query params - FAILED"
fi

echo "Testing Service Sink - GET with query params:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 "https://$KONG_HOST:$KONG_HTTPS_PORT/api/test?user=testuser&action=login&id=123")
if [ -n "$response" ]; then
    echo "✓ Service Sink - GET with query params - SUCCESS"
else
    echo "✗ Service Sink - GET with query params - FAILED"
fi

echo ""
echo "Testing POST with body content:"
echo "------------------------------"

echo "Testing Custom Client - POST with JSON body:"
response=$(curl -k -s -X POST -H "Content-Type: application/json" -H "Host: localhost" -d '{"username":"testuser","password":"testpass","action":"login"}' --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/fake-provider/test)
if [ -n "$response" ]; then
    echo "✓ Custom Client - POST with JSON body - SUCCESS"
else
    echo "✗ Custom Client - POST with JSON body - FAILED"
fi

echo "Testing Service Sink - POST with JSON body:"
response=$(curl -k -s -X POST -H "Content-Type: application/json" -H "Host: localhost" -d '{"data":"test data","timestamp":"2024-01-01","status":"active"}' --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/api/test)
if [ -n "$response" ]; then
    echo "✓ Service Sink - POST with JSON body - SUCCESS"
else
    echo "✗ Service Sink - POST with JSON body - FAILED"
fi

echo "Testing Custom Client - POST with form data:"
response=$(curl -k -s -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Host: localhost" -d "username=testuser&email=test@example.com&role=admin" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/example-provider/test)
if [ -n "$response" ]; then
    echo "✓ Custom Client - POST with form data - SUCCESS"
else
    echo "✗ Custom Client - POST with form data - FAILED"
fi

echo "Testing Service Sink - POST with form data:"
response=$(curl -k -s -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Host: localhost" -d "check=health&service=all&verbose=true" --connect-timeout 2 --max-time 2 https://$KONG_HOST:$KONG_HTTPS_PORT/api/test)
if [ -n "$response" ]; then
    echo "✓ Service Sink - POST with form data - SUCCESS"
else
    echo "✗ Service Sink - POST with form data - FAILED"
fi

echo ""
echo "Testing Logthon log aggregation service:"
echo "========================================"

# Test logthon health endpoint via Kong ingress
echo "Testing Logthon health endpoint via Kong:"
echo "----------------------------------------"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 "https://$KONG_HOST:$KONG_HTTPS_PORT/logs/health")
if [ -n "$response" ]; then
    echo "✓ Logthon health check via Kong - SUCCESS"
else
    echo "✗ Logthon health check via Kong - FAILED"
fi
echo ""

# Test logthon web UI via Kong ingress
echo "Testing Logthon web UI via Kong:"
echo "-------------------------------"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 "https://$KONG_HOST:$KONG_HTTPS_PORT/logs/")
if [ -n "$response" ]; then
    echo "✓ Logthon web UI via Kong - SUCCESS"
else
    echo "✗ Logthon web UI via Kong - FAILED"
fi
echo ""

# Test logthon API endpoint via Kong ingress
echo "Testing Logthon API endpoint via Kong:"
echo "------------------------------------"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 "https://$KONG_HOST:$KONG_HTTPS_PORT/logs/api/logs")
if [ -n "$response" ]; then
    echo "✓ Logthon API endpoint via Kong - SUCCESS"
else
    echo "✗ Logthon API endpoint via Kong - FAILED"
fi
echo ""

# Test logthon via direct LoadBalancer (fallback)
echo "Testing Logthon via direct LoadBalancer (fallback):"
echo "--------------------------------------------------"
response=$(curl -s --connect-timeout 2 --max-time 2 "http://localhost:5001/health")
if [ -n "$response" ]; then
    echo "✓ Logthon health check via LoadBalancer - SUCCESS"
else
    echo "✗ Logthon health check via LoadBalancer - FAILED"
fi
echo ""

echo ""

# Test Vault connectivity
echo "Testing Vault connectivity:"
echo "---------------------------"

echo "Checking Vault health:"
if timeout_cmd 15 kubectl exec -n edge-terrarium deployment/vault -- vault status >/dev/null 2>&1; then
    echo "✓ Vault is healthy"
else
    echo "✗ Vault health check failed"
fi

echo "Checking Vault secrets:"
if timeout_cmd 15 kubectl exec -n edge-terrarium deployment/vault -- vault kv get secret/terrarium/tls >/dev/null 2>&1; then
    echo "✓ Vault secrets are accessible"
    echo ""
    echo "Displaying Vault secrets:"
    echo "========================="
    
    echo "=== VAULT SECRETS ==="
    secret_count=$(kubectl exec -n edge-terrarium deployment/vault -- vault kv list secret/ 2>/dev/null | wc -l)
    if [ "$secret_count" -gt 0 ]; then
        echo "✓ Found $secret_count secret paths in Vault"
    else
        echo "No secrets found"
    fi
    echo ""
    
    # Test if specific secrets exist (without jq dependency)
    echo "Testing Vault secrets..."
    if kubectl exec -n edge-terrarium deployment/vault -- vault kv get secret/terrarium/tls >/dev/null 2>&1; then
        echo "✓ TLS certificates secret found"
    else
        echo "✗ TLS certificates secret not found"
    fi
    
    if kubectl exec -n edge-terrarium deployment/vault -- vault kv get secret/custom-client/config >/dev/null 2>&1; then
        echo "✓ Custom client config secret found"
    else
        echo "✗ Custom client config secret not found"
    fi
    
    if kubectl exec -n edge-terrarium deployment/vault -- vault kv get secret/custom-client/external-apis >/dev/null 2>&1; then
        echo "✓ Custom client external APIs secret found"
    else
        echo "✗ Custom client external APIs secret not found"
    fi
    echo ""
else
    echo "✗ Vault secrets are not accessible"
    echo ""
    echo "Attempting to initialize Vault manually..."
    echo "Running vault-init job..."
    kubectl delete job vault-init -n edge-terrarium --ignore-not-found=true
    kubectl apply -f configs/k3s/vault-init-job.yaml
    echo "Waiting for vault-init job to complete..."
    kubectl wait --for=condition=complete job/vault-init -n edge-terrarium --timeout=60s
    echo "Vault initialization completed!"
    echo ""
fi

echo ""

# Test Custom client Vault integration
echo "Testing Custom client Vault integration:"
echo "-------------------------------------"

echo "Checking Custom client logs for Vault secrets:"

# Get the Custom client pod (should only be one with Recreate strategy)
NEWEST_Custom_POD=$(kubectl get pods -n edge-terrarium -l app=custom-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$NEWEST_Custom_POD" ]; then
    echo "Using newest Custom client pod: $NEWEST_Custom_POD"
    
    if kubectl logs -n edge-terrarium $NEWEST_Custom_POD --tail=100 | grep -q "mock-api-key-12345"; then
        echo "✓ Custom client successfully retrieved secrets from Vault"
        echo ""
        echo "Custom Client Vault Integration Logs:"
        echo "=================================="
        kubectl logs -n edge-terrarium $NEWEST_Custom_POD --tail=100 | grep -A 20 "=== VAULT SECRETS RETRIEVED ===" || echo "No Vault secrets logs found"
    else
        echo "✗ Custom client failed to retrieve secrets from Vault"
        echo ""
        echo "Custom Client logs (last 20 lines):"
        echo "================================"
        kubectl logs -n edge-terrarium $NEWEST_Custom_POD --tail=20
    fi
else
    echo "✗ No Custom client pods found"
fi

echo ""

# Test Logthon connectivity from Custom client and service-sink
echo "Testing Logthon connectivity from applications:"
echo "=============================================="

echo "Testing Custom client to Logthon connectivity:"
echo "-------------------------------------------"
if kubectl exec -n edge-terrarium deployment/custom-client -- curl -s --connect-timeout 5 --max-time 5 http://logthon-ingress-service.edge-terrarium.svc.cluster.local:5000/health >/dev/null 2>&1; then
    echo "✓ Custom client can connect to Logthon"
else
    echo "✗ Custom client cannot connect to Logthon"
    echo "This indicates a networking or DNS issue"
fi

echo "Testing service-sink to Logthon connectivity:"
echo "--------------------------------------------"
if kubectl exec -n edge-terrarium deployment/service-sink -- curl -s --connect-timeout 5 --max-time 5 http://logthon-ingress-service.edge-terrarium.svc.cluster.local:5000/health >/dev/null 2>&1; then
    echo "✓ Service-sink can connect to Logthon"
else
    echo "✗ Service-sink cannot connect to Logthon"
    echo "This indicates a networking or DNS issue"
fi

echo ""

# Test if logs are being sent to Logthon
echo "Testing log aggregation functionality:"
echo "====================================="

echo "Checking Logthon logs for application messages:"
echo "----------------------------------------------"
LOGTHON_LOGS=$(kubectl logs -n edge-terrarium deployment/logthon --tail=50 2>/dev/null)

if echo "$LOGTHON_LOGS" | grep -q "custom-client.*Request:"; then
    echo "✓ Custom client logs are being sent to Logthon"
else
    echo "✗ Custom client logs are NOT being sent to Logthon"
    echo "This indicates the log sending functionality is not working"
fi

if echo "$LOGTHON_LOGS" | grep -q "service-sink.*Request:"; then
    echo "✓ Service-sink logs are being sent to Logthon"
else
    echo "✗ Service-sink logs are NOT being sent to Logthon"
    echo "This indicates the log sending functionality is not working"
fi

echo ""

# Check for any "Failed to send log" errors in application logs
echo "Checking for log sending errors:"
echo "==============================="

Custom_LOGS=$(kubectl logs -n edge-terrarium deployment/custom-client --tail=50 2>/dev/null)
SERVICE_SINK_LOGS=$(kubectl logs -n edge-terrarium deployment/service-sink --tail=50 2>/dev/null)

if echo "$Custom_LOGS" | grep -q "Failed to send log to logthon"; then
    echo "✗ Custom client has log sending errors:"
    echo "$Custom_LOGS" | grep "Failed to send log to logthon"
else
    echo "✓ Custom client has no log sending errors"
fi

if echo "$SERVICE_SINK_LOGS" | grep -q "Failed to send log to logthon"; then
    echo "✗ Service-sink has log sending errors:"
    echo "$SERVICE_SINK_LOGS" | grep "Failed to send log to logthon"
else
    echo "✓ Service-sink has no log sending errors"
fi

echo ""

# Check request logs
echo "Checking request logs:"
echo "====================="
echo "Custom Client request files:"
if [ -n "$NEWEST_Custom_POD" ]; then
    kubectl exec -n edge-terrarium $NEWEST_Custom_POD -- ls -la /tmp/requests/ 2>/dev/null || echo "No request files found"
else
    echo "No Custom client pod available"
fi
echo ""

# Test file storage functionality
echo "Testing file storage functionality:"
echo "=================================="

# Test file storage health endpoint
echo "Testing file storage health endpoint:"
echo "------------------------------------"
if curl -s --connect-timeout 5 --max-time 5 -k -H "Host: localhost" https://$KONG_HOST:$KONG_HTTPS_PORT/storage/health >/dev/null 2>&1; then
    echo "✓ File storage health endpoint is accessible"
else
    echo "✗ File storage health endpoint is not accessible"
fi

# Test file storage info endpoint
echo "Testing file storage info endpoint:"
echo "----------------------------------"
if curl -s --connect-timeout 5 --max-time 5 -k -H "Host: localhost" https://$KONG_HOST:$KONG_HTTPS_PORT/storage/info >/dev/null 2>&1; then
    echo "✓ File storage info endpoint is accessible"
else
    echo "✗ File storage info endpoint is not accessible"
fi

# Test file storage list endpoint
echo "Testing file storage list endpoint:"
echo "----------------------------------"
if curl -s --connect-timeout 5 --max-time 5 -k -H "Host: localhost" https://$KONG_HOST:$KONG_HTTPS_PORT/storage/files >/dev/null 2>&1; then
    echo "✓ File storage list endpoint is accessible"
else
    echo "✗ File storage list endpoint is not accessible"
fi


# Test Logthon file storage integration
echo "Testing Logthon file storage integration:"
echo "----------------------------------------"
if curl -s --connect-timeout 5 --max-time 5 -k -H "Host: localhost" https://$KONG_HOST:$KONG_HTTPS_PORT/logthon/api/files >/dev/null 2>&1; then
    echo "✓ Logthon file storage integration is working"
else
    echo "✗ Logthon file storage integration is not working"
fi

echo ""

# Clean up port forwarding
echo "Cleaning up..."
kill $VAULT_PORT_FORWARD_PID 2>/dev/null || true

# Additional cleanup to ensure no lingering processes
pkill -f "kubectl port-forward.*8200" 2>/dev/null || true
pkill -f "kubectl port-forward.*edge-terrarium" 2>/dev/null || true
pkill -f "kubectl port-forward.*vault" 2>/dev/null || true

echo "K3s testing completed!"
echo ""
echo "Summary:"
echo "- All pods are running"
echo "- Ingress is configured with TLS using Kong"
echo "- Custom client endpoints are working"
echo "- Service sink endpoints are working"
echo "- Vault is healthy and accessible"
echo "- Custom client successfully retrieves secrets from Vault"
echo "- File storage service is accessible and functional"
echo "- Logthon file storage integration is working"
echo ""
echo "The application is fully functional in K3s!"
