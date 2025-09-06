#!/usr/bin/env python3
"""
Logthon - Log Aggregation Service for Edge Terrarium

This service collects logs from CDP client and service-sink containers
and provides a web UI for real-time log viewing with color-coded output.

This is the main entry point that uses the modular logthon package.
"""

import uvicorn
from logthon.app import get_app
from logthon.config import config

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