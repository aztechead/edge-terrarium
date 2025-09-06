"""
Pydantic models for the Logthon service.

This module defines the data models used throughout the application,
following the Single Responsibility Principle by separating data validation
and serialization concerns.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Model representing a log entry with all its metadata."""
    
    id: str = Field(..., description="Unique identifier for the log entry")
    timestamp: str = Field(..., description="ISO format timestamp when the log was created")
    service: str = Field(..., description="Name of the service that generated the log")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, DEBUG)")
    message: str = Field(..., description="The actual log message")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata for the log entry")


class LogSubmission(BaseModel):
    """Model for incoming log submissions from services."""
    
    service: str = Field(..., description="Name of the service submitting the log")
    level: str = Field(default="INFO", description="Log level (INFO, WARNING, ERROR, DEBUG)")
    message: str = Field(..., description="The log message to be stored")
    metadata: Optional[Dict] = Field(default=None, description="Optional metadata for the log entry")


class HealthResponse(BaseModel):
    """Model for health check responses."""
    
    status: str = Field(..., description="Health status of the service")
    service: str = Field(..., description="Name of the service")
    timestamp: str = Field(..., description="ISO format timestamp of the health check")
    connected_clients: int = Field(..., description="Number of connected WebSocket clients")
    log_counts: Dict[str, int] = Field(..., description="Count of logs per service")


class LogsResponse(BaseModel):
    """Model for log retrieval responses."""
    
    logs: list[LogEntry] = Field(..., description="List of log entries")
    count: int = Field(..., description="Total number of logs returned")


class ApiResponse(BaseModel):
    """Generic API response model."""
    
    status: str = Field(..., description="Response status (success, error)")
    message: str = Field(..., description="Response message")
