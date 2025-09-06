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
    echo "  k3s        Deploy to K3s via k3d (Kubernetes testing)"
    echo ""
    echo "ACTION:"
    echo "  deploy     Deploy the application (default)"
    echo "  test       Test the deployed application"
    echo "  clean      Clean up the deployment"
    echo "  logs       Show application logs"
    echo ""
    echo "Examples:"
    echo "  $0 docker deploy    # Deploy to Docker Compose"
    echo "  $0 k3s deploy       # Deploy to K3s (auto-creates k3d cluster if needed)"
    echo "  $0 k3s test         # Test K3s deployment"
    echo "  $0 docker clean     # Clean up Docker Compose"
    echo "  $0 k3s clean        # Clean up K3s deployment (deletes k3d cluster)"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker and Docker Compose (for docker environment)"
    echo "  - k3d (will be auto-installed if missing)"
    echo "  - helm (will be auto-installed if missing)"
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
        ./scripts/generate-tls-certs.sh
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
    
    # Check if k3d cluster exists and create if needed
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_status "K3s cluster not found. Creating k3d cluster..."
        
        # Check if k3d is installed
        if ! command -v k3d &> /dev/null; then
            print_status "k3d is not installed. Attempting to install k3d..."
            
            # Try to install k3d using the official install script
            if curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash; then
                print_success "k3d installed successfully via official install script"
            else
                print_warning "Official install script failed. Trying package manager..."
                
                # Try package managers based on OS
                if command -v brew &> /dev/null; then
                    print_status "Installing k3d via Homebrew..."
                    if brew install k3d; then
                        print_success "k3d installed successfully via Homebrew"
                    else
                        print_error "Homebrew installation failed"
                        exit 1
                    fi
                elif command -v apt-get &> /dev/null; then
                    print_status "Installing k3d via apt..."
                    if curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash; then
                        print_success "k3d installed successfully"
                    else
                        print_error "apt installation failed"
                        exit 1
                    fi
                else
                    print_error "k3d installation failed. Please install k3d manually:"
                    echo "  curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash"
                    echo "  or"
                    echo "  brew install k3d"
                    echo "  or visit: https://github.com/k3d-io/k3d?tab=readme-ov-file#get"
                    exit 1
                fi
            fi
        fi
        
        # Create k3d cluster with port mappings
        k3d cluster create edge-terrarium \
            --port "80:80@loadbalancer" \
            --port "443:443@loadbalancer" \
            --port "8200:8200@loadbalancer" \
            --port "5001:5001@loadbalancer"
        
        print_success "k3d cluster 'edge-terrarium' created successfully"
    else
        # Check if we're connected to the right cluster
        if ! kubectl config current-context | grep -q "k3d-edge-terrarium"; then
            print_warning "Connected to different cluster. Switching to k3d-edge-terrarium..."
            kubectl config use-context k3d-edge-terrarium
        fi
        print_status "K3s cluster is running"
    fi
    
    # Generate certificates and create K3s secret
    print_status "Generating TLS certificates and creating K3s secret..."
    ./scripts/create-k3s-tls-secret.sh
    
    # Build images for K3s
    print_status "Building Docker images for K3s..."
    ./scripts/build-images-k3s.sh
    
    # Import images into k3d cluster
    print_status "Importing Docker images into k3d cluster..."
    k3d image import edge-terrarium-cdp-client:latest -c edge-terrarium
    k3d image import edge-terrarium-service-sink:latest -c edge-terrarium
    k3d image import edge-terrarium-logthon:latest -c edge-terrarium
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_status "helm is not installed. Attempting to install helm..."
        
        # Try to install helm using the official install script
        if curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash; then
            print_success "helm installed successfully via official install script"
        else
            print_warning "Official helm install script failed. Trying package manager..."
            
            # Try package managers based on OS
            if command -v brew &> /dev/null; then
                print_status "Installing helm via Homebrew..."
                if brew install helm; then
                    print_success "helm installed successfully via Homebrew"
                else
                    print_error "Homebrew installation failed"
                    exit 1
                fi
            elif command -v apt-get &> /dev/null; then
                print_status "Installing helm via apt..."
                if curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash; then
                    print_success "helm installed successfully"
                else
                    print_error "apt installation failed"
                    exit 1
                fi
            else
                print_error "helm installation failed. Please install helm manually:"
                echo "  curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
                echo "  or"
                echo "  brew install helm"
                echo "  or visit: https://helm.sh/docs/intro/install/"
                exit 1
            fi
        fi
    fi

    # Install Kong ingress controller (lightweight configuration)
    print_status "Installing Kong ingress controller..."
    helm repo add kong https://charts.konghq.com >/dev/null 2>&1 || true
    helm repo update >/dev/null 2>&1
    
    # Uninstall any existing Kong installation
    helm uninstall kong >/dev/null 2>&1 || true
    sleep 2
    
    # Install Kong with K3s-compatible configuration
    helm install kong kong/kong \
        --set ingressController.enabled=true \
        --set ingressController.ingressClass=kong \
        --set admin.enabled=false \
        --set manager.enabled=false \
        --set portal.enabled=false \
        --set postgresql.enabled=false \
        --set replicaCount=1 \
        --set proxy.type=NodePort \
        --set proxy.http.nodePort=30080 \
        --set proxy.tls.nodePort=30443 \
        --set resources.requests.memory=128Mi \
        --set resources.requests.cpu=100m \
        --set resources.limits.memory=256Mi \
        --set resources.limits.cpu=200m \
        >/dev/null 2>&1
    
    print_status "Waiting for Kong to be ready..."
    kubectl wait --for=condition=ready pod -l app=kong-kong -n default --timeout=120s >/dev/null 2>&1
    
    # Apply all Kubernetes configurations using kustomize
    print_status "Applying Kubernetes configurations using kustomize..."
    kubectl apply -k configs/k3s/
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cdp-client -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/service-sink -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/logthon -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/vault -n edge-terrarium
    
    # Wait for Vault init job to complete
    print_status "Waiting for Vault initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/vault-init -n edge-terrarium
    
    # Set up automatic port forwarding for Vault (if port 8200 is not already in use)
    print_status "Setting up Vault port forwarding..."
    
    # Check if port 8200 is already in use
    if curl -s http://localhost:8200/v1/sys/health > /dev/null 2>&1; then
        print_success "Vault is already accessible at http://localhost:8200 (likely from Docker Compose)"
        echo "Note: Vault is accessible via existing port forwarding or Docker Compose"
    else
        # Try to set up port forwarding on port 8200
        if kubectl port-forward -n edge-terrarium service/vault 8200:8200 >/dev/null 2>&1 &
        then
            VAULT_PORT_FORWARD_PID=$!
            echo $VAULT_PORT_FORWARD_PID > /tmp/vault-port-forward.pid
            sleep 3
            
            # Verify Vault is accessible
            if curl -s http://localhost:8200/v1/sys/health > /dev/null; then
                print_success "Vault is accessible at http://localhost:8200 (port forwarded)"
            else
                print_warning "Vault port forwarding may not be working properly"
            fi
        else
            print_warning "Could not set up Vault port forwarding on port 8200 (port may be in use)"
            print_status "You can manually set up port forwarding with:"
            echo "  kubectl port-forward -n edge-terrarium service/vault 8201:8200"
            echo "  # Then access Vault at http://localhost:8201"
        fi
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
    
    # Stop any running port forwards
    if [ -f /tmp/vault-port-forward.pid ]; then
        kill $(cat /tmp/vault-port-forward.pid) 2>/dev/null || true
        rm -f /tmp/vault-port-forward.pid
    fi
    
    # Clean up Kubernetes resources
    kubectl delete -k configs/k3s/ --ignore-not-found=true
    kubectl delete secret edge-terrarium-tls -n edge-terrarium --ignore-not-found=true
    
    # Optionally delete the entire k3d cluster
    if kubectl config current-context | grep -q "k3d-edge-terrarium"; then
        print_status "Deleting k3d cluster 'edge-terrarium'..."
        k3d cluster delete edge-terrarium
        print_success "k3d cluster deleted"
    fi
    
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
