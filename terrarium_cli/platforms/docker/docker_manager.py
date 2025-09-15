"""
Docker deployment management functionality.

This module handles all Docker-specific deployment operations including:
- Docker Compose service management
- Container health verification
- Docker prerequisites checking
"""

import logging
import time
from typing import List

from terrarium_cli.utils.system.shell import run_command, check_command_exists, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.cli.commands.vault import VaultCommand
from terrarium_cli.core.deployment.common import CommonDeploymentHelpers

logger = logging.getLogger(__name__)


class DockerDeploymentManager(CommonDeploymentHelpers):
    """Manages Docker deployment operations."""
    
    def check_docker_prerequisites(self) -> bool:
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
    
    def cleanup_docker(self) -> None:
        """Clean up Docker deployment."""
        try:
            print(f"{Colors.warning('Cleaning up existing Docker deployment...')}")
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium down -v",
                check=False
            )
        except ShellError:
            pass  # Ignore errors during cleanup
    
    def start_docker_services(self) -> bool:
        """Start Docker Compose services."""
        try:
            print(f"{Colors.info('Starting Vault service...')}")
            
            # Start Vault first
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium up -d vault",
                check=True
            )
            
            # Wait for Vault to be ready
            print(f"{Colors.info('Waiting for Vault to be ready...')}")
            vault_ready = False
            max_attempts = 30
            attempt = 0
            
            while attempt < max_attempts and not vault_ready:
                attempt += 1
                print(f"{Colors.info(f'Waiting for Vault... ({attempt}/{max_attempts})')}")
                time.sleep(2)
                
                # Check if Vault is healthy
                try:
                    result = run_command(
                        "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps vault",
                        capture_output=True,
                        check=False
                    )
                    if "healthy" in result.stdout or "Up" in result.stdout:
                        vault_ready = True
                        print(f"{Colors.success('Vault is ready')}")
                        break
                except:
                    continue
            
            if not vault_ready:
                print(f"{Colors.warning('Vault may not be fully ready, but continuing...')}")
            
            return True
        except ShellError as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False
    
    def verify_docker_deployment(self) -> bool:
        """Verify Docker deployment is working."""
        try:
            print(f"{Colors.info('Verifying Docker deployment...')}")
            
            # Check if all services are running
            result = run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps",
                check=True,
                capture_output=True
            )
            
            if "Up" not in result.stdout:
                print(f"{Colors.error('Some Docker services may not be running')}")
                print(result.stdout)
                return False
            
            print(f"{Colors.success('Docker deployment verified')}")
            return True
            
        except ShellError as e:
            logger.error(f"Failed to verify Docker deployment: {e}")
            return False
    
    def print_docker_access_info(self) -> None:
        """Print access information for Docker deployment."""
        print(f"\n{Colors.success('Docker Compose Deployment Access Information:')}")
        
        apps = self.load_apps()
        for app in apps:
            if app.routes:
                for route in app.routes:
                    print(f"  - {app.name.title()}: https://localhost:8443/api{route.path}")
            else:
                # For apps without explicit routes, show direct access if they have port forwarding
                if hasattr(app.runtime, 'port_forward') and app.runtime.port_forward:
                    print(f"  - {app.name.title()}: https://localhost:8443/api/{app.name}/* (via NGINX) OR http://localhost:{app.runtime.port_forward}/ (direct)")
                else:
                    print(f"  - {app.name.title()}: https://localhost:8443/api/{app.name}/*")
        
        print(f"\nTo test the deployment:")
        print(f"  terrarium.py test")
    
    def deploy(self, check_dependencies_func, cleanup_k3s_func) -> int:
        """Execute Docker deployment."""
        try:
            print(f"{Colors.info('Deploying to Docker Compose...')}")
            
            # Check dependencies
            if not check_dependencies_func(['docker', 'docker_compose', 'curl']):
                return 1
            
            # Check prerequisites
            if not self.check_docker_prerequisites():
                return 1
            
            # Generate TLS certificates
            if not self.generate_certificates():
                return 1
            
            # Clean up K3s if running
            cleanup_k3s_func()
            
            # Generate configuration
            if not self.generate_config("Docker Compose"):
                return 1
            
            # Build images
            apps = self.load_apps()
            if not self.build_app_images(apps):
                return 1
            
            # Start services
            if not self.start_docker_services():
                return 1
            
            # Initialize Vault
            print(f"{Colors.info('Initializing Vault...')}")
            vault_cmd = VaultCommand(None)
            vault_cmd._init_vault()
            
            # Process database secrets
            print(f"{Colors.info('Processing database secrets...')}")
            vault_cmd.process_database_secrets(apps)
            
            # Start all services after Vault is initialized
            print(f"{Colors.info('Starting all services...')}")
            run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium up -d",
                check=True
            )
            
            # Verify deployment
            if not self.verify_docker_deployment():
                return 1
            
            print(f"{Colors.success('Docker Compose deployment completed!')}")
            self.print_docker_access_info()
            return 0
            
        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            return 1
