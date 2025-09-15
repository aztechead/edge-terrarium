"""
Common deployment helpers and utilities.

This module contains shared functionality used by both Docker and K8s deployment managers.
"""

import logging
from typing import List
from pathlib import Path

from terrarium_cli.utils.system.shell import run_command
from terrarium_cli.utils.colors import Colors
from terrarium_cli.config.loaders.app_loader import AppLoader
from terrarium_cli.config.generators.generator import ConfigGenerator

logger = logging.getLogger(__name__)


class CommonDeploymentHelpers:
    """Common deployment functionality shared across different deployment targets."""
    
    def __init__(self):
        """Initialize common deployment helpers."""
        self._app_loader = None
    
    def load_apps(self) -> List:
        """Load all application configurations."""
        if self._app_loader is None:
            self._app_loader = AppLoader()
        return self._app_loader.load_apps()
    
    def generate_config(self, config_type: str) -> bool:
        """Generate configuration files."""
        try:
            print(f"{Colors.info(f'Generating {config_type} configuration...')}")
            apps = self.load_apps()
            generator = ConfigGenerator()
            generator.generate_all_configs(apps)
            print(f"{Colors.success(f'{config_type} configuration generated')}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate {config_type} configuration: {e}")
            return False
    
    def build_app_images(self, apps: List) -> bool:
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
        except Exception as e:
            logger.error(f"Failed to build images: {e}")
            return False
    
    def generate_certificates(self) -> bool:
        """Generate TLS certificates."""
        try:
            print(f"{Colors.info('Generating TLS certificates...')}")
            from terrarium_cli.cli.commands.cert import CertCommand
            
            # Create a mock args object for CertCommand
            class MockArgs:
                def __init__(self):
                    self.action = 'generate'
                    self.name = 'edge-terrarium'
                    self.days = 365
                    self.force = False
            
            cert_cmd = CertCommand(MockArgs())
            result = cert_cmd.run()
            
            if result != 0:
                print(f"{Colors.error('Failed to generate TLS certificates')}")
                return False
            
            print(f"{Colors.success('TLS certificates generated successfully')}")
            return True
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            return False
