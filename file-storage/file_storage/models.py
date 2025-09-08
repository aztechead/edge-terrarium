"""
Data models for the File Storage API service.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Model representing file information."""
    
    filename: str = Field(..., description="Name of the file")
    size: int = Field(..., description="Size of the file in bytes")
    created_at: str = Field(..., description="ISO format timestamp when the file was created")
    modified_at: str = Field(..., description="ISO format timestamp when the file was last modified")
    extension: str = Field(..., description="File extension")
    content_preview: Optional[str] = Field(None, description="Preview of file content (first 200 chars)")


class FileContent(BaseModel):
    """Model representing file content."""
    
    filename: str = Field(..., description="Name of the file")
    content: str = Field(..., description="Full content of the file")
    size: int = Field(..., description="Size of the file in bytes")
    created_at: str = Field(..., description="ISO format timestamp when the file was created")
    modified_at: str = Field(..., description="ISO format timestamp when the file was last modified")


class FileListResponse(BaseModel):
    """Model for file list responses."""
    
    files: List[FileInfo] = Field(..., description="List of file information")
    count: int = Field(..., description="Total number of files")
    storage_path: str = Field(..., description="Path where files are stored")
    max_files: int = Field(..., description="Maximum number of files allowed")


class FileCreateRequest(BaseModel):
    """Model for file creation requests."""
    
    content: str = Field(..., description="Content to write to the file")
    filename_prefix: Optional[str] = Field(None, description="Optional prefix for the filename")
    extension: str = Field(default=".txt", description="File extension")


class FileCreateResponse(BaseModel):
    """Model for file creation responses."""
    
    filename: str = Field(..., description="Name of the created file")
    size: int = Field(..., description="Size of the created file in bytes")
    created_at: str = Field(..., description="ISO format timestamp when the file was created")
    message: str = Field(..., description="Success message")


class FileDeleteResponse(BaseModel):
    """Model for file deletion responses."""
    
    filename: str = Field(..., description="Name of the deleted file")
    message: str = Field(..., description="Success message")


class StorageInfoResponse(BaseModel):
    """Model for storage information responses."""
    
    storage_path: str = Field(..., description="Path where files are stored")
    total_files: int = Field(..., description="Total number of files")
    max_files: int = Field(..., description="Maximum number of files allowed")
    total_size: int = Field(..., description="Total size of all files in bytes")
    available_space: int = Field(..., description="Available space for new files")
    oldest_file: Optional[str] = Field(None, description="Name of the oldest file")
    newest_file: Optional[str] = Field(None, description="Name of the newest file")


class HealthResponse(BaseModel):
    """Model for health check responses."""
    
    status: str = Field(..., description="Health status of the service")
    service: str = Field(..., description="Name of the service")
    timestamp: str = Field(..., description="ISO format timestamp of the health check")
    storage_path: str = Field(..., description="Path where files are stored")
    total_files: int = Field(..., description="Total number of files")
    max_files: int = Field(..., description="Maximum number of files allowed")


class ApiResponse(BaseModel):
    """Generic API response model."""
    
    status: str = Field(..., description="Response status (success, error)")
    message: str = Field(..., description="Response message")
    timestamp: str = Field(..., description="ISO format timestamp of the response")
