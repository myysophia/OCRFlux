"""
File utility functions for OCRFlux API Service
"""
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def temporary_file(suffix: str = "", prefix: str = "ocrflux_", dir: Optional[Path] = None):
    """
    Context manager for creating temporary files
    
    Args:
        suffix: File suffix/extension
        prefix: File prefix
        dir: Directory to create file in
        
    Yields:
        Path to temporary file
    """
    temp_file = None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)  # Close file descriptor, we only need the path
        temp_file = Path(temp_path)
        yield temp_file
    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")


@contextmanager
def temporary_directory(prefix: str = "ocrflux_", dir: Optional[Path] = None):
    """
    Context manager for creating temporary directories
    
    Args:
        prefix: Directory prefix
        dir: Parent directory
        
    Yields:
        Path to temporary directory
    """
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=dir))
        yield temp_dir
    finally:
        if temp_dir and temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension (lowercase, with dot)
    """
    return Path(filename).suffix.lower()


def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF based on extension"""
    return get_file_extension(filename) == '.pdf'


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension"""
    image_extensions = {'.png', '.jpg', '.jpeg'}
    return get_file_extension(filename) in image_extensions


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename by removing/replacing problematic characters
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename
        
    Returns:
        Safe filename
    """
    import re
    
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    safe_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', safe_name)
    
    # Limit length
    if len(safe_name) > max_length:
        name_part = Path(safe_name).stem
        ext_part = Path(safe_name).suffix
        max_name_length = max_length - len(ext_part)
        safe_name = name_part[:max_name_length] + ext_part
    
    return safe_name


def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hex digest of the file hash
    """
    import hashlib
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def get_file_type_info(file_path: Path) -> Dict[str, Any]:
    """
    Get detailed file type information
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file type information
    """
    import mimetypes
    
    info = {
        "extension": file_path.suffix.lower(),
        "mime_type": None,
        "is_pdf": False,
        "is_image": False,
        "is_supported": False
    }
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    info["mime_type"] = mime_type
    
    # Check file type
    extension = info["extension"]
    info["is_pdf"] = extension == '.pdf'
    info["is_image"] = extension in {'.png', '.jpg', '.jpeg'}
    info["is_supported"] = info["is_pdf"] or info["is_image"]
    
    return info


class FileValidator:
    """Additional file validation utilities"""
    
    @staticmethod
    def validate_pdf_structure(file_path: Path) -> bool:
        """
        Basic PDF structure validation
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if PDF structure appears valid
        """
        try:
            with open(file_path, 'rb') as f:
                # Check PDF header
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    return False
                
                # Check for EOF marker (simplified check)
                f.seek(-1024, 2)  # Go to near end of file
                tail = f.read()
                return b'%%EOF' in tail
                
        except Exception as e:
            logger.error(f"Error validating PDF structure: {e}")
            return False
    
    @staticmethod
    def validate_image_structure(file_path: Path) -> bool:
        """
        Basic image structure validation
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if image structure appears valid
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                img.verify()  # Verify image integrity
                return True
        except Exception as e:
            logger.error(f"Error validating image structure: {e}")
            return False
    
    @staticmethod
    def get_image_info(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get image information
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary with image information or None if invalid
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None