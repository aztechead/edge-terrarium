"""
Logging integration module for the File Storage API service.
Sends logs to the logthon service for centralized logging.
"""

import json
import time
import requests
from typing import Optional
from .config import Config


class LoggingManager:
    """Manages logging integration with logthon service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logthon_url = f"http://{config.logging.logthon_host}:{config.logging.logthon_port}/logs"
        self.service_name = config.logging.service_name
    
    def _send_log(self, level: str, message: str, metadata: Optional[dict] = None) -> None:
        """Send a log message to the logthon service."""
        try:
            container_info = self._get_container_info()
            payload = {
                "service": self.service_name,
                "level": level,
                "message": message,
                "metadata": {
                    "timestamp": int(time.time()),
                    "container_id": container_info["container_id"],
                    "container_name": container_info["container_name"],
                    **(metadata or {})
                }
            }
            
            response = requests.post(
                self.logthon_url,
                json=payload,
                timeout=2
            )
            
            if response.status_code != 200:
                print(f"Failed to send log to logthon: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending log to logthon: {e}")
    
    def _get_container_info(self) -> dict:
        """Get container information from environment or hostname."""
        import os
        
        # Get container ID from hostname (pod name in Kubernetes)
        container_id = os.getenv("HOSTNAME", "unknown")
        
        # Try to get a more meaningful container name
        container_name = os.getenv("CONTAINER_NAME")
        if not container_name:
            container_name = os.getenv("POD_NAME")  # In K8s, this is often more meaningful
        if not container_name:
            container_name = container_id  # Fallback to hostname
        
        return {
            "container_id": container_id,
            "container_name": container_name
        }
    
    def info(self, message: str, metadata: Optional[dict] = None) -> None:
        """Send an INFO level log message."""
        self._send_log("INFO", message, metadata)
    
    def warning(self, message: str, metadata: Optional[dict] = None) -> None:
        """Send a WARNING level log message."""
        self._send_log("WARNING", message, metadata)
    
    def error(self, message: str, metadata: Optional[dict] = None) -> None:
        """Send an ERROR level log message."""
        self._send_log("ERROR", message, metadata)
    
    def debug(self, message: str, metadata: Optional[dict] = None) -> None:
        """Send a DEBUG level log message."""
        self._send_log("DEBUG", message, metadata)
    
    def log_file_operation(self, operation: str, filename: str, success: bool, metadata: Optional[dict] = None) -> None:
        """Log a file operation with standardized format."""
        status = "success" if success else "failed"
        message = f"File {operation} {status}: {filename}"
        
        log_metadata = {
            "operation": operation,
            "filename": filename,
            "success": success,
            **(metadata or {})
        }
        
        level = "INFO" if success else "ERROR"
        self._send_log(level, message, log_metadata)
    
    def log_api_request(self, method: str, endpoint: str, status_code: int, response_time: float, metadata: Optional[dict] = None) -> None:
        """Log an API request with standardized format."""
        message = f"API {method} {endpoint} - {status_code} ({response_time:.3f}s)"
        
        log_metadata = {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time": response_time,
            **(metadata or {})
        }
        
        level = "INFO" if 200 <= status_code < 400 else "WARNING" if 400 <= status_code < 500 else "ERROR"
        self._send_log(level, message, log_metadata)
