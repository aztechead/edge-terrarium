#!/usr/bin/env python3
"""
Edge-Terrarium CLI Tool

A unified Python CLI tool for managing the Edge-Terrarium application deployment.
Replaces all Bash scripts with a maintainable Python-based solution.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from terrarium_cli.commands.deploy import DeployCommand
from terrarium_cli.commands.build import BuildCommand
from terrarium_cli.commands.test import TestCommand
from terrarium_cli.commands.add_app import AddAppCommand
from terrarium_cli.commands.vault import VaultCommand
from terrarium_cli.utils.logging import setup_logging
from terrarium_cli.utils.colors import Colors


def create_parser():
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="Edge-Terrarium CLI Tool - Unified deployment and management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terrarium.py deploy docker          # Deploy to Docker Compose
  terrarium.py deploy k3s            # Deploy to K3s
  terrarium.py build                 # Build all Docker images
  terrarium.py test                  # Test the deployment
  terrarium.py add-app               # Add a new application
  terrarium.py vault init            # Initialize Vault
        """
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version="Edge-Terrarium CLI v1.0.0"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output except errors"
    )
    
    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True
    )
    
    # Deploy command
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy the application"
    )
    DeployCommand.add_arguments(deploy_parser)
    
    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build Docker images"
    )
    BuildCommand.add_arguments(build_parser)
    
    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Test the deployment"
    )
    TestCommand.add_arguments(test_parser)
    
    # Add app command
    add_app_parser = subparsers.add_parser(
        "add-app",
        help="Add a new application"
    )
    AddAppCommand.add_arguments(add_app_parser)
    
    # Vault command
    vault_parser = subparsers.add_parser(
        "vault",
        help="Vault management operations"
    )
    VaultCommand.add_arguments(vault_parser)
    
    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Execute the appropriate command
        if args.command == "deploy":
            command = DeployCommand(args)
        elif args.command == "build":
            command = BuildCommand(args)
        elif args.command == "test":
            command = TestCommand(args)
        elif args.command == "add-app":
            command = AddAppCommand(args)
        elif args.command == "vault":
            command = VaultCommand(args)
        else:
            parser.print_help()
            return 1
        
        # Run the command
        result = command.run()
        return result
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.RESET}")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
