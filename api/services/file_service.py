"""
File processing service for OCRFlux API
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from fastapi import UploadFile, HTTPException
from fastapi import status

from ..core.file_handler import file_handler
from ..core.file_utils import (
    FileValidator, 
    get_file_type_info, 
    calculate_file_hash,
    format_file_size
)
from ..models.error import ErrorType, FileErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Service for handling file processing operations"""
    
    def __init__(self):
        self.file_handler = file_handler
        self.validator = FileValidator()
    
    async def process_single_upload(self, upload_file: UploadFile) -> Dict[str, Any]:
        """
        Process a single uploaded file
        
        Args:
            upload_file: FastAPI UploadFile object
            
        Returns:
            Dictionary with processed file information
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Validate and save file
            file_info = await self.file_handler.validate_upload_file(upload_file)
            file_path = await self.file_handler.save_upload_file(upload_file)
            
            # Get additional file information
            type_info = get_file_type_info(file_path)
            
            # Perform structure validation
            structure_valid = await self._validate_file_structure(file_path, type_info)
            
            # Get detailed file info
            detailed_info = self.file_handler.get_file_info(file_path)
            
            result = {
                **file_info,
                **type_info,
                "file_path": str(file_path),
                "structure_valid": structure_valid,
                "detailed_info": detailed_info,
                "processed_at": datetime.utcnow()
            }
            
            logger.info(f"Successfully processed file: {upload_file.filename}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing file {upload_file.filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=FileErrorResponse(
                    message="Failed to process uploaded file",
                    filename=upload_file.filename,
                    details=[
                        ErrorDetail(
                            message=str(e),
                            context={"error_type": type(e).__name__}
                        )
                    ]
                ).dict()
            )
    
    async def process_multiple_uploads(self, upload_files: List[UploadFile]) -> Dict[str, Any]:
        """
        Process multiple uploaded files
        
        Args:
            upload_files: List of FastAPI UploadFile objects
            
        Returns:
            Dictionary with batch processing results
        """
        results = []
        errors = []
        
        for i, upload_file in enumerate(upload_files):
            try:
                result = await self.process_single_upload(upload_file)
                result["batch_index"] = i
                results.append(result)
            except HTTPException as e:
                error_info = {
                    "batch_index": i,
                    "filename": upload_file.filename,
                    "error": e.detail,
                    "status_code": e.status_code
                }
                errors.append(error_info)
                logger.warning(f"Failed to process file {upload_file.filename} in batch")
        
        return {
            "total_files": len(upload_files),
            "successful_files": len(results),
            "failed_files": len(errors),
            "results": results,
            "errors": errors,
            "processed_at": datetime.utcnow()
        }
    
    async def _validate_file_structure(self, file_path: Path, type_info: Dict[str, Any]) -> bool:
        """
        Validate file structure based on file type
        
        Args:
            file_path: Path to the file
            type_info: File type information
            
        Returns:
            True if structure is valid
        """
        try:
            if type_info["is_pdf"]:
                return self.validator.validate_pdf_structure(file_path)
            elif type_info["is_image"]:
                return self.validator.validate_image_structure(file_path)
            else:
                return False
        except Exception as e:
            logger.error(f"Error validating file structure: {e}")
            return False
    
    def get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        """
        Get comprehensive file statistics
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file statistics
        """
        try:
            basic_info = self.file_handler.get_file_info(file_path)
            type_info = get_file_type_info(file_path)
            
            stats = {
                **basic_info,
                **type_info,
                "formatted_size": format_file_size(basic_info["size"]),
                "hash": calculate_file_hash(file_path)
            }
            
            # Add image-specific info if it's an image
            if type_info["is_image"]:
                image_info = self.validator.get_image_info(file_path)
                if image_info:
                    stats["image_info"] = image_info
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting file stats: {e}")
            return {"error": str(e)}
    
    def cleanup_processed_file(self, file_path: Path) -> bool:
        """
        Clean up a processed file
        
        Args:
            file_path: Path to the file to clean up
            
        Returns:
            True if cleanup was successful
        """
        return self.file_handler.cleanup_file(file_path)
    
    def get_temp_directory_status(self) -> Dict[str, Any]:
        """
        Get status of temporary directory
        
        Returns:
            Dictionary with directory status
        """
        return self.file_handler.get_temp_dir_stats()
    
    async def validate_file_for_processing(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate if a file is ready for OCR processing
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            # Get file info
            file_info = self.file_handler.get_file_info(file_path)
            type_info = get_file_type_info(file_path)
            
            # Check if file type is supported
            if not type_info["is_supported"]:
                return False, f"Unsupported file type: {type_info['extension']}"
            
            # Check file size
            if file_info["size"] == 0:
                return False, "File is empty"
            
            if file_info["size"] > self.file_handler.max_file_size:
                return False, f"File too large: {format_file_size(file_info['size'])}"
            
            # Check file structure
            structure_valid = await self._validate_file_structure(file_path, type_info)
            if not structure_valid:
                return False, "File structure is invalid or corrupted"
            
            # Check file permissions
            if not file_info["is_readable"]:
                return False, "File is not readable"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file for processing: {e}")
            return False, f"Validation error: {str(e)}"


# Global file processing service instance
file_service = FileProcessingService()