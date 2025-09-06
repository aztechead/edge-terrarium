#!/usr/bin/env python3
"""
Logthon - Log Aggregation Service for Edge Terrarium

This service collects logs from CDP client and service-sink containers
and provides a web UI for real-time log viewing with color-coded output.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import uuid

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global log storage
log_storage: Dict[str, deque] = {
    'cdp-client': deque(maxlen=1000),
    'service-sink': deque(maxlen=1000),
    'logthon': deque(maxlen=1000)
}

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []

# Color mapping for different services
SERVICE_COLORS = {
    'cdp-client': '#00ff00',      # Green
    'service-sink': '#0080ff',    # Blue
    'logthon': '#ff8000',         # Orange
    'default': '#ffffff'          # White
}

class LogEntry(BaseModel):
    timestamp: str
    service: str
    level: str
    message: str
    metadata: Optional[Dict] = None

class LogSubmission(BaseModel):
    service: str
    level: str = "INFO"
    message: str
    metadata: Optional[Dict] = None

app = FastAPI(
    title="Logthon - Edge Terrarium Log Aggregator",
    description="Real-time log aggregation and viewing service",
    version="0.1.0"
)

def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def add_log_entry(service: str, level: str, message: str, metadata: Optional[Dict] = None):
    """Add a log entry to storage"""
    entry = {
        'id': str(uuid.uuid4()),
        'timestamp': get_timestamp(),
        'service': service,
        'level': level,
        'message': message,
        'metadata': metadata or {}
    }
    
    log_storage[service].append(entry)
    
    # Log to console as well
    logger.info(f"[{service}] {message}")
    
    # Broadcast to all WebSocket connections
    asyncio.create_task(broadcast_log_entry(entry))

async def broadcast_log_entry(entry: Dict):
    """Broadcast log entry to all connected WebSocket clients"""
    if websocket_connections:
        message = json.dumps(entry)
        disconnected = []
        
        for websocket in websocket_connections:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections.remove(ws)

@app.get("/", response_class=HTMLResponse)
async def get_log_ui():
    """Serve the log viewing UI"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Logthon - Edge Terrarium Logs</title>
        <style>
            body {
                font-family: 'Courier New', monospace;
                background-color: #1a1a1a;
                color: #ffffff;
                margin: 0;
                padding: 20px;
                overflow-x: auto;
            }
            
            .header {
                background-color: #2a2a2a;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                text-align: center;
            }
            
            .controls {
                background-color: #2a2a2a;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
                align-items: center;
                flex-wrap: wrap;
            }
            
            .control-group {
                display: flex;
                gap: 5px;
                align-items: center;
            }
            
            .service-filter {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
            }
            
            .service-filter.active {
                background-color: #555;
                border-color: #777;
            }
            
            .log-container {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 5px;
                height: 70vh;
                overflow-y: auto;
                padding: 10px;
                font-size: 12px;
                line-height: 1.4;
            }
            
            .log-entry {
                margin-bottom: 2px;
                padding: 2px 5px;
                border-radius: 2px;
                word-wrap: break-word;
            }
            
            .log-entry:hover {
                background-color: #2a2a2a;
            }
            
            .timestamp {
                color: #888;
                font-size: 10px;
            }
            
            .service {
                font-weight: bold;
                margin: 0 5px;
            }
            
            .level {
                font-weight: bold;
                margin: 0 5px;
            }
            
            .level.INFO { color: #00ff00; }
            .level.WARNING { color: #ffff00; }
            .level.ERROR { color: #ff0000; }
            .level.DEBUG { color: #888; }
            
            .message {
                margin-left: 10px;
            }
            
            .status {
                background-color: #2a2a2a;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
                text-align: center;
            }
            
            .status.connected {
                color: #00ff00;
            }
            
            .status.disconnected {
                color: #ff0000;
            }
            
            .clear-btn {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
            }
            
            .clear-btn:hover {
                background-color: #ff6666;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🐍 Logthon - Edge Terrarium Log Aggregator</h1>
            <p>Real-time log viewing for CDP Client, Service Sink, and Logthon services</p>
        </div>
        
        <div class="status" id="status">
            <span id="status-text">Connecting...</span>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label>Filter Services:</label>
                <button class="service-filter active" data-service="all">All</button>
                <button class="service-filter" data-service="cdp-client">CDP Client</button>
                <button class="service-filter" data-service="service-sink">Service Sink</button>
                <button class="service-filter" data-service="logthon">Logthon</button>
            </div>
            <div class="control-group">
                <button class="clear-btn" onclick="clearLogs()">Clear Logs</button>
            </div>
        </div>
        
        <div class="log-container" id="log-container">
            <div class="log-entry">
                <span class="timestamp">Waiting for logs...</span>
            </div>
        </div>
        
        <script>
            let websocket = null;
            let currentFilter = 'all';
            let logs = [];
            
            const serviceColors = {
                'cdp-client': '#00ff00',
                'service-sink': '#0080ff',
                'logthon': '#ff8000'
            };
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                websocket = new WebSocket(wsUrl);
                
                websocket.onopen = function(event) {
                    updateStatus('Connected', true);
                };
                
                websocket.onmessage = function(event) {
                    const logEntry = JSON.parse(event.data);
                    addLogEntry(logEntry);
                };
                
                websocket.onclose = function(event) {
                    updateStatus('Disconnected', false);
                    setTimeout(connectWebSocket, 3000);
                };
                
                websocket.onerror = function(error) {
                    updateStatus('Error', false);
                };
            }
            
            function updateStatus(text, connected) {
                const statusEl = document.getElementById('status');
                const statusTextEl = document.getElementById('status-text');
                
                statusTextEl.textContent = text;
                statusEl.className = `status ${connected ? 'connected' : 'disconnected'}`;
            }
            
            function addLogEntry(entry) {
                logs.push(entry);
                if (logs.length > 1000) {
                    logs.shift();
                }
                renderLogs();
            }
            
            function renderLogs() {
                const container = document.getElementById('log-container');
                const filteredLogs = currentFilter === 'all' 
                    ? logs 
                    : logs.filter(log => log.service === currentFilter);
                
                container.innerHTML = filteredLogs.map(log => {
                    const color = serviceColors[log.service] || '#ffffff';
                    return `
                        <div class="log-entry" style="border-left: 3px solid ${color}">
                            <span class="timestamp">${log.timestamp}</span>
                            <span class="service" style="color: ${color}">[${log.service}]</span>
                            <span class="level ${log.level}">${log.level}</span>
                            <span class="message">${escapeHtml(log.message)}</span>
                        </div>
                    `;
                }).join('');
                
                container.scrollTop = container.scrollHeight;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function clearLogs() {
                logs = [];
                renderLogs();
            }
            
            // Service filter event listeners
            document.querySelectorAll('.service-filter').forEach(button => {
                button.addEventListener('click', function() {
                    document.querySelectorAll('.service-filter').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentFilter = this.dataset.service;
                    renderLogs();
                });
            });
            
            // Connect on page load
            connectWebSocket();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/logs")
async def submit_log(log_submission: LogSubmission):
    """Endpoint for services to submit logs"""
    try:
        add_log_entry(
            service=log_submission.service,
            level=log_submission.level,
            message=log_submission.message,
            metadata=log_submission.metadata
        )
        return JSONResponse(
            content={"status": "success", "message": "Log entry added"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error adding log entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to add log entry")

@app.get("/api/logs")
async def get_logs(service: Optional[str] = None, limit: int = 100):
    """Get recent logs, optionally filtered by service"""
    try:
        if service and service in log_storage:
            logs = list(log_storage[service])[-limit:]
        elif service is None:
            # Get logs from all services
            all_logs = []
            for service_logs in log_storage.values():
                all_logs.extend(list(service_logs))
            # Sort by timestamp
            all_logs.sort(key=lambda x: x['timestamp'])
            logs = all_logs[-limit:]
        else:
            logs = []
        
        return JSONResponse(content={"logs": logs, "count": len(logs)})
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial logs
        all_logs = []
        for service_logs in log_storage.values():
            all_logs.extend(list(service_logs))
        all_logs.sort(key=lambda x: x['timestamp'])
        
        for log_entry in all_logs[-50:]:  # Send last 50 logs
            await websocket.send_text(json.dumps(log_entry))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "logthon",
        "timestamp": get_timestamp(),
        "connected_clients": len(websocket_connections),
        "log_counts": {service: len(logs) for service, logs in log_storage.items()}
    })

if __name__ == "__main__":
    # Add initial log entry (without asyncio since we're not in an async context yet)
    entry = {
        'id': str(uuid.uuid4()),
        'timestamp': get_timestamp(),
        'service': 'logthon',
        'level': 'INFO',
        'message': 'Logthon service started',
        'metadata': {}
    }
    log_storage['logthon'].append(entry)
    logger.info("[logthon] Logthon service started")
    
    # Start the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        log_level="info",
        access_log=False
    )
