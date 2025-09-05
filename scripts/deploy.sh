#!/bin/bash

# =============================================================================
# TERRARIUM DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys the Terrarium application to either Docker Compose
# or Minikube based on the environment specified

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [ENVIRONMENT] [ACTION]"
    echo ""
    echo "ENVIRONMENT:"
    echo "  docker     Deploy to Docker Compose (development)"
    echo "  k3s        Deploy to K3s (Kubernetes testing)"
    echo ""
    echo "ACTION:"
    echo "  deploy     Deploy the application (default)"
    echo "  test       Test the deployed application"
    echo "  clean      Clean up the deployment"
    echo "  logs       Show application logs"
    echo ""
    echo "Examples:"
    echo "  $0 docker deploy    # Deploy to Docker Compose"
    echo "  $0 k3s test         # Test K3s deployment"
    echo "  $0 docker clean     # Clean up Docker Compose"
}

# Function to deploy to Docker Compose
deploy_docker() {
    print_status "Deploying to Docker Compose..."
    
    # Check for port conflicts and handle them
    check_and_handle_port_conflicts() {
        local port=$1
        local service_name=$2
        
        if lsof -i :$port | grep -q "LISTEN"; then
            print_warning "Port $port is already in use. Checking for conflicting services..."
            
            # Check if k3d cluster is running
            if command -v k3d >/dev/null 2>&1 && k3d cluster list | grep -q "edge-terrarium"; then
                print_warning "k3d cluster 'edge-terrarium' is running and using port $port"
                print_status "Stopping k3d cluster to free up port $port..."
                k3d cluster stop edge-terrarium
                sleep 2
                
                # Verify port is now free
                if lsof -i :$port | grep -q "LISTEN"; then
                    print_error "Port $port is still in use after stopping k3d cluster"
                    print_error "Please manually stop the service using port $port and try again"
                    exit 1
                else
                    print_success "Port $port is now available"
                fi
            else
                print_error "Port $port is in use by another service"
                print_error "Please stop the service using port $port and try again"
                print_error "You can check what's using the port with: lsof -i :$port"
                exit 1
            fi
        fi
    }
    
    # Check for port conflicts on ports used by Docker Compose
    check_and_handle_port_conflicts 8200 "Vault"
    check_and_handle_port_conflicts 80 "HTTP"
    check_and_handle_port_conflicts 443 "HTTPS"
    check_and_handle_port_conflicts 1337 "CDP Client"
    check_and_handle_port_conflicts 8080 "Service Sink"
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/edge-terrarium.crt" ] || [ ! -f "certs/edge-terrarium.key" ]; then
        print_status "Generating TLS certificates..."
        ./scripts/generate-certs.sh
    fi
    
    # Build images
    print_status "Building Docker images..."
    ./scripts/build-images.sh
    
    # Start services (includes automatic Vault initialization)
    print_status "Starting services with Docker Compose..."
    docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check if vault-init completed successfully
    print_status "Checking Vault initialization status..."
    if docker logs edge-terrarium-vault-init 2>/dev/null | grep -q "Vault initialization completed successfully"; then
        print_success "Vault initialization completed automatically!"
    else
        print_warning "Vault initialization may still be in progress. Check logs with: docker logs edge-terrarium-vault-init"
    fi
    
    print_success "Docker Compose deployment completed!"
    echo ""
    echo "Services are running:"
    echo "  - CDP Client: https://localhost:443/fake-provider/* and /example-provider/*"
    echo "  - Service Sink: https://localhost:443/ (default route)"
    echo "  - Vault: http://localhost:8200"
    echo ""
    echo "To test the deployment:"
    echo "  ./scripts/test-setup.sh"
}

# Function to deploy to K3s
deploy_k3s() {
    print_status "Deploying to K3s..."
    
    # Check if Docker Compose is running and stop it
    if docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium ps | grep -q "Up"; then
        print_warning "Docker Compose deployment is running. Stopping it first..."
        docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium down
        print_success "Docker Compose deployment stopped."
    fi
    
    # Check for port conflicts with Docker Compose services
    check_k3s_port_conflicts() {
        local port=$1
        local service_name=$2
        
        if lsof -i :$port | grep -q "LISTEN"; then
            print_warning "Port $port is already in use. This may conflict with K3s deployment..."
            print_warning "K3s will use different ports for external access via k3d loadbalancer"
        fi
    }
    
    # Check for potential port conflicts
    check_k3s_port_conflicts 8200 "Vault"
    check_k3s_port_conflicts 80 "HTTP"
    check_k3s_port_conflicts 443 "HTTPS"
    
    # Check if K3s is running
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "K3s is not running. Please start K3s first:"
        echo "  curl -sfL https://get.k3s.io | sh -"
        echo "  or"
        echo "  sudo systemctl start k3s"
        exit 1
    fi
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/edge-terrarium.crt" ] || [ ! -f "certs/edge-terrarium.key" ]; then
        print_status "Generating TLS certificates..."
        ./scripts/generate-certs.sh
    fi
    
    # Build images for K3s
    print_status "Building Docker images for K3s..."
    ./scripts/build-images-k3s.sh
    
    # Note: K3s comes with Traefik by default, but we're using Kong
    print_status "Note: K3s comes with Traefik by default, but we're using Kong ingress controller"
    print_status "Make sure Kong ingress controller is installed in your K3s cluster"
    
    # Apply base Kubernetes configurations (excluding problematic ingress)
    print_status "Applying base Kubernetes configurations..."
    kubectl apply -f configs/k3s/namespace.yaml
    kubectl apply -f configs/k3s/vault-config.yaml
    kubectl apply -f configs/k3s/vault-pvc.yaml
    kubectl apply -f configs/k3s/vault-service.yaml
    kubectl apply -f configs/k3s/services.yaml
    kubectl apply -f configs/k3s/cdp-client-deployment.yaml
    kubectl apply -f configs/k3s/service-sink-deployment.yaml
    
    # Apply TLS secret
    print_status "Applying TLS secret..."
    kubectl apply -f certs/edge-terrarium-tls-secret.yaml
    
    # Apply K3s-specific configurations
    print_status "Applying K3s-specific configurations..."
    kubectl apply -f configs/k3s/vault-deployment.yaml
    kubectl apply -f configs/k3s/vault-init-job.yaml
    kubectl apply -f configs/k3s/ingress.yaml
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cdp-client -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/service-sink -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/vault -n edge-terrarium
    
    # Wait for Vault init job to complete
    print_status "Waiting for Vault initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/vault-init -n edge-terrarium
    
    # Set up automatic port forwarding for Vault
    print_status "Setting up Vault port forwarding..."
    kubectl port-forward -n edge-terrarium service/vault 8200:8200 &
    VAULT_PORT_FORWARD_PID=$!
    echo $VAULT_PORT_FORWARD_PID > /tmp/vault-port-forward.pid
    sleep 3
    
    # Verify Vault is accessible
    if curl -s http://localhost:8200/v1/sys/health > /dev/null; then
        print_success "Vault is accessible at http://localhost:8200"
    else
        print_warning "Vault port forwarding may not be working properly"
    fi
    
    print_success "K3s deployment completed!"
    echo ""
    echo "Services are running in K3s:"
    echo "  - CDP Client: Available via Kong ingress"
    echo "  - Service Sink: Available via Kong ingress"
    echo "  - Vault: Available at http://localhost:8200 (port forwarded)"
    echo ""
    echo "Vault UI Access:"
    echo "  URL: http://localhost:8200"
    echo "  Token: root"
    echo ""
    echo "To test the deployment:"
    echo "  ./scripts/test-k3s.sh"
    echo ""
    echo "To stop Vault port forwarding:"
    echo "  kill \$(cat /tmp/vault-port-forward.pid) && rm /tmp/vault-port-forward.pid"
    echo ""
    echo "To access via Kong ingress:"
    echo "  # Get Kong proxy IP: kubectl get svc -n kong kong-proxy"
    echo "  # Then: curl -k -H 'Host: edge-terrarium.local' https://<kong-ip>/fake-provider/test"
}

# Function to test Docker Compose deployment
test_docker() {
    print_status "Testing Docker Compose deployment..."
    ./scripts/test-setup.sh
}

# Function to test K3s deployment
test_k3s() {
    print_status "Testing K3s deployment..."
    ./scripts/test-k3s.sh
}

# Function to clean up Docker Compose
clean_docker() {
    print_status "Cleaning up Docker Compose deployment..."
    docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium down -v
    print_success "Docker Compose cleanup completed!"
}

# Function to clean up K3s
clean_k3s() {
    print_status "Cleaning up K3s deployment..."
    kubectl delete -k configs/k3s/ --ignore-not-found=true
    kubectl delete secret edge-terrarium-tls -n edge-terrarium --ignore-not-found=true
    print_success "K3s cleanup completed!"
}

# Function to show logs
show_logs() {
    local environment=$1
    
    if [ "$environment" = "docker" ]; then
        print_status "Showing Docker Compose logs..."
        docker-compose -f configs/docker/docker-compose.yml -p c-edge-terrarium logs -f
    elif [ "$environment" = "k3s" ]; then
        print_status "Showing K3s logs..."
        echo "CDP Client logs:"
        kubectl logs -n edge-terrarium deployment/cdp-client
        echo ""
        echo "Service Sink logs:"
        kubectl logs -n edge-terrarium deployment/service-sink
        echo ""
        echo "Vault logs:"
        kubectl logs -n edge-terrarium deployment/vault
    fi
}

# Main script logic
main() {
    local environment=$1
    local action=${2:-deploy}
    
    # Validate environment
    if [ -z "$environment" ]; then
        print_error "Environment not specified"
        show_usage
        exit 1
    fi
    
    if [ "$environment" != "docker" ] && [ "$environment" != "k3s" ]; then
        print_error "Invalid environment: $environment"
        show_usage
        exit 1
    fi
    
    # Validate action
    if [ "$action" != "deploy" ] && [ "$action" != "test" ] && [ "$action" != "clean" ] && [ "$action" != "logs" ]; then
        print_error "Invalid action: $action"
        show_usage
        exit 1
    fi
    
    # Execute action based on environment
    case "$action" in
        "deploy")
            if [ "$environment" = "docker" ]; then
                deploy_docker
            else
                deploy_k3s
            fi
            ;;
        "test")
            if [ "$environment" = "docker" ]; then
                test_docker
            else
                test_k3s
            fi
            ;;
        "clean")
            if [ "$environment" = "docker" ]; then
                clean_docker
            else
                clean_k3s
            fi
            ;;
        "logs")
            show_logs "$environment"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
