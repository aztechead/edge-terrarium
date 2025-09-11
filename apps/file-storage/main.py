#!/usr/bin/env python3
"""
File Storage API Service
A FastAPI-based service for managing file storage with CRUD operations.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from file_storage.app import create_file_storage_app

def main():
    """Main entry point for the file storage service."""
    # Get configuration from environment variables
    host = os.getenv("FILE_STORAGE_HOST", "0.0.0.0")
    port = int(os.getenv("FILE_STORAGE_PORT", "9000"))
    log_level = os.getenv("FILE_STORAGE_LOG_LEVEL", "info")
    
    # Create the FastAPI application
    app = create_file_storage_app()
    
    # Run the application
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
