#!/bin/bash

# =============================================================================
# TERRARIUM DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys the Terrarium application to either Docker Compose
# or K3s based on the environment specified
#
# Environment Variables:
#   CLEANUP_DASHBOARD=true - Force cleanup of Kubernetes Dashboard during teardown

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

# Function to install k3d
install_k3d() {
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
}

# Function to install helm
install_helm() {
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
    
    # First, ensure K3s is completely cleaned up
    print_status "Ensuring K3s deployment is completely cleaned up..."
    if command -v k3d >/dev/null 2>&1 && k3d cluster list | grep -q "edge-terrarium"; then
        print_warning "K3s cluster 'edge-terrarium' exists. Cleaning it up completely..."
        k3d cluster delete edge-terrarium
        print_success "K3s cluster deleted"
    fi
    
    # Stop any running kubectl port forwards
    if [ -f /tmp/vault-port-forward.pid ]; then
        print_status "Stopping any running kubectl port forwards..."
        kill $(cat /tmp/vault-port-forward.pid) 2>/dev/null || true
        rm -f /tmp/vault-port-forward.pid
    fi
    
    # Check for port conflicts and handle them
    check_and_handle_port_conflicts() {
        local port=$1
        local service_name=$2
        local strict_mode=${3:-true}  # Default to strict mode for Docker
        
        if lsof -i :$port | grep -q "LISTEN"; then
            print_warning "Port $port is already in use. Checking for conflicting services..."
            
            # Check if it's a Docker container using the port
            local container_using_port=$(docker ps --format "table {{.Names}}\t{{.Ports}}" | grep ":$port->" | awk '{print $1}' | head -1)
            if [ -n "$container_using_port" ]; then
                print_warning "Docker container '$container_using_port' is using port $port"
                print_status "Stopping container '$container_using_port'..."
                docker stop "$container_using_port" 2>/dev/null || true
                docker rm "$container_using_port" 2>/dev/null || true
                sleep 2
            fi
            
            # Verify port is now free
            if lsof -i :$port | grep -q "LISTEN"; then
                if [ "$strict_mode" = "true" ]; then
                    print_error "Port $port is still in use after cleanup attempts"
                    print_error "Please manually stop the service using port $port and try again"
                    print_error "You can check what's using the port with: lsof -i :$port"
                    exit 1
                else
                    print_warning "Port $port is still in use after stopping container"
                    print_warning "K3s will use different ports for external access via k3d loadbalancer"
                fi
            else
                print_success "Port $port is now available"
            fi
        fi
    }
    
    # Check for port conflicts on ports used by Docker Compose
    check_and_handle_port_conflicts 8200 "Vault"
    check_and_handle_port_conflicts 80 "HTTP"
    check_and_handle_port_conflicts 443 "HTTPS"
    check_and_handle_port_conflicts 1337 "Custom Client"
    check_and_handle_port_conflicts 8080 "Service Sink"
    check_and_handle_port_conflicts 5001 "Logthon"
    
    # Final verification that all required ports are free
    print_status "Verifying all required ports are available..."
    local required_ports=(8200 80 443 1337 8080 5001)
    local ports_in_use=()
    
    for port in "${required_ports[@]}"; do
        if lsof -i :$port | grep -q "LISTEN"; then
            ports_in_use+=($port)
        fi
    done
    
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        print_error "The following ports are still in use: ${ports_in_use[*]}"
        print_error "Please manually stop the services using these ports and try again"
        print_error "You can check what's using the ports with: lsof -i :<port>"
        exit 1
    fi
    
    print_success "All required ports are available"
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/edge-terrarium.crt" ] || [ ! -f "certs/edge-terrarium.key" ]; then
        print_status "Generating TLS certificates..."
        ./scripts/generate-tls-certs.sh
    fi
    
    # Build images with smart caching
    print_status "Building Docker images with smart caching..."
    if ! ./scripts/build-images-smart.sh; then
        print_error "Failed to build Docker images"
        exit 1
    fi
    
    # Start services (includes automatic Vault initialization)
    print_status "Starting services with Docker Compose..."
    docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium up -d
    
    # Wait for services to be ready
    print_status "Services are ready..."
    
    # Check if vault-init completed successfully
    print_status "Checking Vault initialization status..."
    if docker logs edge-terrarium-vault-init 2>/dev/null | grep -q "Vault initialization completed successfully"; then
        print_success "Vault initialization completed automatically!"
        
        # Extract UI access token from logs if available
        UI_TOKEN=$(docker logs edge-terrarium-vault-init 2>/dev/null | grep -A3 "UI Access Token:" | grep -E "^hvs\." | head -1)
        if [ -n "$UI_TOKEN" ]; then
            echo ""
            echo "=========================================="
            echo "VAULT UI ACCESS INFORMATION"
            echo "=========================================="
            echo "Vault UI URL: http://localhost:8200/ui"
            echo "UI Access Token: $UI_TOKEN"
            echo "Root Token: root"
            echo "=========================================="
            echo ""
        fi
    else
        print_warning "Vault initialization may still be in progress. Check logs with: docker logs edge-terrarium-vault-init"
    fi
    
    # Verify services are working
    verify_docker_service() {
        local service_name=$1
        local url=$2
        local container_name=$3
        
        print_status "Verifying $service_name service is working..."
        sleep 2  # Give service time to start
        
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name service is healthy"
        else
            print_warning "$service_name service may not be fully ready yet"
            print_status "Checking $service_name container logs..."
            docker logs "$container_name" --tail 10
        fi
    }
    
    verify_docker_service "Logthon" "http://localhost:5001/health" "edge-terrarium-logthon"
    verify_docker_service "File Storage" "http://localhost:9000/health" "edge-terrarium-file-storage"
    
    print_success "Docker Compose deployment completed!"
    echo ""
    echo "Services are running:"
    echo "  - Custom Client: https://localhost:443/fake-provider/* and /example-provider/*"
    echo "  - Service Sink: https://localhost:443/ (default route)"
    echo "  - File Storage: https://localhost:443/storage/* and http://localhost:9000"
    echo "  - Logthon: http://localhost:5001"
    echo "  - Vault: http://localhost:8200"
    echo ""
    echo "To test the deployment:"
    echo "  ./scripts/test-docker.sh"
}

# Function to deploy to K3s
deploy_k3s() {
    print_status "Deploying to K3s..."
    
    # First, ensure Docker Compose is completely cleaned up
    print_status "Ensuring Docker Compose deployment is completely cleaned up..."
    if docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps | grep -q "Up"; then
        print_warning "Docker Compose deployment is running. Stopping it completely..."
        docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium down -v
        print_success "Docker Compose deployment stopped and volumes removed."
    fi
    
    # Also check for any individual containers that might be running
    local running_containers=$(docker ps --filter "name=edge-terrarium" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$running_containers" ]; then
        print_warning "Found running edge-terrarium containers. Stopping them..."
        echo "$running_containers" | xargs docker stop 2>/dev/null || true
        echo "$running_containers" | xargs docker rm 2>/dev/null || true
        print_success "Edge-terrarium containers stopped and removed."
    fi
    
    # Use the consolidated port conflict checking function
    check_and_handle_port_conflicts() {
        local port=$1
        local service_name=$2
        local strict_mode=${3:-false}  # Default to non-strict mode for K3s
        
        if lsof -i :$port | grep -q "LISTEN"; then
            print_warning "Port $port is already in use. Checking for conflicting services..."
            
            # Check if it's a Docker container using the port
            local container_using_port=$(docker ps --format "table {{.Names}}\t{{.Ports}}" | grep ":$port->" | awk '{print $1}' | head -1)
            if [ -n "$container_using_port" ]; then
                print_warning "Docker container '$container_using_port' is using port $port"
                print_status "Stopping container '$container_using_port'..."
                docker stop "$container_using_port" 2>/dev/null || true
                docker rm "$container_using_port" 2>/dev/null || true
                sleep 2
            fi
            
            # Verify port is now free
            if lsof -i :$port | grep -q "LISTEN"; then
                if [ "$strict_mode" = "true" ]; then
                    print_error "Port $port is still in use after cleanup attempts"
                    print_error "Please manually stop the service using port $port and try again"
                    print_error "You can check what's using the port with: lsof -i :$port"
                    exit 1
                else
                    print_warning "Port $port is still in use after stopping container"
                    print_warning "K3s will use different ports for external access via k3d loadbalancer"
                fi
            else
                print_success "Port $port is now available"
            fi
        fi
    }
    
    # Check for potential port conflicts (non-strict mode for K3s)
    check_and_handle_port_conflicts 8200 "Vault" false
    check_and_handle_port_conflicts 80 "HTTP" false
    check_and_handle_port_conflicts 443 "HTTPS" false
    check_and_handle_port_conflicts 5001 "Logthon" false
    
    # Final verification that critical ports are free
    print_status "Verifying critical ports are available for K3s..."
    local critical_ports=(8200 80 443 5001)
    local ports_in_use=()
    
    for port in "${critical_ports[@]}"; do
        if lsof -i :$port | grep -q "LISTEN"; then
            ports_in_use+=($port)
        fi
    done
    
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        print_warning "The following ports are still in use: ${ports_in_use[*]}"
        print_warning "K3s will use different ports for external access via k3d loadbalancer"
        print_warning "This may cause conflicts - consider stopping the services using these ports"
    else
        print_success "All critical ports are available"
    fi
    
    # Check if k3d cluster exists and create if needed
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_status "K3s cluster not found. Creating k3d cluster..."
        
        # Check if k3d cluster already exists by name
        if command -v k3d &> /dev/null && k3d cluster list | grep -q "edge-terrarium"; then
            print_warning "k3d cluster 'edge-terrarium' already exists but kubectl is not connected"
            print_status "Starting existing k3d cluster..."
            k3d cluster start edge-terrarium
            sleep 2
            
            # Verify cluster is now accessible
            if kubectl cluster-info >/dev/null 2>&1; then
                print_success "Successfully connected to existing k3d cluster"
                
                # Ensure we're using the correct context
                if ! kubectl config current-context | grep -q "k3d-edge-terrarium"; then
                    print_status "Switching to k3d-edge-terrarium context..."
                    kubectl config use-context k3d-edge-terrarium
                fi
            else
                print_error "Failed to connect to existing k3d cluster"
                print_status "Checking cluster status..."
                k3d cluster list
                print_status "Attempting to get cluster info..."
                kubectl cluster-info
                exit 1
            fi
        else
            # Check if k3d is installed
            if ! command -v k3d &> /dev/null; then
                install_k3d
            fi
            
            # Create k3d cluster with port mappings
            print_status "Creating new k3d cluster 'edge-terrarium'..."
            k3d cluster create edge-terrarium \
                --port "80:80@loadbalancer" \
                --port "443:443@loadbalancer" \
                --port "8200:8200@loadbalancer" \
                --port "5001:5001@loadbalancer" \
                --port "8443:8443@loadbalancer" \
                --api-port 6443 \
                --k3s-arg "--disable=traefik@server:0" \
                --wait
            
            print_success "k3d cluster 'edge-terrarium' created successfully"
            
            # Wait for the cluster to be fully ready
            print_status "Waiting for cluster to be fully ready..."
            sleep 2
            
            # Verify cluster is accessible
            if ! kubectl cluster-info >/dev/null 2>&1; then
                print_error "Failed to connect to newly created k3d cluster"
                exit 1
            fi
        fi
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
    if [ ! -f "certs/edge-terrarium.crt" ] || [ ! -f "certs/edge-terrarium.key" ]; then
        ./scripts/generate-tls-certs.sh
    fi
    
    # Create namespace if it doesn't exist
    print_status "Creating edge-terrarium namespace..."
    kubectl create namespace edge-terrarium --dry-run=client -o yaml | kubectl apply -f -
    
    # Create Kubernetes TLS secret
    print_status "Creating Kubernetes TLS secret..."
    kubectl create secret tls edge-terrarium-tls \
        --cert=certs/edge-terrarium.crt \
        --key=certs/edge-terrarium.key \
        -n edge-terrarium \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Build images for K3s with smart caching
    print_status "Building Docker images for K3s with smart caching..."
    if ! ./scripts/build-images-k3s-smart.sh; then
        print_error "Failed to build Docker images for K3s"
        exit 1
    fi
    
    # Import images into k3d cluster
    print_status "Importing Docker images into k3d cluster..."
    
    print_status "Importing Custom Client image..."
    if ! k3d image import edge-terrarium-custom-client:latest -c edge-terrarium; then
        print_error "Failed to import Custom Client image into k3d cluster"
        exit 1
    fi
    
    print_status "Importing Service Sink image..."
    if ! k3d image import edge-terrarium-service-sink:latest -c edge-terrarium; then
        print_error "Failed to import Service Sink image into k3d cluster"
        exit 1
    fi
    
    print_status "Importing Logthon image..."
    if ! k3d image import edge-terrarium-logthon:latest -c edge-terrarium; then
        print_error "Failed to import Logthon image into k3d cluster"
        exit 1
    fi
    
    print_status "Importing File Storage image..."
    if ! k3d image import edge-terrarium-file-storage:latest -c edge-terrarium; then
        print_error "Failed to import File Storage image into k3d cluster"
        exit 1
    fi
    
    print_status "Importing Kong image..."
    if ! k3d image import edge-terrarium-kong:0.0.1 -c edge-terrarium; then
        print_error "Failed to import Kong image into k3d cluster"
        exit 1
    fi
    
    print_success "All images imported successfully into k3d cluster"
    
    # Install Kong ingress controller
    print_status "Installing Kong ingress controller..."
    helm repo add kong https://charts.konghq.com >/dev/null 2>&1 || true
    helm repo update >/dev/null 2>&1
    
    # Uninstall any existing Kong installation
    helm uninstall kong >/dev/null 2>&1 || true
    sleep 2
    
    # Install Kong with custom image
    helm install kong kong/kong \
        --set image.repository=edge-terrarium-kong \
        --set image.tag=0.0.1 \
        --set ingressController.enabled=true \
        --set ingressController.ingressClass=kong \
        --set admin.enabled=false \
        --set manager.enabled=false \
        --set portal.enabled=false \
        --set postgresql.enabled=false \
        --set replicaCount=1 \
        --set proxy.type=LoadBalancer \
        --set proxy.http.enabled=true \
        --set proxy.tls.enabled=true \
        --set resources.requests.memory=128Mi \
        --set resources.requests.cpu=100m \
        --set resources.limits.memory=256Mi \
        --set resources.limits.cpu=200m \
        >/dev/null 2>&1
    
    print_status "Waiting for Kong to be ready..."
    kubectl wait --for=condition=ready pod -l app=kong-kong -n default --timeout=120s
    
    if [ $? -ne 0 ]; then
        print_error "Kong pods failed to become ready"
        print_status "Checking Kong pod status..."
        kubectl get pods -l app=kong-kong -n default
        print_status "Checking Kong pod logs..."
        kubectl logs -l app=kong-kong -n default --tail=50
        exit 1
    fi
    
    print_success "Kong is ready"
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        install_helm
    fi

    # Verify cluster is accessible before installing Kong
    print_status "Verifying cluster connectivity..."
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "Cannot connect to Kubernetes cluster"
        print_status "Checking cluster status..."
        kubectl cluster-info
        exit 1
    fi
    
    
    # Install Kubernetes Dashboard (only if not already installed)
    print_status "Checking Kubernetes Dashboard installation..."
    helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/ >/dev/null 2>&1 || true
    
    # Check if dashboard is already installed
    if helm list -n kubernetes-dashboard | grep -q "kubernetes-dashboard"; then
        print_status "Kubernetes Dashboard is already installed, skipping installation"
    else
        print_status "Installing Kubernetes Dashboard..."
        helm repo update >/dev/null 2>&1
        
        # Install Kubernetes Dashboard
        helm install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
            --create-namespace \
            --namespace kubernetes-dashboard \
            --set kong.proxy.type=LoadBalancer \
            --set kong.proxy.http.enabled=true \
            --set kong.proxy.http.containerPort=8000 \
            --set kong.proxy.http.servicePort=80 \
            >/dev/null 2>&1
    fi
    
    print_status "Waiting for Kubernetes Dashboard to be ready..."
    kubectl wait --for=condition=available --timeout=120s deployment/kubernetes-dashboard-kong -n kubernetes-dashboard
    
    if [ $? -ne 0 ]; then
        print_warning "Kubernetes Dashboard deployment may not be ready yet"
        print_status "Checking dashboard pod status..."
        kubectl get pods -n kubernetes-dashboard
    else
        print_success "Kubernetes Dashboard is ready"
    fi
    
    # Create dashboard admin service account and token
    print_status "Setting up Kubernetes Dashboard authentication..."
    kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin --dry-run=client -o yaml | kubectl apply -f -
    
    # Generate and display the token
    DASHBOARD_TOKEN=$(kubectl -n kubernetes-dashboard create token dashboard-admin)
    print_success "Kubernetes Dashboard authentication configured"
    echo ""
    echo "=========================================="
    echo "KUBERNETES DASHBOARD ACCESS INFORMATION"
    echo "=========================================="
    echo "Dashboard Token: $DASHBOARD_TOKEN"
    echo ""
    echo "Access Methods:"
    echo "1. Port Forward Access (Recommended):"
    echo "   Command: kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 9443:443"
    echo "   URL: https://localhost:9443"
    echo "   Token: $DASHBOARD_TOKEN"
    echo ""
    echo "2. Direct LoadBalancer Access (Alternative):"
    echo "   URL: https://localhost:443 (may conflict with main Kong ingress)"
    echo "   Token: $DASHBOARD_TOKEN"
    echo ""
    echo "=========================================="
    echo ""
    
    # Set up automatic port forwarding for Dashboard
    print_status "Setting up Kubernetes Dashboard port forwarding..."
    
    # Check if port 9443 is already in use
    if lsof -i :9443 > /dev/null 2>&1; then
        print_warning "Port 9443 is already in use. Dashboard port forwarding may not work properly."
        print_status "You can manually set up port forwarding with:"
        echo "  kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 9443:443"
    else
        # Try to set up port forwarding on port 9443
        if kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 9443:443 >/dev/null 2>&1 &
        then
            DASHBOARD_PORT_FORWARD_PID=$!
            echo $DASHBOARD_PORT_FORWARD_PID > /tmp/dashboard-port-forward.pid
            sleep 3
            
            # Verify Dashboard is accessible
            if curl -k -s https://localhost:9443 > /dev/null; then
                print_success "Kubernetes Dashboard is accessible at https://localhost:9443 (port forwarded)"
            else
                print_warning "Dashboard port forwarding may not be working properly"
            fi
        else
            print_warning "Could not set up Dashboard port forwarding on port 9443"
            print_status "You can manually set up port forwarding with:"
            echo "  kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 9443:443"
        fi
    fi
    
    # Clean up any existing Vault init job to ensure fresh initialization
    print_status "Cleaning up any existing Vault initialization job..."
    kubectl delete job vault-init -n edge-terrarium --ignore-not-found=true
    sleep 2
    
    # Apply all Kubernetes configurations using kustomize
    print_status "Applying Kubernetes configurations using kustomize..."
    kubectl apply -k configs/k3s/
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/custom-client -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/service-sink -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/logthon -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/file-storage -n edge-terrarium
    kubectl wait --for=condition=available --timeout=300s deployment/vault -n edge-terrarium
    
    # Wait for Vault init job to complete
    print_status "Waiting for Vault initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/vault-init -n edge-terrarium
    
    # Check if the Vault init job succeeded
    if [ $? -ne 0 ]; then
        print_error "Vault initialization job failed or timed out"
        print_status "Checking Vault init job status..."
        kubectl describe job vault-init -n edge-terrarium
        print_status "Checking Vault init job logs..."
        kubectl logs job/vault-init -n edge-terrarium --tail=50
        exit 1
    fi
    
    print_success "Vault initialization job completed successfully"
    
    # Extract UI access token from Vault init job logs if available
    UI_TOKEN=$(kubectl logs job/vault-init -n edge-terrarium 2>/dev/null | grep -A3 "UI Access Token:" | grep -E "^hvs\." | head -1)
    if [ -n "$UI_TOKEN" ]; then
        echo ""
        echo "=========================================="
        echo "VAULT UI ACCESS INFORMATION"
        echo "=========================================="
        echo "Vault UI URL: http://localhost:8200/ui"
        echo "UI Access Token: $UI_TOKEN"
        echo "Root Token: root"
        echo "=========================================="
        echo ""
    fi
    
    # Verify that secrets were actually stored in Vault
    print_status "Verifying Vault secrets were stored..."
    
    # Set up temporary port forwarding for verification
    kubectl port-forward -n edge-terrarium service/vault 8201:8200 >/dev/null 2>&1 &
    VAULT_VERIFY_PID=$!
    sleep 3
    
    # Check if secrets exist
    if curl -s -H "X-Vault-Token: root" http://localhost:8201/v1/secret/data/custom-client/config >/dev/null 2>&1; then
        print_success "Custom client config secrets verified in Vault"
    else
        print_error "Custom client config secrets not found in Vault"
        kill $VAULT_VERIFY_PID 2>/dev/null || true
        exit 1
    fi
    
    if curl -s -H "X-Vault-Token: root" http://localhost:8201/v1/secret/data/custom-client/external-apis >/dev/null 2>&1; then
        print_success "Custom client external APIs secrets verified in Vault"
    else
        print_error "Custom client external APIs secrets not found in Vault"
        kill $VAULT_VERIFY_PID 2>/dev/null || true
        exit 1
    fi
    
    if curl -s -H "X-Vault-Token: root" http://localhost:8201/v1/secret/data/terrarium/tls >/dev/null 2>&1; then
        print_success "TLS secrets verified in Vault"
    else
        print_error "TLS secrets not found in Vault"
        kill $VAULT_VERIFY_PID 2>/dev/null || true
        exit 1
    fi
    
    # Clean up temporary port forward
    kill $VAULT_VERIFY_PID 2>/dev/null || true
    
    # Verify K3s services are working
    verify_k3s_service() {
        local service_name=$1
        local service_path=$2
        local local_port=$3
        local service_port=$4
        
        print_status "Verifying $service_name service is working..."
        
        # Set up temporary port forwarding for service verification
        kubectl port-forward -n edge-terrarium "$service_path" "$local_port:$service_port" >/dev/null 2>&1 &
        local verify_pid=$!
        sleep 3
        
        # Check if service is accessible
        if curl -s "http://localhost:$local_port/health" >/dev/null 2>&1; then
            print_success "$service_name service is accessible and healthy"
        else
            print_error "$service_name service is not accessible"
            kill $verify_pid 2>/dev/null || true
            exit 1
        fi
        
        # Clean up temporary port forward
        kill $verify_pid 2>/dev/null || true
    }
    
    verify_k3s_service "File Storage" "service/file-storage-service" 9001 9000
    verify_k3s_service "Logthon" "service/logthon-service" 5001 5000
    
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
    
    # Get external IP for accessing services
    print_status "Getting external access information..."
    
    # Try to get the external IP that can be used to access the services
    EXTERNAL_IP="localhost"
    
    # Check if we can get the host machine's IP
    if command -v hostname >/dev/null 2>&1; then
        # Try to get the primary network interface IP
        if command -v ip >/dev/null 2>&1; then
            # Linux
            HOST_IP=$(ip route get 1.1.1.1 | awk '{print $7; exit}' 2>/dev/null)
        elif command -v ifconfig >/dev/null 2>&1; then
            # macOS/BSD
            HOST_IP=$(ifconfig | grep -E "inet.*broadcast" | awk '{print $2}' | head -1)
        fi
        
        # Use host IP if we found one and it's not localhost
        if [ -n "$HOST_IP" ] && [ "$HOST_IP" != "127.0.0.1" ] && [ "$HOST_IP" != "::1" ]; then
            EXTERNAL_IP="$HOST_IP"
        fi
    fi
    
    print_success "K3s deployment completed!"
    echo ""
    echo "Services are running in K3s:"
    echo "  - Custom Client: Available via Kong ingress"
    echo "  - Service Sink: Available via Kong ingress"
    echo "  - File Storage: Available via Kong ingress at /storage/*"
    echo "  - Logthon: Available via Kong ingress at /logs/*"
    echo "  - Vault: Available at http://localhost:8200 (port forwarded)"
    echo "  - Kubernetes Dashboard: Available via port forwarding"
    echo ""
    echo "External Access Information:"
    echo "  Host IP: $EXTERNAL_IP"
    echo "  Access via: http://$EXTERNAL_IP or https://$EXTERNAL_IP"
    echo "  Kong LoadBalancer ports: 80 (HTTP), 443 (HTTPS), 8200 (Vault), 5001 (Logthon)"
    echo ""
    echo "Vault UI Access:"
    echo "  URL: http://localhost:8200"
    echo "  Token: root"
    echo ""
    echo "Kubernetes Dashboard Access:"
    echo "  URL: https://localhost:9443 (port forwarded)"
    echo "  Token: $DASHBOARD_TOKEN"
    echo "  Alternative: kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 9443:443"
    echo ""
    echo "To test the deployment:"
    echo "  ./scripts/test-k3s.sh"
    echo ""
    echo "To stop port forwarding:"
    echo "  Vault: kill \$(cat /tmp/vault-port-forward.pid) && rm /tmp/vault-port-forward.pid"
    echo "  Dashboard: kill \$(cat /tmp/dashboard-port-forward.pid) && rm /tmp/dashboard-port-forward.pid"
    echo ""
    echo "To access via Kong ingress:"
    echo "  # Get Kong proxy IP: kubectl get svc -n kong kong-proxy"
    echo "  # Then: curl -k -H 'Host: edge-terrarium.local' https://<kong-ip>/fake-provider/test"
}

# Function to test Docker Compose deployment
test_docker() {
    print_status "Testing Docker Compose deployment..."
    ./scripts/test-docker.sh
}

# Function to test K3s deployment
test_k3s() {
    print_status "Testing K3s deployment..."
    ./scripts/test-k3s.sh
}

# Function to clean up Docker Compose
clean_docker() {
    print_status "Cleaning up Docker Compose deployment..."
    docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium down -v
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
    
    if [ -f /tmp/dashboard-port-forward.pid ]; then
        kill $(cat /tmp/dashboard-port-forward.pid) 2>/dev/null || true
        rm -f /tmp/dashboard-port-forward.pid
    fi
    
    # Check if k3d cluster exists and is running
    if k3d cluster list | grep -q "edge-terrarium"; then
        print_status "K3s cluster found, cleaning up resources..."
        
        # Set kubectl context to k3d cluster
        kubectl config use-context k3d-edge-terrarium 2>/dev/null || true
        
        # Check if kubectl can connect to the cluster
        if kubectl cluster-info &>/dev/null; then
            # Clean up Kubernetes resources
            kubectl delete -k configs/k3s/ --ignore-not-found=true
            kubectl delete secret edge-terrarium-tls -n edge-terrarium --ignore-not-found=true
            
            # Clean up Kubernetes Dashboard (only if explicitly requested)
            if [ "$CLEANUP_DASHBOARD" = "true" ]; then
                print_status "Cleaning up Kubernetes Dashboard..."
                helm uninstall kubernetes-dashboard -n kubernetes-dashboard --ignore-not-found=true
                kubectl delete namespace kubernetes-dashboard --ignore-not-found=true
            else
                print_status "Skipping Kubernetes Dashboard cleanup (use CLEANUP_DASHBOARD=true to force cleanup)"
            fi
            
            print_status "Deleting k3d cluster 'edge-terrarium'..."
            k3d cluster delete edge-terrarium
            print_success "k3d cluster deleted"
        else
            print_warning "K3s cluster exists but is not responding, deleting cluster directly..."
            k3d cluster delete edge-terrarium
            print_success "k3d cluster deleted"
        fi
    else
        print_status "No K3s cluster found, nothing to clean up"
    fi
    
    print_success "K3s cleanup completed!"
}

# Function to show logs
show_logs() {
    local environment=$1
    
    if [ "$environment" = "docker" ]; then
        print_status "Showing Docker Compose logs..."
        docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium logs -f
    elif [ "$environment" = "k3s" ]; then
        print_status "Showing K3s logs..."
        echo "Custom Client logs:"
        kubectl logs -n edge-terrarium deployment/custom-client
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
