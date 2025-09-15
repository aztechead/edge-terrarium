"""
File storage management module.
Handles file system operations with rotation and cleanup.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from .models import FileInfo, FileContent, StorageInfoResponse
from .config import Config


class FileStorageManager:
    """Manages file storage operations with automatic rotation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage_path = Path(config.get_storage_path())
        self.max_files = config.get_max_files()
        self.max_file_size = config.get_max_file_size()
        self.allowed_extensions = config.get_allowed_extensions()
        
        # Ensure storage directory exists
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, prefix: Optional[str] = None, extension: str = ".txt") -> str:
        """Generate a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        if prefix:
            filename = f"{prefix}_{timestamp}{extension}"
        else:
            filename = f"file_{timestamp}{extension}"
        
        return filename
    
    def _get_file_info(self, file_path: Path) -> FileInfo:
        """Get file information from a file path."""
        stat = file_path.stat()
        
        # Read content preview (first 200 characters)
        content_preview = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(200)
                if len(content_preview) == 200:
                    content_preview += "..."
        except Exception:
            content_preview = "[Binary or unreadable content]"
        
        return FileInfo(
            filename=file_path.name,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            extension=file_path.suffix,
            content_preview=content_preview
        )
    
    def _rotate_files(self) -> None:
        """Remove oldest files if we exceed the maximum file count."""
        files = list(self.storage_path.glob("*"))
        if len(files) >= self.max_files:
            # Sort by modification time (oldest first)
            files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove oldest files until we're under the limit
            files_to_remove = files[:len(files) - self.max_files + 1]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not remove file {file_path}: {e}")
    
    def create_file(self, content: str, filename_prefix: Optional[str] = None, extension: str = ".txt") -> FileInfo:
        """Create a new file with the given content."""
        # Validate file size
        if len(content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"File content exceeds maximum size of {self.max_file_size} bytes")
        
        # Validate extension
        if extension not in self.allowed_extensions:
            raise ValueError(f"File extension '{extension}' is not allowed. Allowed: {self.allowed_extensions}")
        
        # Generate filename
        filename = self._generate_filename(filename_prefix, extension)
        file_path = self.storage_path / filename
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Rotate files if necessary
        self._rotate_files()
        
        return self._get_file_info(file_path)
    
    def get_file_content(self, filename: str) -> FileContent:
        """Get the content of a specific file."""
        file_path = self.storage_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        stat = file_path.stat()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try reading as binary and convert to base64 or show as binary
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
        
        return FileContent(
            filename=filename,
            content=content,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
        )
    
    def list_files(self) -> List[FileInfo]:
        """List all files in the storage directory."""
        files = []
        for file_path in self.storage_path.glob("*"):
            if file_path.is_file():
                files.append(self._get_file_info(file_path))
        
        # Sort by creation time (newest first)
        files.sort(key=lambda f: f.created_at, reverse=True)
        return files
    
    def delete_file(self, filename: str) -> bool:
        """Delete a specific file."""
        file_path = self.storage_path / filename
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except Exception:
            return False
    
    def clear_all_files(self) -> int:
        """Clear all files from storage."""
        files_removed = 0
        for file_path in self.storage_path.glob("*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    files_removed += 1
                except Exception:
                    pass
        
        return files_removed
    
    def get_storage_info(self) -> StorageInfoResponse:
        """Get information about the storage."""
        files = self.list_files()
        total_size = sum(f.size for f in files)
        
        oldest_file = None
        newest_file = None
        
        if files:
            # Files are already sorted by creation time (newest first)
            newest_file = files[0].filename
            oldest_file = files[-1].filename
        
        return StorageInfoResponse(
            storage_path=str(self.storage_path),
            total_files=len(files),
            max_files=self.max_files,
            total_size=total_size,
            available_space=self.max_files - len(files),
            oldest_file=oldest_file,
            newest_file=newest_file
        )
    
    def get_file_count(self) -> int:
        """Get the current number of files."""
        return len(list(self.storage_path.glob("*")))
    
    def is_storage_full(self) -> bool:
        """Check if storage is at maximum capacity."""
        return self.get_file_count() >= self.max_files
