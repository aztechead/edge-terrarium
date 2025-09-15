"""
Check dependencies command for the CLI tool.
"""

import argparse
import logging

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.dependencies import DependencyChecker
from terrarium_cli.utils.colors import Colors

logger = logging.getLogger(__name__)


class CheckDepsCommand(BaseCommand):
    """Command to check system dependencies."""
    
    @staticmethod
    def add_arguments(parser):
        """Add command-specific arguments."""
        pass
    
    def run(self) -> int:
        """Run the check-deps command."""
        try:
            print(f"{Colors.info('Checking system dependencies...')}")
            
            # Check all dependencies
            dep_checker = DependencyChecker()
            if dep_checker.check_all_dependencies():
                print(f"\n{Colors.success('All dependencies are available!')}")
                return 0
            else:
                print(f"\n{Colors.error('Some dependencies are missing. Please install them and try again.')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to check dependencies: {e}")
            return 1
