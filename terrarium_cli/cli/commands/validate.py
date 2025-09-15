"""
Validate command for checking app-config.yml files.
"""

import argparse
from pathlib import Path
from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.utils.validation.yaml_validator import validate_all_app_configs, print_validation_results
from terrarium_cli.utils.colors import Colors


class ValidateCommand(BaseCommand):
    """Validate app-config.yml files for syntax and structure errors."""
    
    @staticmethod
    def add_arguments(parser):
        """Add command-specific arguments."""
        # No additional arguments needed for validate command
        pass
    
    def run(self) -> int:
        """Run the validate command."""
        print(f"{Colors.info('Validating app-config.yml files...')}")
        
        apps_dir = Path("apps")
        all_valid, errors_by_file, warnings_by_file = validate_all_app_configs(apps_dir)
        
        print_validation_results(all_valid, errors_by_file, warnings_by_file)
        
        if all_valid:
            print(f"\n{Colors.success('All app-config.yml files are valid!')}")
            return 0
        else:
            print(f"\n{Colors.error('Validation failed. Please fix the errors above.')}")
            return 1
