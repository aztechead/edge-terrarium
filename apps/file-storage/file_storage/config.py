"""
Configuration module for the File Storage API service.
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class StorageConfig:
    """Configuration for file storage settings."""
    
    storage_path: str = "/app/storage"
    max_files: int = 15
    allowed_extensions: List[str] = None
    max_file_size: int = 1024 * 1024  # 1MB
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [".txt", ".json", ".log"]


@dataclass
class ServerConfig:
    """Configuration for the FastAPI server."""
    
    host: str = "0.0.0.0"
    port: int = 9000
    log_level: str = "info"
    access_log: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging integration."""
    
    logthon_host: str = "logthon-ingress-service.edge-terrarium.svc.cluster.local"
    logthon_port: int = 5000
    service_name: str = "file-storage"
    log_level: str = "INFO"


class Config:
    """Main configuration class that loads settings from environment variables."""
    
    def __init__(self):
        self.storage = self._load_storage_config()
        self.server = self._load_server_config()
        self.logging = self._load_logging_config()
    
    def _load_storage_config(self) -> StorageConfig:
        """Load storage configuration from environment variables."""
        return StorageConfig(
            storage_path=os.getenv("FILE_STORAGE_PATH", "/app/storage"),
            max_files=int(os.getenv("FILE_STORAGE_MAX_FILES", "15")),
            max_file_size=int(os.getenv("FILE_STORAGE_MAX_SIZE", str(1024 * 1024)))
        )
    
    def _load_server_config(self) -> ServerConfig:
        """Load server configuration from environment variables."""
        return ServerConfig(
            host=os.getenv("FILE_STORAGE_HOST", "0.0.0.0"),
            port=int(os.getenv("FILE_STORAGE_PORT", "9000")),
            log_level=os.getenv("FILE_STORAGE_LOG_LEVEL", "info"),
            access_log=os.getenv("FILE_STORAGE_ACCESS_LOG", "true").lower() == "true"
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration from environment variables."""
        return LoggingConfig(
            logthon_host=os.getenv("LOGTHON_HOST", "logthon-ingress-service.edge-terrarium.svc.cluster.local"),
            logthon_port=int(os.getenv("LOGTHON_PORT", "5000")),
            service_name=os.getenv("SERVICE_NAME", "file-storage"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def get_storage_path(self) -> str:
        """Get the configured storage path."""
        return self.storage.storage_path
    
    def get_max_files(self) -> int:
        """Get the maximum number of files allowed."""
        return self.storage.max_files
    
    def get_max_file_size(self) -> int:
        """Get the maximum file size allowed."""
        return self.storage.max_file_size
    
    def get_allowed_extensions(self) -> List[str]:
        """Get the list of allowed file extensions."""
        return self.storage.allowed_extensions
