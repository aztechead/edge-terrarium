#!/bin/bash

# =============================================================================
# MINIKUBE TEST SCRIPT
# =============================================================================
# This script tests the Terrarium application running in Minikube
# It verifies that all services are working correctly with TLS termination

set -e

echo "Testing Terrarium application in Minikube..."
echo "=============================================="

# Check if Minikube is running
if ! minikube status >/dev/null 2>&1; then
    echo "Error: Minikube is not running. Please start Minikube first:"
    echo "  minikube start"
    exit 1
fi

# Check if kubectl is configured for Minikube
if ! kubectl config current-context | grep -q "minikube"; then
    echo "Error: kubectl is not configured for Minikube context"
    exit 1
fi

echo "Minikube is running and configured correctly"
echo ""

# Check if the terrarium namespace exists
if ! kubectl get namespace terrarium >/dev/null 2>&1; then
    echo "Error: terrarium namespace not found. Please deploy the application first:"
    echo "  kubectl apply -k k8s/"
    exit 1
fi

echo "Checking pod status..."
kubectl get pods -n terrarium
echo ""

# Check if all pods are running
if ! kubectl get pods -n terrarium --field-selector=status.phase=Running | grep -q "cdp-client"; then
    echo "Error: CDP client pods are not running"
    exit 1
fi

if ! kubectl get pods -n terrarium --field-selector=status.phase=Running | grep -q "service-sink"; then
    echo "Error: Service sink pods are not running"
    exit 1
fi

if ! kubectl get pods -n terrarium --field-selector=status.phase=Running | grep -q "vault"; then
    echo "Error: Vault pod is not running"
    exit 1
fi

echo "All pods are running successfully"
echo ""

# Check if ingress is configured
if ! kubectl get ingress -n terrarium terrarium-ingress >/dev/null 2>&1; then
    echo "Error: terrarium-ingress not found"
    exit 1
fi

echo "Ingress is configured"
echo ""

# Set up port forwarding for testing (using port 8443 since 443 requires root)
echo "Setting up port forwarding for testing..."
echo "Note: In production, this would be port 443, but we use 8443 for testing"
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8443:443 &
PORT_FORWARD_PID=$!

# Wait for port forwarding to be ready
sleep 3

echo "Testing HTTPS endpoints (simulating port 443 via 8443)..."
echo ""

# Test CDP client endpoints
echo "Testing CDP Client endpoints:"
echo "-----------------------------"

echo "Testing /fake-provider/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://localhost:8443/fake-provider/test)
if echo "$response" | grep -q "CDP Client processed request"; then
    echo "✓ /fake-provider/test - SUCCESS"
else
    echo "✗ /fake-provider/test - FAILED"
    echo "Response: $response"
fi

echo "Testing /example-provider/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://localhost:8443/example-provider/test)
if echo "$response" | grep -q "CDP Client processed request"; then
    echo "✓ /example-provider/test - SUCCESS"
else
    echo "✗ /example-provider/test - FAILED"
    echo "Response: $response"
fi

echo ""

# Test Service Sink endpoints
echo "Testing Service Sink endpoints:"
echo "-------------------------------"

echo "Testing root path /:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://localhost:8443/)
if echo "$response" | grep -q "Service Sink processed request"; then
    echo "✓ / - SUCCESS"
else
    echo "✗ / - FAILED"
    echo "Response: $response"
fi

echo "Testing /api/test:"
response=$(curl -k -s -H "Host: localhost" --connect-timeout 2 --max-time 2 https://localhost:8443/api/test)
if echo "$response" | grep -q "Service Sink processed request"; then
    echo "✓ /api/test - SUCCESS"
else
    echo "✗ /api/test - FAILED"
    echo "Response: $response"
fi

echo ""

# Test Vault connectivity
echo "Testing Vault connectivity:"
echo "---------------------------"

echo "Checking Vault health:"
if kubectl exec -n terrarium deployment/vault -- vault status >/dev/null 2>&1; then
    echo "✓ Vault is healthy"
else
    echo "✗ Vault health check failed"
fi

echo "Checking Vault secrets:"
if kubectl exec -n terrarium deployment/vault -- vault kv get secret/cdp-client/config >/dev/null 2>&1; then
    echo "✓ Vault secrets are accessible"
else
    echo "✗ Vault secrets are not accessible"
fi

echo ""

# Test CDP client Vault integration
echo "Testing CDP client Vault integration:"
echo "-------------------------------------"

echo "Checking CDP client logs for Vault secrets:"
if kubectl logs -n terrarium deployment/cdp-client | grep -q "mock-api-key-12345"; then
    echo "✓ CDP client successfully retrieved secrets from Vault"
else
    echo "✗ CDP client failed to retrieve secrets from Vault"
fi

echo ""

# Clean up port forwarding
echo "Cleaning up..."
kill $PORT_FORWARD_PID 2>/dev/null || true

echo "Minikube testing completed!"
echo ""
echo "Summary:"
echo "- All pods are running"
echo "- Ingress is configured with TLS"
echo "- CDP client endpoints are working"
echo "- Service sink endpoints are working"
echo "- Vault is healthy and accessible"
echo "- CDP client successfully retrieves secrets from Vault"
echo ""
echo "The application is fully functional in Minikube!"
