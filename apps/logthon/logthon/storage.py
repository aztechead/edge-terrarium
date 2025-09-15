"""
Log storage management for the Logthon service.

This module handles the storage and retrieval of log entries, following the
Single Responsibility Principle by separating storage concerns from the rest
of the application logic.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from .models import LogEntry, LogSubmission
from .config import config

logger = logging.getLogger(__name__)


class LogStorage:
    """Manages log storage with thread-safe operations."""
    
    def __init__(self):
        """Initialize the log storage with configured services."""
        self._storage: Dict[str, deque] = {}
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize storage for all configured services."""
        for service_name in config.get_all_service_names():
            max_logs = config.get_service_max_logs(service_name)
            self._storage[service_name] = deque(maxlen=max_logs)
    
    def add_log_entry(self, log_submission: LogSubmission) -> LogEntry:
        """
        Add a new log entry to storage.
        
        Args:
            log_submission: The log submission data
            
        Returns:
            LogEntry: The created log entry with ID and timestamp
            
        Raises:
            ValueError: If the service is not configured
        """
        if log_submission.service not in self._storage:
            # Auto-create storage for unknown services
            self._storage[log_submission.service] = deque(maxlen=1000)
            logger.warning(f"Auto-created storage for unknown service: {log_submission.service}")
        
        # Create the log entry
        entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            service=log_submission.service,
            level=log_submission.level,
            message=log_submission.message,
            metadata=log_submission.metadata or {}
        )
        
        # Store the entry
        self._storage[log_submission.service].append(entry)
        
        # Log to console as well
        logger.info(f"[{log_submission.service}] {log_submission.message}")
        
        return entry
    
    def get_logs(self, service: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        """
        Retrieve logs from storage.
        
        Args:
            service: Optional service name to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List[LogEntry]: List of log entries
        """
        if service and service in self._storage:
            # Return logs for specific service
            logs = list(self._storage[service])[-limit:]
        elif service is None:
            # Return logs from all services, sorted by timestamp
            all_logs = []
            for service_logs in self._storage.values():
                all_logs.extend(list(service_logs))
            
            # Sort by timestamp
            all_logs.sort(key=lambda x: x.timestamp)
            logs = all_logs[-limit:]
        else:
            # Service not found
            logs = []
        
        return logs
    
    def get_log_counts(self) -> Dict[str, int]:
        """
        Get the count of logs for each service.
        
        Returns:
            Dict[str, int]: Mapping of service names to log counts
        """
        return {service: len(logs) for service, logs in self._storage.items()}
    
    def get_all_logs_for_websocket(self, limit: int = None) -> List[LogEntry]:
        """
        Get all logs for WebSocket broadcasting.
        
        Args:
            limit: Optional limit on number of logs
            
        Returns:
            List[LogEntry]: List of all log entries sorted by timestamp
        """
        if limit is None:
            limit = config.websocket.initial_logs_to_send
        
        all_logs = []
        for service_logs in self._storage.values():
            all_logs.extend(list(service_logs))
        
        # Sort by timestamp
        all_logs.sort(key=lambda x: x.timestamp)
        return all_logs[-limit:]
    
    def clear_logs(self, service: Optional[str] = None) -> None:
        """
        Clear logs for a specific service or all services.
        
        Args:
            service: Optional service name to clear logs for
        """
        if service and service in self._storage:
            self._storage[service].clear()
            logger.info(f"Cleared logs for service: {service}")
        elif service is None:
            for service_name in self._storage:
                self._storage[service_name].clear()
            logger.info("Cleared all logs")
        else:
            logger.warning(f"Attempted to clear logs for unknown service: {service}")
    
    def get_storage_info(self) -> Dict[str, Dict[str, int]]:
        """
        Get information about the storage state.
        
        Returns:
            Dict containing storage information for each service
        """
        info = {}
        for service_name, logs in self._storage.items():
            info[service_name] = {
                'count': len(logs),
                'max_size': logs.maxlen,
                'is_full': len(logs) == logs.maxlen
            }
        return info


# Global storage instance
log_storage = LogStorage()
