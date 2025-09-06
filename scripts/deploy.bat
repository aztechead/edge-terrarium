@echo off
REM =============================================================================
REM TERRARIUM DEPLOYMENT SCRIPT FOR WINDOWS
REM =============================================================================
REM This script deploys the Terrarium application to either Docker Compose
REM or Minikube based on the environment specified

setlocal enabledelayedexpansion

REM Check if at least one argument is provided
if "%~1"=="" (
    echo [ERROR] Environment not specified
    call :show_usage
    exit /b 1
)

set ENVIRONMENT=%1
set ACTION=%2
if "%ACTION%"=="" set ACTION=deploy

REM Validate environment
if not "%ENVIRONMENT%"=="docker" if not "%ENVIRONMENT%"=="k3s" (
    echo [ERROR] Invalid environment: %ENVIRONMENT%
    call :show_usage
    exit /b 1
)

REM Validate action
if not "%ACTION%"=="deploy" if not "%ACTION%"=="test" if not "%ACTION%"=="clean" if not "%ACTION%"=="logs" (
    echo [ERROR] Invalid action: %ACTION%
    call :show_usage
    exit /b 1
)

REM Execute action based on environment
if "%ACTION%"=="deploy" (
    if "%ENVIRONMENT%"=="docker" (
        call :deploy_docker
    ) else (
        call :deploy_k3s
    )
) else if "%ACTION%"=="test" (
    if "%ENVIRONMENT%"=="docker" (
        call :test_docker
    ) else (
        call :test_k3s
    )
) else if "%ACTION%"=="clean" (
    if "%ENVIRONMENT%"=="docker" (
        call :clean_docker
    ) else (
        call :clean_k3s
    )
) else if "%ACTION%"=="logs" (
    call :show_logs %ENVIRONMENT%
)

exit /b 0

REM =============================================================================
REM FUNCTIONS
REM =============================================================================

:show_usage
echo Usage: %0 [ENVIRONMENT] [ACTION]
echo.
echo ENVIRONMENT:
echo   docker     Deploy to Docker Compose (development)
echo   k3s        Deploy to K3s (Kubernetes testing)
echo.
echo ACTION:
echo   deploy     Deploy the application (default)
echo   test       Test the deployed application
echo   clean      Clean up the deployment
echo   logs       Show application logs
echo.
echo Examples:
echo   %0 docker deploy    # Deploy to Docker Compose
echo   %0 k3s test        # Test K3s deployment
echo   %0 docker clean     # Clean up Docker Compose
exit /b 0

:deploy_docker
echo [INFO] Deploying to Docker Compose...

REM Generate certificates if they don't exist
if not exist "certs\edge-terrarium.crt" (
    echo [INFO] Generating TLS certificates...
    call scripts\generate-tls-certs.sh
)

REM Build images
echo [INFO] Building Docker images...
call scripts\build-images.sh

REM Start services
echo [INFO] Starting services with Docker Compose...
docker-compose -f configs\docker\docker-compose.yml up -d

REM Wait for services to be ready
echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Initialize Vault
echo [INFO] Initializing Vault with secrets...
call scripts\init-vault.sh http://localhost:8200

echo [SUCCESS] Docker Compose deployment completed!
echo.
echo Services are running:
echo   - CDP Client: https://localhost:443/fake-provider/* and /example-provider/*
echo   - Service Sink: https://localhost:443/ (default route)
echo   - Vault: http://localhost:8200
echo.
echo To test the deployment:
echo   scripts\test-setup.sh
exit /b 0

:deploy_k3s
echo [INFO] Deploying to K3s...

REM Check if K3s is running
kubectl cluster-info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] K3s is not running. Please start K3s first:
    echo   curl -sfL https://get.k3s.io ^| sh -
    echo   or
    echo   sudo systemctl start k3s
    exit /b 1
)

REM Generate certificates if they don't exist
if not exist "certs\edge-terrarium.crt" (
    echo [INFO] Generating TLS certificates...
    call scripts\generate-tls-certs.sh
)

REM Build images for K3s
echo [INFO] Building Docker images for K3s...
call scripts\build-images-k3s.sh

REM Note: K3s comes with Traefik by default, but we're using Kong
echo [INFO] Note: K3s comes with Traefik by default, but we're using Kong ingress controller
echo [INFO] Make sure Kong ingress controller is installed in your K3s cluster

REM Apply Kubernetes configurations
echo [INFO] Applying Kubernetes configurations...
kubectl apply -k configs\k8s\

REM Apply TLS secret
echo [INFO] Applying TLS secret...
REM TLS certificates are now generated dynamically during deployment

REM Apply K3s-specific configurations
echo [INFO] Applying K3s-specific configurations...
kubectl apply -f configs\k8s\vault-deployment-k3s.yaml
kubectl apply -f configs\k8s\vault-init-job-k3s.yaml
kubectl apply -f configs\k8s\ingress-k3s.yaml

REM Wait for deployment to be ready
echo [INFO] Waiting for deployment to be ready...
kubectl wait --for=condition=available --timeout=300s deployment/cdp-client -n edge-terrarium
kubectl wait --for=condition=available --timeout=300s deployment/service-sink -n edge-terrarium
kubectl wait --for=condition=available --timeout=300s deployment/vault -n edge-terrarium

REM Wait for Vault init job to complete
echo [INFO] Waiting for Vault initialization...
kubectl wait --for=condition=complete --timeout=300s job/vault-init -n edge-terrarium

REM Set up automatic port forwarding for Vault
echo [INFO] Setting up Vault port forwarding...
start /B kubectl port-forward -n edge-terrarium service/vault 8200:8200
timeout /t 3 /nobreak >nul

REM Verify Vault is accessible
curl -s http://localhost:8200/v1/sys/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Vault port forwarding may not be working properly
) else (
    echo [SUCCESS] Vault is accessible at http://localhost:8200
)

echo [SUCCESS] K3s deployment completed!
echo.
echo Services are running in K3s:
echo   - CDP Client: Available via Kong ingress
echo   - Service Sink: Available via Kong ingress
echo   - Vault: Available at http://localhost:8200 (port forwarded)
echo.
echo Vault UI Access:
echo   URL: http://localhost:8200
echo   Token: root
echo.
echo To test the deployment:
echo   scripts\test-k3s.sh
echo.
echo To access via Kong ingress:
echo   # Get Kong proxy IP: kubectl get svc -n kong kong-proxy
echo   # Then: curl -k -H "Host: edge-terrarium.local" https://<kong-ip>/fake-provider/test
exit /b 0

:test_docker
echo [INFO] Testing Docker Compose deployment...
call scripts\test-setup.sh
exit /b 0

:test_k3s
echo [INFO] Testing K3s deployment...
call scripts\test-k3s.sh
exit /b 0

:clean_docker
echo [INFO] Cleaning up Docker Compose deployment...
docker-compose -f configs\docker\docker-compose.yml down -v
echo [SUCCESS] Docker Compose cleanup completed!
exit /b 0

:clean_k3s
echo [INFO] Cleaning up K3s deployment...
kubectl delete -k configs\k8s\ --ignore-not-found=true
kubectl delete secret edge-terrarium-tls -n edge-terrarium --ignore-not-found=true
echo [SUCCESS] K3s cleanup completed!
exit /b 0

:show_logs
set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="docker" (
    echo [INFO] Showing Docker Compose logs...
    docker-compose -f configs\docker\docker-compose.yml logs -f
) else if "%ENVIRONMENT%"=="k3s" (
    echo [INFO] Showing K3s logs...
    echo CDP Client logs:
    kubectl logs -n edge-terrarium deployment/cdp-client
    echo.
    echo Service Sink logs:
    kubectl logs -n edge-terrarium deployment/service-sink
    echo.
    echo Vault logs:
    kubectl logs -n edge-terrarium deployment/vault
)
exit /b 0
