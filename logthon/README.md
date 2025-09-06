# Logthon - Log Aggregation Service

Logthon is a Python-based log aggregation service for the Edge Terrarium project. It collects logs from CDP client and service-sink containers and provides a real-time web UI for viewing them with color-coded output.

## Features

- **Real-time Log Collection**: Receives logs via HTTP POST from other services
- **Web UI**: Beautiful, responsive web interface for log viewing
- **Color-coded Logs**: Different colors for different services
- **WebSocket Support**: Real-time log streaming to connected clients
- **Service Filtering**: Filter logs by service type
- **Log Persistence**: Maintains recent logs in memory (configurable limit)

## API Endpoints

- `GET /` - Web UI for log viewing
- `POST /api/logs` - Submit logs from services
- `GET /api/logs` - Retrieve recent logs (with optional service filtering)
- `GET /health` - Health check endpoint
- `WebSocket /ws` - Real-time log streaming

## Usage

### Starting the Service

```bash
# Using Python directly
python main.py

# Using Docker
docker build -t edge-terrarium-logthon .
docker run -p 5000:5000 edge-terrarium-logthon
```

### Submitting Logs

```bash
curl -X POST http://localhost:5000/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "service": "cdp-client",
    "level": "INFO",
    "message": "Processing request from client",
    "metadata": {"request_id": "12345"}
  }'
```

### Viewing Logs

Open your browser to `http://localhost:5000` to view the real-time log interface.

## Service Colors

- **CDP Client**: Green (#00ff00)
- **Service Sink**: Blue (#0080ff)
- **Logthon**: Orange (#ff8000)

## Configuration

The service can be configured through environment variables:

- `LOGTHON_HOST`: Host to bind to (default: 0.0.0.0)
- `LOGTHON_PORT`: Port to listen on (default: 5000)
- `LOGTHON_LOG_LEVEL`: Logging level (default: INFO)
- `LOGTHON_MAX_LOGS`: Maximum logs to keep per service (default: 1000)
