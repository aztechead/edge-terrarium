"""
UI templates and static content for the Logthon service.

This module handles the HTML templates and UI-related functionality,
following the Single Responsibility Principle by separating UI concerns
from the rest of the application logic.
"""

from .config import config


def get_log_ui_html() -> str:
    """
    Generate the HTML content for the log viewing UI.
    
    Returns:
        str: Complete HTML content for the log viewer
    """
    service_colors = {service: config.get_service_color(service) for service in config.get_all_service_names()}
    service_colors_json = str(service_colors).replace("'", '"')
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Logthon - Edge Terrarium Logs</title>
        <style>
            {_get_css_styles()}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🐍 Logthon - Edge Terrarium Log Aggregator</h1>
            <p>Real-time log viewing for Custom Client, Service Sink, and Logthon services</p>
        </div>
        
        <div class="status" id="status">
            <span id="status-text">Connecting...</span>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label>Filter Services:</label>
                <button class="service-filter active" data-service="all">All</button>
                {_generate_service_filter_buttons()}
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
            {_get_javascript_code(service_colors_json)}
        </script>
    </body>
    </html>
    """


def _get_css_styles() -> str:
    """Get the CSS styles for the log viewer."""
    return """
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
        
        .container-id {
            color: #888;
            font-size: 10px;
            margin: 0 5px;
            font-style: italic;
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
    """


def _generate_service_filter_buttons() -> str:
    """Generate HTML for service filter buttons."""
    buttons = []
    for service_name in config.get_all_service_names():
        display_name = service_name.replace('-', ' ').title()
        buttons.append(f'<button class="service-filter" data-service="{service_name}">{display_name}</button>')
    return ''.join(buttons)


def _get_javascript_code(service_colors_json: str) -> str:
    """Get the JavaScript code for the log viewer."""
    return f"""
        let websocket = null;
        let currentFilter = 'all';
        let logs = [];
        
        const serviceColors = {service_colors_json};
        
        function connectWebSocket() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${{protocol}}//${{window.location.host}}/ws`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function(event) {{
                updateStatus('Connected', true);
            }};
            
            websocket.onmessage = function(event) {{
                const logEntry = JSON.parse(event.data);
                addLogEntry(logEntry);
            }};
            
            websocket.onclose = function(event) {{
                updateStatus('Disconnected', false);
                setTimeout(connectWebSocket, {config.websocket.reconnect_delay});
            }};
            
            websocket.onerror = function(error) {{
                updateStatus('Error', false);
            }};
        }}
        
        function updateStatus(text, connected) {{
            const statusEl = document.getElementById('status');
            const statusTextEl = document.getElementById('status-text');
            
            statusTextEl.textContent = text;
            statusEl.className = `status ${{connected ? 'connected' : 'disconnected'}}`;
        }}
        
        function addLogEntry(entry) {{
            logs.push(entry);
            if (logs.length > 1000) {{
                logs.shift();
            }}
            renderLogs();
        }}
        
        function renderLogs() {{
            const container = document.getElementById('log-container');
            const filteredLogs = currentFilter === 'all' 
                ? logs 
                : logs.filter(log => log.service === currentFilter);
            
            container.innerHTML = filteredLogs.map(log => {{
                const color = serviceColors[log.service] || '#ffffff';
                const containerId = log.metadata && log.metadata.container_id ? log.metadata.container_id : 'unknown';
                return `
                    <div class="log-entry" style="border-left: 3px solid ${{color}}">
                        <span class="timestamp">${{log.timestamp}}</span>
                        <span class="service" style="color: ${{color}}">[${{containerId}}]</span>
                        <span class="level ${{log.level}}">${{log.level}}</span>
                        <span class="message">${{escapeHtml(log.message)}}</span>
                    </div>
                `;
            }}).join('');
            
            container.scrollTop = container.scrollHeight;
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function clearLogs() {{
            logs = [];
            renderLogs();
        }}
        
        // Service filter event listeners
        document.querySelectorAll('.service-filter').forEach(button => {{
            button.addEventListener('click', function() {{
                document.querySelectorAll('.service-filter').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentFilter = this.dataset.service;
                renderLogs();
            }});
        }});
        
        // Connect on page load
        connectWebSocket();
    """
