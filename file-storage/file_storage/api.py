"""
API endpoints for the File Storage service.
"""

import time
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .models import (
    FileInfo, FileContent, FileListResponse, FileCreateRequest, 
    FileCreateResponse, FileDeleteResponse, StorageInfoResponse,
    HealthResponse, ApiResponse
)
from .storage import FileStorageManager
from .logging import LoggingManager
from .config import Config


def create_file_storage_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="File Storage API",
        description="A service for managing file storage with CRUD operations",
        version="1.0.0"
    )
    
    # Initialize configuration and managers
    config = Config()
    storage_manager = FileStorageManager(config)
    logging_manager = LoggingManager(config)
    
    # Log startup
    logging_manager.info("File Storage API starting up", {
        "storage_path": config.get_storage_path(),
        "max_files": config.get_max_files(),
        "max_file_size": config.get_max_file_size()
    })
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Middleware to log all API requests."""
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        logging_manager.log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            response_time=process_time,
            metadata={
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        return response
    
    @app.get("/", response_class=JSONResponse)
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "File Storage API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        file_count = storage_manager.get_file_count()
        
        return HealthResponse(
            status="healthy",
            service="file-storage",
            timestamp=datetime.now().isoformat(),
            storage_path=config.get_storage_path(),
            total_files=file_count,
            max_files=config.get_max_files()
        )
    
    @app.get("/storage/health", response_model=HealthResponse)
    async def health_check_with_prefix():
        """Health check endpoint with /storage prefix for ingress routing."""
        file_count = storage_manager.get_file_count()
        
        return HealthResponse(
            status="healthy",
            service="file-storage",
            timestamp=datetime.now().isoformat(),
            storage_path=config.get_storage_path(),
            total_files=file_count,
            max_files=config.get_max_files()
        )
    
    @app.get("/files", response_model=FileListResponse)
    async def list_files():
        """List all files in storage."""
        try:
            files = storage_manager.list_files()
            
            logging_manager.info(f"Listed {len(files)} files", {
                "file_count": len(files),
                "storage_path": config.get_storage_path()
            })
            
            return FileListResponse(
                files=files,
                count=len(files),
                storage_path=config.get_storage_path(),
                max_files=config.get_max_files()
            )
        except Exception as e:
            logging_manager.error(f"Failed to list files: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list files")
    
    @app.get("/storage/files", response_model=FileListResponse)
    async def list_files_with_prefix():
        """List all files in storage with /storage prefix for ingress routing."""
        try:
            files = storage_manager.list_files()
            
            logging_manager.info(f"Listed {len(files)} files", {
                "file_count": len(files),
                "storage_path": config.get_storage_path()
            })
            
            return FileListResponse(
                files=files,
                count=len(files),
                storage_path=config.get_storage_path(),
                max_files=config.get_max_files()
            )
        except Exception as e:
            logging_manager.error(f"Failed to list files: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list files")
    
    @app.get("/files/{filename}", response_model=FileContent)
    async def get_file(filename: str):
        """Get the content of a specific file."""
        try:
            file_content = storage_manager.get_file_content(filename)
            
            logging_manager.log_file_operation("read", filename, True, {
                "file_size": file_content.size
            })
            
            return file_content
        except FileNotFoundError:
            logging_manager.log_file_operation("read", filename, False, {
                "error": "file_not_found"
            })
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        except Exception as e:
            logging_manager.log_file_operation("read", filename, False, {
                "error": str(e)
            })
            raise HTTPException(status_code=500, detail="Failed to read file")
    
    @app.put("/files", response_model=FileCreateResponse)
    async def create_file(request: FileCreateRequest):
        """Create a new file with the given content."""
        try:
            file_info = storage_manager.create_file(
                content=request.content,
                filename_prefix=request.filename_prefix,
                extension=request.extension
            )
            
            logging_manager.log_file_operation("create", file_info.filename, True, {
                "file_size": file_info.size,
                "extension": file_info.extension,
                "has_prefix": request.filename_prefix is not None
            })
            
            return FileCreateResponse(
                filename=file_info.filename,
                size=file_info.size,
                created_at=file_info.created_at,
                message=f"File '{file_info.filename}' created successfully"
            )
        except ValueError as e:
            logging_manager.error(f"File creation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logging_manager.error(f"File creation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create file")
    
    @app.put("/storage/files", response_model=FileCreateResponse)
    async def create_file_with_prefix(request: FileCreateRequest):
        """Create a new file with the given content (with /storage prefix for ingress routing)."""
        try:
            file_info = storage_manager.create_file(
                content=request.content,
                filename_prefix=request.filename_prefix,
                extension=request.extension
            )
            
            logging_manager.log_file_operation("create", file_info.filename, True, {
                "file_size": file_info.size,
                "extension": file_info.extension,
                "has_prefix": request.filename_prefix is not None
            })
            
            return FileCreateResponse(
                filename=file_info.filename,
                size=file_info.size,
                created_at=file_info.created_at,
                message=f"File '{file_info.filename}' created successfully"
            )
        except ValueError as e:
            logging_manager.error(f"File creation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logging_manager.error(f"File creation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create file")
    
    @app.delete("/files/{filename}", response_model=FileDeleteResponse)
    async def delete_file(filename: str):
        """Delete a specific file."""
        try:
            success = storage_manager.delete_file(filename)
            
            if success:
                logging_manager.log_file_operation("delete", filename, True)
                return FileDeleteResponse(
                    filename=filename,
                    message=f"File '{filename}' deleted successfully"
                )
            else:
                logging_manager.log_file_operation("delete", filename, False, {
                    "error": "file_not_found"
                })
                raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        except HTTPException:
            raise
        except Exception as e:
            logging_manager.log_file_operation("delete", filename, False, {
                "error": str(e)
            })
            raise HTTPException(status_code=500, detail="Failed to delete file")
    
    @app.delete("/files", response_model=ApiResponse)
    async def clear_all_files():
        """Clear all files from storage."""
        try:
            files_removed = storage_manager.clear_all_files()
            
            logging_manager.info(f"Cleared {files_removed} files from storage", {
                "files_removed": files_removed,
                "storage_path": config.get_storage_path()
            })
            
            return ApiResponse(
                status="success",
                message=f"Cleared {files_removed} files from storage",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logging_manager.error(f"Failed to clear files: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to clear files")
    
    @app.get("/storage/info", response_model=StorageInfoResponse)
    async def get_storage_info():
        """Get information about the storage."""
        try:
            storage_info = storage_manager.get_storage_info()
            
            logging_manager.info("Retrieved storage information", {
                "total_files": storage_info.total_files,
                "max_files": storage_info.max_files,
                "total_size": storage_info.total_size
            })
            
            return storage_info
        except Exception as e:
            logging_manager.error(f"Failed to get storage info: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get storage information")
    
    return app
