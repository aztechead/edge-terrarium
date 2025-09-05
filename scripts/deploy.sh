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
    echo "  minikube   Deploy to Minikube (Kubernetes testing)"
    echo ""
    echo "ACTION:"
    echo "  deploy     Deploy the application (default)"
    echo "  test       Test the deployed application"
    echo "  clean      Clean up the deployment"
    echo "  logs       Show application logs"
    echo ""
    echo "Examples:"
    echo "  $0 docker deploy    # Deploy to Docker Compose"
    echo "  $0 minikube test    # Test Minikube deployment"
    echo "  $0 docker clean     # Clean up Docker Compose"
}

# Function to deploy to Docker Compose
deploy_docker() {
    print_status "Deploying to Docker Compose..."
    
    # Check if Minikube is running and stop it
    if minikube status >/dev/null 2>&1; then
        print_warning "Minikube is running. Stopping it first to avoid conflicts..."
        minikube stop
        print_success "Minikube stopped."
    fi
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/terrarium.crt" ] || [ ! -f "certs/terrarium.key" ]; then
        print_status "Generating TLS certificates..."
        ./scripts/generate-certs.sh
    fi
    
    # Build images
    print_status "Building Docker images..."
    ./scripts/build-images.sh
    
    # Start services (includes automatic Vault initialization)
    print_status "Starting services with Docker Compose..."
    docker-compose -f configs/docker/docker-compose.yml -p c-terrarium up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check if vault-init completed successfully
    print_status "Checking Vault initialization status..."
    if docker logs terrarium-vault-init 2>/dev/null | grep -q "Vault initialization completed successfully"; then
        print_success "Vault initialization completed automatically!"
    else
        print_warning "Vault initialization may still be in progress. Check logs with: docker logs terrarium-vault-init"
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

# Function to deploy to Minikube
deploy_minikube() {
    print_status "Deploying to Minikube..."
    
    # Check if Docker Compose is running and stop it
    if docker-compose -f configs/docker/docker-compose.yml -p c-terrarium ps | grep -q "Up"; then
        print_warning "Docker Compose deployment is running. Stopping it first..."
        docker-compose -f configs/docker/docker-compose.yml -p c-terrarium down
        print_success "Docker Compose deployment stopped."
    fi
    
    # Check if Minikube is running
    if ! minikube status >/dev/null 2>&1; then
        print_error "Minikube is not running. Please start Minikube first:"
        echo "  minikube start"
        exit 1
    fi
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/terrarium.crt" ] || [ ! -f "certs/terrarium.key" ]; then
        print_status "Generating TLS certificates..."
        ./scripts/generate-certs.sh
    fi
    
    # Set up Minikube Docker environment
    print_status "Setting up Minikube Docker environment..."
    eval $(minikube docker-env)
    
    # Build images for Minikube
    print_status "Building Docker images for Minikube..."
    ./scripts/build-images-minikube.sh
    
    # Enable ingress addon
    print_status "Enabling NGINX ingress addon..."
    minikube addons enable ingress
    
    # Apply base Kubernetes configurations (excluding problematic ingress)
    print_status "Applying base Kubernetes configurations..."
    kubectl apply -f configs/k8s/namespace.yaml
    kubectl apply -f configs/k8s/vault-config.yaml
    kubectl apply -f configs/k8s/vault-pvc.yaml
    kubectl apply -f configs/k8s/vault-service.yaml
    kubectl apply -f configs/k8s/services.yaml
    kubectl apply -f configs/k8s/cdp-client-deployment.yaml
    kubectl apply -f configs/k8s/service-sink-deployment.yaml
    
    # Apply TLS secret
    print_status "Applying TLS secret..."
    kubectl apply -f certs/terrarium-tls-secret.yaml
    
    # Apply Minikube-specific configurations
    print_status "Applying Minikube-specific configurations..."
    kubectl apply -f configs/k8s/vault-deployment-minikube.yaml
    kubectl apply -f configs/k8s/vault-init-job-minikube.yaml
    kubectl apply -f configs/k8s/ingress-minikube.yaml
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cdp-client -n terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/service-sink -n terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/vault -n terrarium
    
    # Wait for Vault init job to complete
    print_status "Waiting for Vault initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/vault-init -n terrarium
    
    # Set up automatic port forwarding for Vault
    print_status "Setting up Vault port forwarding..."
    kubectl port-forward -n terrarium service/vault 8200:8200 &
    VAULT_PORT_FORWARD_PID=$!
    echo $VAULT_PORT_FORWARD_PID > /tmp/vault-port-forward.pid
    sleep 3
    
    # Verify Vault is accessible
    if curl -s http://localhost:8200/v1/sys/health > /dev/null; then
        print_success "Vault is accessible at http://localhost:8200"
    else
        print_warning "Vault port forwarding may not be working properly"
    fi
    
    print_success "Minikube deployment completed!"
    echo ""
    echo "Services are running in Minikube:"
    echo "  - CDP Client: Available via ingress"
    echo "  - Service Sink: Available via ingress"
    echo "  - Vault: Available at http://localhost:8200 (port forwarded)"
    echo ""
    echo "Vault UI Access:"
    echo "  URL: http://localhost:8200"
    echo "  Token: root"
    echo ""
    echo "To test the deployment:"
    echo "  ./scripts/test-minikube.sh"
    echo ""
    echo "To stop Vault port forwarding:"
    echo "  kill \$(cat /tmp/vault-port-forward.pid) && rm /tmp/vault-port-forward.pid"
    echo ""
    echo "To access via ingress (requires tunnel):"
    echo "  minikube tunnel"
    echo "  curl -k -H 'Host: localhost' https://192.168.49.2/fake-provider/test"
}

# Function to test Docker Compose deployment
test_docker() {
    print_status "Testing Docker Compose deployment..."
    ./scripts/test-setup.sh
}

# Function to test Minikube deployment
test_minikube() {
    print_status "Testing Minikube deployment..."
    ./scripts/test-minikube.sh
}

# Function to clean up Docker Compose
clean_docker() {
    print_status "Cleaning up Docker Compose deployment..."
    docker-compose -f configs/docker/docker-compose.yml -p c-terrarium down -v
    print_success "Docker Compose cleanup completed!"
}

# Function to clean up Minikube
clean_minikube() {
    print_status "Cleaning up Minikube deployment..."
    kubectl delete -k configs/k8s/ --ignore-not-found=true
    kubectl delete secret terrarium-tls -n terrarium --ignore-not-found=true
    print_success "Minikube cleanup completed!"
}

# Function to show logs
show_logs() {
    local environment=$1
    
    if [ "$environment" = "docker" ]; then
        print_status "Showing Docker Compose logs..."
        docker-compose -f configs/docker/docker-compose.yml -p c-terrarium logs -f
    elif [ "$environment" = "minikube" ]; then
        print_status "Showing Minikube logs..."
        echo "CDP Client logs:"
        kubectl logs -n terrarium deployment/cdp-client
        echo ""
        echo "Service Sink logs:"
        kubectl logs -n terrarium deployment/service-sink
        echo ""
        echo "Vault logs:"
        kubectl logs -n terrarium deployment/vault
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
    
    if [ "$environment" != "docker" ] && [ "$environment" != "minikube" ]; then
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
                deploy_minikube
            fi
            ;;
        "test")
            if [ "$environment" = "docker" ]; then
                test_docker
            else
                test_minikube
            fi
            ;;
        "clean")
            if [ "$environment" = "docker" ]; then
                clean_docker
            else
                clean_minikube
            fi
            ;;
        "logs")
            show_logs "$environment"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
