"""
Configuration management for the Logthon service.

This module handles all configuration settings, following the Single Responsibility
Principle by centralizing configuration management and making it easy to modify
settings without changing the core application logic.
"""

import os
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    """Configuration for individual services."""
    
    name: str
    color: str
    max_logs: int = 1000


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connections."""
    
    max_connections: int = 100
    initial_logs_to_send: int = 50
    reconnect_delay: int = 3000  # milliseconds


@dataclass
class ServerConfig:
    """Configuration for the FastAPI server."""
    
    host: str = "0.0.0.0"
    port: int = 5000
    log_level: str = "info"
    access_log: bool = False


class Config:
    """Main configuration class for the Logthon service."""
    
    def __init__(self):
        self.server = ServerConfig(
            host=os.getenv("LOGTHON_HOST", "0.0.0.0"),
            port=int(os.getenv("LOGTHON_PORT", "5000")),
            log_level=os.getenv("LOGTHON_LOG_LEVEL", "info").lower(),
            access_log=os.getenv("LOGTHON_ACCESS_LOG", "false").lower() == "true"
        )
        
        self.websocket = WebSocketConfig(
            max_connections=int(os.getenv("LOGTHON_MAX_WS_CONNECTIONS", "100")),
            initial_logs_to_send=int(os.getenv("LOGTHON_INITIAL_LOGS", "50")),
            reconnect_delay=int(os.getenv("LOGTHON_RECONNECT_DELAY", "3000"))
        )
        
        self.services = self._initialize_services()
    
    def _initialize_services(self) -> Dict[str, ServiceConfig]:
        """Initialize service configurations with default values."""
        return {
            'cdp-client': ServiceConfig(
                name='cdp-client',
                color='#00ff00',  # Green
                max_logs=int(os.getenv("LOGTHON_CDP_CLIENT_MAX_LOGS", "1000"))
            ),
            'service-sink': ServiceConfig(
                name='service-sink',
                color='#0080ff',  # Blue
                max_logs=int(os.getenv("LOGTHON_SERVICE_SINK_MAX_LOGS", "1000"))
            ),
            'logthon': ServiceConfig(
                name='logthon',
                color='#ff8000',  # Orange
                max_logs=int(os.getenv("LOGTHON_LOGTHON_MAX_LOGS", "1000"))
            )
        }
    
    def get_service_color(self, service_name: str) -> str:
        """Get the color for a specific service."""
        if service_name in self.services:
            return self.services[service_name].color
        return '#ffffff'  # Default white color
    
    def get_service_max_logs(self, service_name: str) -> int:
        """Get the maximum number of logs for a specific service."""
        if service_name in self.services:
            return self.services[service_name].max_logs
        return 1000  # Default max logs
    
    def get_all_service_names(self) -> List[str]:
        """Get a list of all configured service names."""
        return list(self.services.keys())


# Global configuration instance
config = Config()
