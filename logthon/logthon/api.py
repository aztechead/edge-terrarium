"""
FastAPI routes and endpoints for the Logthon service.

This module defines all the API endpoints, following the Single Responsibility
Principle by separating API concerns from the rest of the application logic.
"""

import json
import logging
from typing import Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .models import LogSubmission, HealthResponse, LogsResponse, ApiResponse, LogEntry
from .storage import log_storage
from .websocket_manager import websocket_manager
from .ui import get_log_ui_html
from .config import config

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Logthon - Edge Terrarium Log Aggregator",
        description="Real-time log aggregation and viewing service",
        version="0.1.0"
    )
    
    # Add all routes
    _add_routes(app)
    
    return app


def _add_routes(app: FastAPI) -> None:
    """Add all routes to the FastAPI application."""
    
    @app.get("/", response_class=HTMLResponse)
    async def get_log_ui():
        """Serve the log viewing UI."""
        return HTMLResponse(content=get_log_ui_html())
    
    @app.post("/api/logs", response_model=ApiResponse)
    async def submit_log(log_submission: LogSubmission):
        """Endpoint for services to submit logs."""
        try:
            log_entry = log_storage.add_log_entry(log_submission)
            
            # Broadcast to all WebSocket connections
            await websocket_manager.broadcast_log_entry(log_entry)
            
            return ApiResponse(
                status="success",
                message="Log entry added"
            )
        except Exception as e:
            logger.error(f"Error adding log entry: {e}")
            raise HTTPException(status_code=500, detail="Failed to add log entry")
    
    @app.get("/api/logs", response_model=LogsResponse)
    async def get_logs(service: Optional[str] = None, limit: int = 100):
        """Get recent logs, optionally filtered by service."""
        try:
            logs = log_storage.get_logs(service=service, limit=limit)
            return LogsResponse(logs=logs, count=len(logs))
        except Exception as e:
            logger.error(f"Error retrieving logs: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve logs")
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time log streaming."""
        # Check connection limit
        if websocket_manager.is_connection_limit_reached():
            await websocket.close(code=1013, reason="Server overloaded")
            return
        
        await websocket.accept()
        websocket_manager.add_connection(websocket)
        
        try:
            # Send initial logs
            initial_logs = log_storage.get_all_logs_for_websocket()
            await websocket_manager.broadcast_initial_logs(websocket, initial_logs)
            
            # Keep connection alive
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            websocket_manager.remove_connection(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            websocket_manager.remove_connection(websocket)
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime
        
        return HealthResponse(
            status="healthy",
            service="logthon",
            timestamp=datetime.now().isoformat(),
            connected_clients=websocket_manager.get_connection_count(),
            log_counts=log_storage.get_log_counts()
        )
    
    @app.delete("/api/logs")
    async def clear_logs(service: Optional[str] = None):
        """Clear logs for a specific service or all services."""
        try:
            log_storage.clear_logs(service=service)
            return ApiResponse(
                status="success",
                message=f"Logs cleared for {'all services' if service is None else service}"
            )
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear logs")
    
    @app.get("/api/storage/info")
    async def get_storage_info():
        """Get information about log storage."""
        try:
            info = log_storage.get_storage_info()
            return JSONResponse(content=info)
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get storage info")
    
    @app.get("/api/websocket/info")
    async def get_websocket_info():
        """Get information about WebSocket connections."""
        try:
            info = websocket_manager.get_connection_info()
            return JSONResponse(content=info)
        except Exception as e:
            logger.error(f"Error getting WebSocket info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get WebSocket info")
