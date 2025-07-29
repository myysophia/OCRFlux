"""
OCR processing endpoints
"""
import logging
import time
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.process import ProcessOptions, ProcessResult, TaskSubmissionResponse, BatchProcessResult
from ..models.error import ErrorResponse
from ..core.file_handler import file_handler
from ..core.ocr_engine import ocr_engine, ProcessOptions as EngineProcessOptions
from ..core.task_queue import task_queue
from ..core.model_manager import model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["OCR Processing"])


@router.post(
    "/parse",
    response_model=ProcessResult,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity - file format not supported"},
        503: {"model": ErrorResponse, "description": "Service unavailable - model not loaded"},
    },
    summary="Process single file",
    description="Upload and process a single PDF or image file to extract text in Markdown format"
)
async def parse_single_file(
    file: UploadFile = File(..., description="PDF or image file to process"),
    skip_cross_page_merge: bool = Form(
        default=False,
        description="Skip cross-page merging of text elements"
    ),
    max_page_retries: int = Form(
        default=1,
        ge=0,
        le=10,
        description="Maximum retries for failed pages"
    ),
    target_longest_image_dim: int = Form(
        default=1024,
        ge=512,
        le=4096,
        description="Target longest dimension for image processing"
    ),
    image_rotation: int = Form(
        default=0,
        description="Image rotation angle (0, 90, 180, 270)"
    )
):
    """
    Process a single PDF or image file and extract text content in Markdown format.
    
    This endpoint accepts PDF files (.pdf) and image files (.png, .jpg, .jpeg) and
    returns the extracted text content formatted as Markdown.
    
    **Processing Options:**
    - `skip_cross_page_merge`: When true, disables merging of text elements across pages
    - `max_page_retries`: Number of retry attempts for pages that fail initial processing
    - `target_longest_image_dim`: Target size for image processing (affects quality vs speed)
    - `image_rotation`: Rotate image before processing (useful for scanned documents)
    
    **Returns:**
    - Complete document text in Markdown format
    - Individual page texts
    - Processing statistics and metadata
    - List of any pages that failed processing
    """
    try:
        # Validate file
        logger.info(f"Starting single file processing: {file.filename}")
        
        # Check if model is ready
        if not model_manager.is_model_ready():
            logger.error("Model not ready for processing")
            raise HTTPException(
                status_code=503,
                detail="OCR model is not loaded. Please try again later."
            )
        
        # Validate uploaded file
        try:
            file_info = await file_handler.validate_upload_file(file)
            logger.info(f"File validation successful: {file_info}")
        except ValueError as e:
            logger.warning(f"File validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise HTTPException(status_code=422, detail=f"File validation failed: {str(e)}")
        
        # Save file temporarily
        try:
            temp_file_path = await file_handler.save_temp_file(file)
            logger.info(f"File saved temporarily: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
        
        try:
            # Create processing options
            options = EngineProcessOptions(
                skip_cross_page_merge=skip_cross_page_merge,
                max_page_retries=max_page_retries,
                target_longest_image_dim=target_longest_image_dim,
                image_rotation=image_rotation
            )
            
            # Process the file
            result = await ocr_engine.process_single_file(temp_file_path, options)
            
            # Convert to API response format
            api_result = ProcessResult(
                success=result.success,
                file_name=result.file_name,
                file_size=file_info.get("size"),
                num_pages=result.num_pages,
                document_text=result.document_text,
                page_texts=result.page_texts,
                fallback_pages=result.fallback_pages,
                processing_time=result.processing_time,
                error_message=result.error_message
            )
            
            logger.info(
                f"Processing completed: {file.filename}, "
                f"success={result.success}, time={result.processing_time:.2f}s"
            )
            
            return api_result
            
        finally:
            # Clean up temporary file
            try:
                await file_handler.cleanup_temp_file(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file: {e}")
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in single file processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during processing"
        )


@router.post(
    "/parse-async",
    response_model=TaskSubmissionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity - file format not supported"},
        503: {"model": ErrorResponse, "description": "Service unavailable - task queue full"},
    },
    summary="Process single file asynchronously",
    description="Submit a single file for asynchronous processing and receive a task ID for status tracking"
)
async def parse_single_file_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or image file to process"),
    skip_cross_page_merge: bool = Form(
        default=False,
        description="Skip cross-page merging of text elements"
    ),
    max_page_retries: int = Form(
        default=1,
        ge=0,
        le=10,
        description="Maximum retries for failed pages"
    ),
    target_longest_image_dim: int = Form(
        default=1024,
        ge=512,
        le=4096,
        description="Target longest dimension for image processing"
    ),
    image_rotation: int = Form(
        default=0,
        description="Image rotation angle (0, 90, 180, 270)"
    )
):
    """
    Submit a single file for asynchronous OCR processing.
    
    This endpoint is useful for large files or when you don't want to wait for processing
    to complete. It returns a task ID that can be used to check processing status and
    retrieve results when complete.
    
    **Workflow:**
    1. Submit file with this endpoint → receive task_id
    2. Poll `/tasks/{task_id}` to check status
    3. When status is 'completed', get results from `/tasks/{task_id}/result`
    
    **Returns:**
    - Task ID for status tracking
    - URLs for status checking and result retrieval
    - Estimated completion time
    """
    try:
        logger.info(f"Starting async single file processing: {file.filename}")
        
        # Validate file first
        try:
            file_info = await file_handler.validate_upload_file(file)
            logger.info(f"File validation successful for async processing: {file_info}")
        except ValueError as e:
            logger.warning(f"File validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise HTTPException(status_code=422, detail=f"File validation failed: {str(e)}")
        
        # Save file temporarily
        try:
            temp_file_path = await file_handler.save_temp_file(file)
            logger.info(f"File saved for async processing: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
        
        # Create task payload
        task_payload = {
            "file_path": temp_file_path,
            "file_name": file.filename,
            "file_size": file_info.get("size"),
            "options": {
                "skip_cross_page_merge": skip_cross_page_merge,
                "max_page_retries": max_page_retries,
                "target_longest_image_dim": target_longest_image_dim,
                "image_rotation": image_rotation
            }
        }
        
        # Submit task to queue
        try:
            task_id = await task_queue.submit_task("ocr_single_file", task_payload)
            logger.info(f"Task submitted for async processing: {task_id}")
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            # Clean up temp file if task submission failed
            try:
                await file_handler.cleanup_temp_file(temp_file_path)
            except:
                pass
            raise HTTPException(status_code=503, detail="Task queue is currently unavailable")
        
        # Estimate completion time
        estimated_time = await ocr_engine.estimate_processing_time(temp_file_path)
        
        # Create response
        response = TaskSubmissionResponse(
            task_id=task_id,
            status="pending",
            estimated_completion_time=None,  # Will be set by task queue
            status_url=f"/api/v1/tasks/{task_id}",
            result_url=f"/api/v1/tasks/{task_id}/result"
        )
        
        logger.info(f"Async task created: {task_id} for file: {file.filename}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in async file processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during task submission"
        )


# Register OCR task handler with the task queue
async def ocr_single_file_handler(payload: dict) -> dict:
    """
    Task handler for single file OCR processing.
    
    Args:
        payload: Task payload containing file path and options
        
    Returns:
        Processing result dictionary
    """
    try:
        file_path = payload["file_path"]
        file_name = payload["file_name"]
        file_size = payload.get("file_size")
        options_dict = payload["options"]
        
        # Create processing options
        options = EngineProcessOptions(
            skip_cross_page_merge=options_dict["skip_cross_page_merge"],
            max_page_retries=options_dict["max_page_retries"],
            target_longest_image_dim=options_dict["target_longest_image_dim"],
            image_rotation=options_dict["image_rotation"]
        )
        
        # Process the file
        result = await ocr_engine.process_single_file(file_path, options)
        
        # Convert to dictionary for task result
        result_dict = {
            "success": result.success,
            "file_name": result.file_name,
            "file_size": file_size,
            "num_pages": result.num_pages,
            "document_text": result.document_text,
            "page_texts": result.page_texts,
            "fallback_pages": result.fallback_pages,
            "processing_time": result.processing_time,
            "error_message": result.error_message
        }
        
        return result_dict
        
    finally:
        # Clean up temporary file
        try:
            if "file_path" in payload:
                await file_handler.cleanup_temp_file(payload["file_path"])
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file in task handler: {e}")


@router.post(
    "/batch",
    response_model=BatchProcessResult,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid files or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many files"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity - file format not supported"},
        503: {"model": ErrorResponse, "description": "Service unavailable - model not loaded"},
    },
    summary="Process multiple files",
    description="Upload and process multiple PDF or image files to extract text in Markdown format"
)
async def parse_batch_files(
    files: List[UploadFile] = File(..., description="List of PDF or image files to process"),
    skip_cross_page_merge: bool = Form(
        default=False,
        description="Skip cross-page merging of text elements"
    ),
    max_page_retries: int = Form(
        default=1,
        ge=0,
        le=10,
        description="Maximum retries for failed pages"
    ),
    target_longest_image_dim: int = Form(
        default=1024,
        ge=512,
        le=4096,
        description="Target longest dimension for image processing"
    ),
    image_rotation: int = Form(
        default=0,
        description="Image rotation angle (0, 90, 180, 270)"
    )
):
    """
    Process multiple PDF or image files and extract text content in Markdown format.
    
    This endpoint accepts multiple files and processes them in batch, returning individual
    results for each file. If some files fail processing, the endpoint will still return
    results for successful files along with error information for failed files.
    
    **File Limits:**
    - Maximum 10 files per batch request
    - Each file must meet individual size and format requirements
    
    **Processing Behavior:**
    - Files are processed sequentially to manage resource usage
    - Partial failures are handled gracefully
    - Processing continues even if some files fail
    
    **Returns:**
    - Individual processing results for each file
    - Summary statistics (total, successful, failed counts)
    - Total processing time for the entire batch
    """
    try:
        logger.info(f"Starting batch processing for {len(files)} files")
        
        # Check batch size limit
        MAX_BATCH_SIZE = 10
        if len(files) > MAX_BATCH_SIZE:
            logger.warning(f"Batch size too large: {len(files)} > {MAX_BATCH_SIZE}")
            raise HTTPException(
                status_code=400,
                detail=f"Too many files in batch. Maximum {MAX_BATCH_SIZE} files allowed."
            )
        
        # Check if model is ready
        if not model_manager.is_model_ready():
            logger.error("Model not ready for batch processing")
            raise HTTPException(
                status_code=503,
                detail="OCR model is not loaded. Please try again later."
            )
        
        batch_start_time = time.time()
        results = []
        temp_file_paths = []
        
        try:
            # Process each file
            for i, file in enumerate(files):
                logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}")
                
                try:
                    # Validate file
                    file_info = await file_handler.validate_upload_file(file)
                    logger.debug(f"File validation successful: {file.filename}")
                    
                    # Save file temporarily
                    temp_file_path = await file_handler.save_temp_file(file)
                    temp_file_paths.append(temp_file_path)
                    
                    # Create processing options
                    options = EngineProcessOptions(
                        skip_cross_page_merge=skip_cross_page_merge,
                        max_page_retries=max_page_retries,
                        target_longest_image_dim=target_longest_image_dim,
                        image_rotation=image_rotation
                    )
                    
                    # Process the file
                    result = await ocr_engine.process_single_file(temp_file_path, options)
                    
                    # Convert to API response format
                    api_result = ProcessResult(
                        success=result.success,
                        file_name=result.file_name,
                        file_size=file_info.get("size"),
                        num_pages=result.num_pages,
                        document_text=result.document_text,
                        page_texts=result.page_texts,
                        fallback_pages=result.fallback_pages,
                        processing_time=result.processing_time,
                        error_message=result.error_message
                    )
                    
                    results.append(api_result)
                    
                    logger.info(
                        f"File {i+1} processed: {file.filename}, "
                        f"success={result.success}, time={result.processing_time:.2f}s"
                    )
                
                except ValueError as e:
                    # File validation error
                    logger.warning(f"File validation failed for {file.filename}: {e}")
                    error_result = ProcessResult(
                        success=False,
                        file_name=file.filename,
                        file_size=0,
                        num_pages=0,
                        document_text="",
                        page_texts={},
                        fallback_pages=[],
                        processing_time=0.0,
                        error_message=f"File validation failed: {str(e)}"
                    )
                    results.append(error_result)
                
                except Exception as e:
                    # Processing error
                    logger.error(f"Processing failed for {file.filename}: {e}")
                    error_result = ProcessResult(
                        success=False,
                        file_name=file.filename,
                        file_size=0,
                        num_pages=0,
                        document_text="",
                        page_texts={},
                        fallback_pages=[],
                        processing_time=0.0,
                        error_message=f"Processing failed: {str(e)}"
                    )
                    results.append(error_result)
            
            # Calculate batch statistics
            total_processing_time = time.time() - batch_start_time
            successful_files = sum(1 for r in results if r.success)
            failed_files = len(results) - successful_files
            
            # Create batch response
            batch_result = BatchProcessResult(
                total_files=len(files),
                successful_files=successful_files,
                failed_files=failed_files,
                results=results,
                total_processing_time=total_processing_time
            )
            
            logger.info(
                f"Batch processing completed: {successful_files}/{len(files)} successful, "
                f"total time: {total_processing_time:.2f}s"
            )
            
            return batch_result
            
        finally:
            # Clean up all temporary files
            for temp_file_path in temp_file_paths:
                try:
                    await file_handler.cleanup_temp_file(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file: {e}")
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during batch processing"
        )


@router.post(
    "/batch-async",
    response_model=TaskSubmissionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid files or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many files"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity - file format not supported"},
        503: {"model": ErrorResponse, "description": "Service unavailable - task queue full"},
    },
    summary="Process multiple files asynchronously",
    description="Submit multiple files for asynchronous processing and receive a task ID for status tracking"
)
async def parse_batch_files_async(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="List of PDF or image files to process"),
    skip_cross_page_merge: bool = Form(
        default=False,
        description="Skip cross-page merging of text elements"
    ),
    max_page_retries: int = Form(
        default=1,
        ge=0,
        le=10,
        description="Maximum retries for failed pages"
    ),
    target_longest_image_dim: int = Form(
        default=1024,
        ge=512,
        le=4096,
        description="Target longest dimension for image processing"
    ),
    image_rotation: int = Form(
        default=0,
        description="Image rotation angle (0, 90, 180, 270)"
    )
):
    """
    Submit multiple files for asynchronous batch OCR processing.
    
    This endpoint is useful for large batches or when you don't want to wait for processing
    to complete. It returns a task ID that can be used to check processing status and
    retrieve results when complete.
    
    **Workflow:**
    1. Submit files with this endpoint → receive task_id
    2. Poll `/tasks/{task_id}` to check status
    3. When status is 'completed', get results from `/tasks/{task_id}/result`
    
    **File Limits:**
    - Maximum 10 files per batch request
    - Each file must meet individual size and format requirements
    
    **Returns:**
    - Task ID for status tracking
    - URLs for status checking and result retrieval
    - Estimated completion time based on file count
    """
    try:
        logger.info(f"Starting async batch processing for {len(files)} files")
        
        # Check batch size limit
        MAX_BATCH_SIZE = 10
        if len(files) > MAX_BATCH_SIZE:
            logger.warning(f"Batch size too large: {len(files)} > {MAX_BATCH_SIZE}")
            raise HTTPException(
                status_code=400,
                detail=f"Too many files in batch. Maximum {MAX_BATCH_SIZE} files allowed."
            )
        
        # Validate all files first and save temporarily
        temp_file_paths = []
        file_infos = []
        
        try:
            for file in files:
                try:
                    # Validate file
                    file_info = await file_handler.validate_upload_file(file)
                    file_infos.append(file_info)
                    
                    # Save file temporarily
                    temp_file_path = await file_handler.save_temp_file(file)
                    temp_file_paths.append(temp_file_path)
                    
                    logger.debug(f"File prepared for async batch: {file.filename}")
                    
                except Exception as e:
                    # Clean up any files saved so far
                    for temp_path in temp_file_paths:
                        try:
                            await file_handler.cleanup_temp_file(temp_path)
                        except:
                            pass
                    
                    if isinstance(e, ValueError):
                        raise HTTPException(status_code=400, detail=str(e))
                    else:
                        raise HTTPException(status_code=422, detail=f"File validation failed: {str(e)}")
            
            # Create task payload
            task_payload = {
                "file_paths": temp_file_paths,
                "file_names": [file.filename for file in files],
                "file_sizes": [info.get("size", 0) for info in file_infos],
                "options": {
                    "skip_cross_page_merge": skip_cross_page_merge,
                    "max_page_retries": max_page_retries,
                    "target_longest_image_dim": target_longest_image_dim,
                    "image_rotation": image_rotation
                }
            }
            
            # Submit task to queue with higher priority for batch processing
            try:
                task_id = await task_queue.submit_task("ocr_batch_files", task_payload, priority=1)
                logger.info(f"Batch task submitted for async processing: {task_id}")
            except Exception as e:
                logger.error(f"Failed to submit batch task: {e}")
                # Clean up temp files if task submission failed
                for temp_path in temp_file_paths:
                    try:
                        await file_handler.cleanup_temp_file(temp_path)
                    except:
                        pass
                raise HTTPException(status_code=503, detail="Task queue is currently unavailable")
            
            # Create response
            response = TaskSubmissionResponse(
                task_id=task_id,
                status="pending",
                estimated_completion_time=None,  # Will be set by task queue
                status_url=f"/api/v1/tasks/{task_id}",
                result_url=f"/api/v1/tasks/{task_id}/result"
            )
            
            logger.info(f"Async batch task created: {task_id} for {len(files)} files")
            return response
            
        except HTTPException:
            # Clean up temp files on HTTP exceptions
            for temp_path in temp_file_paths:
                try:
                    await file_handler.cleanup_temp_file(temp_path)
                except:
                    pass
            raise
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in async batch processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during batch task submission"
        )


# Register batch OCR task handler with the task queue
async def ocr_batch_files_handler(payload: dict) -> dict:
    """
    Task handler for batch file OCR processing.
    
    Args:
        payload: Task payload containing file paths and options
        
    Returns:
        Batch processing result dictionary
    """
    try:
        file_paths = payload["file_paths"]
        file_names = payload["file_names"]
        file_sizes = payload.get("file_sizes", [0] * len(file_paths))
        options_dict = payload["options"]
        
        # Create processing options
        options = EngineProcessOptions(
            skip_cross_page_merge=options_dict["skip_cross_page_merge"],
            max_page_retries=options_dict["max_page_retries"],
            target_longest_image_dim=options_dict["target_longest_image_dim"],
            image_rotation=options_dict["image_rotation"]
        )
        
        # Process files using OCR engine batch processing
        results = await ocr_engine.process_batch_files(file_paths, options)
        
        # Convert results to dictionary format
        result_dicts = []
        for i, result in enumerate(results):
            result_dict = {
                "success": result.success,
                "file_name": result.file_name,
                "file_size": file_sizes[i] if i < len(file_sizes) else 0,
                "num_pages": result.num_pages,
                "document_text": result.document_text,
                "page_texts": result.page_texts,
                "fallback_pages": result.fallback_pages,
                "processing_time": result.processing_time,
                "error_message": result.error_message
            }
            result_dicts.append(result_dict)
        
        # Calculate batch statistics
        successful_files = sum(1 for r in result_dicts if r["success"])
        failed_files = len(result_dicts) - successful_files
        total_processing_time = sum(r["processing_time"] for r in result_dicts)
        
        # Create batch result
        batch_result = {
            "total_files": len(file_paths),
            "successful_files": successful_files,
            "failed_files": failed_files,
            "results": result_dicts,
            "total_processing_time": total_processing_time
        }
        
        return batch_result
        
    finally:
        # Clean up temporary files
        try:
            if "file_paths" in payload:
                for file_path in payload["file_paths"]:
                    try:
                        await file_handler.cleanup_temp_file(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file in batch handler: {e}")
        except Exception as e:
            logger.warning(f"Error during batch cleanup: {e}")


# Register the task handlers
task_queue.register_task_handler("ocr_single_file", ocr_single_file_handler)
task_queue.register_task_handler("ocr_batch_files", ocr_batch_files_handler)