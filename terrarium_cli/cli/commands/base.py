"""
Base command class for all CLI commands.
"""

import argparse
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self, args: argparse.Namespace):
        """
        Initialize the command.
        
        Args:
            args: Parsed command line arguments
        """
        self.args = args
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def run(self) -> int:
        """
        Run the command.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass
    
    @staticmethod
    @abstractmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """
        Add command-specific arguments to the parser.
        
        Args:
            parser: Argument parser to add arguments to
        """
        pass
