"""
File handling utilities for OCRFlux API Service
"""
import os
import shutil
import tempfile
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime
import hashlib
import logging

from fastapi import UploadFile, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE

from .config import settings
from ..models.error import ErrorType, FileErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file upload, validation, and temporary file management"""
    
    def __init__(self):
        """Initialize FileHandler with configuration from settings"""
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = [ext.lower() for ext in settings.allowed_extensions]
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # MIME type mappings for supported formats
        self.mime_type_mapping = {
            'application/pdf': ['.pdf'],
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/jpg': ['.jpg', '.jpeg']
        }
    
    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension against allowed extensions
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            True if extension is allowed, False otherwise
        """
        if not filename:
            return False
            
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.allowed_extensions
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size against maximum allowed size
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            True if size is within limits, False otherwise
        """
        return file_size <= self.max_file_size
    
    def validate_mime_type(self, file_content: bytes, filename: str) -> bool:
        """
        Validate MIME type by checking file content and extension
        
        Args:
            file_content: First few bytes of the file
            filename: Name of the file
            
        Returns:
            True if MIME type matches extension, False otherwise
        """
        # Get MIME type from content
        import magic
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
        except:
            # Fallback to extension-based detection if python-magic is not available
            mime_type, _ = mimetypes.guess_type(filename)
        
        if not mime_type:
            return False
        
        # Check if MIME type is supported
        if mime_type not in self.mime_type_mapping:
            return False
        
        # Check if extension matches MIME type
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.mime_type_mapping[mime_type]
    
    async def validate_upload_file(self, upload_file: UploadFile) -> Dict[str, Any]:
        """
        Comprehensive validation of uploaded file
        
        Args:
            upload_file: FastAPI UploadFile object
            
        Returns:
            Dictionary with validation results and file info
            
        Raises:
            HTTPException: If validation fails
        """
        if not upload_file.filename:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=FileErrorResponse(
                    message="No filename provided",
                    details=[ErrorDetail(message="Filename is required")]
                ).dict()
            )
        
        # Validate file extension
        if not self.validate_file_extension(upload_file.filename):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=FileErrorResponse(
                    message=f"File extension not allowed",
                    filename=upload_file.filename,
                    details=[
                        ErrorDetail(
                            message=f"Allowed extensions: {', '.join(self.allowed_extensions)}",
                            context={"allowed_extensions": self.allowed_extensions}
                        )
                    ]
                ).dict()
            )
        
        # Read file content for size and MIME type validation
        file_content = await upload_file.read()
        file_size = len(file_content)
        
        # Reset file pointer
        await upload_file.seek(0)
        
        # Validate file size
        if not self.validate_file_size(file_size):
            raise HTTPException(
                status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=FileErrorResponse(
                    message="File size exceeds maximum allowed size",
                    filename=upload_file.filename,
                    file_size=file_size,
                    details=[
                        ErrorDetail(
                            message=f"Maximum allowed size: {self.max_file_size} bytes",
                            context={
                                "max_size": self.max_file_size,
                                "actual_size": file_size
                            }
                        )
                    ]
                ).dict()
            )
        
        # Validate MIME type (check first 1024 bytes)
        mime_check_content = file_content[:1024]
        if not self.validate_mime_type(mime_check_content, upload_file.filename):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=FileErrorResponse(
                    message="File type does not match extension or is not supported",
                    filename=upload_file.filename,
                    details=[
                        ErrorDetail(
                            message="File content does not match the file extension",
                            context={"supported_types": list(self.mime_type_mapping.keys())}
                        )
                    ]
                ).dict()
            )
        
        # Generate file hash for deduplication
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        return {
            "filename": upload_file.filename,
            "size": file_size,
            "content_type": upload_file.content_type,
            "hash": file_hash,
            "extension": Path(upload_file.filename).suffix.lower(),
            "validated_at": datetime.utcnow()
        }
    
    async def save_upload_file(self, upload_file: UploadFile, 
                              custom_filename: Optional[str] = None) -> Path:
        """
        Save uploaded file to temporary directory
        
        Args:
            upload_file: FastAPI UploadFile object
            custom_filename: Optional custom filename to use
            
        Returns:
            Path to the saved file
            
        Raises:
            HTTPException: If file saving fails
        """
        try:
            # Validate file first
            file_info = await self.validate_upload_file(upload_file)
            
            # Generate unique filename
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                original_name = Path(upload_file.filename).stem
                extension = file_info["extension"]
                filename = f"{timestamp}_{original_name}_{file_info['hash'][:8]}{extension}"
            
            # Create full path
            file_path = self.temp_dir / filename
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            logger.info(f"File saved: {filename} ({file_info['size']} bytes)")
            return file_path
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save file {upload_file.filename}: {str(e)}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=FileErrorResponse(
                    message="Failed to save uploaded file",
                    filename=upload_file.filename,
                    details=[
                        ErrorDetail(
                            message=str(e),
                            context={"error_type": type(e).__name__}
                        )
                    ]
                ).dict()
            )
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get detailed information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        
        return {
            "path": str(file_path),
            "filename": file_path.name,
            "size": stat.st_size,
            "extension": file_path.suffix.lower(),
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "is_readable": os.access(file_path, os.R_OK)
        }
    
    def cleanup_file(self, file_path: Path) -> bool:
        """
        Remove a temporary file
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            True if file was removed successfully, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {str(e)}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
            
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        current_time = datetime.utcnow().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        if self.cleanup_file(file_path):
                            cleaned_count += 1
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files")
        
        return cleaned_count
    
    def get_temp_dir_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the temporary directory
        
        Returns:
            Dictionary with directory statistics
        """
        try:
            total_size = 0
            file_count = 0
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            # Get disk usage
            disk_usage = shutil.disk_usage(self.temp_dir)
            
            return {
                "temp_dir": str(self.temp_dir),
                "file_count": file_count,
                "total_size": total_size,
                "disk_total": disk_usage.total,
                "disk_used": disk_usage.used,
                "disk_free": disk_usage.free,
                "disk_usage_percent": (disk_usage.used / disk_usage.total) * 100
            }
        except Exception as e:
            logger.error(f"Error getting temp dir stats: {str(e)}")
            return {
                "temp_dir": str(self.temp_dir),
                "error": str(e)
            }


# Global file handler instance
file_handler = FileHandler()