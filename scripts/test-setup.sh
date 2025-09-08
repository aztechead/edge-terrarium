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
    
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$url" || echo "000")
    
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

# Function to test POST endpoint with body
test_post_endpoint() {
    local url=$1
    local expected_service=$2
    local description=$3
    local post_data=$4
    
    echo "Testing: $description"
    echo "URL: $url"
    echo "POST Data: $post_data"
    
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json -X POST -H "Content-Type: application/json" -d "$post_data" --connect-timeout 10 --max-time 30 "$url" || echo "000")
    
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

# Function to test GET endpoint with query parameters
test_get_with_params() {
    local url=$1
    local expected_service=$2
    local description=$3
    local query_params=$4
    
    echo "Testing: $description"
    echo "URL: $url"
    echo "Query Params: $query_params"
    
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$url?$query_params" || echo "000")
    
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

# Function to test logthon functionality
test_logthon() {
    local base_url=$1
    local description=$2
    
    echo "Testing: $description"
    echo "================================="
    
    # Test logthon health endpoint
    echo "Testing Logthon health endpoint:"
    echo "--------------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/logs/health" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ Logthon health check - SUCCESS"
        echo "  ✓ HTML page loaded successfully"
    else
        echo "✗ Logthon health check - FAILED (HTTP $response)"
    fi
    echo ""
    
    # Test logthon web UI
    echo "Testing Logthon web UI:"
    echo "----------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.html --connect-timeout 10 --max-time 30 "$base_url/logs/" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ Logthon web UI - SUCCESS"
        if [ -f /tmp/response.html ]; then
            if grep -q "Logthon" /tmp/response.html; then
                echo "✓ Logthon web UI contains expected content"
            else
                echo "✗ Logthon web UI missing expected content"
            fi
        fi
    else
        echo "✗ Logthon web UI - FAILED (HTTP $response)"
    fi
    echo ""
    
    # Test logthon API endpoint
    echo "Testing Logthon API endpoint:"
    echo "----------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/logs/api/logs" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ Logthon API endpoint - SUCCESS"
        if [ -f /tmp/response.json ]; then
            # Count the number of logs in the response
            log_count=$(grep -o '"id":' /tmp/response.json | wc -l)
            echo "  ✓ Found $log_count log entries"
        fi
    else
        echo "✗ Logthon API endpoint - FAILED (HTTP $response)"
    fi
    echo ""
}

# Function to test file storage functionality
test_file_storage() {
    local base_url=$1
    local description=$2
    
    echo "Testing: $description"
    echo "================================="
    
    # Test file storage health endpoint
    echo "Testing File Storage health endpoint:"
    echo "------------------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/storage/health" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ File Storage health check - SUCCESS"
        if [ -f /tmp/response.json ]; then
            echo "  ✓ Health response: $(cat /tmp/response.json)"
        fi
    else
        echo "✗ File Storage health check - FAILED (HTTP $response)"
    fi
    echo ""
    
    # Test file storage info endpoint
    echo "Testing File Storage info endpoint:"
    echo "----------------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/storage/storage/info" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ File Storage info endpoint - SUCCESS"
        if [ -f /tmp/response.json ]; then
            echo "  ✓ Storage info: $(cat /tmp/response.json)"
        fi
    else
        echo "✗ File Storage info endpoint - FAILED (HTTP $response)"
    fi
    echo ""
    
    # Test file storage list endpoint
    echo "Testing File Storage list endpoint:"
    echo "----------------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/storage/files" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ File Storage list endpoint - SUCCESS"
        if [ -f /tmp/response.json ]; then
            file_count=$(grep -o '"filename":' /tmp/response.json | wc -l)
            echo "  ✓ Found $file_count files"
        fi
    else
        echo "✗ File Storage list endpoint - FAILED (HTTP $response)"
    fi
    echo ""
    
    # Test file creation endpoint
    echo "Testing File Storage create endpoint:"
    echo "------------------------------------"
    test_data='{"content": "Test file content from test script", "filename_prefix": "test", "extension": ".txt"}'
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json -X PUT -H "Content-Type: application/json" -d "$test_data" --connect-timeout 10 --max-time 30 "$base_url/storage/files" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ File Storage create endpoint - SUCCESS"
        if [ -f /tmp/response.json ]; then
            echo "  ✓ File created: $(cat /tmp/response.json)"
            # Extract filename for later tests
            created_filename=$(grep -o '"filename":"[^"]*"' /tmp/response.json | cut -d'"' -f4)
        fi
    else
        echo "✗ File Storage create endpoint - FAILED (HTTP $response)"
    fi
    echo ""
    
    
    # Test file retrieval if we created a file
    if [ -n "$created_filename" ]; then
        echo "Testing File Storage get endpoint:"
        echo "---------------------------------"
        response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/storage/files/$created_filename" || echo "000")
        
        if [ "$response" = "200" ]; then
            echo "✓ File Storage get endpoint - SUCCESS"
            if [ -f /tmp/response.json ]; then
                echo "  ✓ File content retrieved: $(cat /tmp/response.json)"
            fi
        else
            echo "✗ File Storage get endpoint - FAILED (HTTP $response)"
        fi
        echo ""
    fi
    
    # Test logthon file storage integration
    echo "Testing Logthon File Storage integration:"
    echo "----------------------------------------"
    response=$(curl -s -k -w "%{http_code}" -o /tmp/response.json --connect-timeout 10 --max-time 30 "$base_url/logs/api/files" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "✓ Logthon File Storage integration - SUCCESS"
        if [ -f /tmp/response.json ]; then
            file_count=$(grep -o '"filename":' /tmp/response.json | wc -l)
            echo "  ✓ Found $file_count files via logthon proxy"
        fi
    else
        echo "✗ Logthon File Storage integration - FAILED (HTTP $response)"
    fi
    echo ""
}

# Check if Docker Compose is running
if docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium ps | grep -q "Up"; then
    echo "Testing Docker Compose setup..."
    echo "================================"
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Initialize Vault if it's running
    if docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium ps | grep -q "vault.*Up"; then
        echo "Initializing Vault with secrets..."
        ./scripts/init-vault.sh http://localhost:8200
        echo ""
    fi
    
    # Test Custom Client routes
    test_endpoint "https://localhost:8443/fake-provider/test" "custom-client" "Custom Client - fake-provider route"
    test_endpoint "https://localhost:8443/example-provider/test" "custom-client" "Custom Client - example-provider route"
    
    # Test Service Sink (default route)
    test_endpoint "https://localhost:8443/api/test" "service-sink" "Service Sink - default route"
    test_endpoint "https://localhost:8443/health" "service-sink" "Service Sink - health check"
    
    # Test port 1337
    test_endpoint "https://localhost:8443/test" "custom-client" "Custom Client - port 1337"
    
    echo "Testing enhanced request logging..."
    echo "=================================="
    
    # Test GET requests with query parameters
    test_get_with_params "https://localhost:8443/fake-provider/test" "custom-client" "Custom Client - GET with query params" "param1=value1&param2=value2&test=query"
    test_get_with_params "https://localhost:8443/api/test" "service-sink" "Service Sink - GET with query params" "user=testuser&action=login&id=123"
    
    # Test POST requests with body content
    test_post_endpoint "https://localhost:8443/fake-provider/test" "custom-client" "Custom Client - POST with JSON body" '{"username":"testuser","password":"testpass","action":"login"}'
    test_post_endpoint "https://localhost:8443/api/test" "service-sink" "Service Sink - POST with JSON body" '{"data":"test data","timestamp":"2024-01-01","status":"active"}'
    
    # Test POST requests with form data
    test_post_endpoint "https://localhost:8443/example-provider/test" "custom-client" "Custom Client - POST with form data" "username=testuser&email=test@example.com&role=admin"
    test_post_endpoint "https://localhost:8443/health" "service-sink" "Service Sink - POST with form data" "check=health&service=all&verbose=true"
    
    # Test logthon functionality
    test_logthon "https://localhost:8443" "Docker Compose - Logthon Log Aggregation Service"
    
    # Test File Storage Service
    test_file_storage "https://localhost:8443" "Docker Compose - File Storage Service"
    
    # Test Vault secrets if it's running
    if docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium ps | grep -q "vault.*Up"; then
        echo "Testing Vault secrets..."
        echo "Checking for expected secrets:"
        
        # Test TLS certificates secret
        echo "Testing TLS certificates secret..."
        tls_response=$(curl -s -H "X-Vault-Token: root" "http://localhost:8200/v1/secret/data/terrarium/tls" 2>/dev/null)
        if echo "$tls_response" | grep -q '"cert"' && echo "$tls_response" | grep -q '"key"'; then
            echo "✓ TLS certificates secret found"
            echo "  ✓ Certificate and private key present"
        else
            echo "✗ TLS certificates secret not found or incomplete"
        fi
        
        # Test Custom client config secret
        echo "Testing Custom client config secret..."
        config_response=$(curl -s -H "X-Vault-Token: root" "http://localhost:8200/v1/secret/data/custom-client/config" 2>/dev/null)
        if echo "$config_response" | grep -q '"api_key"' && echo "$config_response" | grep -q '"database_url"'; then
            echo "✓ Custom client config secret found"
            config_count=$(echo "$config_response" | grep -o '"[^"]*":' | wc -l)
            echo "  ✓ Contains $config_count configuration keys"
        else
            echo "✗ Custom client config secret not found or incomplete"
        fi
        
        # Test Custom client external APIs secret
        echo "Testing Custom client external APIs secret..."
        apis_response=$(curl -s -H "X-Vault-Token: root" "http://localhost:8200/v1/secret/data/custom-client/external-apis" 2>/dev/null)
        if echo "$apis_response" | grep -q '"provider_auth_token"' && echo "$apis_response" | grep -q '"webhook_secret"'; then
            echo "✓ Custom client external APIs secret found"
            api_count=$(echo "$apis_response" | grep -o '"[^"]*":' | wc -l)
            echo "  ✓ Contains $api_count API configuration keys"
        else
            echo "✗ Custom client external APIs secret not found or incomplete"
        fi
        
        echo ""
    fi
    
    echo "Docker Compose tests completed!"
    echo ""
fi

# Check if Kubernetes deployment exists
if kubectl get namespace edge-terrarium >/dev/null 2>&1; then
    echo "Testing Kubernetes setup..."
    echo "================================"
    
    # Wait for pods to be ready
    echo "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=custom-client -n edge-terrarium --timeout=60s
    kubectl wait --for=condition=ready pod -l app=service-sink -n edge-terrarium --timeout=60s
    
    # Check if we can access the ingress directly
    ingress_ip=$(kubectl get ingress edge-terrarium-ingress -n edge-terrarium -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$ingress_ip" ] && [ "$ingress_ip" != "localhost" ]; then
        echo "Found ingress IP: $ingress_ip"
        echo "Testing connectivity to ingress..."
        
        # Test if we can actually reach the ingress
        if curl -k -s --connect-timeout 10 --max-time 30 "https://$ingress_ip:443/fake-provider/test" >/dev/null 2>&1; then
            echo "Ingress is accessible, running tests..."
            test_host="$ingress_ip"
            
            # Test Custom Client routes
            test_endpoint "https://$test_host:443/fake-provider/test" "custom-client" "K8s Custom Client - fake-provider route"
            test_endpoint "https://$test_host:443/example-provider/test" "custom-client" "K8s Custom Client - example-provider route"
            
            # Test Service Sink (default route)
            test_endpoint "https://$test_host:443/api/test" "service-sink" "K8s Service Sink - default route"
            
            echo "Testing enhanced request logging..."
            echo "=================================="
            
            # Test GET requests with query parameters
            test_get_with_params "https://$test_host:443/fake-provider/test" "custom-client" "K8s Custom Client - GET with query params" "param1=value1&param2=value2&test=query"
            test_get_with_params "https://$test_host:443/api/test" "service-sink" "K8s Service Sink - GET with query params" "user=testuser&action=login&id=123"
            
            # Test POST requests with body content
            test_post_endpoint "https://$test_host:443/fake-provider/test" "custom-client" "K8s Custom Client - POST with JSON body" '{"username":"testuser","password":"testpass","action":"login"}'
            test_post_endpoint "https://$test_host:443/api/test" "service-sink" "K8s Service Sink - POST with JSON body" '{"data":"test data","timestamp":"2024-01-01","status":"active"}'
            
            # Test logthon functionality
            test_logthon "https://$test_host:443" "Kubernetes - Logthon Log Aggregation Service"
            
            # Test File Storage Service
            test_file_storage "https://$test_host:443" "Kubernetes - File Storage Service"
        else
            echo "Ingress IP found but not accessible (no tunnel or firewall blocking)"
            echo "To test Kubernetes deployment, use one of these methods:"
            echo ""
            echo "1. Use the dedicated K3s test script:"
            echo "   ./scripts/test-k3s.sh"
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
            kubectl get pods -n edge-terrarium
            echo ""
            echo "Custom Client logs:"
            kubectl logs -n edge-terrarium deployment/custom-client --tail=5
            echo ""
            echo "Service Sink logs:"
            kubectl logs -n edge-terrarium deployment/service-sink --tail=5
        fi
    else
        echo "INFO: No ingress IP available for direct testing"
        echo "To test Kubernetes deployment, use one of these methods:"
        echo ""
        echo "1. Use the dedicated K3s test script:"
        echo "   ./scripts/test-k3s.sh"
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
        kubectl get pods -n edge-terrarium
        echo ""
        echo "Custom Client logs:"
        kubectl logs -n edge-terrarium deployment/custom-client --tail=5
        echo ""
        echo "Service Sink logs:"
        kubectl logs -n edge-terrarium deployment/service-sink --tail=5
    fi
    
    echo "Kubernetes tests completed!"
    echo ""
fi

# Check request logs
echo "Checking request logs..."
echo "=========================="

if docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium ps | grep -q "Up"; then
    echo "Docker Compose logs:"
    echo "Custom Client request files:"
    file_count=$(docker exec edge-terrarium-custom-client ls -1 /tmp/requests/ 2>/dev/null | wc -l)
    if [ "$file_count" -gt 0 ]; then
        echo "  ✓ Found $file_count request files"
    else
        echo "  No request files found"
    fi
    echo ""
fi

if kubectl get namespace edge-terrarium >/dev/null 2>&1; then
    echo "Kubernetes logs:"
    echo "Custom Client pods:"
    kubectl get pods -n edge-terrarium -l app=custom-client
    echo ""
    echo "Service Sink pods:"
    kubectl get pods -n edge-terrarium -l app=service-sink
    echo ""
fi

echo "Testing completed!"
echo ""
echo "Tips:"
echo "   - Check application logs for detailed request processing"
echo "   - View request files in /tmp/requests/ (Custom Client)"
echo "   - Use 'kubectl logs -n edge-terrarium deployment/<service-name>' for K8s logs"
echo "   - Use 'docker-compose -f configs/docker/docker-compose.yml logs <service-name>' for Docker Compose logs"
