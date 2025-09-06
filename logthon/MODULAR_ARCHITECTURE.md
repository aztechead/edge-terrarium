# Logthon Modular Architecture

This document describes the modular architecture of the Logthon application, which has been refactored to follow DRY (Don't Repeat Yourself) and SOLID principles.

## Directory Structure

```
logthon/
├── logthon/                 # Main package directory
│   ├── __init__.py         # Package initialization
│   ├── models.py           # Pydantic data models
│   ├── config.py           # Configuration management
│   ├── storage.py          # Log storage management
│   ├── websocket_manager.py # WebSocket connection management
│   ├── ui.py               # HTML templates and UI components
│   ├── api.py              # FastAPI routes and endpoints
│   └── app.py              # Application factory and initialization
├── main.py                 # Application entry point
├── test_modular.py         # Test script demonstrating modularity
├── pyproject.toml          # Project configuration and dependencies
└── .venv/                  # Virtual environment (created by uv)
```

## Module Responsibilities

### 1. `models.py` - Data Models
**Single Responsibility**: Defines all Pydantic models for data validation and serialization.

- `LogEntry`: Complete log entry with metadata
- `LogSubmission`: Incoming log submission from services
- `HealthResponse`: Health check response format
- `LogsResponse`: Log retrieval response format
- `ApiResponse`: Generic API response format

### 2. `config.py` - Configuration Management
**Single Responsibility**: Centralizes all configuration settings and environment variable handling.

- `ServiceConfig`: Individual service configuration
- `WebSocketConfig`: WebSocket connection settings
- `ServerConfig`: FastAPI server settings
- `Config`: Main configuration class with environment variable support

### 3. `storage.py` - Log Storage Management
**Single Responsibility**: Handles log storage, retrieval, and management operations.

- `LogStorage`: Thread-safe log storage with deque-based circular buffers
- Auto-creation of storage for unknown services
- Configurable maximum log counts per service
- Efficient log retrieval with filtering and limiting

### 4. `websocket_manager.py` - WebSocket Management
**Single Responsibility**: Manages WebSocket connections and real-time broadcasting.

- `WebSocketManager`: Connection tracking and broadcasting
- Connection limit enforcement
- Graceful handling of disconnected clients
- Real-time log entry broadcasting

### 5. `ui.py` - User Interface
**Single Responsibility**: Generates HTML templates and UI components.

- Dynamic HTML generation with service-specific styling
- JavaScript for real-time log viewing
- Responsive design with service filtering
- Color-coded log entries by service

### 6. `api.py` - API Endpoints
**Single Responsibility**: Defines all FastAPI routes and endpoint logic.

- RESTful API endpoints for log submission and retrieval
- WebSocket endpoint for real-time streaming
- Health check and monitoring endpoints
- Error handling and HTTP status codes

### 7. `app.py` - Application Factory
**Single Responsibility**: Creates and initializes the FastAPI application.

- Application factory pattern
- Initialization of all components
- Startup logging and configuration
- Clean separation of concerns

## SOLID Principles Implementation

### Single Responsibility Principle (SRP)
Each module has one clear, well-defined responsibility:
- Models handle data validation
- Config handles configuration
- Storage handles data persistence
- WebSocket manager handles real-time communication
- UI handles presentation
- API handles HTTP endpoints
- App handles application initialization

### Open/Closed Principle (OCP)
The architecture is open for extension but closed for modification:
- New services can be added via configuration
- New log levels can be added without changing core logic
- New API endpoints can be added without modifying existing ones
- UI can be extended with new features

### Liskov Substitution Principle (LSP)
Modules can be replaced with compatible implementations:
- Storage can be replaced with database-backed storage
- WebSocket manager can be replaced with different real-time solutions
- UI can be replaced with different template engines

### Interface Segregation Principle (ISP)
Clean, focused interfaces for each module:
- Models have specific, focused interfaces
- Storage has clear read/write operations
- WebSocket manager has connection management operations
- Config has specific getter methods

### Dependency Inversion Principle (DIP)
High-level modules don't depend on low-level details:
- App depends on abstractions (interfaces)
- API uses dependency injection
- Configuration is injected rather than hardcoded
- Storage and WebSocket manager are injected as dependencies

## DRY Principle Implementation

### Configuration Reuse
- Service colors and settings defined once in config
- Environment variables handled centrally
- Default values defined in one place

### Code Reuse
- Common logging patterns centralized
- Error handling patterns reused
- HTML generation uses reusable functions
- JavaScript code is modular and reusable

### Data Model Reuse
- Pydantic models used consistently across modules
- Validation logic centralized in models
- Serialization handled uniformly

## Benefits of Modular Architecture

1. **Maintainability**: Each module can be modified independently
2. **Testability**: Individual modules can be unit tested in isolation
3. **Scalability**: New features can be added without affecting existing code
4. **Reusability**: Modules can be reused in other projects
5. **Debugging**: Issues can be isolated to specific modules
6. **Team Development**: Different developers can work on different modules
7. **Configuration**: Easy to modify behavior through configuration
8. **Documentation**: Each module is self-documenting with clear responsibilities

## Usage Examples

### Running the Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the application
python main.py

# Or run with specific configuration
LOGTHON_PORT=8080 python main.py
```

### Testing Modularity
```bash
# Run the modular test
python test_modular.py
```

### Adding New Services
```python
# In config.py, add new service configuration
'service-name': ServiceConfig(
    name='service-name',
    color='#ff0000',
    max_logs=2000
)
```

### Extending Storage
```python
# Create custom storage implementation
class DatabaseStorage(LogStorage):
    def add_log_entry(self, log_submission):
        # Custom database implementation
        pass
```

This modular architecture makes the Logthon application more maintainable, testable, and extensible while following industry best practices for software design.
