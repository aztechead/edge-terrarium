#!/usr/bin/env python3
"""
Logthon - Log Aggregation Service for Edge Terrarium

This service collects logs from Custom client and service-sink containers
and provides a web UI for real-time log viewing with color-coded output.

This is the main entry point that uses the modular logthon package.
"""

import uvicorn
import sys
import os

# Verify logthon package can be imported
try:
    from logthon.app import get_app
    from logthon.config import config
    print("✓ Logthon package imported successfully")
except ImportError as e:
    print(f"✗ Failed to import logthon package: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print("Contents of current directory:")
    for item in os.listdir('.'):
        print(f"  {item}")
    sys.exit(1)

if __name__ == "__main__":
    # Get the configured application
    app, initial_entry = get_app()
    
    # Start the server
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
        access_log=config.server.access_log
    )