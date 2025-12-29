"""
File management service for uploads and downloads.

This module handles file operations for the web interface including
uploads, downloads, and temporary file management.
"""

import shutil
from pathlib import Path
from typing import List, Optional
import tempfile


class FileManager:
    """
    Manages file operations for the web interface.
    
    This class handles file uploads, downloads, and cleanup operations
    with proper security and validation.
    """
    
    def __init__(self):
        self.upload_dir = Path(tempfile.gettempdir()) / "lesson_generator_uploads"
        self.upload_dir.mkdir(exist_ok=True)
        
        # File size limits
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {'.j2', '.json', '.txt', '.md', '.py'}
    
    async def save_uploaded_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = "custom",
    ) -> Path:
        """
        Save an uploaded file to the appropriate directory.
        
        Args:
            file_content: The file content as bytes
            filename: Original filename
            file_type: Type of file (template, config, etc.)
            
        Returns:
            Path to the saved file
        """
        
        # Validate file size
        if len(file_content) > self.max_file_size:
            raise ValueError(f"File size exceeds maximum limit ({self.max_file_size} bytes)")
        
        # Validate file extension
        file_path = Path(filename)
        if file_path.suffix not in self.allowed_extensions:
            raise ValueError(f"File extension not allowed: {file_path.suffix}")
        
        # Create type-specific directory
        type_dir = self.upload_dir / file_type
        type_dir.mkdir(exist_ok=True)
        
        # Save file with sanitized name
        safe_filename = self._sanitize_filename(filename)
        output_path = type_dir / safe_filename
        
        with open(output_path, 'wb') as f:
            f.write(file_content)
        
        return output_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other issues.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        
        # Remove path components and keep only the filename
        safe_name = Path(filename).name
        
        # Replace potentially dangerous characters
        safe_chars = []
        for char in safe_name:
            if char.isalnum() or char in '.-_':
                safe_chars.append(char)
            else:
                safe_chars.append('_')
        
        return ''.join(safe_chars)
    
    async def list_files(
        self,
        file_type: Optional[str] = None,
        extension: Optional[str] = None,
    ) -> List[dict]:
        """
        List files in the upload directory.
        
        Args:
            file_type: Filter by file type directory
            extension: Filter by file extension
            
        Returns:
            List of file information dictionaries
        """
        
        files = []
        
        if file_type:
            search_dir = self.upload_dir / file_type
            if not search_dir.exists():
                return files
            search_dirs = [search_dir]
        else:
            search_dirs = [d for d in self.upload_dir.iterdir() if d.is_dir()]
        
        for directory in search_dirs:
            for file_path in directory.iterdir():
                if not file_path.is_file():
                    continue
                
                if extension and file_path.suffix != extension:
                    continue
                
                file_info = {
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "type": directory.name,
                    "extension": file_path.suffix,
                    "created_at": file_path.stat().st_ctime,
                }
                files.append(file_info)
        
        return files
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file by path.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        
        try:
            path = Path(file_path)
            
            # Security check: ensure file is within upload directory
            if not str(path.resolve()).startswith(str(self.upload_dir.resolve())):
                raise ValueError("File path outside of allowed directory")
            
            if path.exists() and path.is_file():
                path.unlink()
                return True
            
        except Exception:
            pass
        
        return False
    
    async def cleanup_old_files(self, max_age_days: int = 7):
        """
        Clean up files older than the specified number of days.
        
        Args:
            max_age_days: Maximum age in days before files are deleted
        """
        
        import time
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        for file_path in self.upload_dir.rglob('*'):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                except Exception:
                    pass  # Ignore errors during cleanup


# Singleton instance for dependency injection
_file_manager_instance = None


def get_file_manager() -> FileManager:
    """Get the singleton FileManager instance."""
    global _file_manager_instance
    
    if _file_manager_instance is None:
        _file_manager_instance = FileManager()
    
    return _file_manager_instance