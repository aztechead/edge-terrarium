"""
Add app command for the CLI tool.
"""

import argparse
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.colors import Colors

logger = logging.getLogger(__name__)


class AddAppCommand(BaseCommand):
    """Command to add a new application."""
    
    def run(self) -> int:
        """Run the add-app command."""
        try:
            print(f"{Colors.info('Adding new application...')}")
            
            # Get app information
            app_info = self._get_app_info()
            if not app_info:
                return 1
            
            # Create app directory
            if not self._create_app_directory(app_info):
                return 1
            
            # Create app configuration
            if not self._create_app_config(app_info):
                return 1
            
            # Create Dockerfile
            if not self._create_dockerfile(app_info):
                return 1
            
            # Create basic source structure
            if not self._create_source_structure(app_info):
                return 1
            
            print(f"{Colors.success(f'Application {app_info["name"]} created successfully!')}")
            print(f"\n{Colors.BOLD('Next steps:')}")
            print(f"  1. Add your source code to apps/{app_info['name']}/")
            print(f"  2. Update the Dockerfile if needed")
            print(f"  3. Run 'terrarium.py build' to build the image")
            print(f"  4. Run 'terrarium.py deploy' to deploy all apps")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to add app: {e}")
            return 1
    
    def _get_app_info(self) -> Dict[str, Any]:
        """Get application information from user."""
        app_info = {}
        
        # App name
        app_name = input("Application name (e.g., my-service): ").strip()
        if not app_name:
            print(f"{Colors.error('App name is required')}")
            return None
        
        # Validate app name
        if not app_name.replace("-", "").replace("_", "").isalnum():
            print(f"{Colors.error('App name must contain only alphanumeric characters, hyphens, and underscores')}")
            return None
        
        # Check if app already exists
        if Path(f"apps/{app_name}").exists():
            print(f"{Colors.error(f'App {app_name} already exists')}")
            return None
        
        app_info["name"] = app_name
        
        # Description
        app_info["description"] = input("Application description: ").strip() or f"{app_name} service"
        
        # Port
        while True:
            try:
                port = input("Internal port (e.g., 8080): ").strip()
                if port:
                    app_info["port"] = int(port)
                    break
                else:
                    print(f"{Colors.error('Port is required')}")
            except ValueError:
                print(f"{Colors.error('Port must be a number')}")
        
        # Docker image name
        app_info["image_name"] = input(f"Docker image name (default: edge-terrarium-{app_name}): ").strip()
        if not app_info["image_name"]:
            app_info["image_name"] = f"edge-terrarium-{app_name}"
        
        # Routes
        routes = []
        print(f"\n{Colors.info('Configure routing (press Enter to skip):')}")
        
        # Default route
        default_route = input(f"Default API route (default: /api/{app_name}/*): ").strip()
        if not default_route:
            default_route = f"/api/{app_name}/*"
        
        routes.append({
            "path": default_route,
            "target": "/",
            "strip_prefix": True
        })
        
        # Additional routes
        while True:
            additional_route = input("Additional route (e.g., /api/custom/* -> /custom/): ").strip()
            if not additional_route:
                break
            
            if " -> " in additional_route:
                path, target = additional_route.split(" -> ", 1)
                routes.append({
                    "path": path.strip(),
                    "target": target.strip(),
                    "strip_prefix": True
                })
            else:
                print(f"{Colors.warning('Route format should be: /path/* -> /target/')}")
        
        app_info["routes"] = routes
        
        # Environment variables
        env_vars = []
        print(f"\n{Colors.info('Environment variables (press Enter to skip):')}")
        
        while True:
            env_var = input("Environment variable (name=value or name=vault:path#key): ").strip()
            if not env_var:
                break
            
            if "=" in env_var:
                name, value = env_var.split("=", 1)
                env_vars.append({
                    "name": name.strip(),
                    "value": value.strip()
                })
            else:
                print(f"{Colors.warning('Environment variable format should be: name=value')}")
        
        app_info["environment"] = env_vars
        
        # Volumes
        volumes = []
        print(f"\n{Colors.info('Persistent volumes (press Enter to skip):')}")
        
        while True:
            volume = input("Volume (mount_path:size, e.g., /app/data:1Gi): ").strip()
            if not volume:
                break
            
            if ":" in volume:
                mount_path, size = volume.split(":", 1)
                volumes.append({
                    "name": f"{app_name}-data",
                    "mount_path": mount_path.strip(),
                    "size": size.strip(),
                    "access_mode": "ReadWriteOnce"
                })
            else:
                print(f"{Colors.warning('Volume format should be: mount_path:size')}")
        
        app_info["volumes"] = volumes
        
        return app_info
    
    def _create_app_directory(self, app_info: Dict[str, Any]) -> bool:
        """Create app directory structure."""
        try:
            app_dir = Path(f"apps/{app_info['name']}")
            app_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"{Colors.success(f'Created directory: {app_dir}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create app directory: {e}')}")
            return False
    
    def _create_app_config(self, app_info: Dict[str, Any]) -> bool:
        """Create app configuration file."""
        try:
            config_data = {
                "name": app_info["name"],
                "description": app_info["description"],
                "docker": {
                    "build_context": ".",
                    "dockerfile": "Dockerfile",
                    "image_name": app_info["image_name"],
                    "tag": "latest"
                },
                "runtime": {
                    "port": app_info["port"],
                    "health_check_path": "/health",
                    "startup_timeout": 30
                },
                "environment": app_info["environment"],
                "routes": app_info["routes"],
                "dependencies": [],
                "resources": {
                    "cpu": {
                        "request": "100m",
                        "limit": "200m"
                    },
                    "memory": {
                        "request": "128Mi",
                        "limit": "256Mi"
                    }
                },
                "health_checks": {
                    "liveness": {
                        "path": "/health",
                        "port": app_info["port"],
                        "period_seconds": 30,
                        "timeout_seconds": 3,
                        "failure_threshold": 3
                    },
                    "readiness": {
                        "path": "/health",
                        "port": app_info["port"],
                        "period_seconds": 10,
                        "timeout_seconds": 3,
                        "failure_threshold": 3
                    }
                },
                "volumes": app_info["volumes"],
                "security": {
                    "run_as_non_root": True,
                    "run_as_user": 1001,
                    "run_as_group": 1001,
                    "allow_privilege_escalation": False,
                    "read_only_root_filesystem": False
                }
            }
            
            config_file = Path(f"apps/{app_info['name']}/app-config.yml")
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"{Colors.success(f'Created configuration: {config_file}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create app config: {e}')}")
            return False
    
    def _create_dockerfile(self, app_info: Dict[str, Any]) -> bool:
        """Create Dockerfile."""
        try:
            dockerfile_content = f"""# Dockerfile for {app_info['name']}
# TODO: Customize this Dockerfile for your application

FROM alpine:3.18

# Install runtime dependencies
RUN apk add --no-cache ca-certificates curl

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE {app_info['port']}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{app_info['port']}/health || exit 1

# Run the application
CMD ["echo", "Hello from {app_info['name']}"]
"""
            
            dockerfile_path = Path(f"apps/{app_info['name']}/Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            print(f"{Colors.success(f'Created Dockerfile: {dockerfile_path}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create Dockerfile: {e}')}")
            return False
    
    def _create_source_structure(self, app_info: Dict[str, Any]) -> bool:
        """Create basic source structure."""
        try:
            app_dir = Path(f"apps/{app_info['name']}")
            
            # Create src directory
            src_dir = app_dir / "src"
            src_dir.mkdir(exist_ok=True)
            
            # Create README
            readme_content = f"""# {app_info['name']}

{app_info['description']}

## Configuration

This application is configured via `app-config.yml` and will be automatically included in deployments.

## Development

1. Add your source code to the `src/` directory
2. Update the Dockerfile as needed
3. Run `terrarium.py build` to build the image
4. Run `terrarium.py deploy` to deploy all apps

## API Routes

{chr(10).join([f"- {route['path']} -> {route['target']}" for route in app_info['routes']])}

## Environment Variables

{chr(10).join([f"- {env['name']}" for env in app_info['environment']]) if app_info['environment'] else "- None configured"}

## Volumes

{chr(10).join([f"- {vol['mount_path']} ({vol['size']})" for vol in app_info['volumes']]) if app_info['volumes'] else "- None configured"}
"""
            
            readme_path = app_dir / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            print(f"{Colors.success(f'Created source structure: {app_dir}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create source structure: {e}')}")
            return False
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add add-app command arguments."""
        parser.add_argument(
            "--template",
            choices=["python", "node", "go", "rust", "generic"],
            default="generic",
            help="Application template to use (default: generic)"
        )
        
        parser.add_argument(
            "--interactive",
            action="store_true",
            default=True,
            help="Use interactive mode (default: true)"
        )
