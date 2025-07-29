"""
File handling endpoints for testing and management
"""
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..services.file_service import file_service
from ..core.file_handler import file_handler

router = APIRouter()


@router.post("/files/validate")
async def validate_file(file: UploadFile = File(...)):
    """
    Validate an uploaded file without processing
    
    Args:
        file: Uploaded file to validate
        
    Returns:
        Validation results
    """
    try:
        file_info = await file_handler.validate_upload_file(file)
        return {
            "success": True,
            "message": "File validation successful",
            "file_info": file_info
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a single file
    
    Args:
        file: File to upload and process
        
    Returns:
        Processing results
    """
    result = await file_service.process_single_upload(file)
    return {
        "success": True,
        "message": "File uploaded and processed successfully",
        "result": result
    }


@router.post("/files/upload-batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    """
    Upload and process multiple files
    
    Args:
        files: List of files to upload and process
        
    Returns:
        Batch processing results
    """
    if len(files) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400,
            detail="Too many files in batch. Maximum 10 files allowed."
        )
    
    result = await file_service.process_multiple_uploads(files)
    return {
        "success": True,
        "message": "Batch upload completed",
        "result": result
    }


@router.get("/files/temp-status")
async def get_temp_directory_status():
    """
    Get status of temporary directory
    
    Returns:
        Directory status information
    """
    status = file_service.get_temp_directory_status()
    return {
        "success": True,
        "temp_directory_status": status
    }


@router.post("/files/cleanup")
async def manual_cleanup():
    """
    Manually trigger cleanup of old temporary files
    
    Returns:
        Cleanup results
    """
    cleaned_count = file_handler.cleanup_old_files(max_age_hours=24)
    return {
        "success": True,
        "message": f"Cleanup completed. Removed {cleaned_count} files.",
        "cleaned_files": cleaned_count
    }