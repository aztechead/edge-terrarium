"""
Main application module for the Logthon service.

This module provides the main application entry point and initialization logic,
following the Single Responsibility Principle by separating application startup
concerns from the rest of the application logic.
"""

import logging
import uuid
from datetime import datetime

from .api import create_app
from .storage import log_storage
from .models import LogSubmission
from .config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_logthon_app() -> tuple:
    """
    Create and initialize the Logthon application.
    
    Returns:
        tuple: (FastAPI app, initialization log entry)
    """
    # Create the FastAPI application
    app = create_app()
    
    # Add initial log entry
    initial_log = LogSubmission(
        service='logthon',
        level='INFO',
        message='Logthon service started',
        metadata={'version': '0.1.0', 'startup_time': datetime.now().isoformat()}
    )
    
    initial_entry = log_storage.add_log_entry(initial_log)
    
    logger.info("[logthon] Logthon service started")
    
    return app, initial_entry


def get_app() -> tuple:
    """
    Get the configured Logthon application.
    
    Returns:
        tuple: (FastAPI app, initialization log entry)
    """
    return create_logthon_app()
