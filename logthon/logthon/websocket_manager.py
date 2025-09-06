"""
WebSocket connection management for the Logthon service.

This module handles WebSocket connections and broadcasting, following the
Single Responsibility Principle by separating WebSocket concerns from the
rest of the application logic.
"""

import json
import logging
from typing import List, Set
from fastapi import WebSocket

from .models import LogEntry
from .config import config

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self._connections: Set[WebSocket] = set()
    
    def add_connection(self, websocket: WebSocket) -> None:
        """
        Add a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to add
        """
        self._connections.add(websocket)
        logger.info(f"WebSocket connection added. Total connections: {len(self._connections)}")
    
    def remove_connection(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        if websocket in self._connections:
            self._connections.remove(websocket)
            logger.info(f"WebSocket connection removed. Total connections: {len(self._connections)}")
    
    def get_connection_count(self) -> int:
        """
        Get the number of active WebSocket connections.
        
        Returns:
            int: Number of active connections
        """
        return len(self._connections)
    
    async def broadcast_log_entry(self, log_entry: LogEntry) -> None:
        """
        Broadcast a log entry to all connected WebSocket clients.
        
        Args:
            log_entry: The log entry to broadcast
        """
        if not self._connections:
            return
        
        message = json.dumps(log_entry.model_dump())
        disconnected = set()
        
        for websocket in self._connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.remove_connection(ws)
    
    async def broadcast_initial_logs(self, websocket: WebSocket, initial_logs: List[LogEntry]) -> None:
        """
        Send initial logs to a newly connected WebSocket client.
        
        Args:
            websocket: The WebSocket connection to send logs to
            initial_logs: List of initial log entries to send
        """
        try:
            for log_entry in initial_logs:
                message = json.dumps(log_entry.model_dump())
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send initial logs to WebSocket: {e}")
            raise
    
    def is_connection_limit_reached(self) -> bool:
        """
        Check if the connection limit has been reached.
        
        Returns:
            bool: True if connection limit is reached
        """
        return len(self._connections) >= config.websocket.max_connections
    
    def get_connection_info(self) -> dict:
        """
        Get information about WebSocket connections.
        
        Returns:
            dict: Connection information
        """
        return {
            'active_connections': len(self._connections),
            'max_connections': config.websocket.max_connections,
            'connection_limit_reached': self.is_connection_limit_reached()
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
