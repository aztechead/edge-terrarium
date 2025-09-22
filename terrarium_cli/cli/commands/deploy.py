"""
Deploy command for the CLI tool.
"""

import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, List

from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.cli.commands.vault import VaultCommand
from terrarium_cli.utils.system.shell import run_command, check_command_exists, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.system.dependencies import DependencyChecker, DependencyError
from terrarium_cli.config.loaders.app_loader import AppLoader
from terrarium_cli.config.generators.generator import ConfigGenerator
from terrarium_cli.platforms.docker.docker_manager import DockerDeploymentManager
from terrarium_cli.platforms.k3s.k3s_manager import K3sDeploymentManager

logger = logging.getLogger(__name__)


class DeployCommand(BaseCommand):
    """Command to deploy the application to Docker or K3s."""
    
    def __init__(self, args):
        super().__init__(args)
        self._app_loader = None  # Cache for AppLoader instance
        self.port_forward_processes = []  # Store port forwarding process references
        
        # Initialize deployment managers
        self.docker_manager = DockerDeploymentManager()
        self.k3s_manager = K3sDeploymentManager()
    
    def _get_app_loader(self) -> AppLoader:
        """Get cached AppLoader instance."""
        if self._app_loader is None:
            self._app_loader = AppLoader()
        return self._app_loader
    
    def _load_apps(self) -> List:
        """Load all application configurations."""
        app_loader = self._get_app_loader()
        return app_loader.load_apps()
    
    def _apply_k8s_manifest(self, filepath: str, description: str = None) -> None:
        """Apply a Kubernetes manifest file."""
        if description:
            print(f"{Colors.info(f'Applying {description}...')}")
        run_command(f"kubectl apply -f {filepath}", check=True)
    
    def _apply_k8s_manifests(self, filepaths: List[str], description: str = None) -> None:
        """Apply multiple Kubernetes manifest files."""
        if description:
            print(f"{Colors.info(f'Applying {description}...')}")
        for filepath in filepaths:
            run_command(f"kubectl apply -f {filepath}", check=True)
    
    def _wait_for_deployment(self, deployment_name: str, timeout: int = 120) -> None:
        """Wait for a deployment to be ready."""
        print(f"{Colors.info(f'Waiting for {deployment_name} to be ready...')}")
        run_command(
            f"kubectl wait --for=condition=available --timeout={timeout}s deployment/{deployment_name} -n edge-terrarium",
            check=True
        )
    
    def _generate_config(self, config_type: str) -> bool:
        """Generate configuration files."""
        try:
            print(f"{Colors.info(f'Generating {config_type} configuration...')}")
            apps = self._load_apps()
            generator = ConfigGenerator()
            generator.generate_all_configs(apps)
            print(f"{Colors.success(f'{config_type} configuration generated')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate {config_type} configuration: {e}")
            return False
    
    def _build_app_images(self, apps: List) -> bool:
        """Build Docker images for all applications."""
        try:
            print(f"{Colors.info('Building Docker images...')}")
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
        
        from terrarium_cli.utils.validation.yaml_validator import validate_all_app_configs, print_validation_results
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
        return self.docker_manager.deploy(
            self._check_dependencies,
            self._cleanup_k3s
        )
    
    def _deploy_k3s(self) -> int:
        """Deploy to K3s."""
        return self.k3s_manager.deploy(
            self._check_dependencies,
            self._cleanup_docker,
            self._generate_certificates,
            self._build_and_import_images
        )
    
    def _check_docker_prerequisites(self) -> bool:
        """Check Docker prerequisites."""
        return self.docker_manager.check_docker_prerequisites()
    
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
        return self.docker_manager.generate_certificates()
    
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
        self.k3s_manager.cleanup_k3s()
    
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
        self.docker_manager.cleanup_docker()
    
    def _generate_docker_config(self) -> bool:
        """Generate Docker Compose configuration."""
        return self._generate_config("Docker Compose")
    
    def _generate_k3s_config(self) -> bool:
        """Generate K3s configuration."""
        return self._generate_config("K3s")
    
    def _build_images(self) -> bool:
        """Build Docker images."""
        apps = self._load_apps()
        return self._build_app_images(apps)
    
    def _build_and_import_images(self) -> bool:
        """Build and import images for K3s."""
        try:
            # First build images
            if not self._build_images():
                return False
            
            print(f"{Colors.info('Importing images into k3d cluster...')}")
            
            # Load app configurations
            apps = self._load_apps()
            
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
            apps = self._load_apps()
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
            
            # NGINX ingress controller will be deployed separately after cluster setup
            
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
    
    def _verify_service_health(self, service_name: str, apps: List) -> None:
        """Verify that a service is responding to health checks."""
        try:
            # Find the app configuration for this service
            app_config = None
            for app in apps:
                if app.name == service_name:
                    app_config = app
                    break
            
            if not app_config or not app_config.health_checks:
                print(f"{Colors.info(f'No health check configured for {service_name}, skipping verification')}")
                return
            
            # Use the configured health check endpoint
            health_check = app_config.health_checks.get('readiness') or app_config.health_checks.get('liveness')
            if not health_check:
                print(f"{Colors.info(f'No suitable health check found for {service_name}, skipping verification')}")
                return
            
            path = health_check.path
            port = str(health_check.port)
            print(f"{Colors.info(f'Checking {service_name} health at {path}...')}")
            
            # Get the pod name for the service
            result = run_command(
                f"kubectl get pods -l app={service_name} -n edge-terrarium -o jsonpath='{{.items[0].metadata.name}}'",
                check=True,
                capture_output=True
            )
            pod_name = result.stdout.strip()
            
            if pod_name:
                # Try to curl the health endpoint from inside the pod
                # First check if curl is available in the container
                curl_check_cmd = f"kubectl exec {pod_name} -n edge-terrarium -- which curl"
                
                # Temporarily suppress logging for expected failures
                import logging
                shell_logger = logging.getLogger('terrarium_cli.utils.system.shell')
                original_level = shell_logger.level
                shell_logger.setLevel(logging.CRITICAL)
                
                try:
                    run_command(curl_check_cmd, check=True, capture_output=True)
                    # Curl is available, try the health check
                    health_check_cmd = f"kubectl exec {pod_name} -n edge-terrarium -- curl -f -s http://localhost:{port}{path}"
                    run_command(health_check_cmd, check=True, capture_output=True)
                    print(f"{Colors.success(f'{service_name} health check passed')}")
                except ShellError:
                    print(f"{Colors.warning(f'{service_name} health check failed (curl not available or endpoint not ready)')}")
                finally:
                    # Restore original logging level
                    shell_logger.setLevel(original_level)
            else:
                print(f"{Colors.warning(f'Could not find pod for {service_name}')}")
                
        except ShellError:
            print(f"{Colors.warning(f'{service_name} health check could not be performed, but continuing')}")
            # Don't fail the deployment for health check failures
            # The service might still work even if health endpoint isn't ready
    
    def _calculate_deployment_order(self, apps: List) -> List[str]:
        """Calculate the deployment order based on app dependencies."""
        # Build dependency graph
        app_deps = {}
        app_names = set()
        
        for app in apps:
            app_names.add(app.name)
            app_deps[app.name] = app.dependencies
        
        # Topological sort to determine deployment order
        deployed = set()
        order = []
        
        # Keep trying until all apps are deployed
        while len(order) < len(apps):
            ready_to_deploy = []
            
            for app_name in app_names:
                if app_name in deployed:
                    continue
                    
                # Check if all dependencies are already deployed
                deps_satisfied = True
                for dep in app_deps[app_name]:
                    if dep not in deployed:
                        deps_satisfied = False
                        break
                
                if deps_satisfied:
                    ready_to_deploy.append(app_name)
            
            if not ready_to_deploy:
                # Circular dependency or missing dependency - deploy remaining apps anyway
                remaining = [name for name in app_names if name not in deployed]
                print(f"{Colors.warning(f'Possible circular dependency detected. Deploying remaining apps: {remaining}')}")
                order.extend(remaining)
                break
            
            # Sort alphabetically for consistent ordering when no dependencies
            ready_to_deploy.sort()
            order.extend(ready_to_deploy)
            deployed.update(ready_to_deploy)
        
        return order
    
    def _has_dependents(self, service_name: str, apps: List) -> bool:
        """Check if any other apps depend on this service."""
        for app in apps:
            if service_name in app.dependencies:
                return True
        return False
    
    def _deploy_nginx_ingress_controller(self) -> bool:
        """Deploy NGINX ingress controller using local template."""
        try:
            from terrarium_cli.config.generators.generator import ConfigGenerator
            
            # Generate the NGINX ingress controller manifest
            generator = ConfigGenerator()
            
            # Create temporary directory for nginx ingress manifest
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Generate the NGINX ingress controller manifest
                nginx_ingress_file = temp_path / "nginx-ingress-controller.yaml"
                generator._write_template_file(
                    nginx_ingress_file, 
                    'k3s-nginx-ingress-controller.yaml.j2',
                    global_config=generator.global_config
                )
                
                # Apply the manifest
                print(f"{Colors.info('Applying NGINX ingress controller manifest...')}")
                run_command(f"kubectl apply -f {nginx_ingress_file}", check=True)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to deploy NGINX ingress controller: {e}")
            return False
    
    
    def _cleanup_old_k3s_resources(self) -> None:
        """Clean up Kubernetes resources that are no longer defined in the current manifests."""
        try:
            # Get current app names from the apps directory
            current_apps = self._load_apps()
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
                # Try the Vault health endpoint up to 2 times in case Vault is still starting up
                vault_health_url = "http://localhost:8200/v1/sys/health"
                response = None
                for attempt in range(2):
                    try:
                        response = requests.get(vault_health_url, timeout=5)
                        if response.status_code == 200:
                            break  # Success, no need to retry
                    except Exception:
                        if attempt == 0:
                            time.sleep(2)  # Wait a bit before retrying
                        else:
                            raise  # On second failure, propagate the exception
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
