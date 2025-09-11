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
from terrarium_cli.utils.shell import run_command, check_command_exists, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.dependencies import DependencyChecker, DependencyError
from terrarium_cli.config.app_loader import AppLoader
from terrarium_cli.config.generator import ConfigGenerator

logger = logging.getLogger(__name__)


class DeployCommand(BaseCommand):
    """Command to deploy the application to Docker or K3s."""
    
    def run(self) -> int:
        """Run the deploy command."""
        environment = self.args.environment
        self.dashboard_token = None  # Initialize dashboard token
        
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
            dep_checker = DependencyChecker()
            if not dep_checker.check_all_dependencies(['docker', 'docker_compose', 'curl']):
                print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
                return 1
            
            # Check prerequisites
            if not self._check_docker_prerequisites():
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
            
            
            # Initialize Vault with secrets
            print(f"{Colors.info('Initializing Vault with secrets...')}")
            try:
                from terrarium_cli.commands.vault import VaultCommand
                import argparse
                # Create mock args for VaultCommand
                mock_args = argparse.Namespace()
                vault_cmd = VaultCommand(mock_args)
                vault_cmd._init_vault()
            except Exception as e:
                print(f"{Colors.warning(f'Vault initialization failed: {e}')}")
            
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
            dep_checker = DependencyChecker()
            if not dep_checker.check_all_dependencies(['docker', 'k3d', 'kubectl', 'curl']):
                print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
                return 1
            
            # Check prerequisites
            if not self._check_k3s_prerequisites():
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
            app_loader = AppLoader()
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
            app_loader = AppLoader()
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
            app_loader = AppLoader()
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
            app_loader = AppLoader()
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
            
            # Initialize Vault with secrets
            print(f"{Colors.info('Initializing Vault with secrets...')}")
            try:
                from terrarium_cli.commands.vault import VaultCommand
                import argparse
                # Create mock args for VaultCommand
                mock_args = argparse.Namespace()
                vault_cmd = VaultCommand(mock_args)
                vault_cmd._init_vault()
            except Exception as e:
                print(f"{Colors.warning(f'Vault initialization failed: {e}')}")
            
            # Start all other services after Vault is initialized
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
            # Check if cluster already exists
            result = run_command("k3d cluster list", capture_output=True, check=False)
            if "edge-terrarium" in result.stdout:
                print(f"{Colors.info('K3s cluster already exists')}")
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
            
            run_command(create_cmd, check=True)
            print(f"{Colors.success('K3s cluster created successfully')}")
            
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
            
            # Apply other configurations
            run_command("kubectl apply -k configs/k3s/", check=True)
            
            # Wait for Vault to be ready first
            print(f"{Colors.info('Waiting for Vault to be ready...')}")
            run_command(
                "kubectl wait --for=condition=available --timeout=120s deployment/vault -n edge-terrarium",
                check=True
            )
            
            # Set up port forwarding for Vault
            print(f"{Colors.info('Setting up Vault port forwarding...')}")
            vault_port_forward = subprocess.Popen(
                ["kubectl", "port-forward", "-n", "edge-terrarium", "svc/vault", "8200:8200"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Set up port forwarding for other apps
            from terrarium_cli.config.app_loader import AppLoader
            app_loader = AppLoader()
            apps = app_loader.load_apps()
            
            for app in apps:
                if app.runtime.port_forward:
                    print(f"{Colors.info(f'Setting up port forwarding for {app.name} on port {app.runtime.port_forward}...')}")
                    port_forward_process = subprocess.Popen(
                        ["kubectl", "port-forward", "-n", "edge-terrarium", f"svc/{app.name}", f"{app.runtime.port_forward}:{app.runtime.port}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            
            # Wait a moment for port forwarding to establish
            time.sleep(3)
            
            # Initialize Vault with secrets
            print(f"{Colors.info('Initializing Vault with secrets...')}")
            try:
                from terrarium_cli.commands.vault import VaultCommand
                import argparse
                # Create mock args for VaultCommand
                mock_args = argparse.Namespace()
                vault_cmd = VaultCommand(mock_args)
                vault_cmd._init_vault()
            except Exception as e:
                print(f"{Colors.warning(f'Vault initialization failed: {e}')}")
            
            # Wait for all deployments
            print(f"{Colors.info('Waiting for all deployments to be ready...')}")
            run_command(
                "kubectl wait --for=condition=available --timeout=120s deployment --all -n edge-terrarium",
                check=True
            )
            
            # Set up Kubernetes Dashboard authentication
            print(f"{Colors.info('Setting up Kubernetes Dashboard authentication...')}")
            self._setup_dashboard_auth()
            
            print(f"{Colors.success('K3s deployment completed')}")
            return True
        except ShellError as e:
            self.logger.error(f"Failed to deploy to K3s: {e}")
            return False
    
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
            
            # Wait a moment for port forwarding to establish
            time.sleep(3)
            
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
