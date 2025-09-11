"""
Build command for the CLI tool.
"""

import argparse
import logging
import time
from pathlib import Path

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.shell import run_command, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.config.app_loader import AppLoader
from terrarium_cli.utils.dependencies import DependencyChecker

logger = logging.getLogger(__name__)


class BuildCommand(BaseCommand):
    """Command to build Docker images."""
    
    def run(self) -> int:
        """Run the build command."""
        try:
            print(f"{Colors.info('Building Docker images...')}")
            
            # Check dependencies
            dep_checker = DependencyChecker()
            if not dep_checker.check_all_dependencies(['docker', 'curl']):
                print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
                return 1
            
            # Load app configurations
            app_loader = AppLoader()
            apps = app_loader.load_apps()
            
            if not apps:
                print(f"{Colors.warning('No applications found to build')}")
                return 0
            
            # Build each app
            success_count = 0
            for app in apps:
                if self._build_app(app):
                    success_count += 1
            
            if success_count == len(apps):
                print(f"{Colors.success(f'Successfully built {success_count} images')}")
                return 0
            else:
                print(f"{Colors.error(f'Failed to build {len(apps) - success_count} images')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Build failed: {e}")
            return 1
    
    def _build_app(self, app) -> bool:
        """Build a single app."""
        try:
            # Skip building if using official image (no build_context specified)
            if not hasattr(app.docker, 'build_context') or not getattr(app.docker, 'build_context', None):
                print(f"{Colors.info(f'Skipping {app.name} - using official image {app.docker.image_name}:{app.docker.tag}')}")
                return True
            
            print(f"{Colors.info(f'Building {app.name} image...')}")
            
            # Check if Dockerfile exists
            dockerfile_path = Path(f"apps/{app.name}/{app.docker.dockerfile}")
            if not dockerfile_path.exists():
                print(f"{Colors.error(f'Dockerfile not found: {dockerfile_path}')}")
                return False
            
            # Build the image
            build_cmd = [
                "docker", "build",
                "-t", f"{app.docker.image_name}:{app.docker.tag}",
                "-f", str(dockerfile_path),
                f"apps/{app.name}"
            ]
            
            # Add build arguments if specified
            if hasattr(self.args, 'build_args') and self.args.build_args:
                for build_arg in self.args.build_args:
                    build_cmd.extend(["--build-arg", build_arg])
            
            # Add no-cache flag if specified
            if hasattr(self.args, 'no_cache') and self.args.no_cache:
                build_cmd.append("--no-cache")
            
            # Add platform if specified
            if hasattr(self.args, 'platform') and self.args.platform:
                build_cmd.extend(["--platform", self.args.platform])
            
            start_time = time.time()
            run_command(build_cmd, check=True)
            build_time = time.time() - start_time
            
            print(f"{Colors.success(f'{app.name} image built successfully in {build_time:.1f}s')}")
            return True
            
        except ShellError as e:
            print(f"{Colors.error(f'Failed to build {app.name}: {e}')}")
            return False
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add build command arguments."""
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Build without using cache"
        )
        
        parser.add_argument(
            "--platform",
            help="Set platform for build (e.g., linux/amd64, linux/arm64)"
        )
        
        parser.add_argument(
            "--build-arg",
            action="append",
            dest="build_args",
            help="Set build-time variables (can be used multiple times)"
        )
        
        parser.add_argument(
            "--app",
            help="Build only the specified app"
        )
