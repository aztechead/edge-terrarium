# File Storage API Service

A FastAPI-based service for managing file storage with CRUD operations, designed for the Edge Terrarium project.

## Features

- **CRUD Operations**: Create, read, update, and delete files
- **Automatic Rotation**: Maintains a maximum of 15 files with automatic cleanup
- **Timestamped Files**: Files are automatically named with timestamps
- **Centralized Logging**: Integrates with logthon for centralized log management
- **Health Checks**: Built-in health monitoring endpoints
- **RESTful API**: Clean REST API design following FastAPI best practices

## API Endpoints

### Core Operations
- `GET /` - Service information
- `GET /health` - Health check
- `GET /files` - List all files
- `GET /files/{filename}` - Get specific file content
- `PUT /files` - Create new file
- `DELETE /files/{filename}` - Delete specific file
- `DELETE /files` - Clear all files

### File Creation
```json
PUT /files
{
  "content": "Your file content here",
  "filename_prefix": "optional_prefix",
  "extension": ".txt"
}
```

## Configuration

The service can be configured using environment variables:

- `FILE_STORAGE_PATH` - Storage directory path (default: `/app/storage`)
- `FILE_STORAGE_MAX_FILES` - Maximum number of files (default: `15`)
- `FILE_STORAGE_MAX_SIZE` - Maximum file size in bytes (default: `1048576`)
- `FILE_STORAGE_HOST` - Server host (default: `0.0.0.0`)
- `FILE_STORAGE_PORT` - Server port (default: `9000`)
- `LOGTHON_HOST` - Logthon service hostname
- `LOGTHON_PORT` - Logthon service port (default: `5000`)

## Development

### Local Development
```bash
# Install dependencies
pip install -e .

# Run the service
python main.py
```

### Docker
```bash
# Build image
docker build -t edge-terrarium-file-storage:latest .

# Run container
docker run -p 9000:9000 edge-terrarium-file-storage:latest
```

## Architecture

The service follows a modular architecture:

- `main.py` - Application entry point
- `file_storage/app.py` - Application factory
- `file_storage/api.py` - API endpoints
- `file_storage/models.py` - Pydantic data models
- `file_storage/storage.py` - File storage management
- `file_storage/logging.py` - Logging integration
- `file_storage/config.py` - Configuration management

## Integration

This service integrates with:
- **Kong Gateway**: Routes external traffic via `/storage/*` paths
- **Logthon**: Sends logs for centralized monitoring
- **Custom Client**: Receives file creation requests every 15 seconds
- **K3s/Docker**: Deployed as containerized service
