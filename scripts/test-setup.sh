#!/bin/bash

# Test script for Terrarium setup
# Tests both Docker Compose and Kubernetes deployments

set -e

echo "Testing Terrarium setup..."

# Function to test HTTP endpoint
test_endpoint() {
    local url=$1
    local expected_service=$2
    local description=$3
    
    echo "Testing: $description"
    echo "URL: $url"
    
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 2 --max-time 2 "$url" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "Success (HTTP $response)"
        if [ -f /tmp/response.json ]; then
            echo "Response: $(cat /tmp/response.json)"
        fi
    else
        echo "Failed (HTTP $response)"
    fi
    echo ""
}

# Check if Docker Compose is running
if docker-compose -f configs/docker/docker-compose.yml -p c-terrarium ps | grep -q "Up"; then
    echo "Testing Docker Compose setup..."
    echo "================================"
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Initialize Vault if it's running
    if docker-compose -f configs/docker/docker-compose.yml -p c-terrarium ps | grep -q "vault.*Up"; then
        echo "Initializing Vault with secrets..."
        ./scripts/init-vault.sh http://localhost:8200
        echo ""
    fi
    
    # Test CDP Client routes
    test_endpoint "https://localhost:443/fake-provider/test" "cdp-client" "CDP Client - fake-provider route"
    test_endpoint "https://localhost:443/example-provider/test" "cdp-client" "CDP Client - example-provider route"
    
    # Test Service Sink (default route)
    test_endpoint "https://localhost:443/api/test" "service-sink" "Service Sink - default route"
    test_endpoint "https://localhost:443/health" "service-sink" "Service Sink - health check"
    
    # Test port 1337
    test_endpoint "https://localhost:443/test" "cdp-client" "CDP Client - port 1337"
    
    # Test Vault if it's running
    if docker-compose -f configs/docker/docker-compose.yml -p c-terrarium ps | grep -q "vault.*Up"; then
        echo "Testing Vault..."
        echo "Vault Health:"
        curl -s http://localhost:8200/v1/sys/health | jq . 2>/dev/null || echo "Vault health check failed"
        echo ""
    fi
    
    echo "Docker Compose tests completed!"
    echo ""
fi

# Check if Kubernetes deployment exists
if kubectl get namespace terrarium >/dev/null 2>&1; then
    echo "Testing Kubernetes setup..."
    echo "================================"
    
    # Wait for pods to be ready
    echo "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=cdp-client -n terrarium --timeout=60s
    kubectl wait --for=condition=ready pod -l app=service-sink -n terrarium --timeout=60s
    
    # Check if we can access the ingress directly
    ingress_ip=$(kubectl get ingress terrarium-ingress -n terrarium -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$ingress_ip" ] && [ "$ingress_ip" != "localhost" ]; then
        echo "Found ingress IP: $ingress_ip"
        echo "Testing connectivity to ingress..."
        
        # Test if we can actually reach the ingress
        if curl -k -s --connect-timeout 2 --max-time 2 "https://$ingress_ip:443/fake-provider/test" >/dev/null 2>&1; then
            echo "Ingress is accessible, running tests..."
            test_host="$ingress_ip"
            
            # Test CDP Client routes
            test_endpoint "https://$test_host:443/fake-provider/test" "cdp-client" "K8s CDP Client - fake-provider route"
            test_endpoint "https://$test_host:443/example-provider/test" "cdp-client" "K8s CDP Client - example-provider route"
            
            # Test Service Sink (default route)
            test_endpoint "https://$test_host:443/api/test" "service-sink" "K8s Service Sink - default route"
        else
            echo "Ingress IP found but not accessible (no tunnel or firewall blocking)"
            echo "To test Kubernetes deployment, use one of these methods:"
            echo ""
            echo "1. Use the dedicated Minikube test script:"
            echo "   ./scripts/test-minikube.sh"
            echo ""
            echo "2. Set up port forwarding manually:"
            echo "   kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8443:443"
            echo "   curl -k -H 'Host: localhost' https://localhost:8443/fake-provider/test"
            echo ""
            echo "3. Start minikube tunnel (requires sudo):"
            echo "   sudo minikube tunnel"
            echo "   curl -k -H 'Host: localhost' https://localhost/fake-provider/test"
            echo ""
            echo "4. Check pod status and logs:"
            kubectl get pods -n terrarium
            echo ""
            echo "CDP Client logs:"
            kubectl logs -n terrarium deployment/cdp-client --tail=5
            echo ""
            echo "Service Sink logs:"
            kubectl logs -n terrarium deployment/service-sink --tail=5
        fi
    else
        echo "INFO: No ingress IP available for direct testing"
        echo "To test Kubernetes deployment, use one of these methods:"
        echo ""
        echo "1. Use the dedicated Minikube test script:"
        echo "   ./scripts/test-minikube.sh"
        echo ""
        echo "2. Set up port forwarding manually:"
        echo "   kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8443:443"
        echo "   curl -k -H 'Host: localhost' https://localhost:8443/fake-provider/test"
        echo ""
        echo "3. Start minikube tunnel (requires sudo):"
        echo "   sudo minikube tunnel"
        echo "   curl -k -H 'Host: localhost' https://localhost/fake-provider/test"
        echo ""
        echo "4. Check pod status and logs:"
        kubectl get pods -n terrarium
        echo ""
        echo "CDP Client logs:"
        kubectl logs -n terrarium deployment/cdp-client --tail=5
        echo ""
        echo "Service Sink logs:"
        kubectl logs -n terrarium deployment/service-sink --tail=5
    fi
    
    echo "Kubernetes tests completed!"
    echo ""
fi

# Check request logs
echo "Checking request logs..."
echo "=========================="

if docker-compose -f configs/docker/docker-compose.yml -p c-terrarium ps | grep -q "Up"; then
    echo "Docker Compose logs:"
    echo "CDP Client request files:"
    docker exec terrarium-cdp-client ls -la /tmp/requests/ 2>/dev/null || echo "No request files found"
    echo ""
fi

if kubectl get namespace terrarium >/dev/null 2>&1; then
    echo "Kubernetes logs:"
    echo "CDP Client pods:"
    kubectl get pods -n terrarium -l app=cdp-client
    echo ""
    echo "Service Sink pods:"
    kubectl get pods -n terrarium -l app=service-sink
    echo ""
fi

echo "Testing completed!"
echo ""
echo "Tips:"
echo "   - Check application logs for detailed request processing"
echo "   - View request files in /tmp/requests/ (CDP Client)"
echo "   - Use 'kubectl logs -n terrarium deployment/<service-name>' for K8s logs"
echo "   - Use 'docker-compose -f configs/docker/docker-compose.yml logs <service-name>' for Docker Compose logs"
