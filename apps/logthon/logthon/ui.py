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
        
        <!-- Tab Navigation -->
        <div class="tab-navigation">
            <button class="tab-button active" onclick="switchTab('logs')">📋 Logs</button>
            <button class="tab-button" onclick="switchTab('files')">📁 File Storage</button>
        </div>
        
        <!-- Logs Tab -->
        <div id="logs-tab" class="tab-content active">
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
        </div>
        
        <!-- File Storage Tab -->
        <div id="files-tab" class="tab-content">
            <div class="controls">
                <div class="control-group">
                    <button class="refresh-btn" onclick="refreshFiles()">🔄 Refresh</button>
                    <button class="clear-btn" onclick="clearAllFiles()">🗑️ Clear All Files</button>
                </div>
                <div class="control-group">
                    <span id="file-storage-info">Loading file storage info...</span>
                </div>
            </div>
            
            <div class="file-container" id="file-container">
                <div class="file-entry">
                    <span class="timestamp">Loading files...</span>
                </div>
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
        
        /* Tab Navigation Styles */
        .tab-navigation {
            background-color: #2a2a2a;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            gap: 5px;
        }
        
        .tab-button {
            background-color: #3a3a3a;
            color: #ffffff;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            transition: background-color 0.3s;
        }
        
        .tab-button:hover {
            background-color: #4a4a4a;
        }
        
        .tab-button.active {
            background-color: #007acc;
        }
        
        /* Tab Content Styles */
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* File Storage Styles */
        .file-container {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 10px;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        
        .file-entry {
            background-color: #2a2a2a;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 10px;
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .file-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            color: #00ff00;
        }
        
        .file-name {
            color: #00ff00;
            font-weight: bold;
        }
        
        .file-size {
            color: #ffff00;
            font-size: 12px;
        }
        
        .file-meta {
            display: flex;
            gap: 15px;
            font-size: 12px;
            color: #cccccc;
        }
        
        .file-preview {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 3px;
            padding: 8px;
            margin-top: 5px;
            font-size: 11px;
            color: #aaaaaa;
            max-height: 100px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        .file-actions {
            display: flex;
            gap: 5px;
            margin-top: 5px;
        }
        
        .file-action-btn {
            background-color: #4a4a4a;
            color: #ffffff;
            border: none;
            padding: 3px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            font-family: 'Courier New', monospace;
        }
        
        .file-action-btn:hover {
            background-color: #5a5a5a;
        }
        
        .file-action-btn.delete {
            background-color: #cc0000;
        }
        
        .file-action-btn.delete:hover {
            background-color: #ff0000;
        }
        
        .refresh-btn {
            background-color: #007acc;
            color: #ffffff;
            border: none;
            padding: 8px 15px;
            border-radius: 3px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        
        .refresh-btn:hover {
            background-color: #0088dd;
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
        let files = [];
        let currentTab = 'logs';
        
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
                const containerName = log.metadata && log.metadata.container_name ? log.metadata.container_name : 
                                    (log.metadata && log.metadata.container_id ? log.metadata.container_id : 'unknown');
                return `
                    <div class="log-entry" style="border-left: 3px solid ${{color}}">
                        <span class="timestamp">${{log.timestamp}}</span>
                        <span class="service" style="color: ${{color}}">[${{containerName}}]</span>
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
        
        // Tab switching functionality
        function switchTab(tabName) {{
            currentTab = tabName;
            
            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`[onclick="switchTab('${{tabName}}')"]`).classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(`${{tabName}}-tab`).classList.add('active');
            
            // Load files if switching to files tab
            if (tabName === 'files') {{
                refreshFiles();
            }}
            
        }}
        
        // File storage functionality
        async function refreshFiles() {{
            try {{
                const response = await fetch('/files');
                const data = await response.json();
                files = data.files || [];
                renderFiles();
                updateFileStorageInfo(data);
            }} catch (error) {{
                console.error('Failed to fetch files:', error);
                document.getElementById('file-container').innerHTML = '<div class="file-entry"><span class="timestamp">Error loading files</span></div>';
            }}
        }}
        
        function renderFiles() {{
            const container = document.getElementById('file-container');
            
            if (files.length === 0) {{
                container.innerHTML = '<div class="file-entry"><span class="timestamp">No files found</span></div>';
                return;
            }}
            
            container.innerHTML = files.map(file => {{
                const sizeKB = (file.size / 1024).toFixed(2);
                const createdDate = new Date(file.created_at).toLocaleString();
                const modifiedDate = new Date(file.modified_at).toLocaleString();
                
                return `
                    <div class="file-entry">
                        <div class="file-header">
                            <span class="file-name">${{escapeHtml(file.filename)}}</span>
                            <span class="file-size">${{sizeKB}} KB</span>
                        </div>
                        <div class="file-meta">
                            <span>Created: ${{createdDate}}</span>
                            <span>Modified: ${{modifiedDate}}</span>
                            <span>Extension: ${{file.extension}}</span>
                        </div>
                        <div class="file-preview">${{escapeHtml(file.content_preview || 'No preview available')}}</div>
                        <div class="file-actions">
                            <button class="file-action-btn" onclick="viewFile('${{file.filename}}')">View</button>
                            <button class="file-action-btn delete" onclick="deleteFile('${{file.filename}}')">Delete</button>
                        </div>
                    </div>
                `;
            }}).join('');
        }}
        
        function updateFileStorageInfo(data) {{
            const infoEl = document.getElementById('file-storage-info');
            infoEl.textContent = `Storage: ${{data.storage_path}} | Files: ${{data.count}}/${{data.max_files}}`;
        }}
        
        async function viewFile(filename) {{
            try {{
                const response = await fetch(`/files/${{encodeURIComponent(filename)}}`);
                const data = await response.json();
                
                // Create a modal or new window to display the file content
                const newWindow = window.open('', '_blank', 'width=800,height=600');
                newWindow.document.write(`
                    <html>
                        <head><title>File: ${{filename}}</title></head>
                        <body style="font-family: monospace; background: #1a1a1a; color: #fff; padding: 20px;">
                            <h2>File: ${{filename}}</h2>
                            <p>Size: ${{data.size}} bytes | Created: ${{data.created_at}} | Modified: ${{data.modified_at}}</p>
                            <hr>
                            <pre style="white-space: pre-wrap; background: #2a2a2a; padding: 10px; border-radius: 5px;">${{escapeHtml(data.content)}}</pre>
                        </body>
                    </html>
                `);
            }} catch (error) {{
                console.error('Failed to view file:', error);
                alert('Failed to load file content');
            }}
        }}
        
        async function deleteFile(filename) {{
            if (!confirm(`Are you sure you want to delete ${{filename}}?`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`/files/${{encodeURIComponent(filename)}}`, {{
                    method: 'DELETE'
                }});
                
                if (response.ok) {{
                    refreshFiles();
                }} else {{
                    alert('Failed to delete file');
                }}
            }} catch (error) {{
                console.error('Failed to delete file:', error);
                alert('Failed to delete file');
            }}
        }}
        
        async function clearAllFiles() {{
            if (!confirm('Are you sure you want to delete ALL files? This action cannot be undone.')) {{
                return;
            }}
            
            try {{
                const response = await fetch('/files', {{
                    method: 'DELETE'
                }});
                
                if (response.ok) {{
                    refreshFiles();
                }} else {{
                    alert('Failed to clear files');
                }}
            }} catch (error) {{
                console.error('Failed to clear files:', error);
                alert('Failed to clear files');
            }}
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
