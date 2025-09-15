"""
Deploy command for the CLI tool.
"""

import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.commands.vault import VaultCommand
from terrarium_cli.utils.shell import run_command, check_command_exists, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.dependencies import DependencyChecker, DependencyError
from terrarium_cli.config.app_loader import AppLoader
from terrarium_cli.config.generator import ConfigGenerator

logger = logging.getLogger(__name__)


class DeployCommand(BaseCommand):
    """Command to deploy the application to Docker or K3s."""
    
    def __init__(self, args):
        super().__init__(args)
        self._app_loader = None  # Cache for AppLoader instance
        self.port_forward_processes = []  # Store port forwarding process references
    
    def _get_app_loader(self) -> AppLoader:
        """Get cached AppLoader instance."""
        if self._app_loader is None:
            self._app_loader = AppLoader()
        return self._app_loader
    
    def _check_dependencies(self, dependencies: list) -> bool:
        """Check if required dependencies are available."""
        dep_checker = DependencyChecker()
        if not dep_checker.check_all_dependencies(dependencies):
            print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
            return False
        return True
    
    def _validate_app_configs(self) -> bool:
        """Validate all app-config.yml files before deployment."""
        print(f"{Colors.info('Validating app-config.yml files...')}")
        
        from terrarium_cli.utils.yaml_validator import validate_all_app_configs, print_validation_results
        from pathlib import Path
        
        apps_dir = Path("apps")
        all_valid, errors_by_file, warnings_by_file = validate_all_app_configs(apps_dir)
        
        print_validation_results(all_valid, errors_by_file, warnings_by_file)
        
        if not all_valid:
            print(f"\n{Colors.error('Deployment aborted due to YAML validation errors.')}")
            return False
        
        return True
    
    def run(self) -> int:
        """Run the deploy command."""
        environment = self.args.environment
        self.dashboard_token = None  # Initialize dashboard token
        
        # Validate all app-config.yml files before deployment
        if not self._validate_app_configs():
            return 1
        
        if environment == "docker":
            return self._deploy_docker()
        elif environment == "k3s":
            return self._deploy_k3s()
        else:
            self.logger.error(f"Unknown environment: {environment}")
            return 1
    
    def _deploy_docker(self) -> int:
        """Deploy to Docker Compose."""
        try:
            print(f"{Colors.info('Deploying to Docker Compose...')}")
            
            # Check dependencies
            if not self._check_dependencies(['docker', 'docker_compose', 'curl']):
                return 1
            
            # Check prerequisites
            if not self._check_docker_prerequisites():
                return 1
            
            # Generate TLS certificates
            if not self._generate_certificates():
                return 1
            
            # Clean up K3s if running
            self._cleanup_k3s()
            
            # Generate configuration
            if not self._generate_docker_config():
                return 1
            
            # Build images
            if not self._build_images():
                return 1
            
            # Start services
            if not self._start_docker_services():
                return 1
            
            
            # Initialize Vault
            print(f"{Colors.info('Initializing Vault...')}")
            vault_cmd = VaultCommand(None)
            vault_cmd._init_vault()
            
            # Process database secrets
            print(f"{Colors.info('Processing database secrets...')}")
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            vault_cmd.process_database_secrets(apps)
            
            # Verify deployment
            if not self._verify_docker_deployment():
                return 1
            
            print(f"{Colors.success('Docker Compose deployment completed!')}")
            self._print_docker_access_info()
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to deploy to Docker: {e}")
            return 1
    
    def _deploy_k3s(self) -> int:
        """Deploy to K3s."""
        try:
            print(f"{Colors.info('Deploying to K3s...')}")
            
            # Check dependencies
            if not self._check_dependencies(['docker', 'k3d', 'kubectl', 'curl']):
                return 1
            
            # Check prerequisites
            if not self._check_k3s_prerequisites():
                return 1
            
            # Generate TLS certificates
            if not self._generate_certificates():
                return 1
            
            # Clean up Docker if running
            self._cleanup_docker()
            
            # Setup K3s cluster
            if not self._setup_k3s_cluster():
                return 1
            
            # Generate configuration
            if not self._generate_k3s_config():
                return 1
            
            # Build and import images
            if not self._build_and_import_images():
                return 1
            
            # Deploy to K3s
            if not self._deploy_to_k3s():
                return 1
            
            # Verify deployment
            if not self._verify_k3s_deployment():
                return 1
            
            print(f"{Colors.success('K3s deployment completed!')}")
            self._print_k3s_access_info()
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to deploy to K3s: {e}")
            return 1
    
    def _check_docker_prerequisites(self) -> bool:
        """Check Docker prerequisites."""
        print(f"{Colors.info('Checking Docker prerequisites...')}")
        
        if not check_command_exists("docker"):
            print(f"{Colors.error('Docker is not installed')}")
            return False
        
        if not check_command_exists("docker-compose"):
            print(f"{Colors.error('Docker Compose is not installed')}")
            return False
        
        # Check if Docker daemon is running
        try:
            run_command("docker info", check=True)
        except ShellError:
            print(f"{Colors.error('Docker daemon is not running')}")
            return False
        
        print(f"{Colors.success('Docker prerequisites satisfied')}")
        return True
    
    def _check_k3s_prerequisites(self) -> bool:
        """Check K3s prerequisites."""
        print(f"{Colors.info('Checking K3s prerequisites...')}")
        
        # Check k3d
        if not check_command_exists("k3d"):
            print(f"{Colors.warning('k3d is not installed. Attempting to install...')}")
            if not self._install_k3d():
                return False
        
        # Check kubectl
        if not check_command_exists("kubectl"):
            print(f"{Colors.error('kubectl is not installed')}")
            return False
        
        # Check helm
        if not check_command_exists("helm"):
            print(f"{Colors.warning('helm is not installed. Attempting to install...')}")
            if not self._install_helm():
                return False
        
        print(f"{Colors.success('K3s prerequisites satisfied')}")
        return True
    
    def _generate_certificates(self) -> bool:
        """Generate TLS certificates for the deployment."""
        try:
            print(f"{Colors.info('Generating TLS certificates...')}")
            
            # Import CertCommand to generate certificates
            from terrarium_cli.commands.cert import CertCommand
            
            # Create a mock args object for CertCommand
            class MockArgs:
                def __init__(self):
                    self.force = False
                    self.days = 365
                    self.output_dir = None
            
            cert_command = CertCommand(MockArgs())
            result = cert_command.run()
            
            if result == 0:
                print(f"{Colors.success('TLS certificates generated successfully')}")
                return True
            else:
                print(f"{Colors.error('Failed to generate TLS certificates')}")
                return False
                
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            print(f"{Colors.error(f'Certificate generation failed: {e}')}")
            return False
    
    def _install_k3d(self) -> bool:
        """Install k3d."""
        try:
            print(f"{Colors.info('Installing k3d...')}")
            run_command(
                "curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash",
                check=True
            )
            print(f"{Colors.success('k3d installed successfully')}")
            return True
        except ShellError:
            print(f"{Colors.error('Failed to install k3d')}")
            return False
    
    def _install_helm(self) -> bool:
        """Install helm."""
        try:
            print(f"{Colors.info('Installing helm...')}")
            run_command(
                "curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                check=True
            )
            print(f"{Colors.success('helm installed successfully')}")
            return True
        except ShellError:
            print(f"{Colors.error('Failed to install helm')}")
            return False
    
    def _cleanup_k3s(self) -> None:
        """Clean up K3s deployment."""
        try:
            if check_command_exists("k3d"):
                result = run_command("k3d cluster list", capture_output=True, check=False)
                if "edge-terrarium" in result.stdout:
                    print(f"{Colors.warning('Cleaning up existing K3s cluster...')}")
                    run_command("k3d cluster delete edge-terrarium", check=False)
        except ShellError:
            pass  # Ignore errors during cleanup
    
    def _check_k3s_cluster_health(self) -> bool:
        """Check if K3s cluster exists and is healthy."""
        try:
            # First check if cluster exists in k3d list
            result = run_command("k3d cluster list", capture_output=True, check=False)
            if "edge-terrarium" not in result.stdout:
                return False
            
            # Check if kubectl can connect to the cluster (suppress error output)
            try:
                # Use subprocess directly to avoid logging the error
                import subprocess
                result = subprocess.run(
                    ["kubectl", "cluster-info"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True
            except subprocess.CalledProcessError:
                # Cluster exists but kubectl can't connect - it's corrupted
                print(f"{Colors.warning('K3s cluster exists but appears corrupted, cleaning up...')}")
                self._cleanup_corrupted_k3s_cluster()
                return False
                
        except ShellError:
            return False
    
    def _cleanup_corrupted_k3s_cluster(self) -> None:
        """Clean up a corrupted K3s cluster."""
        try:
            print(f"{Colors.info('Cleaning up corrupted K3s cluster...')}")
            
            # Try to delete the cluster
            run_command("k3d cluster delete edge-terrarium", check=False)
            
            # Wait a moment for cleanup to complete
            import time
            time.sleep(2)
            
            # Verify cluster is gone
            result = run_command("k3d cluster list", capture_output=True, check=False)
            if "edge-terrarium" not in result.stdout:
                print(f"{Colors.success('Corrupted cluster cleaned up successfully')}")
            else:
                print(f"{Colors.warning('Cluster cleanup may not have completed fully')}")
                
        except ShellError as e:
            print(f"{Colors.warning(f'Error during cluster cleanup: {e}')}")
    
    def _cleanup_docker(self) -> None:
        """Clean up Docker deployment."""
        try:
            print(f"{Colors.warning('Cleaning up existing Docker deployment...')}")
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium down -v",
                check=False
            )
        except ShellError:
            pass  # Ignore errors during cleanup
    
    def _generate_docker_config(self) -> bool:
        """Generate Docker Compose configuration."""
        try:
            print(f"{Colors.info('Generating Docker Compose configuration...')}")
            
            # Load app configurations
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            
            # Generate configuration
            generator = ConfigGenerator()
            generator.generate_all_configs(apps)
            
            print(f"{Colors.success('Docker Compose configuration generated')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate Docker configuration: {e}")
            return False
    
    def _generate_k3s_config(self) -> bool:
        """Generate K3s configuration."""
        try:
            print(f"{Colors.info('Generating K3s configuration...')}")
            
            # Load app configurations
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            
            # Generate configuration
            generator = ConfigGenerator()
            generator.generate_all_configs(apps)
            
            print(f"{Colors.success('K3s configuration generated')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate K3s configuration: {e}")
            return False
    
    def _build_images(self) -> bool:
        """Build Docker images."""
        try:
            print(f"{Colors.info('Building Docker images...')}")
            
            # Load app configurations
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            
            for app in apps:
                print(f"{Colors.info(f'Building {app.name} image...')}")
                
                # Build the image
                build_cmd = [
                    "docker", "build",
                    "-t", f"{app.docker.image_name}:{app.docker.tag}",
                    "-f", f"apps/{app.name}/Dockerfile",
                    f"apps/{app.name}"
                ]
                
                run_command(build_cmd, check=True)
                print(f"{Colors.success(f'{app.name} image built successfully')}")
            
            return True
        except ShellError as e:
            self.logger.error(f"Failed to build images: {e}")
            return False
    
    def _build_and_import_images(self) -> bool:
        """Build and import images for K3s."""
        try:
            # First build images
            if not self._build_images():
                return False
            
            print(f"{Colors.info('Importing images into k3d cluster...')}")
            
            # Load app configurations
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            
            for app in apps:
                # Skip importing official images (they'll be pulled by k3d)
                if not hasattr(app.docker, 'build_context') or not getattr(app.docker, 'build_context', None):
                    print(f"{Colors.info(f'Skipping {app.name} - using official image {app.docker.image_name}:{app.docker.tag}')}")
                    continue
                
                print(f"{Colors.info(f'Importing {app.name} image...')}")
                
                # Check if image exists locally first
                check_cmd = ["docker", "images", "-q", f"{app.docker.image_name}:{app.docker.tag}"]
                try:
                    result = run_command(check_cmd, check=False)
                    if not result.stdout.strip():
                        print(f"{Colors.warning(f'Image {app.docker.image_name}:{app.docker.tag} not found locally, skipping import')}")
                        continue
                except:
                    # If check fails, continue with import
                    pass
                
                import_cmd = [
                    "k3d", "image", "import",
                    f"{app.docker.image_name}:{app.docker.tag}",
                    "-c", "edge-terrarium"
                ]
                
                run_command(import_cmd, check=True)
                print(f"{Colors.success(f'{app.name} image imported successfully')}")
            
            return True
        except ShellError as e:
            self.logger.error(f"Failed to import images: {e}")
            return False
    
    def _start_docker_services(self) -> bool:
        """Start Docker Compose services."""
        try:
            # Start Vault first
            print(f"{Colors.info('Starting Vault service...')}")
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium up -d vault",
                check=True
            )
            
            # Wait for Vault to be ready
            print(f"{Colors.info('Waiting for Vault to be ready...')}")
            import time
            max_retries = 30
            for i in range(max_retries):
                try:
                    result = run_command(
                        "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium exec -T vault vault status",
                        check=False
                    )
                    if result.returncode == 0:
                        print(f"{Colors.success('Vault is ready')}")
                        break
                except:
                    pass
                
                if i < max_retries - 1:
                    print(f"{Colors.info(f'Waiting for Vault... ({i+1}/{max_retries})')}")
                    time.sleep(2)
            else:
                print(f"{Colors.warning('Vault may not be ready, continuing anyway...')}")
            
            # Initialize Vault
            print(f"{Colors.info('Initializing Vault...')}")
            vault_cmd = VaultCommand(None)
            vault_cmd._init_vault()
            
            # Process database secrets
            print(f"{Colors.info('Processing database secrets...')}")
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            vault_cmd.process_database_secrets(apps)
            
            # Start all other services
            print(f"{Colors.info('Starting all other services...')}")
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium up -d",
                check=True
            )
            
            print(f"{Colors.success('Docker Compose services started')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to start Docker services: {e}")
            return False
    
    def _setup_k3s_cluster(self) -> bool:
        """Setup K3s cluster."""
        try:
            # Check if cluster already exists and is healthy
            cluster_exists = self._check_k3s_cluster_health()
            
            if cluster_exists:
                print(f"{Colors.info('K3s cluster already exists and is healthy')}")
                return True
            
            print(f"{Colors.info('Creating K3s cluster...')}")
            
            create_cmd = [
                "k3d", "cluster", "create", "edge-terrarium",
                "--port", "80:80@loadbalancer",
                "--port", "443:443@loadbalancer",
                "--port", "8200:8200@loadbalancer",
                "--port", "5001:5001@loadbalancer",
                "--api-port", "6443",
                "--k3s-arg", "--disable=traefik@server:0",
                "--wait"
            ]
            
            try:
                run_command(create_cmd, check=True)
                print(f"{Colors.success('K3s cluster created successfully')}")
            except ShellError as e:
                # Check if the error is due to cluster already existing
                if "already exists" in str(e):
                    print(f"{Colors.warning('Cluster creation failed - cluster may exist but be corrupted')}")
                    print(f"{Colors.info('Attempting to clean up and recreate...')}")
                    self._cleanup_corrupted_k3s_cluster()
                    
                    # Try creating again
                    run_command(create_cmd, check=True)
                    print(f"{Colors.success('K3s cluster created successfully after cleanup')}")
                else:
                    raise e
            
            # Install NGINX ingress controller
            print(f"{Colors.info('Installing NGINX ingress controller...')}")
            run_command(
                "kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml",
                check=True
            )
            
            # Wait for NGINX ingress controller to be ready
            print(f"{Colors.info('Waiting for NGINX ingress controller to be ready...')}")
            run_command(
                "kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s",
                check=True
            )
            
            print(f"{Colors.success('NGINX ingress controller installed successfully')}")
            
            # Install Kubernetes Dashboard
            print(f"{Colors.info('Installing Kubernetes Dashboard...')}")
            run_command(
                "kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml",
                check=True
            )
            
            # Wait for Kubernetes Dashboard to be ready
            print(f"{Colors.info('Waiting for Kubernetes Dashboard to be ready...')}")
            run_command(
                "kubectl wait --for=condition=available --timeout=120s deployment/kubernetes-dashboard -n kubernetes-dashboard",
                check=True
            )
            
            print(f"{Colors.success('Kubernetes Dashboard installed successfully')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to setup K3s cluster: {e}")
            return False
    
    def _deploy_to_k3s(self) -> bool:
        """Deploy to K3s."""
        try:
            print(f"{Colors.info('Deploying to K3s...')}")
            
            # Create namespace
            try:
                run_command("kubectl create namespace edge-terrarium", check=False)
            except:
                pass  # Namespace might already exist
            
            # Create TLS secret for NGINX
            print(f"{Colors.info('Creating TLS secret for NGINX...')}")
            run_command(
                "kubectl create secret tls nginx-ssl --cert=certs/edge-terrarium.crt --key=certs/edge-terrarium.key -n edge-terrarium",
                check=False
            )
            
            # Apply NGINX ConfigMap first
            print(f"{Colors.info('Applying NGINX ConfigMap...')}")
            run_command("kubectl apply -f configs/k3s/nginx-configmap.yaml", check=True)
            
            # Apply Vault deployment first
            print(f"{Colors.info('Applying Vault deployment...')}")
            run_command("kubectl apply -f configs/k3s/vault-deployment.yaml", check=True)
            run_command("kubectl apply -f configs/k3s/vault-service.yaml", check=True)
            run_command("kubectl apply -f configs/k3s/vault-pvc.yaml", check=True)
            
            # Wait for Vault to be ready first
            print(f"{Colors.info('Waiting for Vault to be ready...')}")
            run_command(
                "kubectl wait --for=condition=available --timeout=120s deployment/vault -n edge-terrarium",
                check=True
            )
            
            # Set up Vault port forwarding first (needed for initialization)
            print(f"{Colors.info('Setting up Vault port forwarding for initialization...')}")
            vault_process = subprocess.Popen(
                ["kubectl", "port-forward", "-n", "edge-terrarium", "svc/vault", "8200:8200"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.port_forward_processes.append(vault_process)
            print(f"{Colors.success('Vault port forwarding started')}")
            
            # Wait a moment for port forwarding to establish
            time.sleep(3)
            
            # Initialize Vault
            print(f"{Colors.info('Initializing Vault...')}")
            vault_cmd = VaultCommand(None)
            vault_cmd._init_vault()
            
            # Process database secrets
            print(f"{Colors.info('Processing database secrets...')}")
            app_loader = self._get_app_loader()
            apps = app_loader.load_apps()
            vault_cmd.process_database_secrets(apps)
            
            # Clean up old resources that are no longer defined
            print(f"{Colors.info('Cleaning up old resources...')}")
            self._cleanup_old_k3s_resources()
            
            # Apply all other deployments after Vault is initialized
            print(f"{Colors.info('Applying all other deployments...')}")
            # Apply all files except Vault-related ones and non-deployment files
            import os
            k3s_dir = "configs/k3s"
            vault_files = {"vault-deployment.yaml", "vault-service.yaml", "vault-pvc.yaml"}
            exclude_files = {"kustomization.yaml", "namespace.yaml"}
            
            for filename in os.listdir(k3s_dir):
                if (filename.endswith('.yaml') and 
                    filename not in vault_files and 
                    filename not in exclude_files):
                    filepath = os.path.join(k3s_dir, filename)
                    run_command(f"kubectl apply -f {filepath}", check=True)
            
            # Wait for all deployments
            print(f"{Colors.info('Waiting for all deployments to be ready...')}")
            run_command(
                "kubectl wait --for=condition=available --timeout=60s deployment --all -n edge-terrarium",
                check=True
            )
            
            # Set up port forwarding for all other applications
            print(f"{Colors.info('Setting up port forwarding for all applications...')}")
            self._setup_k3s_port_forwarding()
            
            # Wait a moment for port forwarding to establish
            time.sleep(3)
            
            # Set up Kubernetes Dashboard authentication
            print(f"{Colors.info('Setting up Kubernetes Dashboard authentication...')}")
            self._setup_dashboard_auth()
            
            print(f"{Colors.success('K3s deployment completed')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to deploy to K3s: {e}")
            return False
    
    def _cleanup_old_k3s_resources(self) -> None:
        """Clean up Kubernetes resources that are no longer defined in the current manifests."""
        try:
            # Get current app names from the apps directory
            app_loader = self._get_app_loader()
            current_apps = app_loader.load_apps()
            current_app_names = {app.name for app in current_apps}
            
            # Get all deployments in the namespace
            result = run_command(
                ["kubectl", "get", "deployments", "-n", "edge-terrarium", "-o", "jsonpath={.items[*].metadata.name}"],
                capture_output=True, check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                existing_deployments = set(result.stdout.strip().split())
                
                # Find deployments that are no longer in the current apps
                deployments_to_remove = existing_deployments - current_app_names
                
                for deployment_name in deployments_to_remove:
                    if deployment_name not in {"nginx", "vault"}:  # Don't remove core services
                        print(f"{Colors.info(f'Removing old deployment: {deployment_name}')}")
                        try:
                            run_command(
                                ["kubectl", "delete", "deployment", deployment_name, "-n", "edge-terrarium"],
                                check=False
                            )
                        except:
                            pass  # Ignore errors if deployment doesn't exist
                
                # Also clean up services for removed deployments
                result = run_command(
                    ["kubectl", "get", "services", "-n", "edge-terrarium", "-o", "jsonpath={.items[*].metadata.name}"],
                    capture_output=True, check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    existing_services = set(result.stdout.strip().split())
                    services_to_remove = existing_services - current_app_names
                    
                    for service_name in services_to_remove:
                        if service_name not in {"nginx", "vault"}:  # Don't remove core services
                            print(f"{Colors.info(f'Removing old service: {service_name}')}")
                            try:
                                run_command(
                                    ["kubectl", "delete", "service", service_name, "-n", "edge-terrarium"],
                                    check=False
                                )
                            except:
                                pass  # Ignore errors if service doesn't exist
                                
        except Exception as e:
            self.logger.warning(f"Failed to clean up old resources: {e}")
    
    def _setup_k3s_port_forwarding(self) -> bool:
        """Set up port forwarding for K3s services after pod restarts."""
        try:
            # Kill any existing port forwarding processes
            print(f"{Colors.info('Cleaning up existing port forwarding processes...')}")
            try:
                run_command("pkill -f 'kubectl port-forward'", check=False)
            except:
                pass  # Ignore errors if no processes to kill
            
            # Clear existing process references
            self.port_forward_processes.clear()
            
            # Wait a moment for processes to clean up
            import time
            time.sleep(2)
            
            # Set up port forwarding for NGINX (for application access via ingress)
            print(f"{Colors.info('Setting up NGINX port forwarding for application access...')}")
            nginx_process = subprocess.Popen(
                ["kubectl", "port-forward", "-n", "edge-terrarium", "svc/nginx", "8443:443"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.port_forward_processes.append(nginx_process)
            print(f"{Colors.success('NGINX port forwarding started - applications accessible via https://localhost:8443/api/*')}")
            
            # Set up port forwarding for applications with port_forward configured (for direct access)
            apps = self._get_app_loader().load_apps()
            for app in apps:
                if app.runtime.port_forward:
                    print(f"{Colors.info(f'Setting up direct port forwarding for {app.name} on port {app.runtime.port_forward}...')}")
                    app_process = subprocess.Popen(
                        ["kubectl", "port-forward", "-n", "edge-terrarium", f"svc/{app.name}", f"{app.runtime.port_forward}:{app.runtime.port}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    self.port_forward_processes.append(app_process)
                    print(f"{Colors.success(f'{app.name} direct port forwarding started on port {app.runtime.port_forward}')}")
            
            # Wait a moment for all port forwarding to establish
            time.sleep(3)
            
            # Verify port forwarding is working
            print(f"{Colors.info('Verifying port forwarding...')}")
            self._verify_port_forwarding()
            
            print(f"{Colors.success('Port forwarding re-established successfully')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up port forwarding: {e}")
            return False
    
    def _verify_port_forwarding(self) -> None:
        """Verify that port forwarding is working."""
        try:
            # Check if port forwarding processes are running
            result = run_command("ps aux | grep 'kubectl port-forward' | grep -v grep", capture_output=True, check=False)
            if result.returncode == 0:
                print(f"{Colors.success(f'Found {len(result.stdout.strip().split(chr(10)))} port forwarding processes running')}")
            else:
                print(f"{Colors.warning('No port forwarding processes found')}")
            
            # Test NGINX ingress (primary access method)
            try:
                import requests
                response = requests.get("https://localhost:8443/api/logs/", 
                                     headers={"Host": "edge-terrarium.local"}, 
                                     verify=False, timeout=5)
                if response.status_code == 200:
                    print(f"{Colors.success('NGINX ingress port forwarding verified - applications accessible via https://localhost:8443/api/*')}")
                else:
                    print(f"{Colors.warning(f'NGINX ingress returned status {response.status_code}')}")
            except Exception as e:
                print(f"{Colors.warning(f'Could not verify NGINX ingress: {e}')}")
            
            # Test Vault direct access
            try:
                import requests
                response = requests.get("http://localhost:8200/v1/sys/health", timeout=5)
                if response.status_code == 200:
                    print(f"{Colors.success('Vault direct port forwarding verified on port 8200')}")
                else:
                    print(f"{Colors.warning(f'Vault direct access returned status {response.status_code}')}")
            except Exception as e:
                print(f"{Colors.warning(f'Could not verify Vault direct access: {e}')}")
            
            # Test direct application ports (if configured)
            apps = self._get_app_loader().load_apps()
            for app in apps:
                if app.runtime.port_forward:
                    try:
                        import requests
                        response = requests.get(f"http://localhost:{app.runtime.port_forward}/health", timeout=5)
                        if response.status_code == 200:
                            print(f"{Colors.success(f'{app.name} direct port forwarding verified on port {app.runtime.port_forward}')}")
                        else:
                            print(f"{Colors.warning(f'{app.name} direct port forwarding on port {app.runtime.port_forward} returned status {response.status_code}')}")
                    except Exception as e:
                        print(f"{Colors.warning(f'Could not verify {app.name} direct port forwarding on port {app.runtime.port_forward}: {e}')}")
                        
        except Exception as e:
            print(f"{Colors.warning(f'Error verifying port forwarding: {e}')}")
    
    def _verify_docker_deployment(self) -> bool:
        """Verify Docker deployment."""
        try:
            print(f"{Colors.info('Verifying Docker deployment...')}")
            
            # Check if containers are running
            result = run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps",
                capture_output=True,
                check=True
            )
            
            if "Up" not in result.stdout:
                print(f"{Colors.error('Some containers are not running')}")
                return False
            
            print(f"{Colors.success('Docker deployment verified')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to verify Docker deployment: {e}")
            return False
    
    def _verify_k3s_deployment(self) -> bool:
        """Verify K3s deployment."""
        try:
            print(f"{Colors.info('Verifying K3s deployment...')}")
            
            # Check if pods are running
            result = run_command(
                "kubectl get pods -n edge-terrarium",
                capture_output=True,
                check=True
            )
            
            if "Running" not in result.stdout:
                print(f"{Colors.error('Some pods are not running')}")
                return False
            
            print(f"{Colors.success('K3s deployment verified')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to verify K3s deployment: {e}")
            return False
    
    def _print_docker_access_info(self) -> None:
        """Print Docker access information."""
        print(f"\n{Colors.bold('Docker Compose Deployment Access Information:')}")
        print(f"  - Custom Client: https://localhost:8443/api/fake-provider/* and /api/example-provider/*")
        print(f"  - Service Sink: https://localhost:8443/api/ (default route)")
        print(f"  - File Storage: https://localhost:8443/api/storage/*")
        print(f"  - Logthon: https://localhost:8443/api/logs/* (via NGINX) OR http://localhost:5001/ (direct)")
        print(f"  - Vault: https://localhost:8443/api/vault/v1/sys/health (via NGINX) OR http://localhost:8200/ (direct)")
        print(f"\nTo test the deployment:")
        print(f"  terrarium.py test")
    
    def _print_k3s_access_info(self) -> None:
        """Print K3s access information."""
        print(f"\n{Colors.bold('K3s Deployment Access Information:')}")
        
        # Get the external IP of the NGINX ingress controller
        try:
            result = run_command(
                "kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'",
                capture_output=True, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                external_ip = result.stdout.strip()
            else:
                # Fallback to localhost if no external IP
                external_ip = "localhost"
        except:
            external_ip = "localhost"
        
        print(f"  - Custom Client: https://{external_ip}:8443/api/fake-provider/* and /api/example-provider/*")
        print(f"  - Service Sink: https://{external_ip}:8443/api/ (default route)")
        print(f"  - File Storage: https://{external_ip}:8443/api/storage/*")
        print(f"  - Logthon: https://{external_ip}:8443/api/logs/*")
        print(f"  - Vault: https://{external_ip}:8443/api/vault/v1/sys/health")
        print(f"  - Kubernetes Dashboard: https://localhost:9443 (port forwarded)")
        
        if hasattr(self, 'dashboard_token') and self.dashboard_token:
            print(f"\nKubernetes Dashboard Access:")
            print(f"  URL: https://localhost:9443")
            print(f"  Bearer Token: {self.dashboard_token}")
            print(f"  Alternative: kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard 9443:443")
        
        print(f"\nTo test the deployment:")
        print(f"  terrarium.py test")
    
    def _setup_dashboard_auth(self) -> None:
        """Set up Kubernetes Dashboard authentication and port forwarding."""
        try:
            # Create dashboard admin service account and token
            print(f"{Colors.info('Creating dashboard admin service account...')}")
            run_command(
                "kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard",
                check=False  # Don't fail if it already exists
            )
            
            run_command(
                "kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin",
                check=False  # Don't fail if it already exists
            )
            
            # Generate and display the token
            print(f"{Colors.info('Generating dashboard access token...')}")
            result = run_command(
                "kubectl -n kubernetes-dashboard create token dashboard-admin",
                capture_output=True,
                check=True
            )
            dashboard_token = result.stdout.strip()
            
            print(f"{Colors.success('Kubernetes Dashboard authentication configured')}")
            
            # Set up port forwarding for Dashboard
            print(f"{Colors.info('Setting up Kubernetes Dashboard port forwarding...')}")
            dashboard_port_forward = subprocess.Popen(
                ["kubectl", "-n", "kubernetes-dashboard", "port-forward", "svc/kubernetes-dashboard", "9443:443"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            
            # Store the token for display in access info
            self.dashboard_token = dashboard_token
            
            print(f"{Colors.success('Kubernetes Dashboard port forwarding set up on port 9443')}")
            
        except Exception as e:
            print(f"{Colors.warning(f'Dashboard setup failed: {e}')}")
            self.dashboard_token = None
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add deploy command arguments."""
        parser.add_argument(
            "environment",
            choices=["docker", "k3s"],
            help="Deployment environment"
        )
        
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean up existing deployment before deploying"
        )
        
        parser.add_argument(
            "--no-build",
            action="store_true",
            help="Skip building images (use existing images)"
        )
