"""
Application factory for the File Storage API service.
"""

from fastapi import FastAPI
from .api import create_file_storage_app as create_api_app


def create_file_storage_app() -> FastAPI:
    """Create the File Storage API application."""
    return create_api_app()
